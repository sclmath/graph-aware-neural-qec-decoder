"""Regression tests for the T18 Union-Find peeling fix.

Before the fix the decoder returned the XOR of *every* merged edge, so its
corrections did not reproduce the syndrome. These tests pin the invariant that
matters: the peeled edge set must have the syndrome as its boundary.
"""

from __future__ import annotations

import numpy as np
import pytest
import stim

from graph_qec.config import ExperimentConfig
from graph_qec.data_pipeline import generate_dataset
from graph_qec.decoders import UnionFindDecoder


def _dem_check_matrix(dem: stim.DetectorErrorModel) -> np.ndarray:
    """Builds the detector check matrix in the decoder's edge order."""

    model = dem.flattened()
    columns: list[list[int]] = []
    for instruction in model:
        if instruction.type != "error":
            continue
        components: list[list[int]] = [[]]
        for target in instruction.targets_copy():
            if target.is_separator():
                components.append([])
            elif target.is_relative_detector_id():
                components[-1].append(int(target.val))
        for component in components:
            if not component:
                continue
            assert len(component) <= 2
            columns.append(component)

    matrix = np.zeros((model.num_detectors, len(columns)), dtype=np.uint8)
    for column, detectors in enumerate(columns):
        for detector in detectors:
            matrix[detector, column] ^= 1
    return matrix


def _dataset(family: str, distance: int, rounds: int, model: str, p: float, shots: int):
    return generate_dataset(
        ExperimentConfig(
            name="t18",
            seed=20261014,
            family=family,
            distance=distance,
            rounds=rounds,
            noise_model=model,
            physical_error_rate=p,
            shots=shots,
        )
    )


@pytest.mark.parametrize(
    "family, distance, rounds, model, probability",
    [
        ("repetition_code", 3, 3, "circuit_level", 0.01),
        ("rotated_surface_code", 3, 3, "code_capacity", 0.01),
        ("rotated_surface_code", 3, 3, "circuit_level", 0.005),
    ],
)
def test_union_find_peeled_correction_reproduces_the_syndrome(
    family: str, distance: int, rounds: int, model: str, probability: float
) -> None:
    dataset = _dataset(family, distance, rounds, model, probability, 512)
    decoder = UnionFindDecoder(dataset.matching_dem)
    check_matrix = _dem_check_matrix(dataset.matching_dem)
    assert check_matrix.shape[1] == len(decoder._edges)

    for syndrome in dataset.detections:
        tree_edges, odd_clusters = decoder._grow_clusters(syndrome)
        assert odd_clusters == 0
        _, selected = decoder._peel(syndrome, tree_edges)
        correction = np.zeros(check_matrix.shape[1], dtype=np.uint8)
        correction[selected] = 1
        implied = (check_matrix @ correction) % 2
        assert np.array_equal(implied, syndrome)


def test_union_find_peeling_selects_a_subset_of_grown_edges() -> None:
    dataset = _dataset("rotated_surface_code", 3, 3, "code_capacity", 0.01, 256)
    decoder = UnionFindDecoder(dataset.matching_dem)

    peeled_any = False
    for syndrome in dataset.detections:
        tree_edges, _ = decoder._grow_clusters(syndrome)
        _, selected = decoder._peel(syndrome, tree_edges)
        grown = {edge[3] for edge in tree_edges}
        assert set(selected) <= grown
        if len(selected) < len(tree_edges):
            peeled_any = True
    # The peel must actually discard redundant edges on at least one shot,
    # otherwise the regression test above is vacuous.
    assert peeled_any


def test_union_find_reports_no_unresolved_shots_on_surface_code() -> None:
    dataset = _dataset("rotated_surface_code", 3, 3, "code_capacity", 0.01, 512)
    result = UnionFindDecoder(dataset.matching_dem).decode_batch(dataset.detections)
    assert result.diagnostics["unresolved_shots"] == 0
    assert result.diagnostics["peeling"] == "t_join"
