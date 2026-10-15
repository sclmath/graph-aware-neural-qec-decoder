"""Tests for the T8 OSD combination sweep (OSD-CS / OSD-lambda).

The sweep explores *which bits form a solvable basis* rather than reweighting
per-mechanism marginals. These tests pin the two properties that make it usable
as a decoder: every candidate is syndrome consistent, and the sweep never
returns a heavier correction than OSD-0 under its own objective.
"""

from __future__ import annotations

import numpy as np

from graph_qec.config import ExperimentConfig
from graph_qec.data_pipeline import generate_dataset
from graph_qec.decoders import BPDecoder, BPOSDDecoder, DEMSystem
from graph_qec.decoders.bp import _osd0_correction, _osd_correction
from graph_qec.m2_config import SUPPORTED_BENCHMARK_DECODERS


def _dataset(family: str, distance: int, rounds: int, model: str, p: float, shots: int):
    return generate_dataset(
        ExperimentConfig(
            name="t8",
            seed=20261014,
            family=family,
            distance=distance,
            rounds=rounds,
            noise_model=model,
            physical_error_rate=p,
            shots=shots,
        )
    )


def test_osd_cs_names_are_registered() -> None:
    assert {
        "bp_osd_cs",
        "bp_gnn_osd_cs",
        "bp_gnn_osd_cs_learned_order",
    } <= SUPPORTED_BENCHMARK_DECODERS


def test_combination_sweep_is_syndrome_consistent_and_never_heavier() -> None:
    dataset = _dataset("rotated_surface_code", 3, 3, "code_capacity", 0.02, 256)
    system = DEMSystem.from_detector_error_model(dataset.raw_dem)
    decoder = BPDecoder(dataset.raw_dem)
    prior_llr = decoder.prior_llr
    zero = np.zeros(system.num_errors, dtype=np.uint8)

    strictly_improved = 0
    for syndrome in dataset.detections:
        base, _ = _osd0_correction(system.check_matrix, syndrome, prior_llr, zero)
        swept, _ = _osd_correction(system.check_matrix, syndrome, prior_llr, zero, 4)

        for correction in (base, swept):
            residual = (system.check_matrix @ correction) % 2
            assert np.array_equal(residual, syndrome)

        base_weight = float(np.abs(prior_llr)[base.astype(bool)].sum())
        swept_weight = float(np.abs(prior_llr)[swept.astype(bool)].sum())
        assert swept_weight <= base_weight + 1e-9
        if swept_weight < base_weight - 1e-9:
            strictly_improved += 1

    # The sweep must actually find a lighter correction somewhere, otherwise
    # the assertions above would be vacuous.
    assert strictly_improved > 0


def test_order_zero_reproduces_classic_osd0() -> None:
    dataset = _dataset("repetition_code", 3, 3, "circuit_level", 0.01, 64)
    system = DEMSystem.from_detector_error_model(dataset.raw_dem)
    decoder = BPDecoder(dataset.raw_dem)
    prior_llr = decoder.prior_llr
    zeros = np.zeros((dataset.shots, system.num_errors), dtype=np.uint8)

    for shot in range(dataset.shots):
        expected, rank_a = _osd0_correction(
            system.check_matrix, dataset.detections[shot], prior_llr, zeros[shot]
        )
        actual, rank_b = _osd_correction(
            system.check_matrix, dataset.detections[shot], prior_llr, zeros[shot], 0
        )
        assert rank_a == rank_b
        assert np.array_equal(expected, actual)


def test_bposd_combination_sweep_decoder_is_syndrome_consistent() -> None:
    dataset = _dataset("rotated_surface_code", 3, 3, "code_capacity", 0.02, 256)
    system = DEMSystem.from_detector_error_model(dataset.raw_dem)

    for sweep in (0, 4):
        decoder = BPOSDDecoder(
            dataset.raw_dem,
            max_iterations=32,
            min_sum_scaling=0.75,
            combination_sweep_order=sweep,
            force_osd=True,
        )
        result = decoder.decode_batch(dataset.detections)
        assert result.corrections is not None
        residual = (system.check_matrix @ result.corrections.T) % 2
        assert np.array_equal(residual.T, dataset.detections)
        assert result.diagnostics["combination_sweep_order"] == sweep
