#!/usr/bin/env python3
r"""Estimates the decoder threshold from LER-versus-p sweeps.

Reads one or more sweep records (``surface_sweep.json``/``.csv`` shapes, or any
list of records with ``distance``, ``noise_model``, ``physical_error_rate`` and
``logical_error_rate``) and reports, per noise model and decoder, where the
LER ordering between the two smallest code distances flips. That crossing is the
threshold bracket the sweeps can resolve.

Usage:
    .\.venv\Scripts\python.exe scripts\threshold_estimate.py `
        --inputs results\m4\surface_sweep.json results\m4_threshold\surface_sweep.json `
        --output results\m4\THRESHOLD.md
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Sequence


def load(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return list(payload)
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            {
                "distance": int(row["distance"]),
                "noise_model": row["noise_model"],
                "physical_error_rate": float(row["physical_error_rate"]),
                "decoder": row["decoder"],
                "shots": int(row["shots"]),
                "logical_error_rate": float(row["logical_error_rate"]),
                "logical_error_rate_standard_error": float(
                    row["logical_error_rate_standard_error"] or 0.0
                ),
            }
            for row in csv.DictReader(handle)
        ]


def merge(paths: Sequence[Path]) -> dict[tuple[str, str], dict[tuple[int, float], dict[str, Any]]]:
    """Indexes records by (noise_model, decoder) -> (distance, rate) -> record.

    Repeated measurements of the same point keep the one with the most shots.
    """

    index: dict[tuple[str, str], dict[tuple[int, float], dict[str, Any]]] = {}
    for path in paths:
        for record in load(path):
            key = (str(record["noise_model"]), str(record["decoder"]))
            point = (int(record["distance"]), round(float(record["physical_error_rate"]), 6))
            bucket = index.setdefault(key, {})
            previous = bucket.get(point)
            if previous is None or int(record.get("shots", 0)) > int(previous.get("shots", 0)):
                bucket[point] = record
    return index


def bracket(points: list[tuple[float, float]]) -> tuple[float, float, float] | None:
    """Returns (p_lo, p_hi, fraction) where the LER ordering flips."""

    for (p_lo, delta_lo), (p_hi, delta_hi) in zip(points, points[1:]):
        if delta_lo == 0.0 or delta_hi == 0.0:
            continue
        if (delta_lo > 0) != (delta_hi > 0):
            fraction = abs(delta_lo) / (abs(delta_lo) + abs(delta_hi))
            return p_lo, p_hi, fraction
    return None


def render(index: dict[tuple[str, str], dict[tuple[int, float], dict[str, Any]]], shots_note: str) -> str:
    lines = [
        "# 阈值估计",
        "",
        "由 `scripts/threshold_estimate.py` 从 LER-p 扫描结果自动生成，请勿手工编辑。",
        "判据：两个最小码距的 LER 排序在哪一段噪声率之间翻转；该区间即扫描能分辨的阈值范围。",
        "",
        ">" + shots_note,
        "",
    ]
    for (noise_model, decoder), bucket in sorted(index.items()):
        distances = sorted({distance for distance, _ in bucket})
        if len(distances) < 2:
            continue
        low, high = distances[0], distances[1]
        rates = sorted({rate for _, rate in bucket})
        rows = []
        deltas = []
        for rate in rates:
            entry_low = bucket.get((low, rate))
            entry_high = bucket.get((high, rate))
            if entry_low is None or entry_high is None:
                continue
            ler_low = float(entry_low["logical_error_rate"])
            ler_high = float(entry_high["logical_error_rate"])
            shots = int(min(entry_low.get("shots", 0), entry_high.get("shots", 0)))
            deltas.append((rate, ler_low - ler_high))
            marker = "d%d 更优" % low if ler_low < ler_high else "d%d 更优" % high
            rows.append((rate, ler_low, ler_high, shots, marker))

        lines += [
            "## %s / %s" % (noise_model, decoder),
            "",
            "| p | LER d=%d | LER d=%d | shots | 更优的码距 |" % (low, high),
            "|---:|---:|---:|---:|---|",
        ]
        for rate, ler_low, ler_high, shots, marker in rows:
            lines.append("| {:g} | {:.5f} | {:.5f} | {} | {} |".format(rate, ler_low, ler_high, shots, marker))
        result = bracket(deltas)
        lines.append("")
        if result is None:
            lines.append(
                "**未观测到排序翻转**：在采样区间 {:.3g}-{:.3g} 内，d={} 始终优于 d={}（或始终相反）。"
                "阈值落在采样区间之外，需要扩展噪声率范围。".format(
                    rates[0], rates[-1], low, high
                )
            )
        else:
            p_lo, p_hi, fraction = result
            estimate = p_lo + fraction * (p_hi - p_lo)
            lines.append(
                "**阈值区间：{:.3g} < p_th < {:.3g}**（线性插值估计 {:.3g}）".format(p_lo, p_hi, estimate)
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, default=Path("results/m4/THRESHOLD.md"))
    args = parser.parse_args(argv)

    index = merge(args.inputs)
    note = "数据来源：" + "、".join("`{}`".format(path.as_posix()) for path in args.inputs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(index, note), encoding="utf-8", newline="\n")
    print("wrote", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())