#!/usr/bin/env python3
r"""Builds the CPU engineering performance table from the recorded results.

Every cell is read from ``results/`` (M1 benchmark files and M2/M3/M4 run
records); nothing is typed in by hand, so the table can be regenerated after any
re-run. Missing quantities are reported explicitly together with the reason.

Usage:
    .\.venv\Scripts\python.exe scripts\engineering_table.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

UNAVAILABLE = {
    "gpu_latency": "交付环境为 CPU-only（`torch.cuda.is_available() == False`）",
    "gpu_memory": "同左，见 `docs/M5_ENGINEERING.md` 第 4 节",
    "batch_throughput_multi": "M1 的 `timed_runs` 已覆盖固定 batch 的吞吐；更大 batch 的吞吐随噪声率/码距变化，未逐点测量",
}

FIELDS = [
    ("配置", "config"),
    ("解码器", "decoder"),
    ("LER", "ler"),
    ("µs/shot", "latency"),
    ("shot/s", "throughput"),
    ("峰值 RSS delta", "rss_delta"),
    ("BP 平均迭代", "iterations"),
    ("OSD 触发比例", "osd_rate"),
    ("syndrome 一致率", "consistency"),
]


def _fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        if value != value:  # NaN
            return "-"
        if value >= 1000:
            return "{:,.0f}".format(value)
        return ("{:." + str(digits) + "g}").format(value)
    return str(value)


def _row(config: str, entry: dict[str, Any]) -> dict[str, Any]:
    latency = entry.get("latency") or {}
    diagnostics = entry.get("diagnostics") or {}
    memory = entry.get("memory") or {}
    return {
        "config": config,
        "decoder": entry.get("decoder"),
        "ler": entry.get("logical_error_rate"),
        "latency": latency.get("mean_per_shot_microseconds"),
        "throughput": latency.get("throughput_shots_per_second"),
        "rss_delta": memory.get("peak_rss_delta_bytes"),
        "iterations": diagnostics.get("average_iterations"),
        "osd_rate": diagnostics.get("osd_rate"),
        "consistency": entry.get("syndrome_consistency_rate"),
    }


def collect_m1(results_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(results_dir.glob("*/benchmark.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for entry in payload.get("decoders", []):
            rows.append(_row(path.parent.name, entry))
    return rows


def collect_runs(results_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(results_dir.glob("*/results.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        name = path.parent.name
        for entry in payload.get("decoders", []):
            rows.append(_row(name, entry))
    return rows


def render(rows: Sequence[dict[str, Any]]) -> str:
    lines = [
        "# CPU 工程性能表",
        "",
        "由 `scripts/engineering_table.py` 从 `results/` 自动生成，请勿手工编辑。",
        "延迟与吞吐为固定 batch 的测量值；内存为执行期间 working set 的峰值增量。",
        "",
        "| " + " | ".join(label for label, _ in FIELDS) + " |",
        "|" + "---|" * len(FIELDS),
    ]
    for row in rows:
        lines.append("| " + " | ".join(_fmt(row[key]) for _, key in FIELDS) + " |")
    lines += [
        "",
        "## 模型规模",
        "",
        "| 模型 | 参数量 | float32 权重 | int8 动态量化权重 |",
        "|---|---:|---:|---:|",
    ]
    quantization = Path("results/m5/quantization.json")
    if quantization.exists():
        payload = json.loads(quantization.read_text(encoding="utf-8"))
        architecture = (payload.get("checkpoint") or {}).get("architecture", {})
        float32 = payload.get("float32") or {}
        int8 = payload.get("int8_dynamic") or {}
        lines.append(
            "| BipartiteSyndromeGNN (hidden={}, layers={}) | {} shots/batch | {} MB | {} MB |".format(
                architecture.get("hidden_size", "-"),
                architecture.get("num_layers", "-"),
                payload.get("batch_size", "-"),
                _fmt(float32.get("model_size_mb"), 4),
                _fmt(int8.get("model_size_mb"), 4),
            )
        )
        lines += [
            "",
            "量化推理（`scripts/m5_quantization.py`，batch={}，{} shots）：float32 {} µs/shot、"
            "int8 动态 {} µs/shot（speedup {}），权重压缩 {}，机制符号一致率 {}，logit 最大偏差 {}。".format(
                payload.get("batch_size", "-"),
                payload.get("shots", "-"),
                _fmt(float32.get("microseconds_per_shot"), 4),
                _fmt(int8.get("microseconds_per_shot"), 4),
                _fmt(payload.get("speedup"), 4),
                _fmt(payload.get("size_ratio"), 4),
                _fmt(payload.get("sign_agreement"), 6),
                _fmt(payload.get("max_abs_logit_delta"), 4),
            ),
        ]
    else:
        lines.append("| BipartiteSyndromeGNN | - | - | - |")
    lines += [
        "",
        "## 不可测项与原因",
        "",
        "| 项 | 原因 |",
        "|---|---|",
    ]
    for key, reason in UNAVAILABLE.items():
        lines.append("| {} | {} |".format(key, reason))
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--output", type=Path, default=Path("results/m5/ENGINEERING_TABLE.md"))
    args = parser.parse_args(argv)

    rows = collect_m1(args.results_dir / "m1")
    for sub in ("m2", "m3", "m4_surface", "m4_surface_cc", "m4_hgp"):
        rows.extend(collect_runs(args.results_dir / sub))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(rows), encoding="utf-8", newline="\n")
    print("wrote {} ({} rows)".format(args.output, len(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())