"""Detector-graph features for graph-aware neural decoding.

The M2 stage needs a graph representation that is faithful to the DEM used by
BP (one variable per ``error`` instruction, hyperedges kept intact) while still
being a fixed, batchable tensor structure for a message-passing network.

The graph is bipartite: one node per detector (check) and one node per DEM
error mechanism (variable). Features are deterministic functions of the DEM,
the code geometry, and the per-shot syndrome, so they can be recomputed for any
new code distance or noise rate without retraining the feature definition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from .decoders.dem import DEMSystem


VARIABLE_FEATURE_NAMES = (
    "prior_log_odds",
    "prior_probability",
    "hyperedge_size",
    "observable_count",
    "detector_index_mean",
    "detector_time_mean",
)

CHECK_FEATURE_NAMES = (
    "degree_norm",
    "detector_index",
    "detector_time",
)

EDGE_FEATURE_NAMES = (
    "prior_log_odds_scaled",
    "inverse_variable_degree",
    "inverse_check_degree",
)

_LOG_ODDS_CLIP = 30.0


@dataclass(frozen=True, slots=True)
class GraphTensor:
    """Fixed-shape graph representation of one detector error model."""

    edge_checks: np.ndarray
    edge_variables: np.ndarray
    edge_features: np.ndarray
    variable_features: np.ndarray
    check_features: np.ndarray
    priors: np.ndarray
    check_matrix: np.ndarray
    observable_matrix: np.ndarray
    variable_feature_names: tuple[str, ...] = VARIABLE_FEATURE_NAMES
    check_feature_names: tuple[str, ...] = CHECK_FEATURE_NAMES
    edge_feature_names: tuple[str, ...] = EDGE_FEATURE_NAMES

    @property
    def num_checks(self) -> int:
        return int(self.check_features.shape[0])

    @property
    def num_variables(self) -> int:
        return int(self.variable_features.shape[0])

    @property
    def num_edges(self) -> int:
        return int(self.edge_checks.shape[0])

    @property
    def variable_feature_dim(self) -> int:
        return int(self.variable_features.shape[1])

    @property
    def check_feature_dim(self) -> int:
        return int(self.check_features.shape[1])

    @property
    def edge_feature_dim(self) -> int:
        return int(self.edge_features.shape[1])


def _normalized_coordinates(
    detector_coordinates: Mapping[int, Sequence[float]] | None,
    num_detectors: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Returns per-detector ``(index_normalized, time_normalized)`` arrays.

    ``time_normalized`` uses the last detector coordinate (Stim's time axis)
    when coordinates are available; otherwise it degrades to the normalized
    detector index so that the feature vector keeps a fixed width.
    """

    index = np.arange(num_detectors, dtype=np.float64)
    index_normalized = index / max(num_detectors - 1, 1)

    if not detector_coordinates:
        return index_normalized, index_normalized.copy()

    times = np.zeros(num_detectors, dtype=np.float64)
    for detector in range(num_detectors):
        coords = detector_coordinates.get(detector)
        if coords is None:
            times[detector] = 0.0
        elif len(coords) == 1:
            times[detector] = float(coords[0])
        else:
            times[detector] = float(coords[-1])
    span = float(np.max(times) - np.min(times))
    if span <= 0.0:
        time_normalized = np.zeros(num_detectors, dtype=np.float64)
    else:
        time_normalized = (times - float(np.min(times))) / span
    return index_normalized, time_normalized


def build_graph_tensor(
    system: DEMSystem,
    *,
    detector_coordinates: Mapping[int, Sequence[float]] | None = None,
) -> GraphTensor:
    """Builds the bipartite detector graph tensor for one DEM."""

    check_matrix = np.asarray(system.check_matrix, dtype=np.uint8)
    num_checks = int(check_matrix.shape[0])
    num_variables = int(check_matrix.shape[1])

    index_normalized, time_normalized = _normalized_coordinates(
        detector_coordinates, num_checks
    )

    priors = np.clip(np.asarray(system.priors, dtype=np.float64), 1e-12, 1.0 - 1e-12)
    prior_log_odds = np.clip(np.log((1.0 - priors) / priors), -_LOG_ODDS_CLIP, _LOG_ODDS_CLIP)

    edge_checks, edge_variables = np.nonzero(check_matrix)
    edge_checks = edge_checks.astype(np.int64)
    edge_variables = edge_variables.astype(np.int64)

    variable_degree = check_matrix.sum(axis=0).astype(np.float64)
    check_degree = check_matrix.sum(axis=1).astype(np.float64)

    variable_features = np.zeros((num_variables, len(VARIABLE_FEATURE_NAMES)), dtype=np.float64)
    variable_features[:, 0] = prior_log_odds
    variable_features[:, 1] = priors
    variable_features[:, 2] = variable_degree
    variable_features[:, 3] = (
        np.asarray(system.observable_matrix, dtype=np.uint8).sum(axis=0).astype(np.float64)
    )
    for variable in range(num_variables):
        detectors = edge_checks[edge_variables == variable]
        if detectors.size:
            variable_features[variable, 4] = float(index_normalized[detectors].mean())
            variable_features[variable, 5] = float(time_normalized[detectors].mean())

    check_features = np.zeros((num_checks, len(CHECK_FEATURE_NAMES)), dtype=np.float64)
    for check in range(num_checks):
        check_features[check, 0] = check_degree[check] / max(num_variables, 1)
        check_features[check, 1] = index_normalized[check]
        check_features[check, 2] = time_normalized[check]

    edge_features = np.zeros((edge_checks.size, len(EDGE_FEATURE_NAMES)), dtype=np.float64)
    edge_features[:, 0] = prior_log_odds[edge_variables] / _LOG_ODDS_CLIP
    edge_features[:, 1] = 1.0 / np.maximum(variable_degree[edge_variables], 1.0)
    edge_features[:, 2] = 1.0 / np.maximum(check_degree[edge_checks], 1.0)

    return GraphTensor(
        edge_checks=np.ascontiguousarray(edge_checks),
        edge_variables=np.ascontiguousarray(edge_variables),
        edge_features=np.ascontiguousarray(edge_features, dtype=np.float32),
        variable_features=np.ascontiguousarray(variable_features, dtype=np.float32),
        check_features=np.ascontiguousarray(check_features, dtype=np.float32),
        priors=np.ascontiguousarray(priors, dtype=np.float64),
        check_matrix=np.ascontiguousarray(check_matrix),
        observable_matrix=np.ascontiguousarray(np.asarray(system.observable_matrix, dtype=np.uint8)),
    )


def prior_log_odds(priors: np.ndarray) -> np.ndarray:
    """Returns clipped log-odds ``log((1-p)/p)`` for priors in ``(0, 1)``."""

    clipped = np.clip(np.asarray(priors, dtype=np.float64), 1e-12, 1.0 - 1e-12)
    return np.clip(np.log((1.0 - clipped) / clipped), -_LOG_ODDS_CLIP, _LOG_ODDS_CLIP)
