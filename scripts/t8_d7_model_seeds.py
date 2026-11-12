r"""Aggregate the T8 d=7 OSD-CS probes over *model* seeds (model + data both vary).

``scripts/t8_d7_multiseed.py`` pools several independent 1024-shot test splits of
the **same** checkpoint, so it only shrinks the LER estimation error; the headline
OSD-CS gain could still be a property of that one model.  This script instead uses
one directory per (noise rate, model seed) -- each with its own ``model_state.pt``
and its own test split -- and reports the per-seed delta plus the cross-seed mean
+- SE, with the **seed** (not the shot) as the unit of replication.

Directory convention (one directory per (rate, model seed))::

    results/t8/d7_p0p003_probe            # model seed 1 = the grid's s1 run
    results/t8/d7_p0p003_probe_s2model    # model seed 2 = the grid's s2 run
    results/t8/d7_p0p003_probe_s3model    # model seed 3 = the grid's s3 run

The model-seed suffix deliberately does not match the regex used by
``t8_d7_multiseed.py`` (``_probe_s<offset>``), so the test-set-only table stays
clean and the two conventions never get mixed.

Usage:
    .\.venv\Scripts\python.exe scripts\t8_d7_model_seeds.py --probe-root results\t8 --output results\t8\D7_MODEL_SEEDS.md
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Sequence

NAME = re.compile(r"^d7_(p0p[0-9]+)_probe(?:_s(?P<model>[0-9])model)?$")

DECODERS = ("mwpm", "bp", "bp_gnn", "bp_gnn_osd_cs0", "bp_gnn_osd_cs4")
PAIRS = (
    ("bp_gnn", "bp_gnn_osd_cs0"),
    ("bp_gnn_osd_cs0", "bp_gnn_osd_cs4"),
    ("bp_gnn", "bp_gnn_osd_cs4"),
    ("bp", "bp_gnn_osd_cs4"),
)
MODEL_SEEDS = (1, 2, 3)


def rate_from_tag(tag: str) -> float:
    return float("0." + tag[3:])


def collect(root: Path) -> dict[float, dict[int, dict[str, Any]]]:
    groups: dict[float, dict[int, dict[str, Any]]] = {}
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
        model_seed = int(match.group("model") or 1)
        groups.setdefault(rate_from_tag(match.group(1)), {})[model_seed] = {
            "dir": directory.name,
            "shots": int(summary["shots"]),
            "test_seeds": summary.get("test_seeds"),
            "per_decoder": summary["per_decoder"],
            "pairwise": {(pair["a"], pair["b"]): pair for pair in summary["pairwise"]},
            "non_converged_shots": summary.get("non_converged_shots"),
        }
    return groups


def mean_se(values: Sequence[float]) -> tuple[float, float]:
    count = len(values)
    if count == 0:
        return float("nan"), float("nan")
    mean = sum(values) / count
    if count < 2:
        return mean, float("nan")
    variance = sum((value - mean) ** 2 for value in values) / (count - 1)
    return mean, math.sqrt(variance / count)


def delta(run: dict[str, Any], a: str, b: str) -> float:
    """LER(a) - LER(b): negative means A makes fewer logical errors."""
    return float(run["per_decoder"][a]["logical_error_rate"]) - float(
        run["per_decoder"][b]["logical_error_rate"]
    )


def fmt(value: float, digits: int = 5) -> str:
    return "-" if value != value else f"{value:.{digits}f}"


def markdown(groups: dict[float, dict[int, dict[str, Any]]]) -> str:
    lines: list[str] = [
        "# d=7 OSD-CS 探针：模型种子与独立测试集",
        "",
        "由 `scripts/t8_d7_model_seeds.py` 自动生成，勿手改。",
        "",
        "**口径**：每个目录 = 一个**模型 seed 自己的 checkpoint**，评测用**该 seed 自己的**",
        "1024-shot 测试集（模型 seed 偏移同时移动 `training.seed` 与全部 split seed）。",
        "种子是重复单位，因此下表给逐 seed Δ 与**跨 seed 均值 ± SE**；不把不同 seed 的 shot",
        "求和（那会把模型间散布当成二项噪声）。对照：只换测试集的口径见",
        "`results/t8/D7_MULTISEED.md`（`scripts/t8_d7_multiseed.py`）。",
        "",
    ]
    for p in sorted(groups):
        by_seed = groups[p]
        found = sorted(by_seed)
        missing = [seed for seed in MODEL_SEEDS if seed not in by_seed]
        lines.append(
            f"## p = {p:g}　（{len(found)} 个模型 seed："
            + ", ".join(f"s{seed}" for seed in found)
            + f"；每 seed {by_seed[found[0]]['shots']} shots）"
        )
        lines.append("")
        if missing:
            lines.append(
                f"⚠ 缺模型 seed " + ", ".join(f"s{seed}" for seed in missing)
                + "（该噪声率下尚未跑该 seed 的探针）。"
            )
            lines.append("")
        lines.append("| 模型 seed | 目录 | bp | bp_gnn | `bp_gnn_osd_cs0` | `bp_gnn_osd_cs4` | 未收敛 shot |")
        lines.append("|---|---|---:|---:|---:|---:|---:|")
        for seed in found:
            run = by_seed[seed]
            cells = " | ".join(
                fmt(run["per_decoder"][name]["logical_error_rate"])
                for name in ("bp", "bp_gnn", "bp_gnn_osd_cs0", "bp_gnn_osd_cs4")
            )
            lines.append(
                f"| s{seed} | `{run['dir']}` | {cells} | {run['non_converged_shots']} |"
            )
        lines.append("")
        lines.append("### 跨 seed 配对（种子是重复单位）")
        lines.append("")
        lines.append("ΔLER = LER(A) − LER(B)，**负值表示 A 更好**；相对一列以该配对的 B 为基准。")
        lines.append("")
        lines.append("| 配对 | 逐 seed ΔLER | 跨 seed 均值 ± SE | 相对 B |")
        lines.append("|---|---|---:|---:|")
        for a, b in PAIRS:
            values = [delta(by_seed[seed], a, b) for seed in found]
            mean, error = mean_se(values)
            cells = " / ".join(f"{value:+.5f}" for value in values)
            reference = sum(
                float(by_seed[seed]["per_decoder"][b]["logical_error_rate"])
                for seed in found
            ) / len(found)
            lines.append(
                f"| `{a}` − `{b}` | {cells} | {mean:+.5f} ± {error:.5f} | {mean / reference * 100:+.1f}% |"
            )
        lines.append("")
        lines.append("### 每个 seed 的配对 McNemar（单份 1024-shot 测试集，仅供方向）")
        lines.append("")
        lines.append("| 模型 seed | 配对 | 只 A 错 | 只 B 错 | z |")
        lines.append("|---|---|---:|---:|---:|")
        for seed in found:
            run = by_seed[seed]
            for a, b in PAIRS:
                pair = run["pairwise"].get((a, b))
                if pair is None:
                    continue
                only_a = int(pair["only_a"])
                only_b = int(pair["only_b"])
                total = only_a + only_b
                z = 0.0 if total == 0 else (only_b - only_a) / math.sqrt(total)
                lines.append(f"| s{seed} | `{a}` vs `{b}` | {only_a} | {only_b} | {z:+.2f} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-root", type=Path, default=Path("results/t8"))
    parser.add_argument("--output", type=Path, default=Path("results/t8/D7_MODEL_SEEDS.md"))
    args = parser.parse_args(argv)

    groups = collect(args.probe_root)
    if not groups:
        raise SystemExit(
            f"no model-seed probe directories (d7_p0p*_probe[_sNmodel]) under {args.probe_root}"
        )
    text = markdown(groups)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
