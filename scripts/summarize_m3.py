r"""Summarizes M3 transfer result directories into markdown and CSV.

Usage:
    .\.venv\Scripts\python.exe scripts\summarize_m3.py --results-dir results\m3
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Sequence


def load_results(results_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in sorted(results_dir.glob("*/results.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_path"] = str(path.parent)
        results.append(payload)
    return results


def _fmt(value: Any, digits: int = 5) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _decoder(entry: dict[str, Any]) -> str:
    return entry["decoder"]


def _target(result: dict[str, Any]) -> dict[str, Any]:
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


def _source(result: dict[str, Any]) -> dict[str, Any]:
    if "transfer" in result:
        return result["transfer"]["source_experiment"]
    experiment = result["config"]["experiment"]
    return {
        "family": experiment["code"]["family"],
        "distance": experiment["code"]["distance"],
        "rounds": experiment["code"]["rounds"],
        "noise_model": experiment["noise"]["model"],
        "physical_error_rate": experiment["noise"]["physical_error_rate"],
    }


def _entry(result: dict[str, Any], decoder: str) -> dict[str, Any] | None:
    return next((item for item in result["decoders"] if _decoder(item) == decoder), None)


def _ler_table(results: Sequence[dict[str, Any]], key: str) -> list[str]:
    """Renders one LER matrix; ``key`` selects the varying transfer axis."""

    decoders: list[str] = []
    for result in results:
        for entry in result["decoders"]:
            if _decoder(entry) not in decoders:
                decoders.append(_decoder(entry))
    lines = ["| " + key + " | shots | " + " | ".join(decoders) + " |"]
    lines.append("|---" * (len(decoders) + 2) + "|")
    for result in sorted(results, key=lambda item: _target(item)[key]):
        if key == "physical_error_rate":
            label = f"{_target(result)[key]:g}"
        else:
            label = str(_target(result)[key])
        row = []
        for name in decoders:
            entry = _entry(result, name)
            row.append("-" if entry is None else _fmt(entry["logical_error_rate"]))
        lines.append(
            f"| {label} | {result['splits']['test']['shots']} | " + " | ".join(row) + " |"
        )
    return lines


def _syndrome_table(results: Sequence[dict[str, Any]]) -> list[str]:
    decoders: list[str] = []
    for result in results:
        for entry in result["decoders"]:
            if _decoder(entry) not in decoders:
                decoders.append(_decoder(entry))
    lines = ["| target | " + " | ".join(decoders) + " |"]
    lines.append("|---" * (len(decoders) + 1) + "|")
    for result in sorted(
        results,
        key=lambda item: (
            _target(item)["physical_error_rate"],
            _target(item)["distance"],
        ),
    ):
        target = _target(result)
        label = f"d{target['distance']} p={target['physical_error_rate']:g}"
        row = []
        for name in decoders:
            entry = _entry(result, name)
            row.append(
                "-"
                if entry is None
                else _fmt(entry["syndrome_consistency_rate"], 4)
            )
        lines.append(f"| {label} | " + " | ".join(row) + " |")
    return lines


def _source_key(result: dict[str, Any]) -> tuple:
    source = _source(result)
    return (
        source["family"],
        source["distance"],
        source["rounds"],
        source["noise_model"],
        source["physical_error_rate"],
    )


def render(results_dir: Path) -> str:
    transfers = [item for item in load_results(results_dir) if item.get("stage") == "M3-transfer"]
    headline = [item for item in load_results(results_dir) if item.get("stage") == "M2"]

    # Transfer runs are grouped by the checkpoint they start from; the group with
    # the most runs is treated as the primary source of the report.
    groups: dict[tuple, list[dict[str, Any]]] = {}
    for item in transfers:
        groups.setdefault(_source_key(item), []).append(item)
    primary_key = max(groups, key=lambda key: len(groups[key])) if groups else None
    results = groups.get(primary_key, []) if primary_key is not None else []
    foreign = [item for item in transfers if primary_key is not None and _source_key(item) != primary_key]
    source = next(
        (_source(item) for item in results),
        {"family": "repetition_code", "distance": 3, "rounds": 3, "noise_model": "circuit_level", "physical_error_rate": 0.01},
    )

    lines: list[str] = ["# M3 result summary", "", f"Source: `{results_dir}`", ""]
    lines.append(
        "Source checkpoint: {family} d={distance} r={rounds} {noise_model} p={physical_error_rate:g}".format(
            **source
        )
    )
    lines.append("")

    noise = [
        item
        for item in results
        if _target(item)["distance"] == source["distance"]
        and _target(item)["noise_model"] == source["noise_model"]
    ]
    distance = [
        item
        for item in results
        if _target(item)["distance"] != source["distance"]
        and _target(item)["noise_model"] == source["noise_model"]
    ]
    other = [item for item in results if item not in noise and item not in distance]

    if headline:
        lines.append("## In-distribution reference (source noise rate)")
        lines.append("")
        lines.append("| experiment | shots | decoders |")
        lines.append("|---|---|---|")
        for result in headline:
            target = _target(result)
            lines.append(
                f"| {result['name']} d{target['distance']} p={target['physical_error_rate']:g} "
                f"| {result['splits']['test']['shots']} "
                f"| {', '.join(_decoder(entry) for entry in result['decoders'])} |"
            )
        lines.append("")

    if noise:
        lines.append("## Noise-rate extrapolation (same code, different physical error rate)")
        lines.append("")
        lines.append("Test logical error rate:")
        lines.append("")
        lines.extend(_ler_table(noise, "physical_error_rate"))
        lines.append("")
        lines.append("Syndrome consistency rate:")
        lines.append("")
        lines.extend(_syndrome_table(noise))
        lines.append("")

    if distance:
        lines.append("## Code-distance extrapolation (same noise model and code family)")
        lines.append("")
        lines.append("Test logical error rate:")
        lines.append("")
        lines.extend(_ler_table(distance, "distance"))
        lines.append("")

    if other or foreign:
        lines.append("## Other checkpoints and transfer axes")
        lines.append("")
        lines.append("| source | target | shots | decoders |")
        lines.append("|---|---|---:|---|")
        for result in list(other) + list(foreign):
            target = _target(result)
            src = _source(result)
            lines.append(
                f"| d{src['distance']} p={src['physical_error_rate']:g} "
                f"| d{target['distance']} {target['noise_model']} p={target['physical_error_rate']:g} "
                f"| {result['splits']['test']['shots']} "
                f"| {', '.join(_decoder(entry) for entry in result['decoders'])} |"
            )
        lines.append("")

    lines.append("## Mechanism-posterior calibration under distribution shift")
    lines.append("")
    lines.append(
        "| target | shots | learned log loss | DEM-prior log loss | learned AUC | DEM-prior AUC | mechanism accuracy |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for result in sorted(
        results + foreign,
        key=lambda item: (
            _target(item)["distance"],
            _target(item)["physical_error_rate"],
        ),
    ):
        target = _target(result)
        source = _source(result)
        prediction = result["mechanism_prediction"]
        lines.append(
            "| d{src_d}->d{d} p={p:g} | {shots} | {loss} | {prior} | {auc} | {prior_auc} | {acc} |".format(
                src_d=source["distance"],
                d=target["distance"],
                p=target["physical_error_rate"],
                shots=result["splits"]["test"]["shots"],
                loss=_fmt(prediction["test_log_loss"]),
                prior=_fmt(prediction["dem_prior_log_loss"]),
                auc=_fmt(prediction["test_roc_auc"], 4),
                prior_auc=_fmt(prediction["dem_prior_roc_auc"], 4),
                acc=_fmt(prediction["test_binary_accuracy"], 4),
            )
        )
    lines.append("")

    lines.append("## Per-run detail")
    lines.append("")
    for result in sorted(
        results,
        key=lambda item: (
            _target(item)["distance"],
            _target(item)["physical_error_rate"],
        ),
    ):
        target = _target(result)
        lines.append(
            f"### d{target['distance']} {target['noise_model']} p={target['physical_error_rate']:g} "
            f"({result['_path']})"
        )
        lines.append("")
        lines.append(
            "- graph: {checks} detectors, {variables} mechanisms, {edges} edges; "
            "test shots: {shots} (seeds {seeds})".format(
                checks=result["graph"]["num_detectors"],
                variables=result["graph"]["num_errors"],
                edges=result["graph"]["num_edges"],
                shots=result["splits"]["test"]["shots"],
                seeds=result["splits"]["test"]["seeds"],
            )
        )
        lines.append(
            "- reweight strength fixed at {strength}".format(
                strength=_fmt(result["transfer"]["reweight_strength"], 2)
            )
        )
        lines.append("")
        lines.append(
            "| decoder | logical errors | LER | s.e. | syndrome consistency | convergence | mean iterations | OSD rate | us/shot |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for entry in result["decoders"]:
            diagnostics = entry["diagnostics"]
            lines.append(
                "| {decoder} | {errors} | {ler} | {se} | {sync} | {conv} | {iters} | {osd} | {latency} |".format(
                    decoder=entry["decoder"],
                    errors=entry["logical_errors"],
                    ler=_fmt(entry["logical_error_rate"]),
                    se=_fmt(entry["logical_error_rate_standard_error"]),
                    sync=_fmt(entry["syndrome_consistency_rate"], 4),
                    conv=_fmt(diagnostics.get("convergence_rate"), 4),
                    iters=_fmt(diagnostics.get("average_iterations"), 3),
                    osd=_fmt(diagnostics.get("osd_rate"), 4),
                    latency=_fmt(entry["latency"]["mean_per_shot_microseconds"], 1),
                )
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def write_csv(results_dir: Path, results: Sequence[dict[str, Any]], path: Path) -> None:
    fields = [
        "name",
        "source_distance",
        "source_p",
        "target_distance",
        "target_noise_model",
        "target_p",
        "shots",
        "decoder",
        "logical_errors",
        "ler",
        "ler_standard_error",
        "syndrome_consistency_rate",
        "convergence_rate",
        "mean_iterations",
        "osd_rate",
        "us_per_shot",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in results:
            if result.get("stage") != "M3-transfer":
                continue
            source = _source(result)
            target = _target(result)
            for entry in result["decoders"]:
                diagnostics = entry["diagnostics"]
                writer.writerow(
                    {
                        "name": result["name"],
                        "source_distance": source["distance"],
                        "source_p": source["physical_error_rate"],
                        "target_distance": target["distance"],
                        "target_noise_model": target["noise_model"],
                        "target_p": target["physical_error_rate"],
                        "shots": result["splits"]["test"]["shots"],
                        "decoder": entry["decoder"],
                        "logical_errors": entry["logical_errors"],
                        "ler": entry["logical_error_rate"],
                        "ler_standard_error": entry["logical_error_rate_standard_error"],
                        "syndrome_consistency_rate": entry["syndrome_consistency_rate"],
                        "convergence_rate": diagnostics.get("convergence_rate"),
                        "mean_iterations": diagnostics.get("average_iterations"),
                        "osd_rate": diagnostics.get("osd_rate"),
                        "us_per_shot": entry["latency"]["mean_per_shot_microseconds"],
                    }
                )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize M3 transfer results.")
    parser.add_argument("--results-dir", type=Path, default=Path("results/m3"))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--csv", type=Path, default=None)
    args = parser.parse_args(argv)

    output = args.output or args.results_dir / "SUMMARY.md"
    output.write_text(render(args.results_dir), encoding="utf-8")
    print(output.resolve())
    csv_path = args.csv or args.results_dir / "sweep.csv"
    write_csv(args.results_dir, load_results(args.results_dir), csv_path)
    print(csv_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
