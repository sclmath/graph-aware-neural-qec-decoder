from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from graph_qec.benchmark import run_benchmark
from graph_qec.benchmark_config import BenchmarkConfig
from graph_qec.config import ExperimentConfig
from graph_qec.data_pipeline import GeneratedDataset, generate_dataset
from graph_qec.decoders import (
    BPDecoder,
    BPOSDDecoder,
    DEMSystem,
    MWPMDecoder,
    UnionFindDecoder,
)


@pytest.fixture(scope="module")
def dataset() -> GeneratedDataset:
    config = ExperimentConfig(
        name="m1_test",
        seed=20261003,
        family="repetition_code",
        distance=3,
        rounds=3,
        noise_model="circuit_level",
        physical_error_rate=0.01,
        shots=128,
    )
    return generate_dataset(config)


def test_dem_system_contains_hyperedges_and_priors(dataset: GeneratedDataset) -> None:
    system = DEMSystem.from_detector_error_model(dataset.raw_dem)

    assert system.check_matrix.shape == (8, 21)
    assert system.observable_matrix.shape == (1, 21)
    assert np.all((system.check_matrix == 0) | (system.check_matrix == 1))
    assert np.all((system.priors > 0.0) & (system.priors < 1.0))


def test_mwpm_and_union_find_decode_batches(dataset: GeneratedDataset) -> None:
    detections = dataset.detections
    for decoder in (
        MWPMDecoder(dataset.matching_dem),
        UnionFindDecoder(dataset.matching_dem),
    ):
        first = decoder.decode_batch(detections)
        second = decoder.decode_batch(detections)

        assert first.predictions.shape == (len(detections), 1)
        assert np.array_equal(first.predictions, second.predictions)
        assert first.corrections is None
        assert first.diagnostics["num_edges"] > 0

    union_find = UnionFindDecoder(dataset.matching_dem).decode_batch(detections)
    assert union_find.diagnostics["unresolved_shots"] == 0


def test_bp_and_osd_produce_explicit_syndrome_consistent_osd_corrections(
    dataset: GeneratedDataset,
) -> None:
    system = DEMSystem.from_detector_error_model(dataset.raw_dem)
    bp_result = BPDecoder(dataset.raw_dem).decode_batch(dataset.detections)
    osd_result = BPOSDDecoder(dataset.raw_dem).decode_batch(dataset.detections)

    assert bp_result.corrections is not None
    assert osd_result.corrections is not None
    assert bp_result.corrections.shape == (dataset.shots, system.num_errors)
    assert osd_result.corrections.shape == bp_result.corrections.shape

    osd_residual = (system.check_matrix @ osd_result.corrections.T) % 2
    assert np.array_equal(osd_residual.T, dataset.detections)
    assert osd_result.diagnostics["osd_shots"] >= 1
    assert osd_result.diagnostics["convergence_rate"] <= 1.0


def test_all_zero_syndrome_decodes_to_no_observable_flip(
    dataset: GeneratedDataset,
) -> None:
    zeros = np.zeros((4, dataset.raw_dem.num_detectors), dtype=np.uint8)
    for decoder in (
        MWPMDecoder(dataset.matching_dem),
        UnionFindDecoder(dataset.matching_dem),
        BPDecoder(dataset.raw_dem),
        BPOSDDecoder(dataset.raw_dem),
    ):
        result = decoder.decode_batch(zeros)
        assert not np.any(result.predictions)


def test_benchmark_config_json_round_trip() -> None:
    payload = {
        "schema_version": 1,
        "name": "round_trip",
        "experiment": {
            "name": "repetition",
            "seed": 7,
            "code": {
                "family": "repetition_code",
                "distance": 3,
                "rounds": 3,
            },
            "noise": {
                "model": "circuit_level",
                "physical_error_rate": 0.01,
            },
            "sampling": {"shots": 64},
        },
        "benchmark": {
            "decoders": ["mwpm", "union_find", "bp", "bp_osd"],
            "warmup_runs": 0,
            "timed_runs": 1,
            "max_shots": 32,
        },
        "decoder_parameters": {
            "bp": {"max_iterations": 16},
            "bp_osd": {"max_iterations": 16, "osd_order": 0},
        },
    }

    config = BenchmarkConfig.from_dict(payload)
    assert BenchmarkConfig.from_dict(config.to_dict()) == config
    assert config.sha256() == config.sha256()


def test_benchmark_runs_all_decoders(dataset: GeneratedDataset) -> None:
    config = BenchmarkConfig.from_dict(
        {
            "schema_version": 1,
            "name": "benchmark_smoke",
            "experiment": replace(dataset.config, shots=32).to_dict(),
            "benchmark": {
                "decoders": ["mwpm", "union_find", "bp", "bp_osd"],
                "warmup_runs": 0,
                "timed_runs": 1,
                "max_shots": 32,
            },
            "decoder_parameters": {
                "bp": {"max_iterations": 16},
                "bp_osd": {"max_iterations": 16, "osd_order": 0},
            },
        }
    )

    result = run_benchmark(dataset, config)

    assert result["stage"] == "M1"
    assert result["dataset"]["shots"] == 32
    assert [item["decoder"] for item in result["decoders"]] == [
        "mwpm",
        "union_find",
        "bp",
        "bp_osd",
    ]
    for item in result["decoders"]:
        assert 0.0 <= item["logical_error_rate"] <= 1.0
        assert item["latency"]["mean_total_seconds"] > 0.0
        assert item["latency"]["throughput_shots_per_second"] > 0.0
        assert item["memory"]["peak_python_bytes"] >= 0

    osd_result = result["decoders"][-1]
    assert osd_result["diagnostics"]["syndrome_consistency_rate"] == 1.0
