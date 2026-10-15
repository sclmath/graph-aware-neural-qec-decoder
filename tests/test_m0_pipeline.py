from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import stim

from graph_qec.circuits import build_repetition_circuit
from graph_qec.config import ExperimentConfig
from graph_qec.data_pipeline import (
    generate_dataset,
    load_manifest,
    save_dataset,
    verify_manifest,
)


def make_config(**overrides: object) -> ExperimentConfig:
    values: dict[str, object] = {
        "name": "test_repetition",
        "seed": 12345,
        "family": "repetition_code",
        "distance": 3,
        "rounds": 3,
        "noise_model": "code_capacity",
        "physical_error_rate": 0.01,
        "shots": 128,
    }
    values.update(overrides)
    return ExperimentConfig(**values)  # type: ignore[arg-type]


def test_config_rejects_invalid_probability() -> None:
    with pytest.raises(ValueError, match="physical_error_rate"):
        make_config(physical_error_rate=0.0)


def test_repetition_circuit_has_expected_dimensions() -> None:
    config = make_config()
    circuit = build_repetition_circuit(config)

    assert circuit.num_detectors == (config.distance - 1) * (config.rounds + 1)
    assert circuit.num_observables == 1
    assert circuit.num_qubits == 2 * config.distance - 1


def test_sampling_is_deterministic_and_mechanism_labels_exist() -> None:
    config = make_config()
    first = generate_dataset(config)
    second = generate_dataset(config)

    np.testing.assert_array_equal(first.detections, second.detections)
    np.testing.assert_array_equal(first.observables, second.observables)
    np.testing.assert_array_equal(
        first.error_mechanisms, second.error_mechanisms
    )
    assert first.error_mechanisms.shape == (
        config.shots,
        first.raw_dem.num_errors,
    )


def test_saved_dataset_round_trip_and_hashes(tmp_path: Path) -> None:
    config = make_config(shots=64)
    dataset = generate_dataset(config)
    artifact_dir = tmp_path / "artifact"
    manifest = save_dataset(dataset, artifact_dir)
    verify_manifest(artifact_dir)

    loaded = load_manifest(artifact_dir)
    assert loaded == manifest
    assert manifest["stage"] == "M0"
    assert manifest["samples"]["shots"] == 64
    assert manifest["pymatching_smoke"]["decoded_shots"] == 64


@pytest.mark.parametrize("noise_model", ["code_capacity", "circuit_level"])
def test_pymatching_accepts_decomposed_dem(noise_model: str) -> None:
    config = make_config(
        noise_model=noise_model,
        physical_error_rate=0.03,
        shots=256,
    )
    dataset = generate_dataset(config)

    assert isinstance(dataset.matching_dem, stim.DetectorErrorModel)
    assert dataset.matching_num_edges > 0
    assert 0 <= dataset.logical_errors <= dataset.shots


def test_config_json_round_trip() -> None:
    config = make_config()
    payload = json.loads(config.canonical_json())
    restored = ExperimentConfig.from_dict(payload)
    assert restored == config
