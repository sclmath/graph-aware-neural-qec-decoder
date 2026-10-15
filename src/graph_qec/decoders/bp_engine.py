"""Batched (shot-vectorized) normalized min-sum belief propagation.

The scalar reference implementation in :mod:`graph_qec.decoders.bp` walks the
Tanner graph once per shot in Python, which costs milliseconds per shot and
makes surface-code or d>=5 sweeps infeasible. This module runs the *same*
algorithm for many shots at once with NumPy segment operations and a compaction
step that removes shots as soon as they converge.

The equivalence with the scalar implementation is pinned by
``tests/test_batched_bp.py``: for identical inputs the corrections, posterior
log-likelihood ratios, per-shot iteration counts and convergence flags must be
bit-identical.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


_DEGREE_ONE_MESSAGE = 20.0
_DEFAULT_SHOT_BUDGET = 4_000_000


@dataclass(slots=True)
class BatchedBPOutput:
    """Per-shot BP outcome, one row per shot."""

    corrections: np.ndarray
    posterior_llr: np.ndarray
    iterations: np.ndarray
    converged: np.ndarray
    syndrome_distance: np.ndarray


class BatchedMinSumBP:
    """Shot-vectorized normalized min-sum BP over a fixed check matrix."""

    def __init__(
        self,
        check_matrix: np.ndarray,
        priors: np.ndarray,
        *,
        max_iterations: int,
        min_sum_scaling: float,
        damping: float = 0.0,
        shot_budget: int = _DEFAULT_SHOT_BUDGET,
    ) -> None:
        if max_iterations < 1:
            raise ValueError("max_iterations must be positive")
        if not 0.0 < min_sum_scaling <= 1.0:
            raise ValueError("min_sum_scaling must be in (0, 1]")
        if not 0.0 <= damping < 1.0:
            raise ValueError("damping must be in [0, 1)")

        self.check_matrix = np.ascontiguousarray(np.asarray(check_matrix, dtype=np.uint8))
        self.num_checks, self.num_variables = self.check_matrix.shape
        probabilities = np.clip(np.asarray(priors, dtype=np.float64), 1e-12, 1.0 - 1e-12)
        self.prior_llr = np.log((1.0 - probabilities) / probabilities)
        self.max_iterations = int(max_iterations)
        self.min_sum_scaling = float(min_sum_scaling)
        self.damping = float(damping)
        self.shot_budget = max(int(shot_budget), 1)

        # Edges in canonical (row-major) order: contiguous slices per check.
        edge_check, edge_variable = np.nonzero(self.check_matrix)
        self.edge_check = edge_check.astype(np.int64)
        self.edge_variable = edge_variable.astype(np.int64)
        self.num_edges = int(self.edge_check.size)

        check_degree = self.check_matrix.sum(axis=1).astype(np.int64)
        variable_degree = self.check_matrix.sum(axis=0).astype(np.int64)
        self.max_check_degree = int(check_degree.max()) if self.num_checks else 0

        # Padded check layout: (num_checks, max_degree) -> edge index or -1.
        self.check_pad = np.full((self.num_checks, max(self.max_check_degree, 1)), -1, dtype=np.int64)
        self.check_pad_mask = np.zeros_like(self.check_pad, dtype=bool)
        if self.num_checks:
            starts = np.concatenate([[0], np.cumsum(check_degree)])
            for check in range(self.num_checks):
                start, stop = int(starts[check]), int(starts[check + 1])
                self.check_pad[check, : stop - start] = np.arange(start, stop)
                self.check_pad_mask[check, : stop - start] = True
        safe_pad = np.where(self.check_pad_mask, self.check_pad, 0)
        self.check_pad_edge = safe_pad
        self.check_pad_variable = np.where(
            self.check_pad_mask, self.edge_variable[safe_pad], 0
        ).astype(np.int64)
        self.check_pad_sign_safe = self.check_pad_mask.astype(np.float64)

        # Variable-grouped permutation of the edge axis for segment sums.
        var_order = np.argsort(self.edge_variable, kind="stable")
        self.variable_edge_order = var_order.astype(np.int64)
        var_starts = np.concatenate([[0], np.cumsum(variable_degree)])
        self.variable_starts = var_starts[:-1].astype(np.int64)
        self.variable_degree = variable_degree
        self.variable_has_edges = variable_degree > 0

        # Padding mask for the check-side min-sum (broadcast over shots).
        self._pad_active = self.check_pad_mask[None, :, :]

    # ------------------------------------------------------------------ public

    def decode(
        self,
        syndromes: np.ndarray,
        prior_llr: np.ndarray | None = None,
    ) -> BatchedBPOutput:
        """Decodes ``syndromes`` (shots, checks) with optional per-shot priors."""

        syndromes = np.ascontiguousarray(np.asarray(syndromes, dtype=np.uint8))
        shots = int(syndromes.shape[0])
        if syndromes.shape[1] != self.num_checks:
            raise ValueError(
                f"syndromes must have shape (shots, {self.num_checks}); got {syndromes.shape}"
            )

        if prior_llr is None:
            priors = np.broadcast_to(self.prior_llr, (shots, self.num_variables))
            priors = np.ascontiguousarray(priors, dtype=np.float64)
        else:
            priors = np.asarray(prior_llr, dtype=np.float64)
            if priors.shape == (self.num_variables,):
                priors = np.broadcast_to(priors, (shots, self.num_variables))
            elif priors.shape != (shots, self.num_variables):
                raise ValueError(
                    f"prior_llr must have shape ({self.num_variables},) or "
                    f"({shots}, {self.num_variables}); got {prior_llr.shape}"
                )
            priors = np.ascontiguousarray(priors, dtype=np.float64)

        corrections = np.zeros((shots, self.num_variables), dtype=np.uint8)
        posterior = priors.copy()
        iterations = np.zeros(shots, dtype=np.int64)
        converged = np.zeros(shots, dtype=bool)
        distances = np.zeros(shots, dtype=np.int64)
        if shots == 0:
            return BatchedBPOutput(corrections, posterior, iterations, converged, distances)

        zero_syndrome = ~np.any(syndromes, axis=1)
        converged[zero_syndrome] = True
        remaining = np.flatnonzero(~zero_syndrome)
        if remaining.size == 0 or self.num_edges == 0:
            return BatchedBPOutput(corrections, posterior, iterations, converged, distances)

        chunk = max(1, min(self.shot_budget // max(self.num_edges, 1), shots))
        for start in range(0, remaining.size, chunk):
            index = remaining[start : start + chunk]
            self._decode_chunk(
                syndromes[index],
                priors[index],
                corrections,
                posterior,
                iterations,
                converged,
                distances,
                index,
            )
        return BatchedBPOutput(corrections, posterior, iterations, converged, distances)

    # ----------------------------------------------------------------- private

    def _decode_chunk(
        self,
        syndromes: np.ndarray,
        priors: np.ndarray,
        corrections: np.ndarray,
        posterior_out: np.ndarray,
        iterations_out: np.ndarray,
        converged_out: np.ndarray,
        distances_out: np.ndarray,
        global_index: np.ndarray,
    ) -> None:
        active = np.arange(syndromes.shape[0], dtype=np.int64)
        active_syndrome = syndromes

        message_c2v = np.zeros((active.size, self.num_edges), dtype=np.float64)
        message_v2c = np.ascontiguousarray(priors[:, self.edge_variable], dtype=np.float64)

        best_correction = np.zeros((active.size, self.num_variables), dtype=np.uint8)
        best_posterior = priors.copy()
        best_distance = np.full(active.size, self.num_checks + 1, dtype=np.int64)

        for iteration in range(1, self.max_iterations + 1):
            if active.size == 0:
                break
            self._check_update(active_syndrome, message_v2c, message_c2v)
            posterior = self._posterior(priors, message_c2v)
            message_v2c = posterior[:, self.edge_variable] - message_c2v

            correction = (posterior < 0.0).astype(np.uint8)
            residual = self._residual(correction)
            distance = np.count_nonzero(residual ^ active_syndrome, axis=1)

            improved = distance < best_distance
            if np.any(improved):
                best_distance[improved] = distance[improved]
                best_correction[improved] = correction[improved]
                best_posterior[improved] = posterior[improved]

            done = distance == 0
            if np.any(done):
                rows = active[done]
                corrections[global_index[rows]] = correction[done]
                posterior_out[global_index[rows]] = posterior[done]
                iterations_out[global_index[rows]] = iteration
                converged_out[global_index[rows]] = True
                distances_out[global_index[rows]] = 0

            keep = ~done
            if not np.any(keep):
                active = active[:0]
                active_syndrome = active_syndrome[:0]
                break
            if np.any(done):
                active = active[keep]
                active_syndrome = active_syndrome[keep]
                message_c2v = message_c2v[keep]
                message_v2c = message_v2c[keep]
                priors = priors[keep]
                best_correction = best_correction[keep]
                best_posterior = best_posterior[keep]
                best_distance = best_distance[keep]

        if active.size:
            rows = active
            corrections[global_index[rows]] = best_correction
            posterior_out[global_index[rows]] = best_posterior
            iterations_out[global_index[rows]] = self.max_iterations
            converged_out[global_index[rows]] = False
            distances_out[global_index[rows]] = best_distance

    def _check_update(
        self,
        syndromes: np.ndarray,
        message_v2c: np.ndarray,
        message_c2v: np.ndarray,
    ) -> None:
        """Writes check-to-variable messages for the active shots."""

        padded = message_v2c[:, self.check_pad_edge]
        magnitudes = np.abs(padded)
        magnitudes = np.where(self._pad_active, magnitudes, np.inf)
        signs = np.where(padded < 0.0, -1.0, 1.0)
        signs = np.where(self._pad_active, signs, 1.0)

        if magnitudes.shape[2] > 1:
            partitioned = np.partition(magnitudes, 1, axis=2)
            min1 = partitioned[:, :, 0]
            min2 = partitioned[:, :, 1]
        else:
            min1 = magnitudes[:, :, 0]
            min2 = min1
        first_min = np.argmin(magnitudes, axis=2)
        position = np.arange(magnitudes.shape[2])[None, None, :]
        min_excluding = np.where(position == first_min[:, :, None], min2[:, :, None], min1[:, :, None])

        base_sign = np.where(syndromes.astype(bool), -1.0, 1.0)[:, :, None] * np.prod(
            signs, axis=2
        )[:, :, None]
        new_messages = self.min_sum_scaling * base_sign * signs * min_excluding

        degree_one = self.check_matrix.sum(axis=1) == 1
        if np.any(degree_one):
            override = _DEGREE_ONE_MESSAGE * base_sign
            new_messages = np.where(degree_one[None, :, None], override, new_messages)

        if self.damping:
            previous = message_c2v[:, self.check_pad_edge]
            new_messages = self.damping * previous + (1.0 - self.damping) * new_messages

        flat = new_messages.reshape(new_messages.shape[0], -1)
        index = self.check_pad_edge.reshape(-1)
        mask = self.check_pad_mask.reshape(-1)
        if mask.all():
            message_c2v[:, index] = flat
        else:
            message_c2v[:, index[mask]] = flat[:, mask]

    def _posterior(self, priors: np.ndarray, message_c2v: np.ndarray) -> np.ndarray:
        ordered = message_c2v[:, self.variable_edge_order]
        totals = np.zeros((priors.shape[0], self.num_variables), dtype=np.float64)
        if self.num_edges:
            summed = np.add.reduceat(ordered, self.variable_starts, axis=1)
            totals[:, self.variable_has_edges] = summed
        return priors + totals

    def _residual(self, correction: np.ndarray) -> np.ndarray:
        padded = correction[:, self.check_pad_variable]
        padded = np.where(self._pad_active, padded, 0).astype(np.uint8)
        return np.bitwise_xor.reduce(padded, axis=2)
