"""Detector error model conversion into binary matrices."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import stim


@dataclass(frozen=True, slots=True)
class DEMSystem:
    """Binary system ``H @ e = syndrome`` and ``L @ e = observables``."""

    check_matrix: np.ndarray
    observable_matrix: np.ndarray
    priors: np.ndarray
    num_detectors: int
    num_observables: int

    @property
    def num_errors(self) -> int:
        return int(self.check_matrix.shape[1])

    @classmethod
    def from_detector_error_model(
        cls,
        detector_error_model: stim.DetectorErrorModel,
    ) -> "DEMSystem":
        """Converts a Stim DEM without losing hyperedges.

        Each ``error`` instruction is one BP variable. Separator targets in a
        suggested decomposition are therefore kept together in the same row,
        while the decomposed DEM remains available for graph decoders.
        """

        model = detector_error_model.flattened()
        num_checks = model.num_detectors
        num_observables = model.num_observables
        detector_rows: list[tuple[int, ...]] = []
        observable_rows: list[tuple[int, ...]] = []
        priors: list[float] = []

        for instruction in model:
            if instruction.type != "error":
                continue
            args = instruction.args_copy()
            if len(args) != 1:
                raise ValueError("DEM error instructions must have exactly one probability")
            probability = float(args[0])
            if not 0.0 <= probability <= 1.0:
                raise ValueError(f"Invalid DEM error probability: {probability}")

            detectors: list[int] = []
            observables: list[int] = []
            for target in instruction.targets_copy():
                if target.is_separator():
                    continue
                if target.is_relative_detector_id():
                    detectors.append(int(target.val))
                elif target.is_logical_observable_id():
                    observables.append(int(target.val))
                else:
                    raise ValueError(f"Unsupported DEM target: {target}")

            detector_rows.append(tuple(detectors))
            observable_rows.append(tuple(observables))
            priors.append(probability)

        check_matrix = np.zeros((num_checks, len(priors)), dtype=np.uint8)
        observable_matrix = np.zeros(
            (num_observables, len(priors)), dtype=np.uint8
        )
        for column, detectors in enumerate(detector_rows):
            check_matrix[list(detectors), column] = 1
        for column, observables in enumerate(observable_rows):
            for observable in observables:
                observable_matrix[observable, column] ^= 1

        if priors and len(priors) != model.num_errors:
            raise RuntimeError(
                f"Parsed {len(priors)} errors but DEM reports {model.num_errors}"
            )

        return cls(
            check_matrix=np.ascontiguousarray(check_matrix),
            observable_matrix=np.ascontiguousarray(observable_matrix),
            priors=np.ascontiguousarray(priors, dtype=np.float64),
            num_detectors=num_checks,
            num_observables=num_observables,
        )

    def syndrome(self, correction: np.ndarray) -> np.ndarray:
        """Computes the syndrome for one binary correction vector."""

        return (
            self.check_matrix.astype(np.int64) @ correction.astype(np.int64)
        ) % 2

    def logical_parity(self, correction: np.ndarray) -> np.ndarray:
        """Computes logical-observable parity for one correction vector."""

        return (
            self.observable_matrix.astype(np.int64) @ correction.astype(np.int64)
        ) % 2
