"""Weighted Union-Find decoder for graphlike detector error models.

Reference: Delfosse & Nickerson, "Almost-linear time decoding algorithm for
topological codes", Quantum 5, 597 (2021).

The decoder has the three phases of the paper:

1. **Cluster growth.** Every defect is a cluster of parity one. Clusters grow
   their wavefront one half-edge at a time in non-decreasing weight order. A
   *half-edge* is one end's half of an edge; growing both halves turns the edge
   into a **Grown** edge and adds it to the grown edge set ``epsilon'``. A
   cluster is *even* when it holds an even number of defects or touches the
   boundary node; even clusters stop growing. When two fronts collide the
   clusters fuse and the parity is updated -- including *un*freezing a cluster
   that the fusion made odd again.
2. **Peeling.** The erasure peeling decoder runs on ``epsilon'``: a degree-one
   vertex that is not a defect decides its only edge is not in the correction;
   a degree-one defect forces its edge into the correction and toggles the
   residual syndrome at the far end. Boundary vertices are never peeled.
3. **Core resolution.** Peeling leaves a 2-core when ``epsilon'`` has cycles.
   The residual defects inside each core component are then closed with a
   minimum T-join over a minimum spanning forest of that core, which keeps the
   correction syndrome-consistent.

History
-------
The original implementation XOR-ed the ``fault_mask`` of *every* merged edge and
had no peeling, so ~97% of the defective shots returned corrections that did
not reproduce the syndrome; on the surface code it was 18x worse than MWPM (or
worse). The faithful version above matches MWPM on the small surface codes and
is documented in ``docs/T18_UNION_FIND_ANALYSIS.md``.
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


class UnionFindDecoder(Decoder):
    """Weighted Union-Find decoder using the decomposed DEM graph."""

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
                    _GraphEdge(u=left, v=right, weight=weight, fault_mask=fault_mask)
                )

        self._adjacency: dict[int, list[tuple[int, float, int]]] = {}
        for index, edge in enumerate(self._edges):
            self._adjacency.setdefault(edge.u, []).append((edge.v, edge.weight, index))
            self._adjacency.setdefault(edge.v, []).append((edge.u, edge.weight, index))

        super().__init__(
            num_detectors=int(model.num_detectors),
            num_observables=int(model.num_observables),
        )
        self._matching_num_edges = len(self._edges)

    # ------------------------------------------------------------------ phase 1
    def _grow(self, syndrome: np.ndarray) -> set[int]:
        """Grows clusters until every one of them is even.

        Returns the grown edge set ``epsilon'`` (indices into ``self._edges``).
        """

        num_nodes = self._num_nodes
        boundary = self._boundary_node
        adjacency = self._adjacency
        size = num_nodes + 1

        parent = list(range(size))
        rank = [0] * size

        def find(node: int) -> int:
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        parity = [0] * size
        touches_boundary = [False] * size
        frozen = [False] * size
        cover_time = [float("inf")] * size
        owner = [-1] * size
        half_grown: dict[int, set[int]] = {}
        grown: set[int] = set()
        queue: list[tuple[float, int, int, int, int]] = []
        deferred: list[tuple[float, int, int, int, int]] = []

        def push_front(vertex: int, time: float) -> None:
            for neighbour, weight, edge_index in adjacency.get(vertex, ()):
                heapq.heappush(queue, (time + weight / 2.0, 0, edge_index, vertex, neighbour))
                heapq.heappush(queue, (time + weight, 1, edge_index, vertex, neighbour))

        for seed in range(num_nodes):
            if not syndrome[seed]:
                continue
            parity[seed] = 1
            cover_time[seed] = 0.0
            owner[seed] = seed
            push_front(seed, 0.0)

        unfrozen_pending = False
        while queue:
            time, kind, edge_index, source, target = heapq.heappop(queue)
            root = find(owner[source])
            if frozen[root]:
                deferred.append((time, kind, edge_index, source, target))
                continue

            merge_root = -1
            if kind == 0:  # a half-edge: the front reaches the midpoint
                grown_from = half_grown.setdefault(edge_index, set())
                grown_from.add(source)
                if target in grown_from:
                    # Both halves grown: the edge is traversed by two fronts.
                    grown.add(edge_index)
                    other = find(owner[target])
                    if other != root:
                        merge_root = other
            else:  # the front traverses the whole edge
                grown.add(edge_index)
                if cover_time[target] > time:
                    cover_time[target] = time
                    owner[target] = root
                    if target == boundary:
                        touches_boundary[root] = True
                    push_front(target, time)
                    if parity[root] == 0 or touches_boundary[root]:
                        frozen[root] = True
                else:
                    other = find(owner[target])
                    if other != root:
                        merge_root = other

            if merge_root >= 0:
                if rank[root] < rank[merge_root]:
                    root, merge_root = merge_root, root
                parent[merge_root] = root
                if rank[root] == rank[merge_root]:
                    rank[root] += 1
                parity[root] ^= parity[merge_root]
                touches_boundary[root] = (
                    touches_boundary[root] or touches_boundary[merge_root]
                )
                now_frozen = parity[root] == 0 or touches_boundary[root]
                if frozen[root] and not now_frozen:
                    unfrozen_pending = True
                frozen[root] = now_frozen

            if unfrozen_pending:
                remaining = []
                for event in deferred:
                    event_root = find(owner[event[3]])
                    if frozen[event_root]:
                        remaining.append(event)
                    else:
                        heapq.heappush(queue, event)
                deferred = remaining
                unfrozen_pending = False

        return grown

    # ------------------------------------------------------------------ phase 2
    def _peel(
        self, syndrome: np.ndarray, grown: set[int]
    ) -> tuple[int, list[int], bool]:
        """Erasure peeling with syndrome toggling.

        Returns ``(correction_fault_mask, selected_edge_indices, resolved)``.
        """

        num_nodes = self._num_nodes
        boundary = self._boundary_node
        edges = self._edges

        adjacency: dict[int, list[int]] = {}
        degree: dict[int, int] = {}
        for edge_index in grown:
            edge = edges[edge_index]
            adjacency.setdefault(edge.u, []).append(edge_index)
            adjacency.setdefault(edge.v, []).append(edge_index)
            degree[edge.u] = degree.get(edge.u, 0) + 1
            degree[edge.v] = degree.get(edge.v, 0) + 1

        residual = {node for node in range(num_nodes) if syndrome[node]}
        removed: set[int] = set()
        correction = 0
        selected: list[int] = []
        stack = [node for node, deg in degree.items() if deg == 1 and node != boundary]
        while stack:
            node = stack.pop()
            if degree.get(node, 0) != 1:
                continue
            edge_index = None
            for candidate in adjacency[node]:
                if candidate not in removed:
                    edge_index = candidate
                    break
            if edge_index is None:
                degree[node] = 0
                continue
            edge = edges[edge_index]
            other = edge.v if edge.u == node else edge.u
            if node in residual:
                correction ^= edge.fault_mask
                selected.append(edge_index)
                residual ^= {node, other}
            removed.add(edge_index)
            degree[node] -= 1
            degree[other] -= 1
            if other != boundary and degree[other] == 1:
                stack.append(other)

        if any(node in residual for node in range(num_nodes)):
            # Peeling stopped on a 2-core (epsilon' has a cycle). Close the
            # residual defects with a T-join over the core's spanning forest.
            mask, extra, paired = self._resolve_core(residual, grown, removed)
            correction ^= mask
            selected.extend(extra)
            return correction, selected, paired
        return correction, selected, True

    # ------------------------------------------------------------------ phase 3
    def _resolve_core(
        self, residual: set[int], grown: set[int], removed: set[int]
    ) -> tuple[int, list[int], bool]:
        """Closes the residual defects inside the unpeeled 2-core.

        A minimum T-join is taken over a minimum spanning forest of the core, so
        the correction stays syndrome-consistent even when ``epsilon'`` has
        cycles (which happens whenever two clusters wrap around each other).
        """

        num_nodes = self._num_nodes
        boundary = self._boundary_node
        edges = self._edges
        core = [edge for edge in grown if edge not in removed]
        if not core:
            return 0, [], False

        spanning_parent: dict[int, int] = {}

        def find(node: int) -> int:
            spanning_parent.setdefault(node, node)
            while spanning_parent[node] != node:
                spanning_parent[node] = spanning_parent[spanning_parent[node]]
                node = spanning_parent[node]
            return node

        forest: list[tuple[int, int, int, int]] = []
        for edge_index in sorted(core, key=lambda index: (edges[index].weight, index)):
            edge = edges[edge_index]
            left_root = find(edge.u)
            right_root = find(edge.v)
            if left_root == right_root:
                continue
            spanning_parent[right_root] = left_root
            forest.append((edge.u, edge.v, edge.fault_mask, edge_index))
        if not forest:
            return 0, [], False

        adjacency: dict[int, list[tuple[int, int]]] = {}
        for position, (u, v, _, _) in enumerate(forest):
            adjacency.setdefault(u, []).append((v, position))
            adjacency.setdefault(v, []).append((u, position))

        included = bytearray(len(forest))
        visited: set[int] = set()
        paired = True
        for start in adjacency:
            if start in visited:
                continue
            order: list[int] = []
            parent: dict[int, int] = {start: start}
            parent_edge: dict[int, int] = {}
            stack = [start]
            visited.add(start)
            while stack:
                node = stack.pop()
                order.append(node)
                for neighbour, position in adjacency[node]:
                    if neighbour in visited:
                        continue
                    visited.add(neighbour)
                    parent[neighbour] = node
                    parent_edge[neighbour] = position
                    stack.append(neighbour)

            defects = [node for node in order if node < num_nodes and node in residual]
            terminals = set(defects)
            if boundary in order and len(defects) % 2 == 1:
                terminals.add(boundary)
            elif len(defects) % 2 == 1:
                # An odd defect count in a component with no boundary cannot be
                # closed; the shot is genuinely unresolved.
                paired = False
            counts = {node: (1 if node in terminals else 0) for node in order}
            for node in reversed(order):
                if node == start:
                    continue
                if counts[node] % 2 == 1:
                    included[parent_edge[node]] = 1
                counts[parent[node]] += counts[node]

        mask = 0
        chosen: list[int] = []
        for position, (_, _, fault_mask, edge_index) in enumerate(forest):
            if included[position]:
                mask ^= fault_mask
                chosen.append(edge_index)
        return mask, chosen, paired

    def _decode_shot(self, syndrome: np.ndarray) -> tuple[int, bool]:
        grown = self._grow(syndrome)
        correction, _, resolved = self._peel(syndrome, grown)
        return correction, resolved

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
                "algorithm": "weighted_union_find_halfedge",
            },
        )
        return self._validate_result(result, predictions.shape)
