"""M5+: decompose-preserving reweighting of the matching graph.

The naive way to feed learned mechanism posteriors into MWPM is to rebuild a
detector error model from the binary ``(H, L)`` system.  That loses Stim's
suggested ``^`` decomposition of multi-detector mechanisms: hyperedges stay
hyperedges and PyMatching silently builds a *different* (denser, wrong) matching
graph, which destroys MWPM before the learned weights can help (see
``docs/M5_ENGINEERING.md`` section 5).

This module keeps the decomposed DEM's instruction structure intact and only
replaces per-instruction probabilities.  Because the decomposed DEM is a
re-encoding of the raw (undecomposed) DEM, every decomposed instruction can be
traced back to the raw error mechanism whose learned posterior should drive it:

* ``error(0.001) D2 D6 ^ D9 D13`` is *one* decomposed instruction (two pieces)
  belonging to the raw 4-detector mechanism ``D2 D6 D9 D13``;
* single-piece instructions map back to the unique raw mechanism with the same
  support whenever that support is minimal.

The mapping is a heuristic (support containment plus a minimality tie-break),
so it ships with a falsifiable check: feeding the raw DEM's *own* priors back
through the mapping must reproduce the baseline matching graph and LER.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pymatching
import stim

__all__ = [
    "DemErrorInstruction",
    "collapse_to_instructions",
    "error_instructions",
    "map_decomposed_to_raw",
    "matching_from_probabilities",
    "rewrite_probabilities",
]


@dataclass(frozen=True, slots=True)
class DemErrorInstruction:
    """One ``error`` instruction of a DEM, with its decomposition preserved."""

    detectors: tuple[int, ...]
    observables: tuple[int, ...]
    pieces: tuple[tuple[int, ...], ...]
    probability: float

    @property
    def num_pieces(self) -> int:
        return len(self.pieces)

    @property
    def is_decomposed(self) -> bool:
        return self.num_pieces > 1


def error_instructions(detector_error_model: stim.DetectorErrorModel) -> list[DemErrorInstruction]:
    """Returns every ``error`` instruction in flattened order.

    Detector targets are grouped by ``^`` separators so the suggested
    decomposition survives; observables are collected over the whole
    instruction because they are shared by all pieces.
    """

    instructions: list[DemErrorInstruction] = []
    for instruction in detector_error_model.flattened():
        if instruction.type != "error":
            continue
        args = instruction.args_copy()
        if len(args) != 1:
            raise ValueError("DEM error instructions must have exactly one probability")
        detectors: list[int] = []
        observables: list[int] = []
        pieces: list[list[int]] = [[]]
        for target in instruction.targets_copy():
            if target.is_separator():
                pieces.append([])
            elif target.is_relative_detector_id():
                value = int(target.val)
                detectors.append(value)
                pieces[-1].append(value)
            elif target.is_logical_observable_id():
                observables.append(int(target.val))
            else:
                raise ValueError(f"Unsupported DEM target: {target}")
        instructions.append(
            DemErrorInstruction(
                detectors=tuple(sorted(detectors)),
                observables=tuple(sorted(observables)),
                pieces=tuple(tuple(sorted(piece)) for piece in pieces),
                probability=float(args[0]),
            )
        )
    return instructions


def rewrite_probabilities(
    detector_error_model: stim.DetectorErrorModel,
    probabilities: np.ndarray | Sequence[float],
) -> stim.DetectorErrorModel:
    """Rebuilds a DEM with identical targets and new error probabilities.

    Separators are copied verbatim, so the rebuilt model keeps exactly the same
    decomposition as the input and is always graphlike when the input was.
    """

    values = np.asarray(probabilities, dtype=np.float64).reshape(-1)
    values = np.clip(values, 1e-9, 1.0 - 1e-9)
    flattened = detector_error_model.flattened()
    lines: list[str] = []
    index = 0
    for instruction in flattened:
        if instruction.type != "error":
            continue
        if index >= values.size:
            raise ValueError("fewer probabilities than error instructions")
        targets = " ".join(str(target) for target in instruction.targets_copy())
        lines.append(f"error({float(values[index])}) {targets}")
        index += 1
    if index != values.size:
        raise ValueError(
            f"expected {index} probabilities, received {values.size}"
        )
    lines.extend(f"detector D{index}" for index in range(flattened.num_detectors))
    lines.extend(f"logical_observable L{index}" for index in range(flattened.num_observables))
    return stim.DetectorErrorModel("\n".join(lines))


def map_decomposed_to_raw(
    raw_dem: stim.DetectorErrorModel,
    matching_dem: stim.DetectorErrorModel,
) -> tuple[np.ndarray, dict[str, float]]:
    """Maps each decomposed instruction to the raw mechanism it came from.

    Returns ``(parents, stats)`` where ``parents[j]`` is the raw mechanism index
    for decomposed instruction ``j`` (``-1`` when no candidate exists) and
    ``stats`` describes how determinate the mapping was.
    """

    raw = error_instructions(raw_dem)
    decomposed = error_instructions(matching_dem)
    parents = np.full(len(decomposed), -1, dtype=np.int64)
    raw_supports = [set(item.detectors) for item in raw]
    raw_observables = [set(item.observables) for item in raw]

    stats: dict[str, float] = {
        "raw_mechanisms": float(len(raw)),
        "decomposed_instructions": float(len(decomposed)),
        "mapped": 0.0,
        "unmapped": 0.0,
        "ambiguous": 0.0,
        "unique": 0.0,
    }

    for index, instruction in enumerate(decomposed):
        detectors = set(instruction.detectors)
        observables = set(instruction.observables)
        candidates = [
            candidate
            for candidate in range(len(raw))
            if detectors <= raw_supports[candidate]
            and observables <= raw_observables[candidate]
        ]
        if not candidates:
            stats["unmapped"] += 1.0
            continue
        smallest = min(len(raw[candidate].detectors) for candidate in candidates)
        tied = [
            candidate
            for candidate in candidates
            if len(raw[candidate].detectors) == smallest
        ]
        if len(tied) > 1:
            stats["ambiguous"] += 1.0
            # Prefer the parent whose prior is closest to the decomposed
            # instruction's own probability: Stim derives the latter from the
            # former, so this breaks ties on real evidence instead of index order.
            tied.sort(
                key=lambda candidate: abs(
                    np.log(raw[candidate].probability)
                    - np.log(instruction.probability)
                )
            )
        else:
            stats["unique"] += 1.0
        parents[index] = tied[0]
        stats["mapped"] += 1.0

    total = max(len(decomposed), 1)
    stats["unique_fraction"] = stats["unique"] / total
    stats["ambiguous_fraction"] = stats["ambiguous"] / total
    return parents, stats


def collapse_to_instructions(
    parents: np.ndarray,
    parent_probabilities: np.ndarray,
    fallback: np.ndarray,
) -> np.ndarray:
    """Picks, for each decomposed instruction, its parent's probability.

    ``parents`` has shape ``(instructions,)``; ``parent_probabilities`` has shape
    ``(shots, mechanisms)`` (or ``(mechanisms,)`` for a single set of values).
    Unmapped instructions fall back to ``fallback`` so the pipeline never
    silently drops an edge.
    """

    parents = np.asarray(parents, dtype=np.int64)
    fallback = np.asarray(fallback, dtype=np.float64)
    values = np.asarray(parent_probabilities, dtype=np.float64)
    if values.ndim == 1:
        values = values[None, :]
    collapsed = np.tile(fallback[None, :], (values.shape[0], 1))
    mapped = parents >= 0
    if np.any(mapped):
        collapsed[:, mapped] = values[:, parents[mapped]]
    return collapsed


def matching_from_probabilities(
    detector_error_model: stim.DetectorErrorModel,
    probabilities: np.ndarray | Sequence[float],
) -> pymatching.Matching:
    """Builds a matching graph from a DEM with substituted probabilities."""

    return pymatching.Matching.from_detector_error_model(
        rewrite_probabilities(detector_error_model, probabilities)
    )


def log_odds_to_probabilities(log_odds: np.ndarray) -> np.ndarray:
    """Converts BP-convention LLRs ``log((1-p)/p)`` into probabilities.

    NB: ``p = sigmoid(-llr)``. The M5 prototype used ``sigmoid(+llr)`` and
    therefore fed ``1 - p`` into every rebuilt matching graph; see
    ``docs/MWPM_REWEIGHTING.md``.
    """

    values = np.asarray(log_odds, dtype=np.float64)
    return 1.0 / (1.0 + np.exp(values))


def apply_relative_shift(
    decomposed_priors: np.ndarray,
    parents: np.ndarray,
    instruction_shifts: np.ndarray,
) -> np.ndarray:
    """Applies per-mechanism LLR shifts to a decomposed DEM's instructions.

    Stim's decomposed DEM re-scales probabilities relative to the undecomposed
    mechanisms (a hyperedge split into ``k`` graphlike pieces does not give each
    piece the mechanism's own probability).  Substituting a mechanism's
    probability verbatim therefore changes the matching graph even when the
    substitution is done with the mechanism's *own* prior.  The scale-free
    formulation is the relative one, mirroring how the learned prior is applied
    to BP in :func:`graph_qec.m2_pipeline.combined_logits`:

        llr_j = log((1 - p_j) / p_j) + shift[parent(j)]

    with ``shift = strength * (learned_llr - prior_llr)``.  A zero shift
    reproduces the DEM exactly, so strength 0 is an exact control.

    Parameters
    ----------
    decomposed_priors:
        Baseline probabilities of the decomposed instructions (shape ``(n,)``).
    parents:
        Parent mechanism index per instruction (``-1`` for unmapped
        instructions, which are left at their prior).
    instruction_shifts:
        BP-convention LLR shifts per mechanism, shape ``(mechanisms,)`` or
        ``(shots, mechanisms)``.

    Returns
    -------
    ``(shots, n)`` probabilities for the decomposed instructions.
    """

    priors = np.clip(np.asarray(decomposed_priors, dtype=np.float64), 1e-12, 1.0 - 1e-12)
    base_llr = np.log((1.0 - priors) / priors)
    parents = np.asarray(parents, dtype=np.int64)
    shifts = np.asarray(instruction_shifts, dtype=np.float64)
    if shifts.ndim == 1:
        shifts = shifts[None, :]
    out = np.tile(base_llr[None, :], (shifts.shape[0], 1))
    mapped = parents >= 0
    if np.any(mapped):
        out[:, mapped] += shifts[:, parents[mapped]]
    return 1.0 / (1.0 + np.exp(out))
