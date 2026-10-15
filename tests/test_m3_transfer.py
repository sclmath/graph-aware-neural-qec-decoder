"""Tests for the M3 transfer pipeline (checkpoint reuse across noise/code changes)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from graph_qec.m2_config import M2Config
from graph_qec.m2_pipeline import build_experiment_graph, generate_split, run_m2
from graph_qec.m3_pipeline import (
    TransferError,
    load_reweighting_checkpoint,
    run_transfer_evaluation,
    target_experiment,
)


def _tiny_config(**overrides) -> M2Config:
    payload = {
        "schema_version": 1,
        "name": "m3_test",
        "experiment": {
            "name": "repetition",
            "seed": 20261012,
            "code": {"family": "repetition_code", "distance": 3, "rounds": 3},
            "noise": {"model": "circuit_level", "physical_error_rate": 0.01},
            "sampling": {"shots": 128},
        },
        "splits": {
            "train_seeds": [11],
            "validation_seeds": [21],
            "test_seeds": [31],
            "train_shots": 256,
            "validation_shots": 256,
            "test_shots": 256,
        },
        "model": {"hidden_size": 8, "num_layers": 2, "dropout": 0.0},
        "training": {
            "epochs": 2,
            "batch_size": 128,
            "learning_rate": 0.002,
            "weight_decay": 0.0,
            "seed": 7,
            "max_grad_norm": 1.0,
            "torch_threads": 2,
        },
        "decoder": {
            "max_iterations": 32,
            "min_sum_scaling": 0.75,
            "damping": 0.0,
            "reweight_strengths": [0.0, 1.0],
        },
        "benchmark": {"decoders": ["mwpm", "bp", "bp_gnn"], "timed_runs": 1},
    }
    payload.update(overrides)
    return M2Config.from_dict(payload)


@pytest.fixture(scope="module")
def trained_checkpoint(tmp_path_factory) -> tuple[M2Config, object]:
    config = _tiny_config()
    artifact_dir = tmp_path_factory.mktemp("m3_checkpoint")
    run_m2(config, artifact_dir=artifact_dir)
    return config, artifact_dir / "model_state.pt"


def test_target_experiment_only_replaces_requested_axes() -> None:
    base = _tiny_config().experiment
    changed = target_experiment(base, physical_error_rate=0.003, distance=5)
    assert changed.physical_error_rate == 0.003
    assert changed.distance == 5
    assert changed.rounds == base.rounds
    assert changed.noise_model == base.noise_model
    assert changed.seed == base.seed


def test_transfer_across_physical_error_rate(trained_checkpoint) -> None:
    config, checkpoint = trained_checkpoint
    experiment = target_experiment(config.experiment, physical_error_rate=0.005)
    result = run_transfer_evaluation(
        config,
        checkpoint_path=checkpoint,
        experiment=experiment,
        benchmark_decoders=["mwpm", "bp", "bp_gnn", "bp_gnn_osd"],
        timed_runs=1,
    )

    assert result["stage"] == "M3-transfer"
    assert result["transfer"]["target_experiment"]["physical_error_rate"] == 0.005
    assert result["transfer"]["source_experiment"]["physical_error_rate"] == 0.01
    entries = {entry["decoder"]: entry for entry in result["decoders"]}
    assert set(entries) == {"mwpm", "bp", "bp_gnn", "bp_gnn_osd"}
    # The learned prior must still reach BP and OSD must restore consistency.
    assert entries["bp_gnn"]["diagnostics"]["prior_llr_override"] is True
    assert entries["bp_gnn_osd"]["diagnostics"]["prior_llr_override"] is True
    assert entries["bp_gnn_osd"]["syndrome_consistency_rate"] == 1.0
    for entry in result["decoders"]:
        assert 0.0 <= entry["logical_error_rate"] <= 1.0
    assert result["mechanism_prediction"]["test_log_loss"] > 0.0


def test_transfer_across_code_distance(trained_checkpoint) -> None:
    config, checkpoint = trained_checkpoint
    experiment = target_experiment(config.experiment, distance=5, rounds=5)
    result = run_transfer_evaluation(
        config,
        checkpoint_path=checkpoint,
        experiment=experiment,
        benchmark_decoders=["mwpm", "bp_gnn_osd"],
        timed_runs=1,
    )
    assert result["graph"]["num_detectors"] > 8
    assert result["transfer"]["target_experiment"]["distance"] == 5
    assert result["decoders"][1]["decoder"] == "bp_gnn_osd"


def test_incompatible_checkpoint_is_rejected(trained_checkpoint) -> None:
    config, checkpoint = trained_checkpoint
    mismatched = _tiny_config(model={"hidden_size": 16, "num_layers": 2, "dropout": 0.0})

    _, reference = generate_split(mismatched, mismatched.splits.test_seeds, 128)
    graph = build_experiment_graph(reference)

    with pytest.raises(TransferError, match="hidden_size"):
        load_reweighting_checkpoint(mismatched, graph, checkpoint)


def _load_script(name: str):
    path = Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_strength_recalibration_uses_target_validation_split(trained_checkpoint) -> None:
    """The recalibration script must re-select the strength on the target noise rate."""

    config, checkpoint = trained_checkpoint
    module = _load_script("m3_strength_recalibration")
    result = module.recalibrate(
        config,
        checkpoint,
        0.005,
        validation_shots=256,
        test_shots=256,
        timed_runs=1,
    )

    strengths = list(config.decoder.reweight_strengths)
    assert [item["strength"] for item in result["validation_sweep"]] == strengths
    assert result["selected_strength"] in strengths
    assert result["physical_error_rate"] == 0.005
    assert result["validation_shots"] == 256
    assert result["test_shots"] == 256

    entries = {entry["decoder"]: entry for entry in result["decoders"]}
    assert set(entries) == {
        "bp",
        "bp_gnn_recalibrated",
        "bp_gnn_osd_recalibrated",
    }
    assert entries["bp_gnn_osd_recalibrated"]["syndrome_consistency_rate"] == 1.0
    for entry in result["decoders"]:
        assert 0.0 <= entry["logical_error_rate"] <= 1.0


def test_osd_trigger_policy_endpoints(trained_checkpoint, tmp_path) -> None:
    """k=0 must reproduce the OSD fallback and a large k must reproduce pure BP."""

    config, checkpoint = trained_checkpoint
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config.to_dict()), encoding="utf-8")
    output = tmp_path / "policy.json"
    markdown = tmp_path / "policy.md"

    module = _load_script("m3_osd_trigger_policy")
    exit_code = module.main(
        [
            "--config",
            str(config_path),
            "--checkpoint",
            str(checkpoint),
            "--thresholds",
            "0",
            "1000000",
            "--output",
            str(output),
            "--markdown",
            str(markdown),
        ]
    )
    assert exit_code == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    policy = {item["threshold"]: item for item in payload["policy"]}
    assert set(policy) == {0, 1000000}
    # Unconditional OSD fallback is syndrome-consistent by construction.
    assert policy[0]["syndrome_consistency_rate"] == 1.0
    assert policy[0]["osd_shots"] == payload["non_converged_shots"]
    # A large threshold never runs OSD, so it keeps BP's (possibly inconsistent) output.
    assert policy[1000000]["osd_shots"] == 0
    assert policy[1000000]["syndrome_consistency_rate"] <= 1.0
    assert markdown.exists()
