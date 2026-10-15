r"""Summarizes M2 result directories into a markdown report.

Usage:
    .\.venv\Scripts\python.exe scripts\summarize_m2.py --results-dir results\m2
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence


def _load(results_dir: Path) -> list[dict[str, Any]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(results_dir.glob("*/results.json"))
    ]


def _fmt(value: Any, digits: int = 5) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render(results_dir: Path) -> str:
    results = _load(results_dir)
    lines: list[str] = ["# M2 result summary", "", f"Source: `{results_dir}`", ""]
    lines.append("| experiment | code | noise | p | selected strength | test shots | mechanism accuracy | test log loss |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for result in results:
        experiment = result["config"]["experiment"]
        code = experiment["code"]
        noise = experiment["noise"]
        lines.append(
            "| {name} | {family} d={distance} r={rounds} | {model} | {p} | {strength} | {shots} | {accuracy} | {loss} |".format(
                name=result["name"],
                family=code["family"],
                distance=code["distance"],
                rounds=code["rounds"],
                model=noise["model"],
                p=noise["physical_error_rate"],
                strength=_fmt(result["selected_reweight_strength"], 2),
                shots=result["splits"]["test"]["shots"],
                accuracy=_fmt(result["mechanism_prediction"]["test_binary_accuracy"], 4),
                loss=_fmt(result["mechanism_prediction"]["test_log_loss"], 5),
            )
        )
    lines.append("")

    for result in results:
        experiment = result["config"]["experiment"]
        lines.append(f"## {result['name']}")
        lines.append("")
        lines.append(
            "- graph: {checks} detectors, {variables} error mechanisms, {edges} edges".format(
                checks=result["graph"]["num_detectors"],
                variables=result["graph"]["num_errors"],
                edges=result["graph"]["num_edges"],
            )
        )
        lines.append(
            "- splits: train {train} / validation {validation} / test {test} shots".format(
                train=result["splits"]["train"]["shots"],
                validation=result["splits"]["validation"]["shots"],
                test=result["splits"]["test"]["shots"],
            )
        )
        lines.append(
            "- training: {params} parameters, {epochs} epochs, best validation log loss {loss}".format(
                params=result["training"]["parameters"],
                epochs=result["training"]["epochs"],
                loss=_fmt(result["training"]["best_validation_log_loss"]),
            )
        )
        lines.append(
            "- noise model {model} at p={p}, distance {distance}".format(
                model=experiment["noise"]["model"],
                p=experiment["noise"]["physical_error_rate"],
                distance=experiment["code"]["distance"],
            )
        )
        lines.append("")
        lines.append("| decoder | logical errors | LER | s.e. | convergence | mean iterations | syndrome consistency | us/shot |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
        for entry in result["decoders"]:
            diagnostics = entry["diagnostics"]
            lines.append(
                "| {decoder} | {errors} | {ler} | {se} | {conv} | {iters} | {sync} | {latency} |".format(
                    decoder=entry["decoder"],
                    errors=entry["logical_errors"],
                    ler=_fmt(entry["logical_error_rate"]),
                    se=_fmt(entry["logical_error_rate_standard_error"]),
                    conv=_fmt(diagnostics.get("convergence_rate"), 4),
                    iters=_fmt(diagnostics.get("average_iterations"), 3),
                    sync=_fmt(entry["syndrome_consistency_rate"], 4),
                    latency=_fmt(entry["latency"]["mean_per_shot_microseconds"], 1),
                )
            )
        lines.append("")
        lines.append("Validation sweep:")
        lines.append("")
        lines.append("| strength | LER | mean iterations | convergence |")
        lines.append("|---:|---:|---:|---:|")
        for item in result["validation_selection"]:
            lines.append(
                f"| {item['reweight_strength']} | {_fmt(item['logical_error_rate'])} | "
                f"{_fmt(item['mean_iterations'], 3)} | {_fmt(item['convergence_rate'], 4)} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render an M2 markdown summary.")
    parser.add_argument("--results-dir", type=Path, default=Path("results/m2"))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    output = args.output or (args.results_dir / "SUMMARY.md")
    output.write_text(render(args.results_dir), encoding="utf-8")
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
