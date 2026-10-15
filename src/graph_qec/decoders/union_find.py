"""A boundary-aware single-shot Union-Find decoder."""

from __future__ import annotations

import heapq
from dataclasses import dataclass

import numpy as np
import stim

from .base import DecodeResult, Decoder


@dataclass(frozen=True, slots=True)
class _GraphEdge:
    u: int
    v: int
    weight: float
    fault_mask: int


class _DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = np.arange(size, dtype=np.int64)
        self.rank = np.zeros(size, dtype=np.uint8)

    def find(self, node: int) -> int:
        root = node
        while int(self.parent[root]) != root:
            root = int(self.parent[root])
        while int(self.parent[node]) != node:
            parent = int(self.parent[node])
            self.parent[node] = root
            node = parent
        return root

    def union(self, left: int, right: int) -> int:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return left_root
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1
        return left_root


class UnionFindDecoder(Decoder):
    """Greedy cluster-growing decoder using the decomposed DEM graph."""

    name = "union_find"

    def __init__(self, detector_error_model: stim.DetectorErrorModel) -> None:
        model = detector_error_model.flattened()
        self._num_nodes = int(model.num_detectors)
        self._boundary_node = self._num_nodes
        self._edges: list[_GraphEdge] = []

        for instruction in model:
            if instruction.type != "error":
                continue
            probability = float(instruction.args_copy()[0])
            probability = min(max(probability, 1e-15), 1.0 - 1e-15)
            weight = float(np.log((1.0 - probability) / probability))

            components: list[list[stim.DemTarget]] = [[]]
            for target in instruction.targets_copy():
                if target.is_separator():
                    components.append([])
                else:
                    components[-1].append(target)

            for component in components:
                detectors: list[int] = []
                observables: list[int] = []
                for target in component:
                    if target.is_relative_detector_id():
                        detectors.append(int(target.val))
                    elif target.is_logical_observable_id():
                        observables.append(int(target.val))

                if len(detectors) == 0:
                    continue
                if len(detectors) > 2:
                    raise ValueError(
                        "Decomposed DEM contains a non-graphlike component"
                    )
                fault_mask = 0
                for observable in observables:
                    fault_mask ^= 1 << observable
                left = detectors[0]
                right = detectors[1] if len(detectors) == 2 else self._boundary_node
                self._edges.append(
                    _GraphEdge(
                        u=left,
                        v=right,
                        weight=weight,
                        fault_mask=fault_mask,
                    )
                )

        super().__init__(
            num_detectors=int(model.num_detectors),
            num_observables=int(model.num_observables),
        )
        self._matching_num_edges = len(self._edges)

    def _decode_shot(self, syndrome: np.ndarray) -> tuple[int, bool]:
        size = self._num_nodes + 1
        dsu = _DisjointSet(size)
        parity = np.zeros(size, dtype=np.uint8)
        on_boundary = np.zeros(size, dtype=np.uint8)
        parity[: self._num_nodes] = syndrome
        on_boundary[self._boundary_node] = 1

        heap = [
            (edge.weight, index)
            for index, edge in enumerate(self._edges)
        ]
        heapq.heapify(heap)
        fault_mask = 0

        while heap:
            _, edge_index = heapq.heappop(heap)
            edge = self._edges[edge_index]
            left_root = dsu.find(edge.u)
            right_root = dsu.find(edge.v)
            if left_root == right_root:
                continue

            left_parity = int(parity[left_root])
            right_parity = int(parity[right_root])
            if left_parity == 0 and right_parity == 0:
                continue

            fault_mask ^= edge.fault_mask
            new_root = dsu.union(left_root, right_root)
            parity[new_root] = left_parity ^ right_parity
            boundary = int(on_boundary[left_root] or on_boundary[right_root])
            on_boundary[new_root] = boundary
            if boundary:
                parity[new_root] = 0

            if not np.any(parity[[dsu.find(i) for i in range(size)]]):
                return fault_mask, True

        for node in range(size):
            if int(parity[dsu.find(node)]):
                return fault_mask, False
        return fault_mask, True

    def decode_batch(self, detections: np.ndarray) -> DecodeResult:
        detections = self._validate_detections(detections)
        predictions = np.zeros(
            (detections.shape[0], self.num_observables), dtype=np.uint8
        )
        unresolved = 0
        for shot, syndrome in enumerate(detections):
            fault_mask, resolved = self._decode_shot(syndrome)
            unresolved += int(not resolved)
            for observable in range(self.num_observables):
                predictions[shot, observable] = (fault_mask >> observable) & 1

        result = DecodeResult(
            predictions=predictions,
            diagnostics={
                "num_nodes": self._num_nodes,
                "num_edges": self._matching_num_edges,
                "unresolved_shots": unresolved,
            },
        )
        return self._validate_result(result, predictions.shape)
