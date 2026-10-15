r"""Generates M2 figures from ``results/m2/*/results.json``.

Usage:
    .\.venv\Scripts\python.exe scripts\plot_m2_results.py --results-dir results\m2
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _load_results(results_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in sorted(results_dir.glob("*/results.json")):
        with path.open("r", encoding="utf-8") as handle:
            results.append(json.load(handle))
    if not results:
        raise FileNotFoundError(f"No results.json found under {results_dir}")
    return results


def _label(result: dict[str, Any]) -> str:
    code = result["config"]["experiment"]["code"]
    noise = result["config"]["experiment"]["noise"]
    return f"d={code['distance']} {noise['model']} p={noise['physical_error_rate']}"


def _plot_decoder_comparison(results: Sequence[dict[str, Any]], output: Path) -> None:
    labels = [_label(result) for result in results]
    decoder_names: list[str] = []
    for result in results:
        for entry in result["decoders"]:
            if entry["decoder"] not in decoder_names:
                decoder_names.append(entry["decoder"])

    figure, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    width = 0.8 / max(len(decoder_names), 1)
    positions = range(len(results))

    for index, name in enumerate(decoder_names):
        rates = []
        errors = []
        for result in results:
            entry = next((item for item in result["decoders"] if item["decoder"] == name), None)
            rates.append(entry["logical_error_rate"] if entry else float("nan"))
            errors.append(
                entry["logical_error_rate_standard_error"] if entry else float("nan")
            )
        offsets = [position + (index - (len(decoder_names) - 1) / 2) * width for position in positions]
        axes[0].bar(offsets, rates, width=width, yerr=errors, capsize=3, label=name)
        axes[1].bar(
            offsets,
            [
                next(
                    (item for item in result["decoders"] if item["decoder"] == name),
                    {"latency": {"mean_per_shot_microseconds": float("nan")}},
                )["latency"]["mean_per_shot_microseconds"]
                for result in results
            ],
            width=width,
            label=name,
        )

    axes[0].set_ylabel("logical error rate")
    axes[0].set_yscale("log")
    axes[0].set_title("Test LER (log scale, error bars = 1 s.e.)")
    axes[1].set_ylabel("mean per-shot latency [us]")
    axes[1].set_yscale("log")
    axes[1].set_title("Decode latency (log scale)")
    for axis in axes:
        axis.set_xticks(list(positions))
        axis.set_xticklabels(labels, rotation=15, ha="right")
        axis.grid(axis="y", alpha=0.3)
    axes[0].legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)


def _plot_training(results: Sequence[dict[str, Any]], output: Path) -> None:
    figure, axes = plt.subplots(1, len(results), figsize=(4.2 * len(results), 3.6), squeeze=False)
    for axis, result in zip(axes[0], results):
        history = result["training"]["history"]
        epochs = [item["epoch"] for item in history]
        axis.plot(epochs, [item["train_log_loss"] for item in history], label="train")
        axis.plot(epochs, [item["validation_log_loss"] for item in history], label="validation")
        axis.set_xlabel("epoch")
        axis.set_ylabel("BCE log loss")
        axis.set_title(_label(result), fontsize=9)
        axis.grid(alpha=0.3)
        axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)


def _plot_reweight_sweep(results: Sequence[dict[str, Any]], output: Path) -> None:
    figure, axis = plt.subplots(figsize=(6.5, 4.2))
    for result in results:
        selection = result["validation_selection"]
        strengths = [item["reweight_strength"] for item in selection]
        rates = [item["logical_error_rate"] for item in selection]
        axis.plot(strengths, rates, marker="o", label=_label(result))
    axis.set_xlabel("reweight strength (0 = DEM prior, 1 = learned prior)")
    axis.set_ylabel("validation logical error rate")
    axis.set_title("Validation LER versus learned-prior interpolation")
    axis.grid(alpha=0.3)
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)


def build_figures(results_dir: Path, output_dir: Path | None = None) -> list[Path]:
    results = _load_results(results_dir)
    figures_dir = output_dir or (results_dir / "figures")
    figures_dir.mkdir(parents=True, exist_ok=True)
    outputs = [
        figures_dir / "decoder_comparison.png",
        figures_dir / "training_curves.png",
        figures_dir / "reweight_sweep.png",
    ]
    _plot_decoder_comparison(results, outputs[0])
    _plot_training(results, outputs[1])
    _plot_reweight_sweep(results, outputs[2])
    return outputs


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plot M2 result figures.")
    parser.add_argument("--results-dir", type=Path, default=Path("results/m2"))
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    for path in build_figures(args.results_dir, args.output_dir):
        print(path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
