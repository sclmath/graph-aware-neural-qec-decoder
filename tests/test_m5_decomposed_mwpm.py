"""Tests for the decompose-preserving learned-posterior -> MWPM pipeline."""

from __future__ import annotations

import numpy as np
import pytest
import stim

from graph_qec.config import ExperimentConfig
from graph_qec.data_pipeline import generate_dataset
from graph_qec.decoders import MWPMDecoder
from graph_qec.m5 import (
    collapse_to_instructions,
    error_instructions,
    log_odds_to_probabilities,
    map_decomposed_to_raw,
    matching_from_probabilities,
    rewrite_probabilities,
)


@pytest.fixture(scope="module")
def code_capacity_dataset():
    config = ExperimentConfig(
        name="m5-cc", seed=20261014, family="rotated_surface_code", distance=3,
        rounds=3, noise_model="code_capacity", physical_error_rate=0.05, shots=512,
    )
    return generate_dataset(config)


def test_llr_probability_convention_matches_prior_log_odds():
    from graph_qec.graph_features import prior_log_odds

    priors = np.array([1e-4, 0.01, 0.05, 0.4])
    recovered = log_odds_to_probabilities(prior_log_odds(priors))
    assert np.allclose(recovered, priors, atol=1e-12)


def test_rewrite_preserves_instruction_structure(code_capacity_dataset):
    matching_dem = code_capacity_dataset.matching_dem
    original = error_instructions(matching_dem)
    rebuilt_dem = rewrite_probabilities(matching_dem, np.full(len(original), 0.01))
    rebuilt = error_instructions(rebuilt_dem)

    assert len(rebuilt) == len(original)
    assert rebuilt_dem.num_detectors == matching_dem.num_detectors
    assert rebuilt_dem.num_observables == matching_dem.num_observables
    for before, after in zip(original, rebuilt):
        assert before.detectors == after.detectors
        assert before.observables == after.observables
        assert before.pieces == after.pieces
        assert after.probability == pytest.approx(0.01)


def test_rewrite_rejects_wrong_probability_count(code_capacity_dataset):
    dem = code_capacity_dataset.matching_dem
    with pytest.raises(ValueError):
        rewrite_probabilities(dem, np.full(3, 0.1))


def test_identity_rewrite_reproduces_baseline_mwpm(code_capacity_dataset):
    dataset = code_capacity_dataset
    priors = np.array([item.probability for item in error_instructions(dataset.matching_dem)])
    baseline = MWPMDecoder(dataset.matching_dem)
    rebuilt = matching_from_probabilities(dataset.matching_dem, priors)

    baseline_result = baseline.decode_batch(dataset.detections)
    rebuilt_predictions = rebuilt.decode_batch(dataset.detections)

    assert rebuilt.num_edges == baseline_result.diagnostics["num_edges"]
    assert np.array_equal(baseline_result.predictions, rebuilt_predictions)


def test_mapping_is_unique_on_code_capacity_surface_code(code_capacity_dataset):
    parents, stats = map_decomposed_to_raw(
        code_capacity_dataset.raw_dem, code_capacity_dataset.matching_dem
    )
    assert stats["unmapped"] == 0
    assert stats["ambiguous"] == 0
    assert stats["unique_fraction"] == 1.0
    assert np.all(parents >= 0)


def test_mapped_priors_reproduce_baseline_mwpm(code_capacity_dataset):
    dataset = code_capacity_dataset
    decomposed = error_instructions(dataset.matching_dem)
    decomposed_priors = np.array([item.probability for item in decomposed])
    raw_priors = np.array(
        [item.probability for item in error_instructions(dataset.raw_dem)]
    )
    parents, _ = map_decomposed_to_raw(dataset.raw_dem, dataset.matching_dem)
    collapsed = collapse_to_instructions(
        parents, raw_priors, fallback=decomposed_priors
    )[0]

    baseline = MWPMDecoder(dataset.matching_dem).decode_batch(dataset.detections)
    mapped = matching_from_probabilities(dataset.matching_dem, collapsed)
    mapped_predictions = mapped.decode_batch(dataset.detections)
    assert np.array_equal(baseline.predictions, mapped_predictions)


def test_naive_raw_hyperedges_change_the_matching_graph(code_capacity_dataset):
    """Reproduces the M5 section-5 structural bug: rebuilding from the raw DEM
    yields a strictly denser matching graph than Stim's decomposition."""

    dataset = code_capacity_dataset
    raw_priors = np.array(
        [item.probability for item in error_instructions(dataset.raw_dem)]
    )
    naive = matching_from_probabilities(dataset.raw_dem, raw_priors)
    baseline_edges = MWPMDecoder(dataset.matching_dem).decode_batch(
        dataset.detections
    ).diagnostics["num_edges"]
    assert naive.num_edges > baseline_edges


def test_collapse_uses_fallback_for_unmapped_instructions():
    parents = np.array([1, -1, 0], dtype=np.int64)
    values = np.array([[0.1, 0.2, 0.3]])
    fallback = np.array([9.0, 9.0, 9.0])
    collapsed = collapse_to_instructions(parents, values, fallback=fallback)
    assert collapsed.shape == (1, 3)
    assert collapsed[0, 0] == pytest.approx(0.2)
    assert collapsed[0, 1] == pytest.approx(9.0)
    assert collapsed[0, 2] == pytest.approx(0.1)


def test_collapse_broadcasts_single_shot_vectors():
    parents = np.array([0, 1], dtype=np.int64)
    fallback = np.array([0.5, 0.5])
    collapsed = collapse_to_instructions(parents, np.array([1e-3, 2e-3]), fallback=fallback)
    assert collapsed.shape == (1, 2)
    assert collapsed[0, 1] == pytest.approx(2e-3)


def test_error_instructions_keeps_separators(code_capacity_dataset):
    decomposed = error_instructions(code_capacity_dataset.matching_dem)
    assert any(item.is_decomposed for item in decomposed)
    for item in decomposed:
        flat = [detector for piece in item.pieces for detector in piece]
        assert sorted(flat) == list(item.detectors)



def test_relative_shift_with_zero_shift_reproduces_priors():
    from graph_qec.m5 import apply_relative_shift

    priors = np.array([1e-4, 0.001, 0.02, 0.2])
    parents = np.array([0, 1, 2, 3])
    recovered = apply_relative_shift(priors, parents, np.zeros((5, 4)))
    assert recovered.shape == (5, 4)
    assert np.allclose(recovered, priors[None, :], atol=1e-12)


def test_relative_shift_is_scale_preserving():
    from graph_qec.m5 import apply_relative_shift

    priors = np.array([0.001, 0.004])
    parents = np.array([0, 1])
    # A positive LLR shift (more likely to be 0) must *lower* the probability.
    shift = np.array([[1.0, -1.0]])
    out = apply_relative_shift(priors, parents, shift)
    assert out[0, 0] < priors[0]
    assert out[0, 1] > priors[1]


def test_relative_shift_ignores_unmapped_instructions():
    from graph_qec.m5 import apply_relative_shift

    priors = np.array([0.001, 0.004])
    parents = np.array([-1, 0])
    shift = np.array([[7.0, 7.0]])
    out = apply_relative_shift(priors, parents, shift)
    assert out[0, 0] == pytest.approx(priors[0])
    assert out[0, 1] != pytest.approx(priors[1])
