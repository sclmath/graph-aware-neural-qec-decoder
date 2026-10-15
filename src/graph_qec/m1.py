"""Command-line entry point for M1 baseline benchmarks."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Sequence

from .benchmark import run_benchmark
from .benchmark_config import BenchmarkConfig
from .data_pipeline import generate_dataset


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run reproducible M1 decoder benchmarks."
    )
    parser.add_argument(
        "--config",
        type=Path,
        nargs="+",
        required=True,
        help="One or more M1 benchmark JSON configuration files.",
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
        "mean_total_seconds",
        "mean_per_shot_microseconds",
        "throughput_shots_per_second",
        "peak_rss_bytes",
        "peak_rss_delta_bytes",
        "peak_python_bytes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for decoder_result in result["decoders"]:
            writer.writerow(
                {
                    "decoder": decoder_result["decoder"],
                    "shots": decoder_result["shots"],
                    "logical_errors": decoder_result["logical_errors"],
                    "logical_error_rate": decoder_result["logical_error_rate"],
                    "logical_error_rate_standard_error": decoder_result[
                        "logical_error_rate_standard_error"
                    ],
                    "mean_total_seconds": decoder_result["latency"][
                        "mean_total_seconds"
                    ],
                    "mean_per_shot_microseconds": decoder_result["latency"][
                        "mean_per_shot_microseconds"
                    ],
                    "throughput_shots_per_second": decoder_result["latency"][
                        "throughput_shots_per_second"
                    ],
                    "peak_rss_bytes": decoder_result["memory"]["peak_rss_bytes"],
                    "peak_rss_delta_bytes": decoder_result["memory"][
                        "peak_rss_delta_bytes"
                    ],
                    "peak_python_bytes": decoder_result["memory"]["peak_python_bytes"],
                }
            )


def _save_result(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=False)
    with (output_dir / "config.json").open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        json.dump(result["config"], handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (output_dir / "benchmark.json").open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    _write_summary_csv(output_dir / "summary.csv", result)


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []

    for config_path in args.config:
        config = BenchmarkConfig.from_json_file(config_path)
        output_dir = args.output_dir / config.artifact_name()
        if output_dir.exists():
            raise FileExistsError(
                f"Result directory already exists: {output_dir}. "
                "Choose another --output-dir or remove it explicitly."
            )

        dataset = generate_dataset(config.experiment)
        result = run_benchmark(dataset, config)
        _save_result(result, output_dir)
        summaries.append(
            {
                "output_dir": str(output_dir.resolve()),
                "config_sha256": result["config_sha256"],
                "shots": result["dataset"]["shots"],
                "decoders": [
                    {
                        "name": decoder_result["decoder"],
                        "ler": decoder_result["logical_error_rate"],
                        "mean_per_shot_us": decoder_result["latency"][
                            "mean_per_shot_microseconds"
                        ],
                    }
                    for decoder_result in result["decoders"]
                ],
            }
        )

    print(json.dumps(summaries, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
