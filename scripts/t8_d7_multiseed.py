r"""Aggregate the T8 d=7 OSD-CS probes over independent seeds.

Scans ``results/t8/d7_p0pXXX_probe*`` outputs (one directory per independent
1024-shot test split), groups them by physical error rate, and reports each
decoder as a pooled LER +- standard error.  The paired comparisons reuse the
per-shot discordant counts stored by the probe, which simply add up across
independent splits, so a pooled McNemar test is available without the raw
per-shot data.

Usage:
    .\.venv\Scripts\python.exe scripts\t8_d7_multiseed.py `
        --probe-root results\t8 --output results\t8\D7_MULTISEED.md
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Sequence

NAME = re.compile(r"^d7_(p0p[0-9]+)_probe(?:_s(?P<offset>[0-9]+))?$")

DECODERS = (
    "mwpm",
    "bp",
    "bp_gnn",
    "bp_gnn_osd_cs0",
    "bp_gnn_osd_cs4",
)
PAIRS = (
    ("bp_gnn", "bp_gnn_osd_cs0"),
    ("bp_gnn_osd_cs0", "bp_gnn_osd_cs4"),
    ("bp_gnn", "bp_gnn_osd_cs4"),
    ("bp", "bp_gnn_osd_cs4"),
)


def rate_from_tag(tag: str) -> float:
    return float("0." + tag[3:])


def collect(root: Path) -> dict[float, list[dict[str, Any]]]:
    groups: dict[float, list[dict[str, Any]]] = {}
    for directory in sorted(root.iterdir()):
        if not directory.is_dir():
            continue
        match = NAME.match(directory.name)
        study = directory / "study.json"
        if match is None or not study.exists():
            continue
        summary = json.loads(study.read_text(encoding="utf-8"))
        if "bp_gnn_osd_cs4" not in summary["per_decoder"]:
            continue
        groups.setdefault(rate_from_tag(match.group(1)), []).append(
            {
                "dir": directory.name,
                "offset": int(match.group("offset") or 0),
                "shots": int(summary["shots"]),
                "per_decoder": summary["per_decoder"],
                "pairwise": {
                    (pair["a"], pair["b"]): pair for pair in summary["pairwise"]
                },
                "non_converged_shots": summary.get("non_converged_shots"),
            }
        )
    for runs in groups.values():
        runs.sort(key=lambda run: run["offset"])
    return groups


def pooled(runs: Sequence[dict[str, Any]], name: str) -> tuple[float, float, int, int]:
    shots = sum(run["shots"] for run in runs)
    errors = sum(run["per_decoder"][name]["logical_errors"] for run in runs)
    rate = errors / shots if shots else float("nan")
    error = math.sqrt(rate * (1.0 - rate) / shots) if shots else float("nan")
    return rate, error, errors, shots


def pooled_mcnemar(
    runs: Sequence[dict[str, Any]], a: str, b: str
) -> dict[str, Any] | None:
    only_a = only_b = 0
    for run in runs:
        pair = run["pairwise"].get((a, b))
        if pair is None:
            return None
        only_a += int(pair["only_a"])
        only_b += int(pair["only_b"])
    if only_a + only_b == 0:
        return {"only_a": 0, "only_b": 0, "z": 0.0, "p_normal": 1.0}
    z = (only_b - only_a) / math.sqrt(only_a + only_b)
    p = math.erfc(abs(z) / math.sqrt(2.0))
    return {"only_a": only_a, "only_b": only_b, "z": z, "p_normal": p}


def fmt(value: float, digits: int = 5) -> str:
    return f"{value:.{digits}f}"


def markdown(groups: dict[float, list[dict[str, Any]]]) -> str:
    lines: list[str] = [
        "# T8 · d=7 OSD-CS 探针的多种子汇总",
        "",
        "由 `scripts/t8_d7_multiseed.py` 自动生成，勿手改。每个目录 = 一份**独立 seed",
        "偏移**的 1024-shot 测试集；同一点的多份测试集相互独立，逐 shot 错误可直接",
        "汇总求和（因此标准误与 McNemar 都是 pooled 口径）。",
        "",
    ]
    for p in sorted(groups):
        runs = groups[p]
        offsets = ", ".join(str(run["offset"]) for run in runs)
        shots = sum(run["shots"] for run in runs)
        lines.append(f"## p = {p:g}　（{len(runs)} 份测试集，seed offset {offsets}，共 {shots} shots）")
        lines.append("")
        lines.append("| decoder | LER（pooled） | 标准误 | 错误数 | 相对 bp_gnn |")
        lines.append("|---|---:|---:|---:|---:|")
        reference, _, _, _ = pooled(runs, "bp_gnn")
        for name in DECODERS:
            if name not in runs[0]["per_decoder"]:
                continue
            rate, error, errors, _ = pooled(runs, name)
            delta = f"{(rate / reference - 1.0) * 100:+.1f}%" if name != "bp_gnn" else "—"
            lines.append(f"| `{name}` | {fmt(rate)} | {fmt(error)} | {errors} | {delta} |")
        lines.append("")
        lines.append("| 配对比较（pooled McNemar） | 只 A 错 | 只 B 错 | z | p（双侧） |")
        lines.append("|---|---:|---:|---:|---:|")
        for a, b in PAIRS:
            stats = pooled_mcnemar(runs, a, b)
            if stats is None:
                continue
            lines.append(
                f"| `{a}` vs `{b}` | {stats['only_a']} | {stats['only_b']} | "
                f"{stats['z']:+.2f} | {stats['p_normal']:.4f} |"
            )
        lines.append("")
        lines.append("| 单份测试集 | seed offset | shots | bp | bp_gnn | `bp_gnn_osd_cs0` | `bp_gnn_osd_cs4` | 未收敛 shot |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
        for run in runs:
            cells = " | ".join(
                fmt(run["per_decoder"][name]["logical_error_rate"])
                for name in DECODERS
                if name != "mwpm"
            )
            lines.append(
                f"| `{run['dir']}` | {run['offset']} | {run['shots']} | {cells} | "
                f"{run['non_converged_shots']} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-root", type=Path, default=Path("results/t8"))
    parser.add_argument("--output", type=Path, default=Path("results/t8/D7_MULTISEED.md"))
    parser.add_argument("--json", type=Path, default=Path("results/t8/d7_multiseed.json"))
    args = parser.parse_args(argv)

    groups = collect(args.probe_root)
    if not groups:
        raise SystemExit(f"no probe directories under {args.probe_root}")
    text = markdown(groups)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8", newline="\n")
    payload = {
        f"p={p:g}": {
            name: dict(zip(("logical_error_rate", "standard_error", "logical_errors", "shots"),
                           pooled(runs, name)))
            for name in DECODERS
            if name in runs[0]["per_decoder"]
        }
        for p, runs in sorted(groups.items())
    }
    args.json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
