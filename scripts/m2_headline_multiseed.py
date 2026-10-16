r"""Extra seeds for the M2 flagship run, plus its multi-seed aggregation.

The flagship same-distribution table (repetition d=3, circuit level, p=0.01,
32768 test shots) is the report's most quoted one and its effect sizes are tiny
(bp 0.00943 vs bp_gnn 0.00952), so it needs seed error bars like every other
table.  Seeds are added the same way `scripts/t9_feature_ablation.py
--seed-offset` does it: bump `training.seed` and every entry of
`train_seeds` / `validation_seeds` / `test_seeds` by the offset, leaving the
experiment sampling seed untouched.

Usage:
    .\.venv\Scripts\python.exe scripts\m2_headline_multiseed.py --write-configs
    # then run the two configs through graph_qec.m2 (scripts\m2_headline_seeds.ps1)
    .\.venv\Scripts\python.exe scripts\m2_headline_multiseed.py --aggregate
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Sequence

BASE_CONFIG = Path("configs/m2_learned_basis_repetition_circuit_level_d3.json")
OFFSETS = (10, 20)
CONFIG_DIR = Path("configs")
RUN_ROOT = Path("results/m2")
BASE_RUN = "m2_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01"
#: decoder in the m2 results.json  ->  column name used in the report table
COLUMNS = (("mwpm", "mwpm"), ("bp", "bp"), ("osd_gnn", "osd_gnn"),
           ("bp_osd", "bp_osd"))


def config_name(offset: int) -> str:
    return f"m2_learned_basis_repetition_circuit_level_d3_s{offset}"


def build_config(offset: int) -> dict[str, Any]:
    config = json.loads(BASE_CONFIG.read_text(encoding="utf-8"))
    config["name"] = config_name(offset)
    config["experiment"]["name"] = config_name(offset)
    config["training"]["seed"] = int(config["training"]["seed"]) + offset
    splits = config["splits"]
    for key in ("train_seeds", "validation_seeds", "test_seeds"):
        splits[key] = [int(seed) + offset for seed in splits[key]]
    return config


def write_configs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    for offset in OFFSETS:
        path = CONFIG_DIR / f"m2_headline_seed{offset}.json"
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(build_config(offset), handle, indent=2, sort_keys=True)
            handle.write("\n")
        print(f"wrote {path}")


def load_run(tag: str) -> dict[str, Any] | None:
    path = RUN_ROOT / tag / "results.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def decoder_rows(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["decoder"]: entry for entry in data["decoders"]}


def ablation_all(offset: int) -> dict[str, Any] | None:
    """The `all` arm of the T9 repetition ablation = bp_gnn at the same seeds.

    The ablation directories are named ``repetition_d3_circuit_level`` for the
    original seed and ``repetition_d3_seedNN`` for the follow-ups, so match on
    the recorded ``seed_offset`` instead of on the directory name.
    """

    for directory in sorted(Path("results/t9").glob("repetition_d3*")):
        study = directory / "ablation.json"
        if not study.exists():
            continue
        payload = json.loads(study.read_text(encoding="utf-8"))
        if int(payload.get("seed_offset", 0)) != offset:
            continue
        rows = payload["rows"]
        return next((row for row in rows if row["arm"] == "all"), None)
    return None


def markdown() -> str:
    runs: list[tuple[int, dict[str, Any], dict[str, Any] | None]] = []
    for offset in (0,) + OFFSETS:
        tag = BASE_RUN if offset == 0 else f"{config_name(offset)}__d3__circuit_level__p0p01"
        data = load_run(tag)
        if data is None:
            raise SystemExit(f"missing run: {tag}")
        runs.append((offset, data, ablation_all(offset)))

    shots = runs[0][1]["splits"]["test"]["shots"]
    decoders = decoder_rows(runs[0][1])
    lines = [
        "# M2 旗舰表（repetition d=3，线路级 p=0.01）的多种子复核",
        "",
        "由 `scripts/m2_headline_multiseed.py` 自动生成，勿手改。",
        f"每个 seed = {shots} test shots（`splits.test_seeds` 两个 seed 合并）；"
        "除 `all` 之外的列来自 `graph_qec.m2` 的 `results.json`，",
        "`bp_gnn` 列来自 T9 消融的 `all` 臂（同一 splits、同一训练种子，seed 0 与旗舰值逐位一致）。",
        "",
        "| 训练/测试种子偏移 | 数据来源 | " + " | ".join(name for _, name in COLUMNS) + " | bp_gnn |",
        "|---:|---|" + "---:|" * (len(COLUMNS) + 1),
    ]
    for offset, data, ablation in runs:
        cells = []
        for decoder, _ in COLUMNS:
            entry = decoder_rows(data)[decoder]
            cells.append(f"{entry['logical_error_rate']:.5f} ({entry['logical_errors']})")
        gnn = "—" if ablation is None else f"{ablation['logical_error_rate']:.5f} ({ablation['logical_errors']})"
        lines.append(f"| {offset} | `{data['name']}` | " + " | ".join(cells) + f" | {gnn} |")

    lines += ["", "## 跨 seed 配对（种子是重复单位）", "",
              "| 比较 | 逐 seed ΔLER | 跨 seed 均值 ± SE | 相对 |", "|---|---|---:|---:|"]
    comparisons = [("bp vs bp_gnn", "bp", "bp_gnn"), ("mwpm vs bp_gnn", "mwpm", "bp_gnn")]
    for label, left, right in comparisons:
        deltas: list[float] = []
        cells: list[str] = []
        for offset, data, ablation in runs:
            if ablation is None:
                continue
            rows = decoder_rows(data)
            delta = float(ablation["logical_error_rate"]) - float(rows[left]["logical_error_rate"])
            deltas.append(delta)
            cells.append(f"offset {offset}: {delta:+.5f}")
        mean, error = mean_se(deltas)
        base = pooled_rate(runs, left)
        lines.append(f"| `{label}` | " + "；".join(cells) + f" | {mean:+.5f} ± {error:.5f} | "
                     f"{mean / base * 100:+.1f}% |")

    lines += ["", "## 合并口径（整体尺度）", "",
              "| decoder | LER（pooled） | 标准误 | 逻辑错误 | shots |", "|---|---:|---:|---:|---:|"]
    for name in ("mwpm", "bp", "osd_gnn", "bp_osd"):
        rate, error, errors, total = pooled_decoder(runs, name)
        lines.append(f"| `{name}` | {rate:.5f} | {error:.5f} | {errors} | {total} |")
    gnn_rates = [ablation for _, _, ablation in runs if ablation is not None]
    rate, error, errors, total = pooled_rows(gnn_rates)
    lines.append(f"| `bp_gnn`（T9 all 臂） | {rate:.5f} | {error:.5f} | {errors} | {total} |")
    return "\n".join(lines) + "\n"


def mean_se(values: Sequence[float]) -> tuple[float, float]:
    count = len(values)
    if count < 2:
        return (values[0] if count else float("nan")), float("nan")
    mean = sum(values) / count
    variance = sum((value - mean) ** 2 for value in values) / (count - 1)
    return mean, math.sqrt(variance / count)


def pooled_decoder(runs: Sequence[tuple[int, dict[str, Any], Any]], name: str) -> tuple[float, float, int, int]:
    shots = sum(run[1]["splits"]["test"]["shots"] for run in runs)
    errors = sum(decoder_rows(run[1])[name]["logical_errors"] for run in runs)
    rate = errors / shots
    return rate, math.sqrt(rate * (1 - rate) / shots), errors, shots


def pooled_rate(runs: Sequence[tuple[int, dict[str, Any], Any]], name: str) -> float:
    return pooled_decoder(runs, name)[0]


def pooled_rows(rows: Sequence[dict[str, Any]]) -> tuple[float, float, int, int]:
    shots = sum(int(row["shots"]) for row in rows)
    errors = sum(int(row["logical_errors"]) for row in rows)
    rate = errors / shots
    return rate, math.sqrt(rate * (1 - rate) / shots), errors, shots


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-configs", action="store_true")
    parser.add_argument("--aggregate", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("results/m2/HEADLINE_MULTISEED.md"))
    args = parser.parse_args(argv)

    if args.write_configs:
        write_configs()
    if args.aggregate:
        text = markdown()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
        print(text)
    if not (args.write_configs or args.aggregate):
        parser.error("pass --write-configs and/or --aggregate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
