"""Tests for the M2 graph features, GNN model, and reweighting pipeline."""

from __future__ import annotations

import numpy as np
import pytest
import stim

from graph_qec.config import ExperimentConfig
from graph_qec.decoders import BPDecoder, DEMSystem
from graph_qec.graph_features import (
    CHECK_FEATURE_NAMES,
    EDGE_FEATURE_NAMES,
    VARIABLE_FEATURE_NAMES,
    build_graph_tensor,
    prior_log_odds,
)
from graph_qec.m2_config import M2Config
from graph_qec.m2_pipeline import (
    build_experiment_graph,
    combined_logits,
    generate_split,
    learned_logits_to_llr,
    run_m2,
)
from graph_qec.models import BipartiteSyndromeGNN, graph_to_tensors, predict_logits


def _experiment(distance: int = 3, shots: int = 64, seed: int = 5) -> ExperimentConfig:
    return ExperimentConfig(
        name="repetition",
        seed=seed,
        family="repetition_code",
        distance=distance,
        rounds=distance,
        noise_model="circuit_level",
        physical_error_rate=0.01,
        shots=shots,
    )


def _smoke_config_dict() -> dict:
    return {
        "schema_version": 1,
        "name": "m2_test",
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
            "reweight_strengths": [0.0, 0.5, 1.0],
        },
        "benchmark": {"decoders": ["mwpm", "bp", "bp_gnn"]},
    }


def test_graph_tensor_shapes_and_determinism() -> None:
    experiment = _experiment()
    circuit = stim.Circuit.generated(
        "repetition_code:memory",
        distance=experiment.distance,
        rounds=experiment.rounds,
        after_clifford_depolarization=0.01,
        before_round_data_depolarization=0.01,
        before_measure_flip_probability=0.01,
        after_reset_flip_probability=0.01,
    )
    dem = circuit.detector_error_model(decompose_errors=False)
    system = DEMSystem.from_detector_error_model(dem)
    coordinates = circuit.get_detector_coordinates()

    graph = build_graph_tensor(system, detector_coordinates=coordinates)
    repeat = build_graph_tensor(system, detector_coordinates=coordinates)

    assert graph.num_checks == system.num_detectors
    assert graph.num_variables == system.num_errors
    assert graph.num_edges == int(system.check_matrix.sum())
    assert graph.variable_feature_names == VARIABLE_FEATURE_NAMES
    assert graph.check_feature_names == CHECK_FEATURE_NAMES
    assert graph.edge_feature_names == EDGE_FEATURE_NAMES
    assert graph.variable_features.shape == (graph.num_variables, len(VARIABLE_FEATURE_NAMES))
    assert graph.check_features.shape == (graph.num_checks, len(CHECK_FEATURE_NAMES))
    assert graph.edge_features.shape == (graph.num_edges, len(EDGE_FEATURE_NAMES))
    assert np.array_equal(graph.variable_features, repeat.variable_features)
    assert np.array_equal(graph.edge_features, repeat.edge_features)
    assert np.all(np.isfinite(graph.variable_features))
    assert np.all(np.isfinite(graph.edge_features))


def test_prior_log_odds_are_finite_and_clipped() -> None:
    llr = prior_log_odds(np.array([1e-9, 0.01, 0.5, 1.0 - 1e-9]))
    assert np.all(np.isfinite(llr))
    assert llr[0] > 0.0
    assert llr[2] == pytest.approx(0.0, abs=1e-9)
    assert llr[3] < 0.0
    assert np.max(np.abs(llr)) <= 30.0


def test_combined_logits_interpolates_between_prior_and_model() -> None:
    base = np.array([1.0, -2.0, 0.5])
    learned = np.array([3.0, 0.0, -0.5])
    learned_llr = learned_logits_to_llr(learned)
    assert np.array_equal(learned_llr, -learned)
    assert np.array_equal(combined_logits(base, learned, 0.0), base)
    assert np.array_equal(combined_logits(base, learned, 1.0), learned_llr)
    midpoint = combined_logits(base, learned, 0.5)
    assert np.allclose(midpoint, 0.5 * (base + learned_llr))
    with pytest.raises(ValueError):
        combined_logits(base, learned, 1.5)


def test_learned_logits_sign_convention_matches_bp_priors() -> None:
    """Model log-odds are inverted relative to the BP LLR convention."""

    fired = np.array([6.0, 6.0])   # model is confident the mechanism fired
    quiet = np.array([-6.0, -6.0])  # model is confident nothing happened
    assert np.all(learned_logits_to_llr(fired) < 0.0)
    assert np.all(learned_logits_to_llr(quiet) > 0.0)


def test_bp_accepts_prior_llr_override() -> None:
    experiment = _experiment(shots=32)
    circuit = stim.Circuit.generated(
        "repetition_code:memory",
        distance=experiment.distance,
        rounds=experiment.rounds,
        after_clifford_depolarization=0.01,
        before_round_data_depolarization=0.01,
        before_measure_flip_probability=0.01,
        after_reset_flip_probability=0.01,
    )
    dem = circuit.detector_error_model(decompose_errors=False)
    sampler = dem.compile_sampler(seed=experiment.seed)
    detections, _, _ = sampler.sample(experiment.shots, return_errors=True)
    detections = np.ascontiguousarray(detections, dtype=np.uint8)

    decoder = BPDecoder(dem, max_iterations=16)
    baseline = decoder.decode_batch(detections)
    override = decoder.decode_batch(detections, prior_llr=np.tile(decoder.prior_llr, (detections.shape[0], 1)))
    assert np.array_equal(baseline.predictions, override.predictions)
    assert override.diagnostics["prior_llr_override"] is True
    assert baseline.diagnostics["prior_llr_override"] is False

    with pytest.raises(ValueError):
        decoder.decode_batch(detections, prior_llr=np.zeros((detections.shape[0] + 1, decoder.system.num_errors)))


def test_forced_osd_and_ordering_override() -> None:
    experiment = _experiment(shots=64)
    circuit = stim.Circuit.generated(
        "repetition_code:memory",
        distance=experiment.distance,
        rounds=experiment.rounds,
        after_clifford_depolarization=0.01,
        before_round_data_depolarization=0.01,
        before_measure_flip_probability=0.01,
        after_reset_flip_probability=0.01,
    )
    dem = circuit.detector_error_model(decompose_errors=False)
    sampler = dem.compile_sampler(seed=experiment.seed)
    detections, _, _ = sampler.sample(experiment.shots, return_errors=True)
    detections = np.ascontiguousarray(detections, dtype=np.uint8)

    from graph_qec.decoders import BPOSDDecoder

    decoder = BPOSDDecoder(dem, max_iterations=8, force_osd=True)
    result = decoder.decode_batch(detections, osd_ordering_llr=np.zeros_like(
        np.tile(decoder.prior_llr, (detections.shape[0], 1))
    ))
    assert result.diagnostics["forced_osd"] is True
    assert result.diagnostics["osd_ordering_override"] is True
    system = decoder.system
    residual = (system.check_matrix.astype(np.int64) @ result.corrections.T.astype(np.int64)) % 2
    assert np.all(residual.T == detections)

    with pytest.raises(ValueError):
        decoder.decode_batch(detections, osd_ordering_llr=np.zeros((detections.shape[0] + 1, system.num_errors)))


def test_m2_config_round_trip_and_validation() -> None:
    payload = _smoke_config_dict()
    config = M2Config.from_dict(payload)
    assert config.to_dict()["benchmark"]["decoders"] == ["mwpm", "bp", "bp_gnn"]
    assert M2Config.from_dict(config.to_dict()).sha256() == config.sha256()

    overlapping = _smoke_config_dict()
    overlapping["splits"]["validation_seeds"] = [11]
    with pytest.raises(ValueError):
        M2Config.from_dict(overlapping)

    missing_baseline = _smoke_config_dict()
    missing_baseline["decoder"]["reweight_strengths"] = [0.5, 1.0]
    with pytest.raises(ValueError):
        M2Config.from_dict(missing_baseline)

    bad_decoder = _smoke_config_dict()
    bad_decoder["benchmark"]["decoders"] = ["not_a_decoder"]
    with pytest.raises(ValueError):
        M2Config.from_dict(bad_decoder)


def test_model_forward_and_predict_logits() -> None:
    experiment = _experiment(shots=16)
    circuit = stim.Circuit.generated(
        "repetition_code:memory",
        distance=experiment.distance,
        rounds=experiment.rounds,
        after_clifford_depolarization=0.01,
        before_round_data_depolarization=0.01,
        before_measure_flip_probability=0.01,
        after_reset_flip_probability=0.01,
    )
    graph = build_graph_tensor(
        DEMSystem.from_detector_error_model(circuit.detector_error_model(decompose_errors=False)),
        detector_coordinates=circuit.get_detector_coordinates(),
    )
    tensors = graph_to_tensors(graph)
    model = BipartiteSyndromeGNN(
        variable_feature_dim=graph.variable_feature_dim,
        check_feature_dim=graph.check_feature_dim,
        edge_feature_dim=graph.edge_feature_dim,
        hidden_size=8,
        num_layers=2,
    )
    detections = np.zeros((16, graph.num_checks), dtype=np.uint8)
    logits = predict_logits(model, tensors, detections, batch_size=8)
    assert logits.shape == (16, graph.num_variables)
    assert np.all(np.isfinite(logits))


def test_m2_pipeline_smoke() -> None:
    config = M2Config.from_dict(_smoke_config_dict())
    result = run_m2(config)

    assert result["stage"] == "M2"
    assert result["graph"]["num_errors"] > 0
    assert result["splits"]["test"]["shots"] == 256
    assert result["selected_reweight_strength"] in (0.0, 0.5, 1.0)
    assert len(result["validation_selection"]) == 3
    assert result["mechanism_prediction"]["test_binary_accuracy"] > 0.5
    assert result["training"]["parameters"] > 0

    decoder_names = {entry["decoder"] for entry in result["decoders"]}
    assert decoder_names == {"mwpm", "bp", "bp_gnn"}
    for entry in result["decoders"]:
        assert 0.0 <= entry["logical_error_rate"] <= 1.0
        assert entry["latency"]["mean_per_shot_microseconds"] > 0.0
    bp_entry = next(entry for entry in result["decoders"] if entry["decoder"] == "bp")
    gnn_entry = next(entry for entry in result["decoders"] if entry["decoder"] == "bp_gnn")
    assert bp_entry["latency"]["mean_per_shot_microseconds"] > 0.0
    assert gnn_entry["latency"]["mean_per_shot_microseconds"] > 0.0
    # NOTE: this test used to also assert a *latency ratio* between bp and
    # bp_gnn. Wall-clock ratios are not reproducible on a machine that is busy
    # (the T6 grid and the T9 ablation run concurrently with pytest), and the
    # assertion says nothing about correctness. Latency comparisons live in
    # results/m5/ENGINEERING_TABLE.md, which is generated by
    # scripts/engineering_table.py under controlled conditions.
    assert gnn_entry["syndrome_consistency_rate"] is not None

def test_m3_bp_gnn_osd_semantics() -> None:
    """M3: ``bp_gnn_osd`` must combine the learned BP prior with OSD-0 fallback."""

    payload = _smoke_config_dict()
    payload["name"] = "m3_test"
    payload["benchmark"]["decoders"] = [
        "bp",
        "bp_osd",
        "bp_gnn",
        "bp_gnn_osd",
        "bp_gnn_osd_learned_order",
        "osd_gnn",
    ]
    config = M2Config.from_dict(payload)
    result = run_m2(config)
    entries = {entry["decoder"]: entry for entry in result["decoders"]}
    assert set(entries) == set(payload["benchmark"]["decoders"])

    # The learned posterior reaches BP as a prior for every bp_gnn* variant.
    for name in ("bp_gnn", "bp_gnn_osd", "bp_gnn_osd_learned_order"):
        assert entries[name]["diagnostics"]["prior_llr_override"] is True
    assert entries["bp"]["diagnostics"]["prior_llr_override"] is False
    assert entries["bp_osd"]["diagnostics"]["prior_llr_override"] is False

    # OSD ordering source is what separates the two bp_gnn_osd variants.
    assert entries["bp_gnn_osd"]["diagnostics"]["osd_ordering_override"] is False
    assert entries["bp_gnn_osd_learned_order"]["diagnostics"]["osd_ordering_override"] is True

    # OSD runs only as a fallback, never forced, for the bp_gnn_osd variants.
    assert entries["bp_gnn_osd"]["diagnostics"]["forced_osd"] is False
    assert entries["bp_gnn_osd_learned_order"]["diagnostics"]["forced_osd"] is False
    assert entries["osd_gnn"]["diagnostics"]["forced_osd"] is True

    # The OSD fallback makes every correction syndrome-consistent by construction.
    assert entries["bp_gnn_osd"]["syndrome_consistency_rate"] == 1.0
    assert entries["bp_gnn_osd_learned_order"]["syndrome_consistency_rate"] == 1.0
