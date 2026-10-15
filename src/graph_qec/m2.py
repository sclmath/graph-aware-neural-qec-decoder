"""Command-line entry point for M2 GNN reweighting experiments."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Sequence

from .m2_config import M2Config
from .m2_pipeline import run_m2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train and evaluate GNN-reweighted BP decoders (M2)."
    )
    parser.add_argument(
        "--config",
        type=Path,
        nargs="+",
        required=True,
        help="One or more M2 JSON configuration files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory in which per-config result directories are created.",
    )
    return parser


def _write_summary_csv(path: Path, result: dict[str, Any]) -> None:
    fields = [
        "decoder",
        "shots",
        "logical_errors",
        "logical_error_rate",
        "logical_error_rate_standard_error",
        "mean_per_shot_microseconds",
        "throughput_shots_per_second",
        "convergence_rate",
        "mean_iterations",
        "syndrome_consistency_rate",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for entry in result["decoders"]:
            diagnostics = entry["diagnostics"]
            writer.writerow(
                {
                    "decoder": entry["decoder"],
                    "shots": result["splits"]["test"]["shots"],
                    "logical_errors": entry["logical_errors"],
                    "logical_error_rate": entry["logical_error_rate"],
                    "logical_error_rate_standard_error": entry[
                        "logical_error_rate_standard_error"
                    ],
                    "mean_per_shot_microseconds": entry["latency"][
                        "mean_per_shot_microseconds"
                    ],
                    "throughput_shots_per_second": entry["latency"][
                        "throughput_shots_per_second"
                    ],
                    "convergence_rate": diagnostics.get("convergence_rate", ""),
                    "mean_iterations": diagnostics.get("average_iterations", ""),
                    "syndrome_consistency_rate": entry["syndrome_consistency_rate"],
                }
            )


def _write_training_csv(path: Path, result: dict[str, Any]) -> None:
    fields = ["epoch", "train_log_loss", "validation_log_loss", "seconds"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in result["training"]["history"]:
            writer.writerow(row)


def _save_result(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "config.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(result["config"], handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (output_dir / "results.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    _write_summary_csv(output_dir / "summary.csv", result)
    _write_training_csv(output_dir / "training_history.csv", result)


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []

    for config_path in args.config:
        config = M2Config.from_json_file(config_path)
        output_dir = args.output_dir / config.artifact_name()
        if output_dir.exists():
            raise FileExistsError(
                f"Result directory already exists: {output_dir}. "
                "Choose another --output-dir or remove it explicitly."
            )
        output_dir.mkdir(parents=True, exist_ok=False)
        result = run_m2(config, artifact_dir=output_dir)
        _save_result(result, output_dir)
        summaries.append(
            {
                "output_dir": str(output_dir.resolve()),
                "config_sha256": result["config_sha256"],
                "selected_reweight_strength": result["selected_reweight_strength"],
                "decoders": [
                    {
                        "name": entry["decoder"],
                        "ler": entry["logical_error_rate"],
                        "mean_per_shot_us": entry["latency"]["mean_per_shot_microseconds"],
                    }
                    for entry in result["decoders"]
                ],
            }
        )

    print(json.dumps(summaries, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
