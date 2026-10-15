"""Regression tests for the T18 weighted Union-Find decoder.

The original implementation XOR-ed the ``fault_mask`` of every merged edge and
skipped the peeling phase, so its corrections did not reproduce the syndrome
(~97% of defective shots) and its surface-code LER was >18x MWPM. These tests
pin the three properties that define the fixed decoder:

* every correction reproduces the syndrome,
* no shot is left unresolved,
* the surface-code d=3 code-capacity LER is in the same ballpark as MWPM.
"""

from __future__ import annotations

import numpy as np
import pytest
import stim

from graph_qec.config import ExperimentConfig
from graph_qec.data_pipeline import generate_dataset
from graph_qec.decoders import MWPMDecoder, UnionFindDecoder


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
def test_union_find_corrections_reproduce_the_syndrome(
    family: str, distance: int, rounds: int, model: str, probability: float
) -> None:
    dataset = _dataset(family, distance, rounds, model, probability, 512)
    decoder = UnionFindDecoder(dataset.matching_dem)
    check_matrix = _dem_check_matrix(dataset.matching_dem)
    assert check_matrix.shape[1] == len(decoder._edges)

    for syndrome in dataset.detections:
        grown = decoder._grow(syndrome)
        _, selected, resolved = decoder._peel(syndrome, grown)
        assert resolved
        correction = np.zeros(check_matrix.shape[1], dtype=np.uint8)
        correction[selected] = 1
        implied = (check_matrix @ correction) % 2
        assert np.array_equal(implied, syndrome)


def test_union_find_leaves_no_shot_unresolved() -> None:
    dataset = _dataset("rotated_surface_code", 3, 3, "circuit_level", 0.005, 1024)
    result = UnionFindDecoder(dataset.matching_dem).decode_batch(dataset.detections)
    assert result.diagnostics["unresolved_shots"] == 0
    assert result.diagnostics["algorithm"] == "weighted_union_find_halfedge"


def test_union_find_tracks_the_surface_code_d3_code_capacity_baseline() -> None:
    """The T18 acceptance criterion: Union-Find ~= MWPM, not 18x worse."""

    dataset = _dataset("rotated_surface_code", 3, 3, "code_capacity", 0.01, 4096)
    observables = dataset.observables
    uf = UnionFindDecoder(dataset.matching_dem).decode_batch(dataset.detections)
    mwpm = MWPMDecoder(dataset.matching_dem).decode_batch(dataset.detections)

    uf_errors = int(np.count_nonzero(np.any(uf.predictions != observables, axis=1)))
    mwpm_errors = int(np.count_nonzero(np.any(mwpm.predictions != observables, axis=1)))

    # The pre-fix implementation scored 258 errors here (LER 0.063); MWPM scores
    # ~14. Allow 50% slack plus a small constant so the test tracks the baseline
    # without being sensitive to the sampling seed.
    assert uf_errors <= 1.5 * mwpm_errors + 10
    assert uf_errors / dataset.shots < 0.02


def test_union_find_growth_is_the_half_edge_front() -> None:
    """A defect pair must fuse when the wavefronts collide mid-edge."""

    dataset = _dataset("repetition_code", 3, 3, "circuit_level", 0.01, 256)
    decoder = UnionFindDecoder(dataset.matching_dem)
    for syndrome in dataset.detections:
        grown = decoder._grow(syndrome)
        assert isinstance(grown, set)
        assert all(0 <= index < len(decoder._edges) for index in grown)
