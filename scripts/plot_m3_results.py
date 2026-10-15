r"""Plots M3 transfer figures (noise extrapolation, distance transfer, Pareto).

Usage:
    .\.venv\Scripts\python.exe scripts\plot_m3_results.py --results-dir results\m3
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load(results_dir: Path) -> list[dict[str, Any]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(results_dir.glob("*/results.json"))
    ]


def target_of(result: dict[str, Any]) -> dict[str, Any]:
    if "transfer" in result:
        return result["transfer"]["target_experiment"]
    experiment = result["config"]["experiment"]
    return {
        "family": experiment["code"]["family"],
        "distance": experiment["code"]["distance"],
        "rounds": experiment["code"]["rounds"],
        "noise_model": experiment["noise"]["model"],
        "physical_error_rate": experiment["noise"]["physical_error_rate"],
    }


def _series(results: Sequence[dict[str, Any]], decoder: str) -> list[tuple[float, float, float]]:
    points = []
    for result in results:
        entry = next((item for item in result["decoders"] if item["decoder"] == decoder), None)
        if entry is None:
            continue
        points.append(
            (
                target_of(result)["physical_error_rate"],
                entry["logical_error_rate"],
                entry["logical_error_rate_standard_error"],
            )
        )
    return sorted(points)


def _decoder_names(results: Sequence[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for result in results:
        for entry in result["decoders"]:
            if entry["decoder"] not in names:
                names.append(entry["decoder"])
    return names


def plot_noise_extrapolation(results_dir: Path, output: Path) -> None:
    results = load(results_dir)
    source = next((item for item in results if item.get("stage") == "M3-transfer"), None)
    source_p = (
        source["transfer"]["source_experiment"]["physical_error_rate"] if source else None
    )
    in_distribution = [
        item for item in results if item.get("stage") == "M2" and target_of(item)["distance"] == 3
    ]
    transfers = [
        item
        for item in results
        if item.get("stage") == "M3-transfer" and target_of(item)["distance"] == 3
    ]
    combined = list(in_distribution) + list(transfers)

    figure, axis = plt.subplots(figsize=(7.2, 4.8))
    for name in _decoder_names(combined):
        points = _series(combined, name)
        if len(points) < 2:
            continue
        axis.errorbar(
            [point[0] for point in points],
            [point[1] for point in points],
            yerr=[point[2] for point in points],
            marker="o",
            capsize=3,
            label=name,
        )
    if source_p is not None:
        axis.axvline(source_p, color="grey", linestyle="--", linewidth=1)
        axis.annotate(
            f"training p={source_p:g}",
            xy=(source_p, 0.5),
            xycoords=("data", "axes fraction"),
            xytext=(-6, -12),
            textcoords="offset points",
            ha="right",
            fontsize=8,
            color="grey",
        )
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel("physical error rate p")
    axis.set_ylabel("logical error rate")
    axis.set_title("M3 noise extrapolation: repetition d=3, circuit-level")
    axis.grid(alpha=0.3, which="both")
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)


def plot_distance_transfer(results_dir: Path, output: Path) -> None:
    results = load(results_dir)
    source_distance = next(
        (target_of(item)["distance"] for item in results if item.get("stage") == "M3-transfer"),
        None,
    )
    if source_distance is None:
        return
    in_distribution = [
        item
        for item in results
        if item.get("stage") == "M2" and target_of(item)["distance"] == source_distance
    ]
    transfers = [
        item
        for item in results
        if item.get("stage") == "M3-transfer" and target_of(item)["distance"] != source_distance
    ]
    figure, axis = plt.subplots(figsize=(6.4, 4.6))
    for name in _decoder_names(list(in_distribution) + list(transfers)):
        points = [(float(target_of(item)["distance"]), item, name) for item in in_distribution + transfers]
        xs, ys, errs = [], [], []
        for distance, result, decoder in points:
            entry = next((item for item in result["decoders"] if item["decoder"] == decoder), None)
            if entry is None:
                continue
            xs.append(distance)
            ys.append(entry["logical_error_rate"])
            errs.append(entry["logical_error_rate_standard_error"])
        if len(xs) < 2:
            continue
        axis.errorbar(xs, ys, yerr=errs, marker="o", capsize=3, label=name)
    axis.set_yscale("log")
    axis.set_xticks(sorted({float(target_of(item)["distance"]) for item in in_distribution + transfers}))
    axis.set_xlabel("code distance d (trained at d=%d)" % source_distance)
    axis.set_ylabel("logical error rate")
    axis.set_title("M3 distance transfer: circuit-level p=0.01")
    axis.grid(alpha=0.3, which="both")
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)


def plot_pareto(results_dir: Path, output: Path, title: str) -> None:
    results = [item for item in load(results_dir) if item.get("stage") == "M2"]
    if not results:
        return
    result = results[-1]
    figure, axis = plt.subplots(figsize=(6.8, 4.8))
    for entry in result["decoders"]:
        latency = entry["latency"]["mean_per_shot_microseconds"]
        rate = entry["logical_error_rate"]
        axis.scatter(latency, rate, s=45)
        axis.annotate(
            entry["decoder"],
            xy=(latency, rate),
            xytext=(5, 4),
            textcoords="offset points",
            fontsize=8,
        )
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel("mean decode latency [us/shot]")
    axis.set_ylabel("logical error rate")
    axis.set_title(title)
    axis.grid(alpha=0.3, which="both")
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)


def plot_osd_tradeoff(results_dir: Path, output: Path) -> None:
    """LER versus syndrome consistency for the OSD trigger sweep and the decoders."""

    policy_path = results_dir / "osd_trigger_policy.json"
    if not policy_path.exists():
        return
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    figure, axis = plt.subplots(figsize=(6.6, 4.8))

    xs = [item["syndrome_consistency_rate"] for item in payload["policy"]]
    ys = [item["logical_error_rate"] for item in payload["policy"]]
    order = np.argsort(xs)
    axis.plot([xs[i] for i in order], [ys[i] for i in order], marker="o", label="OSD trigger policy sweep")
    for item in payload["policy"]:
        if item["threshold"] in (0, 1, 2, 3, 10**6):
            label = "never" if item["threshold"] >= 10**6 else f"k={item['threshold']}"
            axis.annotate(
                label,
                xy=(item["syndrome_consistency_rate"], item["logical_error_rate"]),
                xytext=(5, 4),
                textcoords="offset points",
                fontsize=8,
            )

    for result in load(results_dir):
        if result.get("stage") != "M2":
            continue
        for entry in result["decoders"]:
            if entry["syndrome_consistency_rate"] is None:
                continue
            axis.scatter(
                entry["syndrome_consistency_rate"],
                entry["logical_error_rate"],
                marker="s",
                s=28,
                color="tab:red",
            )
            axis.annotate(
                entry["decoder"],
                xy=(entry["syndrome_consistency_rate"], entry["logical_error_rate"]),
                xytext=(5, -10),
                textcoords="offset points",
                fontsize=7,
                color="tab:red",
            )

    axis.set_xlabel("syndrome consistency rate")
    axis.set_ylabel("logical error rate")
    axis.set_yscale("log")
    axis.set_title("M3 LER versus syndrome consistency (d=3 circuit-level p=0.01)")
    axis.grid(alpha=0.3, which="both")
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)


def plot_strength_recalibration(results_dir: Path, output: Path) -> None:
    """Validation LER versus learned-prior strength for each target noise rate."""

    inputs = [
        results_dir / "recal_lowp" / "results.json",
        results_dir / "recal_highp" / "results.json",
        results_dir / "recal_d5" / "results.json",
    ]
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in inputs if path.exists()]
    if not payloads:
        return
    figure, axis = plt.subplots(figsize=(6.8, 4.8))
    for payload in payloads:
        for result in payload["results"]:
            sweep = result["validation_sweep"]
            strengths = [item["strength"] for item in sweep]
            rates = [max(item["logical_error_rate"], 1e-6) for item in sweep]
            axis.plot(
                strengths,
                rates,
                marker="o",
                label="target p={:g} (chose {:.2f})".format(
                    result["physical_error_rate"], result["selected_strength"]
                ),
            )
            axis.scatter(
                [result["selected_strength"]],
                [
                    next(
                        item["logical_error_rate"]
                        for item in sweep
                        if item["strength"] == result["selected_strength"]
                    )
                ],
                s=90,
                facecolors="none",
                edgecolors="tab:red",
                linewidths=1.5,
            )
    axis.set_xlabel("learned-prior interpolation strength (0 = DEM prior, 1 = learned)")
    axis.set_ylabel("validation logical error rate")
    axis.set_title("M3 strength recalibration on the target noise rate")
    axis.grid(alpha=0.3)
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plot M3 result figures.")
    parser.add_argument("--results-dir", type=Path, default=Path("results/m3"))
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--pareto-title",
        default="M3 Pareto: repetition d=3 circuit-level p=0.01 (32768 test shots)",
    )
    args = parser.parse_args(argv)

    figures = args.output_dir or args.results_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    outputs = [
        figures / "noise_extrapolation.png",
        figures / "distance_transfer.png",
        figures / "pareto_ler_latency.png",
        figures / "osd_consistency_tradeoff.png",
        figures / "strength_recalibration.png",
    ]
    plot_noise_extrapolation(args.results_dir, outputs[0])
    plot_distance_transfer(args.results_dir, outputs[1])
    plot_pareto(args.results_dir, outputs[2], args.pareto_title)
    plot_osd_tradeoff(args.results_dir, outputs[3])
    plot_strength_recalibration(args.results_dir, outputs[4])
    for path in outputs:
        print(path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
