"""Tests for the M4 HGP construction, DEM generation and pipeline."""

from __future__ import annotations

import numpy as np
import pytest

from graph_qec.codes.hgp import (
    build_hgp_code,
    gf2_inverse,
    gf2_null_space,
    gf2_rank,
    hamming_classical_code,
    repetition_classical_code,
    small_hgp_codes,
)
from graph_qec.decoders import DEMSystem
from graph_qec.m2_config import M2Config
from graph_qec.m4_pipeline import build_reference, generate_dem_split, run_m4


@pytest.mark.parametrize(
    "family,qubits,k_value,x_checks",
    [("hgp_rep3x3", 13, 1, 6), ("hgp_hamming7x7", 58, 16, 21)],
)
def test_hgp_code_parameters(family: str, qubits: int, k_value: int, x_checks: int) -> None:
    code = small_hgp_codes()[family]

    assert code.num_qubits == qubits
    assert code.k == k_value
    assert code.num_x_checks == x_checks
    assert code.num_z_checks == x_checks
    assert code.num_detectors == 2 * x_checks
    code.check_orthogonality()
    pairing = code.logical_pairing()
    assert np.array_equal(pairing, np.eye(k_value, dtype=np.int64))
    # A logical X must commute with every Z-check, and vice versa.
    assert not ((code.logical_x.astype(np.int64) @ code.hz.T.astype(np.int64)) % 2).any()
    assert not ((code.logical_z.astype(np.int64) @ code.hx.T.astype(np.int64)) % 2).any()


def test_gf2_helpers() -> None:
    assert gf2_rank(np.eye(4, dtype=np.uint8)) == 4
    # [1 1] has rank 1 and a one-dimensional null space spanned by (1, 1).
    assert gf2_rank(np.array([[1, 1]], dtype=np.uint8)) == 1
    null = gf2_null_space(np.array([[1, 1, 1]], dtype=np.uint8))
    assert null.shape == (2, 3)
    assert not ((np.array([[1, 1, 1]], dtype=np.uint8) @ null.T) % 2).any()

    matrix = np.array([[1, 1], [0, 1]], dtype=np.uint8)
    inverse = gf2_inverse(matrix)
    assert np.array_equal((matrix @ inverse) % 2, np.eye(2, dtype=np.uint8))
    with pytest.raises(ValueError):
        gf2_inverse(np.array([[1, 1], [1, 1]], dtype=np.uint8))


def test_hgp_detector_error_model_matches_the_check_matrices() -> None:
    code = small_hgp_codes()["hgp_rep3x3"]
    dem = code.detector_error_model(0.06)
    system = DEMSystem.from_detector_error_model(dem)

    assert dem.num_errors == 3 * code.num_qubits
    assert dem.num_detectors == code.num_detectors
    assert dem.num_observables == 2 * code.k
    assert np.allclose(system.priors, 0.02)  # p / 3 with p = 0.06

    # Z-error mechanisms (index 2 of each qubit triple) flip X-checks only, and
    # X-error mechanisms (index 0) flip Z-checks only.
    for qubit in range(code.num_qubits):
        z_column = system.check_matrix[:, 3 * qubit + 2]
        x_column = system.check_matrix[:, 3 * qubit + 0]
        assert np.array_equal(z_column[: code.num_x_checks], code.hx[:, qubit])
        assert not z_column[code.num_x_checks :].any()
        assert not x_column[: code.num_x_checks].any()
        assert np.array_equal(x_column[code.num_x_checks :], code.hz[:, qubit])


def test_hgp_sampling_matches_the_error_model() -> None:
    config = M2Config.from_dict(_smoke_config_dict())
    reference = build_reference(config)
    system = DEMSystem.from_detector_error_model(reference.raw_dem)

    split = generate_dem_split(reference, system.priors, [5], 512)
    assert split.detections.shape == (512, system.num_detectors)
    assert split.observables.shape == (512, system.num_observables)
    assert split.error_mechanisms.shape == (512, system.num_errors)

    # Syndrome and observables follow from the sampled mechanisms by construction.
    expected_syndrome = (
        system.check_matrix.astype(np.int64) @ split.error_mechanisms.T.astype(np.int64)
    ) % 2
    assert np.array_equal(expected_syndrome.T.astype(np.uint8), split.detections)

    # Sampling must be reproducible for a fixed seed.
    repeat = generate_dem_split(reference, system.priors, [5], 512)
    assert np.array_equal(split.detections, repeat.detections)


def _smoke_config_dict() -> dict:
    return {
        "schema_version": 1,
        "name": "m4_test",
        "experiment": {
            "name": "hgp",
            "seed": 20261013,
            "code": {"family": "hgp_rep3x3", "distance": 3, "rounds": 1},
            "noise": {"model": "code_capacity", "physical_error_rate": 0.06},
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
        "benchmark": {"decoders": ["bp", "bp_gnn"], "timed_runs": 1},
    }


def test_m4_pipeline_smoke() -> None:
    config = M2Config.from_dict(_smoke_config_dict())
    result = run_m4(config)

    assert result["stage"] == "M4"
    assert result["code"]["num_qubits"] == 13
    assert result["code"]["k"] == 1
    assert result["graph"]["num_detectors"] == 12
    assert len(result["validation_selection"]) == 3
    decoder_names = {entry["decoder"] for entry in result["decoders"]}
    assert decoder_names == {"bp", "bp_gnn"}
    for entry in result["decoders"]:
        assert 0.0 <= entry["logical_error_rate"] <= 1.0
        assert entry["latency"]["mean_per_shot_microseconds"] > 0.0
    assert result["mechanism_prediction"]["test_binary_accuracy"] > 0.5


def test_circuit_families_reject_dem_level_codes() -> None:
    from graph_qec.circuits import build_circuit
    from graph_qec.config import ExperimentConfig

    config = ExperimentConfig(
        name="hgp", seed=1, family="hgp_rep3x3", distance=3, rounds=1,
        noise_model="code_capacity", physical_error_rate=0.05, shots=16,
    )
    with pytest.raises(ValueError, match="detector-error-model-level"):
        build_circuit(config)


def test_hgp_code_rejects_non_dem_level_families() -> None:
    config = M2Config.from_dict(
        {**_smoke_config_dict(), "experiment": {
            **_smoke_config_dict()["experiment"],
            "code": {"family": "repetition_code", "distance": 3, "rounds": 3},
        }}
    )
    with pytest.raises(ValueError):
        build_reference(config)
