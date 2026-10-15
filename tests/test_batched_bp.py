"""Equivalence and semantics tests for the batched min-sum BP engine.

The engine is a shot-vectorized rewrite of ``BPDecoder._decode_shot``. The two
must agree on every decoding decision; log-likelihood ratios may differ only by
floating-point reassociation (observed at the 1e-15 level when checks have high
degree, because NumPy segment sums reduce in a different order).
"""

from __future__ import annotations

import numpy as np
import pytest

from graph_qec.config import ExperimentConfig
from graph_qec.data_pipeline import generate_dataset
from graph_qec.decoders import BPDecoder, BPOSDDecoder
from graph_qec.decoders.bp_engine import BatchedMinSumBP


def _dataset(family: str, distance: int = 3, rounds: int = 3, p: float = 0.01, shots: int = 96):
    config = ExperimentConfig(
        name="batched_bp_test",
        seed=11,
        family=family,
        distance=distance,
        rounds=rounds,
        noise_model="circuit_level",
        physical_error_rate=p,
        shots=shots,
    )
    return generate_dataset(config)


def _decoder(dataset, **kwargs) -> BPDecoder:
    return BPDecoder(dataset.raw_dem, max_iterations=32, min_sum_scaling=0.75, **kwargs)


@pytest.mark.parametrize("family", ["repetition_code", "rotated_surface_code"])
def test_batched_engine_matches_scalar_reference(family: str) -> None:
    dataset = _dataset(family)
    decoder = _decoder(dataset)
    output = decoder._engine().decode(dataset.detections)

    assert output.iterations.shape == (dataset.shots,)
    for shot in range(dataset.shots):
        state = decoder._decode_shot(dataset.detections[shot])
        assert np.array_equal(state.correction, output.corrections[shot])
        assert state.iterations == output.iterations[shot]
        assert bool(state.converged) == bool(output.converged[shot])
        assert state.syndrome_distance == output.syndrome_distance[shot]
        assert np.allclose(state.posterior_llr, output.posterior_llr[shot], atol=1e-12)


def test_batched_engine_matches_scalar_with_prior_override() -> None:
    dataset = _dataset("repetition_code")
    decoder = _decoder(dataset)
    rng = np.random.default_rng(3)
    priors = decoder.prior_llr[None, :] + rng.normal(
        scale=0.25, size=(dataset.shots, decoder.system.num_errors)
    )

    output = decoder._engine().decode(dataset.detections, priors)
    for shot in range(dataset.shots):
        state = decoder._decode_shot(dataset.detections[shot], priors[shot])
        assert np.array_equal(state.correction, output.corrections[shot])
        assert state.iterations == output.iterations[shot]
        assert bool(state.converged) == bool(output.converged[shot])


def test_batched_engine_handles_zero_syndrome_without_iterations() -> None:
    dataset = _dataset("repetition_code", shots=8)
    decoder = _decoder(dataset)
    zero = np.zeros_like(dataset.detections[:3])
    output = decoder._engine().decode(zero)

    assert np.all(output.converged)
    assert np.all(output.iterations == 0)
    assert np.all(output.syndrome_distance == 0)
    assert not output.corrections.any()


def test_check_update_excludes_the_variable_itself() -> None:
    """The message to a variable must use the minimum magnitude of the *others*."""

    check_matrix = np.array([[1, 1, 1]], dtype=np.uint8)
    engine = BatchedMinSumBP(
        check_matrix, np.full(3, 0.1), max_iterations=4, min_sum_scaling=1.0
    )
    # Magnitudes 1.0, 2.0, 4.0 with mixed signs, all fed as variable-to-check.
    message_v2c = np.array([[1.0, -2.0, 4.0]])
    message_c2v = np.zeros((1, engine.num_edges))
    engine._check_update(np.zeros((1, 1), dtype=np.uint8), message_v2c, message_c2v)

    magnitudes = np.abs(message_c2v[0])
    # base sign is +1; excluding variable j leaves min of the others, so the
    # largest incoming magnitude (4.0) must not leak back into its own message.
    assert magnitudes[0] == pytest.approx(2.0)
    assert magnitudes[1] == pytest.approx(1.0)
    assert magnitudes[2] == pytest.approx(1.0)


def test_degree_one_check_uses_the_capped_message() -> None:
    check_matrix = np.array([[1, 0], [0, 1]], dtype=np.uint8)
    engine = BatchedMinSumBP(
        check_matrix, np.full(2, 0.1), max_iterations=4, min_sum_scaling=1.0
    )
    message_v2c = np.array([[3.0, -3.0]])
    message_c2v = np.zeros((1, engine.num_edges))
    engine._check_update(np.array([[1, 0]], dtype=np.uint8), message_v2c, message_c2v)

    # Check 0 is violated with a positive incoming message -> -20; check 1 is
    # satisfied but its single incoming message is negative -> also -20.
    assert message_c2v[0, 0] == pytest.approx(-20.0)
    assert message_c2v[0, 1] == pytest.approx(-20.0)


def test_batched_osd_fallback_restores_syndrome_consistency() -> None:
    dataset = _dataset("rotated_surface_code", shots=64)
    decoder = BPOSDDecoder(dataset.raw_dem, max_iterations=32, min_sum_scaling=0.75, osd_order=0)
    result = decoder.decode_batch(dataset.detections)

    residual = (
        decoder.system.check_matrix.astype(np.int64) @ result.corrections.T.astype(np.int64)
    ) % 2
    assert np.array_equal(residual.T.astype(np.uint8), dataset.detections)
    assert result.diagnostics["osd_shots"] >= 0
    assert result.diagnostics["engine"] == "batched_min_sum"
