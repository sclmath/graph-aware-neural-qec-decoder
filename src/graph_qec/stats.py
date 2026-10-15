"""Paired statistical tests shared by the analysis scripts."""

from __future__ import annotations

import math
from math import exp, lgamma, log
from typing import Any

import numpy as np


def mcnemar(only_a: int, only_b: int) -> dict[str, float]:
    """Two-sided McNemar test, normal approximation plus an exact binomial p."""

    if only_a + only_b == 0:
        return {"b": 0, "c": 0, "z": 0.0, "p_normal": 1.0, "p_exact": 1.0}
    z = (only_a - only_b) / math.sqrt(only_a + only_b)
    # Log-space binomial tail: the direct form overflows once b + c reaches a
    # few thousand, which happens on the 32768-shot runs.
    total = only_a + only_b
    tail = sum(
        exp(
            lgamma(total + 1)
            - lgamma(k + 1)
            - lgamma(total - k + 1)
            - total * log(2.0)
        )
        for k in range(0, min(only_a, only_b) + 1)
    )
    return {
        "b": int(only_a),
        "c": int(only_b),
        "z": float(z),
        "p_normal": float(math.erfc(abs(z) / math.sqrt(2.0))),
        "p_exact": float(min(1.0, 2.0 * tail)),
    }


def standard_error(errors: np.ndarray) -> float:
    """Binomial standard error of the mean of a boolean per-shot error vector."""

    rate = float(np.mean(errors)) if errors.size else 0.0
    return float(math.sqrt(max(rate * (1.0 - rate), 0.0) / errors.size)) if errors.size else 0.0


def pair_comparison(
    label_a: str,
    errors_a: np.ndarray,
    label_b: str,
    errors_b: np.ndarray,
    mask: np.ndarray | None = None,
) -> dict[str, Any]:
    """Paired comparison of two per-shot logical-error vectors."""

    if mask is not None:
        errors_a = errors_a[mask]
        errors_b = errors_b[mask]
    only_a = int(np.count_nonzero(errors_a & ~errors_b))
    only_b = int(np.count_nonzero(errors_b & ~errors_a))
    shots = int(errors_a.size)
    return {
        "a": label_a,
        "b": label_b,
        "shots": shots,
        "errors_a": int(np.count_nonzero(errors_a)),
        "errors_b": int(np.count_nonzero(errors_b)),
        "rate_a": float(np.mean(errors_a)) if shots else 0.0,
        "rate_b": float(np.mean(errors_b)) if shots else 0.0,
        "standard_error_a": standard_error(errors_a),
        "standard_error_b": standard_error(errors_b),
        "only_a": only_a,
        "only_b": only_b,
        "mcnemar": mcnemar(only_a, only_b),
    }
