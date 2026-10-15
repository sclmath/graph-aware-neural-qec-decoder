"""Minimum-weight perfect matching baseline."""

from __future__ import annotations

import numpy as np
import pymatching
import stim

from .base import DecodeResult, Decoder


class MWPMDecoder(Decoder):
    """PyMatching decoder loaded from a decomposed Stim DEM."""

    name = "mwpm"

    def __init__(self, detector_error_model: stim.DetectorErrorModel) -> None:
        self._matching = pymatching.Matching.from_detector_error_model(
            detector_error_model
        )
        super().__init__(
            num_detectors=self._matching.num_detectors,
            num_observables=self._matching.num_fault_ids,
        )

    def decode_batch(self, detections: np.ndarray) -> DecodeResult:
        detections = self._validate_detections(detections)
        predictions = self._matching.decode_batch(detections)
        result = DecodeResult(
            predictions=predictions,
            diagnostics={
                "num_nodes": int(self._matching.num_nodes),
                "num_edges": int(self._matching.num_edges),
            },
        )
        return self._validate_result(result, (detections.shape[0], self.num_observables))
