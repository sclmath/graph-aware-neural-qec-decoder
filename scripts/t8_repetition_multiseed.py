r"""Aggregate the T8 repetition d=3 OSD-CS study over independent seeds.

The original study (``results/t8/repetition_d3_circuit_level``) is a single
seed, and one of its headline claims is an *equality*: at lambda = 4 the DEM
prior and the learned prior tie (247 vs 249 errors, McNemar p = 0.53).  A tie
claim needs an error bar, so the study was repeated on the two extra M2 runs
(``results/m2/..._s10`` / ``_s20``: same shift of ``training.seed`` and every
split seed) with those runs' own configs and checkpoints, giving three fully
independent seeds.

Usage:
    .\.venv\Scripts\python.exe scripts\t8_repetition_multiseed.py `
        --output results\t8\REPETITION_D3_MULTISEED.md
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Sequence

RUNS = (
    (0, Path("results/t8/repetition_d3_circuit_level")),
    (10, Path("results/t8/repetition_d3_seed10")),
    (20, Path("results/t8/repetition_d3_seed20")),
)
DECODERS = (
    "mwpm",
    "bp",
    "bp_osd_cs0",
    "bp_osd_cs4",
    "bp_gnn",
    "bp_gnn_osd_cs0",
    "bp_gnn_osd_cs4",
)
PAIRS = (
    ("bp", "bp_osd_cs0"),
    ("bp_osd_cs0", "bp_osd_cs4"),
    ("bp", "bp_osd_cs4"),
    ("bp_gnn", "bp_gnn_osd_cs4"),
    ("bp_osd_cs4", "bp_gnn_osd_cs4"),
)


def load(offset: int, directory: Path) -> dict[str, Any]:
    study = directory / "study.json"
    if not study.exists():
        raise SystemExit(f"missing {study}")
    payload = json.loads(study.read_text(encoding="utf-8"))
    if "bp_gnn_osd_cs4" not in payload["per_decoder"]:
        raise SystemExit(f"{study} has no lambda=4 sweep")
    payload["offset"] = offset
    payload["pairwise_index"] = {
        (pair["a"], pair["b"]): pair for pair in payload["pairwise"]
    }
    return payload


def mean_se(values: Sequence[float]) -> tuple[float, float]:
    count = len(values)
    if count < 2:
        return (values[0] if count else float("nan")), float("nan")
    mean = sum(values) / count
    variance = sum((value - mean) ** 2 for value in values) / (count - 1)
    return mean, math.sqrt(variance / count)


def markdown(runs: Sequence[dict[str, Any]]) -> str:
    shots = sum(run["shots"] for run in runs)
    lines = [
        "# T8 · repetition d=3 OSD-CS 研究的多种子复核",
        "",
        "由 `scripts/t8_repetition_multiseed.py` 自动生成，勿手改。",
        f"{len(runs)} 个独立 seed（M2 运行的种子偏移 "
        + " / ".join(str(run["offset"]) for run in runs)
        + f"），每个 {runs[0]['shots']} shots，合计 {shots} shots。",
        "每个 seed 用的是**该 seed 自己训练的模型与自己的 splits**（不是只换测试集），",
        "因此这里的跨 seed 散布同时包含模型与数据方差。",
        "",
        "## 1. 逐 seed 的 LER",
        "",
        "| 解码器 | " + " | ".join(f"offset {run['offset']}" for run in runs) + " |",
        "|---|" + "---:|" * len(runs),
    ]
    for name in DECODERS:
        cells = [f"{run['per_decoder'][name]['logical_error_rate']:.5f}" for run in runs]
        lines.append(f"| `{name}` | " + " | ".join(cells) + " |")
    lines += ["", "## 2. 跨 seed 配对（种子是重复单位）", "",
              "| 配对 | 逐 seed ΔLER | 跨 seed 均值 ± SE | 相对 | 合并 McNemar |",
              "|---|---|---:|---:|---|"]
    for left, right in PAIRS:
        deltas: list[float] = []
        cells: list[str] = []
        only_left = only_right = 0
        for run in runs:
            delta = (run["per_decoder"][right]["logical_error_rate"]
                     - run["per_decoder"][left]["logical_error_rate"])
            deltas.append(delta)
            cells.append(f"{delta:+.5f}")
            pair = run["pairwise_index"][(left, right)]
            only_left += int(pair["only_a"])
            only_right += int(pair["only_b"])
        mean, error = mean_se(deltas)
        base = sum(run["per_decoder"][left]["logical_errors"] for run in runs) / shots
        z = ((only_right - only_left) / math.sqrt(only_left + only_right)
             if only_left + only_right else 0.0)
        p_value = math.erfc(abs(z) / math.sqrt(2.0))
        lines.append(
            f"| `{left}` → `{right}` | " + " / ".join(cells)
            + f" | {mean:+.5f} ± {error:.5f} | {mean / base * 100:+.1f}% "
            + f"| z={z:+.2f} (p={p_value:.3g}) |"
        )
    lines += ["", "## 3. 合并口径（整体尺度）", "",
              "| 解码器 | LER（pooled） | 标准误 | 逻辑错误 |", "|---|---:|---:|---:|"]
    for name in DECODERS:
        errors = sum(run["per_decoder"][name]["logical_errors"] for run in runs)
        rate = errors / shots
        lines.append(f"| `{name}` | {rate:.5f} | "
                     f"{math.sqrt(rate * (1 - rate) / shots):.5f} | {errors} |")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path("results/t8/REPETITION_D3_MULTISEED.md"))
    args = parser.parse_args(argv)

    runs = [load(offset, directory) for offset, directory in RUNS]
    text = markdown(runs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
