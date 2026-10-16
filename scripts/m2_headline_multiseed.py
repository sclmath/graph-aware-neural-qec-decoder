r"""Seed-offset runs for an M2/M4 config, plus their multi-seed aggregation.

Several report tables carry effects that are small compared with the seed-to-seed
spread, so they need error bars: bump ``training.seed`` and every entry of
``train_seeds`` / ``validation_seeds`` / ``test_seeds`` by the offset (the same
convention as ``scripts/t9_feature_ablation.py --seed-offset``), run the pipeline
again, and pool the results.

Usage (repetition d=3 flagship table):

    .\.venv\Scripts\python.exe scripts\m2_headline_multiseed.py --write-configs
    .\scripts\m2_headline_seeds.ps1
    .\.venv\Scripts\python.exe scripts\m2_headline_multiseed.py --aggregate

Usage (rotated surface code d=3, circuit level p=0.005):

    .\.venv\Scripts\python.exe scripts\m2_headline_multiseed.py --write-configs `
        --base-config "results\m4_surface\m4_learned_basis_rotated_surface_code_circuit_level_d3__d3__circuit_level__p0p005\config.json" `
        --out-dir results\m4_surface --output results\m4_surface\D3_MULTISEED.md
    .\scripts\m2_headline_seeds.ps1 -BaseConfig <同样的路径> -OutDir results\m4_surface
    .\.venv\Scripts\python.exe scripts\m2_headline_multiseed.py --aggregate --base-config <同样的路径> --out-dir results\m4_surface --output results\m4_surface\D3_MULTISEED.md
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Sequence

DEFAULT_BASE_CONFIG = Path("configs/m2_learned_basis_repetition_circuit_level_d3.json")
DEFAULT_OUT_DIR = Path("results/m2")
DEFAULT_OUTPUT = Path("results/m2/HEADLINE_MULTISEED.md")
OFFSETS = (10, 20)
#: columns to report, taken from the run's own results.json when available
COLUMNS = ("mwpm", "bp", "bp_gnn", "bp_osd")


def config_name(base: dict[str, Any], offset: int) -> str:
    return f"{base['name']}_s{offset}"


def build_config(base_path: Path, offset: int) -> dict[str, Any]:
    config = json.loads(base_path.read_text(encoding="utf-8"))
    config["name"] = config_name(config, offset)
    config["experiment"]["name"] = config["name"]
    config["training"]["seed"] = int(config["training"]["seed"]) + offset
    for key in ("train_seeds", "validation_seeds", "test_seeds"):
        config["splits"][key] = [int(seed) + offset for seed in config["splits"][key]]
    return config


def write_configs(base_path: Path, offsets: Sequence[int], configs_dir: Path) -> None:
    base = json.loads(base_path.read_text(encoding="utf-8"))
    configs_dir.mkdir(parents=True, exist_ok=True)
    for offset in offsets:
        path = configs_dir / f"{config_name(base, offset)}.json"
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(build_config(base_path, offset), handle, indent=2, sort_keys=True)
            handle.write("\n")
        print(f"wrote {path}")


def find_run(out_dir: Path, name: str) -> Path:
    matches = sorted(path for path in out_dir.glob(f"{name}__*") if (path / "results.json").exists())
    if len(matches) != 1:
        raise SystemExit(f"expected one run for {name} under {out_dir}, found {len(matches)}")
    return matches[0]


def load_run(path: Path) -> dict[str, Any]:
    return json.loads((path / "results.json").read_text(encoding="utf-8"))


def decoder_rows(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["decoder"]: entry for entry in data["decoders"]}


def ablation_all(offset: int) -> dict[str, Any] | None:
    """The `all` arm of the T9 repetition ablation = bp_gnn at the same seeds."""

    for directory in sorted(Path("results/t9").glob("repetition_d3*")):
        study = directory / "ablation.json"
        if not study.exists():
            continue
        payload = json.loads(study.read_text(encoding="utf-8"))
        if int(payload.get("seed_offset", 0)) != offset:
            continue
        return next((row for row in payload["rows"] if row["arm"] == "all"), None)
    return None


def ordered_columns(rows: dict[str, dict[str, Any]]) -> list[str]:
    columns = [name for name in COLUMNS if name in rows]
    return columns + [name for name in rows if name not in columns and name != "union_find"]


def mean_se(values: Sequence[float]) -> tuple[float, float]:
    count = len(values)
    if count < 2:
        return (values[0] if count else float("nan")), float("nan")
    mean = sum(values) / count
    variance = sum((value - mean) ** 2 for value in values) / (count - 1)
    return mean, math.sqrt(variance / count)


def markdown(base_config: Path, out_dir: Path, offsets: Sequence[int]) -> str:
    base = json.loads(base_config.read_text(encoding="utf-8"))
    runs: list[tuple[int, dict[str, Any], dict[str, Any] | None]] = []
    for offset in (0,) + tuple(offsets):
        name = base["name"] if offset == 0 else config_name(base, offset)
        data = load_run(find_run(out_dir, name))
        rows = decoder_rows(data)
        # bp_gnn: use the run's own decoder when the pipeline emits one,
        # otherwise fall back to the T9 ablation `all` arm (same seeds).
        gnn = None
        if "bp_gnn" in rows:
            gnn = {
                "logical_error_rate": rows["bp_gnn"]["logical_error_rate"],
                "logical_errors": rows["bp_gnn"]["logical_errors"],
                "shots": data["splits"]["test"]["shots"],
                "source": "results.json",
            }
        else:
            ablation = ablation_all(offset)
            if ablation is not None:
                gnn = {**ablation, "source": "T9 all 臂"}
        runs.append((offset, data, gnn))

    shots = runs[0][1]["splits"]["test"]["shots"]
    columns = ordered_columns(decoder_rows(runs[0][1]))
    lines = [
        f"# {base['name']} · 多种子复核",
        "",
        "由 `scripts/m2_headline_multiseed.py` 自动生成，勿手改。",
        f"每个 seed = {shots} test shots（`splits.test_seeds` 合并），共 {len(runs)} 个 seed。",
        "种子偏移同时移动 `training.seed` 与三个 split seed 列表（与 `t9_feature_ablation.py --seed-offset` 同一约定），",
        "因此跨 seed 散布同时含模型与数据方差。",
        "",
        "| 种子偏移 | " + " | ".join(f"`{name}`" for name in columns) + " | bp_gnn | 来源 |",
        "|---:|" + "---:|" * (len(columns) + 2),
    ]
    for offset, data, gnn in runs:
        rows = decoder_rows(data)
        cells = [f"{rows[name]['logical_error_rate']:.5f} ({rows[name]['logical_errors']})" for name in columns]
        gnn_cell = "—" if gnn is None else f"{gnn['logical_error_rate']:.5f} ({gnn['logical_errors']})"
        lines.append(f"| {offset} | " + " | ".join(cells) + f" | {gnn_cell} | {data['name']} |")

    lines += ["", "## 跨 seed 配对（种子是重复单位）", "",
              "| 比较 | 逐 seed ΔLER | 跨 seed 均值 ± SE | 相对 |", "|---|---|---:|---:|"]
    for left in columns:
        if left == "bp_gnn" or left.startswith("bp") is False and left != "mwpm":
            continue
        deltas: list[float] = []
        cells: list[str] = []
        for offset, data, gnn in runs:
            if gnn is None:
                continue
            delta = float(gnn["logical_error_rate"]) - float(decoder_rows(data)[left]["logical_error_rate"])
            deltas.append(delta)
            cells.append(f"{delta:+.5f}")
        if not deltas:
            continue
        mean, error = mean_se(deltas)
        base_rate = pooled_decoder(runs, left)[0]
        lines.append(f"| `{left}` → `bp_gnn` | " + " / ".join(cells)
                     + f" | {mean:+.5f} ± {error:.5f} | {mean / base_rate * 100:+.1f}% |")

    lines += ["", "## 合并口径（整体尺度）", "",
              "| decoder | LER（pooled） | 标准误 | 逻辑错误 | shots |", "|---|---:|---:|---:|---:|"]
    for name in columns:
        rate, error, errors, total = pooled_decoder(runs, name)
        lines.append(f"| `{name}` | {rate:.5f} | {error:.5f} | {errors} | {total} |")
    if any(run[2] is not None for run in runs):
        gnn_rows = [run[2] for run in runs if run[2] is not None]
        shots_total = sum(int(row["shots"]) for row in gnn_rows)
        errors_total = sum(int(row["logical_errors"]) for row in gnn_rows)
        rate = errors_total / shots_total
        lines.append(f"| `bp_gnn` | {rate:.5f} | "
                     f"{math.sqrt(rate * (1 - rate) / shots_total):.5f} | {errors_total} | {shots_total} |")
    return "\n".join(lines) + "\n"


def pooled_decoder(runs: Sequence[tuple[int, dict[str, Any], Any]], name: str) -> tuple[float, float, int, int]:
    shots = sum(run[1]["splits"]["test"]["shots"] for run in runs)
    errors = sum(decoder_rows(run[1])[name]["logical_errors"] for run in runs)
    rate = errors / shots
    return rate, math.sqrt(rate * (1 - rate) / shots), errors, shots


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-config", type=Path, default=DEFAULT_BASE_CONFIG)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--configs-dir", type=Path, default=Path("configs"))
    parser.add_argument("--offsets", type=int, nargs="+", default=list(OFFSETS))
    parser.add_argument("--write-configs", action="store_true")
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args(argv)

    if args.write_configs:
        write_configs(args.base_config, args.offsets, args.configs_dir)
    if args.aggregate:
        text = markdown(args.base_config, args.out_dir, args.offsets)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
        print(text)
    if not (args.write_configs or args.aggregate):
        parser.error("pass --write-configs and/or --aggregate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
