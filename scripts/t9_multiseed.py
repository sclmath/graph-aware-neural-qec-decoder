r"""Aggregate a T9 ablation series over independent seeds.

Reads every ``results/t9/<prefix>*`` directory that holds an ``ablation.json``
(seed 0 = unsuffixed directory, further seeds = ``_seedNN`` suffix) and reports

* a pooled LER over all shots (one number, all seeds merged), and
* the **paired per-seed** delta against the ``all`` arm together with the
  cross-seed mean +- standard error.

The second table is the one to quote: seeds -- not shots -- are the unit of
replication here.  Pooling shots across seeds pretends the seed-to-seed spread
is only binomial noise, which understates the uncertainty (measured spread at
32768 shots is ~+-15%, far above the binomial standard error).

Usage:
    .\.venv\Scripts\python.exe scripts\t9_multiseed.py `
        --prefix repetition_d3 --output results\t9\REPETITION_D3_MULTISEED.md
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Sequence


def seed_of(name: str, prefix: str) -> int:
    if not name.startswith(prefix):
        raise ValueError(name)
    match = re.search(r"_seed([0-9]+)$", name)
    return int(match.group(1)) if match else 0


def collect(results_dir: Path, prefix: str) -> list[tuple[int, dict[str, Any]]]:
    runs: list[tuple[int, dict[str, Any]]] = []
    for directory in sorted(results_dir.iterdir()):
        if not directory.is_dir() or not directory.name.startswith(prefix):
            continue
        study = directory / "ablation.json"
        if not study.exists():
            continue
        summary = json.loads(study.read_text(encoding="utf-8"))
        runs.append(
            (
                int(summary.get("seed_offset", seed_of(directory.name, prefix))),
                summary,
            )
        )
    runs.sort(key=lambda run: run[0])
    return runs


def arm_row(summary: dict[str, Any], arm: str) -> dict[str, Any] | None:
    return next((row for row in summary["rows"] if row["arm"] == arm), None)


def pooled(rows: Sequence[dict[str, Any]]) -> tuple[float, float, int, int]:
    shots = sum(int(row["shots"]) for row in rows)
    errors = sum(int(row["logical_errors"]) for row in rows)
    rate = errors / shots if shots else float("nan")
    error = math.sqrt(rate * (1.0 - rate) / shots) if shots else float("nan")
    return rate, error, errors, shots


def mean_se(values: Sequence[float]) -> tuple[float, float]:
    count = len(values)
    if count == 0:
        return float("nan"), float("nan")
    mean = sum(values) / count
    if count < 2:
        return mean, float("nan")
    variance = sum((value - mean) ** 2 for value in values) / (count - 1)
    return mean, math.sqrt(variance / count)


def markdown(prefix: str, runs: list[tuple[int, dict[str, Any]]]) -> str:
    arms: list[str] = []
    for _, summary in runs:
        for row in summary["rows"]:
            if row["arm"] not in arms:
                arms.append(row["arm"])
    # Arms that exist in every seed (the newer seeds only run a subset).
    common = [arm for arm in arms
              if all(arm_row(summary, arm) is not None for _, summary in runs)]
    lines = [
        f"# T9 多种子汇总 · {prefix}",
        "",
        "由 `scripts/t9_multiseed.py` 自动生成，勿手改。",
        "",
        f"使用 {len(runs)} 个 seed（offset " + ", ".join(str(seed) for seed, _ in runs) + "）。",
        "**跨 seed 的配对表是推断口径**：种子才是重复单位，把各 seed 的 shot 直接",
        "求和会把种子间散布（32768 shots 下实测 ±15%）当成二项噪声，从而高估显著性。",
        "",
        "## 1. 跨 seed 配对（推荐引用）",
        "",
        "| 消融臂 | 逐 seed ΔLER vs all | 跨 seed 均值 ± SE | 相对 all |",
        "|---|---|---:|---:|",
    ]
    for arm in common:
        deltas: list[float] = []
        cells: list[str] = []
        for seed, summary in runs:
            row = arm_row(summary, arm)
            base = arm_row(summary, "all")
            delta = float(row["logical_error_rate"]) - float(base["logical_error_rate"])
            deltas.append(delta)
            cells.append(f"seed {seed}: {delta:+.5f}")
        mean, error = mean_se(deltas)
        base_rate = pooled([arm_row(summary, "all") for _, summary in runs])[0]
        relative = f"{mean / base_rate * 100:+.1f}%" if arm != "all" else "—"
        lines.append(
            f"| `{arm}` | " + "；".join(cells) + f" | {mean:+.5f} ± {error:.5f} | {relative} |"
        )
    lines += [
        "",
        "## 2. 合并口径（仅作整体尺度参考）",
        "",
        "| 消融臂 | LER（pooled） | 标准误 | 逻辑错误 | shots | Δ vs all | 机制 AUC 范围 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for arm in arms:
        rows = [arm_row(summary, arm) for _, summary in runs]
        present = [row for row in rows if row is not None]
        rate, error, errors, shots = pooled(present)
        baseline = pooled([arm_row(summary, "all") for _, summary in runs])[0]
        delta = f"{(rate / baseline - 1.0) * 100:+.1f}%" if arm != "all" else "—"
        aucs = [float(row["mechanism_auc"]) for row in present]
        note = "" if len(present) == len(runs) else f"（仅 {len(present)}/{len(runs)} seeds）"
        lines.append(
            f"| `{arm}`{note} | {rate:.5f} | {error:.5f} | {errors} | {shots} | {delta} | "
            f"{min(aucs):.4f}-{max(aucs):.4f} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=Path("results/t9"))
    parser.add_argument("--prefix", type=str, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    runs = collect(args.results_dir, args.prefix)
    if not runs:
        raise SystemExit(f"no {args.prefix}* ablation.json under {args.results_dir}")
    text = markdown(args.prefix, runs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
