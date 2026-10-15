"""A boundary-aware single-shot Union-Find decoder.

Reference: Delfosse & Nickerson, "Almost-linear time decoding algorithm for
topological codes" (Quantum 2021). The decoder has two phases:

1. **Cluster growth** -- edges of the (decomposed, graphlike) DEM graph are
   added in non-decreasing weight order. An edge is accepted when it joins two
   distinct clusters and at least one of them is odd; a cluster is even when it
   contains an even number of defects or touches the boundary. Growth stops as
   soon as every cluster is even. The accepted edges form a spanning forest.

2. **Peeling** -- inside each grown cluster the correction is the minimum
   T-join of the cluster's defects *within its spanning tree*, computed by the
   classic subtree-parity sweep (root the tree, include an edge iff the subtree
   below it holds an odd number of terminals; the boundary joins the terminal
   set when the cluster has an odd defect count).

History / status
----------------
The original implementation accumulated the ``fault_mask`` of *every* merged
edge and had no peeling step, so its corrections did not reproduce the
syndrome. The T-join peel below fixes that invariant. The decoder is still a
greedy approximation: its logical error rate remains above MWPM on surface
codes because the growth is myopic around the boundary. The full analysis,
measurements and the remaining open work are in
``docs/T18_UNION_FIND_ANALYSIS.md``.
"""

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
    """Union-Find decoder using the decomposed DEM graph."""

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

    def _grow_clusters(
        self, syndrome: np.ndarray
    ) -> tuple[list[tuple[int, int, int, int]], int]:
        """Phase 1: grow clusters until every one of them is even.

        Returns ``(tree_edges, odd_clusters)`` where each tree edge is
        ``(u, v, fault_mask, global_edge_index)``.
        """

        size = self._num_nodes + 1
        dsu = _DisjointSet(size)
        parity = np.zeros(size, dtype=np.uint8)
        on_boundary = np.zeros(size, dtype=np.uint8)
        parity[: self._num_nodes] = syndrome
        on_boundary[self._boundary_node] = 1
        odd_clusters = int(np.count_nonzero(syndrome))

        heap = [(edge.weight, index) for index, edge in enumerate(self._edges)]
        heapq.heapify(heap)
        tree_edges: list[tuple[int, int, int, int]] = []

        while odd_clusters and heap:
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

            boundary = int(on_boundary[left_root] or on_boundary[right_root])
            new_root = dsu.union(left_root, right_root)
            new_parity = left_parity ^ right_parity
            if boundary:
                new_parity = 0
            parity[new_root] = new_parity
            on_boundary[new_root] = boundary
            odd_clusters -= left_parity + right_parity - new_parity
            tree_edges.append((edge.u, edge.v, edge.fault_mask, edge_index))

        return tree_edges, odd_clusters

    def _peel(
        self,
        syndrome: np.ndarray,
        tree_edges: list[tuple[int, int, int, int]],
    ) -> tuple[int, list[int]]:
        """Phase 2: minimum T-join of the spanning forest.

        Returns ``(correction_fault_mask, included_edge_indices)``.
        """

        if not tree_edges:
            return 0, []

        boundary = self._boundary_node
        num_detectors = self._num_nodes

        adjacency: dict[int, list[tuple[int, int]]] = {}
        for index, (u, v, _, _) in enumerate(tree_edges):
            adjacency.setdefault(u, []).append((v, index))
            adjacency.setdefault(v, []).append((u, index))

        included = bytearray(len(tree_edges))
        visited: set[int] = set()

        for start_node in adjacency:
            if start_node in visited:
                continue
            order: list[int] = []
            parent: dict[int, int] = {start_node: start_node}
            parent_edge: dict[int, int] = {}
            stack = [start_node]
            visited.add(start_node)
            while stack:
                node = stack.pop()
                order.append(node)
                for neighbor, edge_index in adjacency[node]:
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)
                    parent[neighbor] = node
                    parent_edge[neighbor] = edge_index
                    stack.append(neighbor)

            defects = [x for x in order if x < num_detectors and syndrome[x]]
            terminals = set(defects)
            if boundary in order and len(defects) % 2 == 1:
                terminals.add(boundary)

            counts = {node: (1 if node in terminals else 0) for node in order}
            for node in reversed(order):
                if node == start_node:
                    continue
                if counts[node] % 2 == 1:
                    included[parent_edge[node]] = 1
                counts[parent[node]] += counts[node]

        correction = 0
        selected: list[int] = []
        for index, (_, _, fault_mask, global_index) in enumerate(tree_edges):
            if included[index]:
                correction ^= fault_mask
                selected.append(global_index)
        return correction, selected

    def _decode_shot(self, syndrome: np.ndarray) -> tuple[int, bool]:
        tree_edges, odd_clusters = self._grow_clusters(syndrome)
        correction, _ = self._peel(syndrome, tree_edges)
        return correction, odd_clusters == 0

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
                "peeling": "t_join",
            },
        )
        return self._validate_result(result, predictions.shape)
