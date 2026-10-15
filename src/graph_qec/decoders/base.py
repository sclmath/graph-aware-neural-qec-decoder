"""Shared decoder interfaces and result types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(slots=True)
class DecodeResult:
    """Batch decoder output.

    ``predictions`` contains predicted logical-observable flips. ``corrections``
    is populated when a decoder materializes an explicit error-mechanism vector.
    """

    predictions: np.ndarray
    corrections: np.ndarray | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)


class Decoder(ABC):
    """Common interface used by M1 benchmarks and later hybrid decoders."""

    def __init__(self, *, num_detectors: int, num_observables: int) -> None:
        if num_detectors < 1:
            raise ValueError("num_detectors must be positive")
        if num_observables < 0:
            raise ValueError("num_observables must be non-negative")
        self.num_detectors = num_detectors
        self.num_observables = num_observables

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable decoder identifier used in result files."""

    @abstractmethod
    def decode_batch(self, detections: np.ndarray) -> DecodeResult:
        """Decodes a batch with shape ``(shots, num_detectors)``."""

    def _validate_detections(self, detections: np.ndarray) -> np.ndarray:
        array = np.asarray(detections)
        if array.ndim != 2 or array.shape[1] != self.num_detectors:
            raise ValueError(
                "detections must have shape "
                f"(shots, {self.num_detectors}); got {array.shape}"
            )
        if not np.all((array == 0) | (array == 1)):
            raise ValueError("detections must contain only binary values")
        return np.ascontiguousarray(array, dtype=np.uint8)

    @staticmethod
    def _validate_result(result: DecodeResult, shape: tuple[int, int]) -> DecodeResult:
        predictions = np.ascontiguousarray(result.predictions, dtype=np.uint8)
        if predictions.shape != shape:
            raise RuntimeError(
                f"Decoder returned predictions with shape {predictions.shape}; "
                f"expected {shape}"
            )
        result.predictions = predictions
        if result.corrections is not None:
            corrections = np.ascontiguousarray(result.corrections, dtype=np.uint8)
            if corrections.ndim != 2 or corrections.shape[0] != shape[0]:
                raise RuntimeError(
                    f"Decoder returned invalid corrections shape {corrections.shape}"
                )
            result.corrections = corrections
        return result
