r"""T10: multi-seed aggregation for the T6 surface-code sweep.

Scans the M2 result directories, groups them by (distance, physical error rate)
and reports, per decoder, the across-seed mean +- standard error of the logical
error rate together with the per-seed values. Also reports the paired
seed-level deltas for the headline comparisons and a sign test over the seeds.

Usage:
    .\.venv\Scripts\python.exe scripts\t10_multiseed_stats.py `
        --results-dir results\m4_surface --output-dir results\t10
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Sequence

import numpy as np


_ARTIFACT = re.compile(r"__d(?P<distance>\d+)__(?P<noise>[a-z_]+)__p(?P<p>[0-9]+p?[0-9]*)")

COMPARISONS = (
    ("bp", "bp_gnn"),
    ("bp", "bp_osd"),
    ("bp_gnn", "bp_gnn_osd"),
)


def _parse_p(tag: str) -> float:
    return float(tag.replace("p", ".", 1)) if "p" in tag else float(tag)


def _sign_test(deltas: Sequence[float]) -> dict[str, Any]:
    positives = sum(1 for value in deltas if value > 0)
    negatives = sum(1 for value in deltas if value < 0)
    n = positives + negatives
    if n == 0:
        return {"positive": 0, "negative": 0, "p": 1.0}
    tail = sum(math.comb(n, k) for k in range(0, min(positives, negatives) + 1)) / 2.0**n
    return {"positive": positives, "negative": negatives, "p": float(min(1.0, 2.0 * tail))}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--min-test-shots",
        type=int,
        default=0,
        help="Ignore runs whose test split is smaller than this (keeps legacy "
        "single points at a different shot count out of a multi-seed group).",
    )
    args = parser.parse_args(argv)

    runs: list[dict[str, Any]] = []
    for result_path in sorted(args.results_dir.glob("*/results.json")):
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        experiment = payload["config"]["experiment"]
        match = _ARTIFACT.search(result_path.parent.name)
        if match is None:
            continue
        if int(payload["splits"]["test"]["shots"]) < args.min_test_shots:
            continue
        runs.append(
            {
                "path": str(result_path.parent),
                "distance": int(match.group("distance")),
                "noise_model": match.group("noise"),
                "physical_error_rate": _parse_p(match.group("p")),
                "training_seed": payload["config"]["training"]["seed"],
                "test_seeds": payload["splits"]["test"]["seeds"],
                "test_shots": payload["splits"]["test"]["shots"],
                "selected_strength": payload.get("selected_reweight_strength"),
                "decoders": {
                    entry["decoder"]: entry["logical_error_rate"]
                    for entry in payload["decoders"]
                },
                "decoder_errors": {
                    entry["decoder"]: entry["logical_errors"]
                    for entry in payload["decoders"]
                },
            }
        )

    groups: dict[tuple[int, float], list[dict[str, Any]]] = {}
    for run in runs:
        groups.setdefault((run["distance"], run["physical_error_rate"]), []).append(run)

    summary: dict[str, Any] = {
        "results_dir": str(args.results_dir),
        "runs": len(runs),
        "groups": [],
    }
    markdown = [
        "# 多种子统计：表面码扫描",
        "",
        "每个点是单 seed 的一条 (distance, p) 曲线；下表给出跨 seed 的均值 ± 标准误。",
        "",
    ]

    for (distance, probability), members in sorted(groups.items()):
        members.sort(key=lambda item: item["training_seed"])
        decoders = sorted({name for item in members for name in item["decoders"]})
        per_decoder: dict[str, Any] = {}
        for name in decoders:
            rates = [item["decoders"][name] for item in members if name in item["decoders"]]
            if not rates:
                continue
            mean = float(np.mean(rates))
            sem = float(np.std(rates, ddof=1) / math.sqrt(len(rates))) if len(rates) > 1 else 0.0
            per_decoder[name] = {
                "seeds": [item["training_seed"] for item in members if name in item["decoders"]],
                "rates": rates,
                "mean": mean,
                "standard_error": sem,
            }

        comparisons = []
        for label_a, label_b in COMPARISONS:
            if label_a not in per_decoder or label_b not in per_decoder:
                continue
            deltas = [
                a - b
                for a, b in zip(
                    per_decoder[label_a]["rates"], per_decoder[label_b]["rates"]
                )
            ]
            comparisons.append(
                {
                    "a": label_a,
                    "b": label_b,
                    "deltas": deltas,
                    "mean_delta": float(np.mean(deltas)),
                    "sign_test": _sign_test(deltas),
                }
            )

        group = {
            "distance": distance,
            "noise_model": members[0]["noise_model"],
            "physical_error_rate": probability,
            "seeds": [item["training_seed"] for item in members],
            "test_shots_per_seed": members[0]["test_shots"],
            "selected_strengths": [item["selected_strength"] for item in members],
            "per_decoder": per_decoder,
            "comparisons": comparisons,
        }
        summary["groups"].append(group)

        markdown += [
            f"## d={distance}, {group['noise_model']}, p={probability:g}"
            f"（{len(members)} seeds，每 seed {group['test_shots_per_seed']} shots）",
            "",
            "| decoder | 各 seed LER | 均值 | 标准误 |",
            "|---|---|---:|---:|",
        ]
        for name in decoders:
            entry = per_decoder.get(name)
            if entry is None:
                continue
            values = ", ".join(f"{rate:.5f}" for rate in entry["rates"])
            markdown.append(
                f"| {name} | {values} | {entry['mean']:.5f} | {entry['standard_error']:.5f} |"
            )
        markdown.append("")
        if comparisons:
            markdown += [
                "| A | B | Δ(各 seed) | Δ 均值 | 符号检验 p |",
                "|---|---|---|---:|---:|",
            ]
            for comparison in comparisons:
                deltas = ", ".join(f"{delta:+.5f}" for delta in comparison["deltas"])
                markdown.append(
                    f"| {comparison['a']} | {comparison['b']} | {deltas} | "
                    f"{comparison['mean_delta']:+.5f} | {comparison['sign_test']['p']:.3f} |"
                )
            markdown.append("")

    # Also emit a sweep-shaped file (across-seed mean per point) so that
    # scripts/threshold_estimate.py can consume the T6 curve directly.
    sweep_records = []
    for group in summary["groups"]:
        for name, entry in group["per_decoder"].items():
            sweep_records.append(
                {
                    "distance": group["distance"],
                    "noise_model": group["noise_model"],
                    "physical_error_rate": group["physical_error_rate"],
                    "decoder": name,
                    "shots": group["test_shots_per_seed"] * len(group["seeds"]),
                    "logical_error_rate": entry["mean"],
                    "logical_error_rate_standard_error": entry["standard_error"],
                }
            )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "surface_sweep_mean.json").open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        json.dump(sweep_records, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (args.output_dir / "multiseed.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (args.output_dir / "MULTISEED.md").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(markdown).rstrip("\n") + "\n")

    print(f"aggregated {len(runs)} runs into {len(summary['groups'])} (distance, p) groups")
    for group in summary["groups"]:
        print(f"  d={group['distance']} p={group['physical_error_rate']:g}: {len(group['seeds'])} seeds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
