"""Normalized min-sum belief propagation and OSD post-processing."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import stim

from .base import DecodeResult, Decoder
from .bp_engine import BatchedMinSumBP
from .dem import DEMSystem


@dataclass(frozen=True, slots=True)
class _BPState:
    correction: np.ndarray
    posterior_llr: np.ndarray
    iterations: int
    converged: bool
    syndrome_distance: int


def _osd_correction(
    check_matrix: np.ndarray,
    syndrome: np.ndarray,
    posterior_llr: np.ndarray,
    bp_correction: np.ndarray,
    combination_sweep_order: int = 0,
    weight_llr: np.ndarray | None = None,
) -> tuple[np.ndarray, int]:
    """Returns an OSD correction and the rank of the selected basis.

    ``combination_sweep_order == 0`` is classic OSD-0: the columns are sorted by
    descending posterior reliability, Gaussian elimination picks a pivot basis,
    and the non-pivot columns keep the BP hard decision.

    For ``combination_sweep_order = lam > 0`` the decoder additionally sweeps
    every subset of the ``lam`` least reliable non-pivot columns (a
    combination sweep, i.e. OSD-CS(lam)) and keeps the candidate of smallest
    soft weight ``sum_i |posterior_llr_i|``. The sweep is what lets the decoder
    look past the per-mechanism marginal: it explores *which bits form a
    solvable basis*, not just how likely each bit is.
    """

    num_checks, num_errors = check_matrix.shape
    reliability_order = np.argsort(-np.abs(posterior_llr), kind="stable")
    matrix = check_matrix[:, reliability_order].copy()
    transformed_syndrome = np.asarray(syndrome, dtype=np.uint8).copy()

    pivot_rows: list[int] = []
    pivot_columns: list[int] = []
    next_row = 0
    for column in range(num_errors):
        candidates = np.flatnonzero(matrix[next_row:, column])
        if candidates.size == 0:
            continue
        pivot_row = next_row + int(candidates[0])
        if pivot_row != next_row:
            matrix[[next_row, pivot_row], :] = matrix[[pivot_row, next_row], :]
            transformed_syndrome[[next_row, pivot_row]] = transformed_syndrome[
                [pivot_row, next_row]
            ]
            pivot_row = next_row

        rows_to_eliminate = np.flatnonzero(matrix[:, column])
        rows_to_eliminate = rows_to_eliminate[rows_to_eliminate != pivot_row]
        if rows_to_eliminate.size:
            matrix[rows_to_eliminate, :] ^= matrix[pivot_row, :]
            transformed_syndrome[rows_to_eliminate] ^= transformed_syndrome[pivot_row]

        pivot_rows.append(pivot_row)
        pivot_columns.append(column)
        next_row += 1
        if next_row == num_checks:
            break

    correction = np.ascontiguousarray(bp_correction, dtype=np.uint8).copy()
    rank = len(pivot_rows)
    pivot_columns_array = np.asarray(pivot_columns, dtype=np.int64)
    nonpivot_columns = np.setdiff1d(
        np.arange(num_errors, dtype=np.int64),
        pivot_columns_array,
        assume_unique=False,
    )
    residual = (
        transformed_syndrome.astype(np.int64)
        ^ (matrix[:, nonpivot_columns].astype(np.int64)
           @ correction[reliability_order[nonpivot_columns]].astype(np.int64))
    ) % 2

    for ordered_column, pivot_row in zip(pivot_columns, pivot_rows):
        original_column = int(reliability_order[ordered_column])
        correction[original_column] = int(residual[pivot_row])

    if combination_sweep_order <= 0 or rank == 0 or nonpivot_columns.size == 0:
        return correction, rank

    # ---- combination sweep (OSD-CS) -----------------------------------------
    order = min(int(combination_sweep_order), int(nonpivot_columns.size), 12)
    weight_source = posterior_llr if weight_llr is None else weight_llr
    weights = np.abs(np.asarray(weight_source, dtype=np.float64))
    nonpivot_weights = weights[reliability_order[nonpivot_columns]]
    sweep_order = np.argsort(nonpivot_weights, kind="stable")[:order]
    sweep_positions = nonpivot_columns[sweep_order]

    pivot_rows_array = np.asarray(pivot_rows, dtype=np.int64)
    base_nonpivot = correction[reliability_order[nonpivot_columns]].astype(np.int64)
    pivot_block = matrix[np.ix_(pivot_rows_array, nonpivot_columns)].astype(np.int64)
    base_pivot = (
        transformed_syndrome[pivot_rows_array].astype(np.int64)
        ^ (pivot_block @ base_nonpivot)
    ) % 2

    sweep_block = matrix[np.ix_(pivot_rows_array, sweep_positions)].astype(np.uint8)

    # Weight change for flipping one non-pivot bit.
    nonpivot_delta = np.where(
        base_nonpivot[sweep_order] == 0,
        weights[reliability_order[sweep_positions]],
        -weights[reliability_order[sweep_positions]],
    )
    # Weight change for flipping one pivot bit.
    pivot_delta = np.where(
        base_pivot == 0,
        weights[reliability_order[pivot_columns_array]],
        -weights[reliability_order[pivot_columns_array]],
    )

    best_delta = np.zeros(rank, dtype=np.uint8)
    best_gray = 0
    best_change = 0.0
    current_delta = np.zeros(rank, dtype=np.uint8)
    subset_change = 0.0
    previous_gray = 0
    for step in range(1, 1 << order):
        gray = step ^ (step >> 1)
        changed_bit = (gray ^ previous_gray).bit_length() - 1
        current_delta = current_delta ^ sweep_block[:, changed_bit]
        if (gray >> changed_bit) & 1:
            subset_change += float(nonpivot_delta[changed_bit])
        else:
            subset_change -= float(nonpivot_delta[changed_bit])
        pivot_change = float(pivot_delta[current_delta.astype(bool)].sum())
        total_change = subset_change + pivot_change
        if total_change < best_change:
            best_change = total_change
            best_delta = current_delta.copy()
            best_gray = gray
        previous_gray = gray

    if best_gray:
        best_nonpivot = base_nonpivot.copy()
        for bit in range(order):
            if (best_gray >> bit) & 1:
                best_nonpivot[sweep_order[bit]] ^= 1
        best_pivot = base_pivot ^ best_delta.astype(np.int64)
        correction[reliability_order[nonpivot_columns]] = best_nonpivot.astype(np.uint8)
        correction[reliability_order[pivot_columns_array]] = best_pivot.astype(np.uint8)

    return correction, rank


def _osd0_correction(
    check_matrix: np.ndarray,
    syndrome: np.ndarray,
    posterior_llr: np.ndarray,
    bp_correction: np.ndarray,
) -> tuple[np.ndarray, int]:
    """Backwards-compatible OSD-0 entry point."""

    return _osd_correction(check_matrix, syndrome, posterior_llr, bp_correction, 0)


class BPDecoder(Decoder):
    """Normalized min-sum BP on the raw, possibly hyperedge, DEM."""

    name = "bp"

    def __init__(
        self,
        detector_error_model: stim.DetectorErrorModel,
        *,
        max_iterations: int = 32,
        min_sum_scaling: float = 0.75,
        damping: float = 0.0,
    ) -> None:
        self.system = DEMSystem.from_detector_error_model(detector_error_model)
        if max_iterations < 1:
            raise ValueError("max_iterations must be positive")
        if not 0.0 < min_sum_scaling <= 1.0:
            raise ValueError("min_sum_scaling must be in (0, 1]")
        if not 0.0 <= damping < 1.0:
            raise ValueError("damping must be in [0, 1)")
        self.max_iterations = int(max_iterations)
        self.min_sum_scaling = float(min_sum_scaling)
        self.damping = float(damping)

        probabilities = np.clip(self.system.priors, 1e-12, 1.0 - 1e-12)
        self.prior_llr = np.log((1.0 - probabilities) / probabilities)
        self.check_to_variables = tuple(
            np.flatnonzero(self.system.check_matrix[check, :]).astype(np.int64)
            for check in range(self.system.num_detectors)
        )
        self.variable_to_checks = tuple(
            np.flatnonzero(self.system.check_matrix[:, variable]).astype(np.int64)
            for variable in range(self.system.num_errors)
        )
        super().__init__(
            num_detectors=self.system.num_detectors,
            num_observables=self.system.num_observables,
        )

    def _decode_shot(
        self,
        syndrome: np.ndarray,
        prior_llr: np.ndarray | None = None,
    ) -> _BPState:
        """Runs BP for one shot.

        ``prior_llr`` optionally overrides the DEM-derived prior log-likelihood
        ratios, which is how M2 feeds learned (syndrome-conditioned) priors back
        into the same BP machinery.
        """

        if prior_llr is None:
            prior_log_odds = self.prior_llr
        else:
            prior_log_odds = np.asarray(prior_llr, dtype=np.float64)
            if prior_log_odds.shape != (self.system.num_errors,):
                raise ValueError(
                    f"prior_llr must have shape ({self.system.num_errors},); "
                    f"got {prior_log_odds.shape}"
                )

        syndrome = np.asarray(syndrome, dtype=np.uint8)
        if not np.any(syndrome):
            return _BPState(
                correction=np.zeros(self.system.num_errors, dtype=np.uint8),
                posterior_llr=prior_log_odds.copy(),
                iterations=0,
                converged=True,
                syndrome_distance=0,
            )

        message_c2v = np.zeros(
            (self.system.num_detectors, self.system.num_errors),
            dtype=np.float64,
        )
        message_v2c = np.zeros_like(message_c2v)
        for variable, checks in enumerate(self.variable_to_checks):
            message_v2c[checks, variable] = prior_log_odds[variable]

        best_correction = np.zeros(self.system.num_errors, dtype=np.uint8)
        best_posterior = prior_log_odds.copy()
        best_distance = self.system.num_detectors + 1
        iterations_used = 0

        for iteration in range(1, self.max_iterations + 1):
            iterations_used = iteration

            for check, variables in enumerate(self.check_to_variables):
                if variables.size == 0:
                    continue
                incoming = message_v2c[check, variables]
                signs = np.where(incoming < 0.0, -1.0, 1.0)
                parity_sign = -1.0 if syndrome[check] else 1.0
                base_sign = parity_sign * float(np.prod(signs))

                if variables.size == 1:
                    new_messages = np.asarray([20.0 * base_sign], dtype=np.float64)
                else:
                    # Textbook self-excluded min-sum: the message to variable j is
                    # scaled by min_{k != j} |m_k|. Leaving |m_j| in place for
                    # j != argmin would feed a variable its own magnitude back.
                    magnitudes = np.abs(incoming)
                    order = np.argsort(magnitudes, kind="stable")
                    smallest = int(order[0])
                    min1 = float(magnitudes[smallest])
                    min2 = float(magnitudes[int(order[1])])
                    min_excluding = np.full_like(magnitudes, min1)
                    min_excluding[smallest] = min2
                    signs_excluding = base_sign * signs
                    new_messages = (
                        self.min_sum_scaling * signs_excluding * min_excluding
                    )

                if self.damping:
                    new_messages = (
                        self.damping * message_c2v[check, variables]
                        + (1.0 - self.damping) * new_messages
                    )
                message_c2v[check, variables] = new_messages

            # The posterior must be anchored on the *effective* prior: a caller
            # supplied override (learned reweighting) has to reach the decision,
            # not just the variable-to-check initialisation.
            posterior = prior_log_odds.copy()
            for variable, checks in enumerate(self.variable_to_checks):
                if checks.size:
                    posterior[variable] += float(np.sum(message_c2v[checks, variable]))

            for variable, checks in enumerate(self.variable_to_checks):
                if checks.size:
                    message_v2c[checks, variable] = (
                        posterior[variable] - message_c2v[checks, variable]
                    )

            correction = (posterior < 0.0).astype(np.uint8)
            residual = (
                self.system.check_matrix.astype(np.int64)
                @ correction.astype(np.int64)
            ) % 2
            distance = int(np.count_nonzero(residual ^ syndrome))
            if distance < best_distance:
                best_distance = distance
                best_correction = correction.copy()
                best_posterior = posterior.copy()
            if distance == 0:
                return _BPState(
                    correction=correction,
                    posterior_llr=posterior,
                    iterations=iteration,
                    converged=True,
                    syndrome_distance=0,
                )

        return _BPState(
            correction=best_correction,
            posterior_llr=best_posterior,
            iterations=iterations_used,
            converged=False,
            syndrome_distance=best_distance,
        )

    def _engine(self) -> BatchedMinSumBP:
        """Returns the cached shot-vectorized message-passing engine."""

        engine = getattr(self, "_batched_engine", None)
        if engine is None:
            engine = BatchedMinSumBP(
                self.system.check_matrix,
                self.system.priors,
                max_iterations=self.max_iterations,
                min_sum_scaling=self.min_sum_scaling,
                damping=self.damping,
            )
            self._batched_engine = engine
        return engine

    def decode_batch(
        self,
        detections: np.ndarray,
        prior_llr: np.ndarray | None = None,
    ) -> DecodeResult:
        """Decodes a batch, optionally with per-shot prior log-odds overrides.

        Shots are decoded with the vectorized engine in
        :mod:`graph_qec.decoders.bp_engine`, which runs the same normalized
        min-sum update as :meth:`_decode_shot` for every shot at once.
        """

        detections = self._validate_detections(detections)
        if prior_llr is not None:
            prior_llr = np.asarray(prior_llr, dtype=np.float64)
            expected = (detections.shape[0], self.system.num_errors)
            if prior_llr.shape != expected:
                raise ValueError(
                    f"prior_llr must have shape {expected}; got {prior_llr.shape}"
                )

        output = self._engine().decode(detections, prior_llr)
        shots = detections.shape[0]
        predictions = (self.system.observable_matrix @ output.corrections.T) % 2
        predictions = np.ascontiguousarray(predictions.T, dtype=np.uint8)
        result = DecodeResult(
            predictions=predictions,
            corrections=output.corrections,
            diagnostics={
                "average_iterations": float(output.iterations.sum()) / shots
                if shots
                else 0.0,
                "converged_shots": int(np.count_nonzero(output.converged)),
                "convergence_rate": float(np.mean(output.converged)) if shots else 0.0,
                "average_final_syndrome_distance": float(output.syndrome_distance.mean())
                if shots
                else 0.0,
                "prior_llr_override": prior_llr is not None,
                "engine": "batched_min_sum",
            },
        )
        return self._validate_result(result, predictions.shape)


class BPOSDDecoder(BPDecoder):
    """BP followed by OSD-0 / OSD-CS for shots where BP does not converge."""

    name = "bp_osd"

    def __init__(
        self,
        detector_error_model: stim.DetectorErrorModel,
        *,
        max_iterations: int = 32,
        min_sum_scaling: float = 0.75,
        damping: float = 0.0,
        osd_order: int = 0,
        combination_sweep_order: int = 0,
        force_osd: bool = False,
    ) -> None:
        if int(osd_order) < 0:
            raise ValueError("osd_order must be non-negative")
        if int(combination_sweep_order) < 0:
            raise ValueError("combination_sweep_order must be non-negative")
        self.osd_order = int(osd_order)
        self.combination_sweep_order = int(combination_sweep_order)
        self.force_osd = bool(force_osd)
        super().__init__(
            detector_error_model,
            max_iterations=max_iterations,
            min_sum_scaling=min_sum_scaling,
            damping=damping,
        )

    def decode_batch(
        self,
        detections: np.ndarray,
        prior_llr: np.ndarray | None = None,
        osd_ordering_llr: np.ndarray | None = None,
    ) -> DecodeResult:
        """BP followed by OSD-0 for non-converged shots.

        ``prior_llr`` overrides the BP priors. ``osd_ordering_llr`` overrides
        only the reliability order used to pick OSD pivot columns, which lets a
        learned model propose the candidate basis without changing BP dynamics.
        """

        detections = self._validate_detections(detections)
        if prior_llr is not None:
            prior_llr = np.asarray(prior_llr, dtype=np.float64)
            expected = (detections.shape[0], self.system.num_errors)
            if prior_llr.shape != expected:
                raise ValueError(
                    f"prior_llr must have shape {expected}; got {prior_llr.shape}"
                )
        if osd_ordering_llr is not None:
            osd_ordering_llr = np.asarray(osd_ordering_llr, dtype=np.float64)
            expected = (detections.shape[0], self.system.num_errors)
            if osd_ordering_llr.shape != expected:
                raise ValueError(
                    f"osd_ordering_llr must have shape {expected}; "
                    f"got {osd_ordering_llr.shape}"
                )
        output = self._engine().decode(detections, prior_llr)
        corrections = np.ascontiguousarray(output.corrections, dtype=np.uint8).copy()
        total_iterations = float(output.iterations.sum())
        converged_shots = int(np.count_nonzero(output.converged))
        osd_shots = 0
        total_osd_rank = 0

        needs_osd = (~output.converged) | self.force_osd
        for shot in np.flatnonzero(needs_osd):
            ordering = (
                output.posterior_llr[shot]
                if osd_ordering_llr is None
                else osd_ordering_llr[shot]
            )
            correction, rank = _osd_correction(
                self.system.check_matrix,
                detections[shot],
                ordering,
                output.corrections[shot],
                self.combination_sweep_order,
            )
            corrections[shot] = correction
            osd_shots += 1
            total_osd_rank += rank

        predictions = (self.system.observable_matrix @ corrections.T) % 2
        predictions = np.ascontiguousarray(predictions.T, dtype=np.uint8)
        shots = detections.shape[0]
        result = DecodeResult(
            predictions=predictions,
            corrections=corrections,
            diagnostics={
                "average_iterations": total_iterations / shots,
                "converged_shots": converged_shots,
                "convergence_rate": converged_shots / shots,
                "osd_shots": osd_shots,
                "osd_rate": osd_shots / shots,
                "average_osd_rank": total_osd_rank / osd_shots
                if osd_shots
                else 0.0,
                "osd_order": self.osd_order,
                "combination_sweep_order": self.combination_sweep_order,
                "prior_llr_override": prior_llr is not None,
                "osd_ordering_override": osd_ordering_llr is not None,
                "forced_osd": self.force_osd,
                "engine": "batched_min_sum",
            },
        )
        return self._validate_result(result, predictions.shape)
