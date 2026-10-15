"""Command-line entry point for M3 transfer evaluations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .m2 import _write_summary_csv
from .m2_config import M2Config
from .m2_pipeline import _log
from .m3_pipeline import run_transfer_evaluation, target_experiment


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate a trained M2 checkpoint on a new noise rate, noise model or code distance (M3)."
    )
    parser.add_argument("--config", type=Path, required=True, help="Source M2/M3 JSON config.")
    parser.add_argument("--checkpoint", type=Path, required=True, help="Path to model_state.pt.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Result directory for this transfer run.")
    parser.add_argument("--tag", default=None, help="Artifact directory name; defaults to a description of the target.")
    parser.add_argument("--target-distance", type=int, default=None)
    parser.add_argument("--target-rounds", type=int, default=None)
    parser.add_argument("--target-noise-model", default=None)
    parser.add_argument("--target-physical-error-rate", type=float, default=None)
    parser.add_argument("--test-seeds", type=int, nargs="+", default=None)
    parser.add_argument("--test-shots", type=int, default=None)
    parser.add_argument("--decoders", nargs="+", default=None)
    parser.add_argument("--timed-runs", type=int, default=None)
    return parser


def _artifact_tag(config: M2Config, experiment: Any) -> str:
    probability = f"{experiment.physical_error_rate:g}".replace(".", "p")
    return f"{config.name}__from_d{config.experiment.distance}__to_d{experiment.distance}__{experiment.noise_model}__p{probability}"


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    config = M2Config.from_json_file(args.config)
    experiment = target_experiment(
        config.experiment,
        distance=args.target_distance,
        rounds=args.target_rounds,
        noise_model=args.target_noise_model,
        physical_error_rate=args.target_physical_error_rate,
    )
    tag = args.tag or _artifact_tag(config, experiment)
    output_dir = args.output_dir / tag
    if output_dir.exists():
        raise FileExistsError(
            f"Result directory already exists: {output_dir}. "
            "Choose another --output-dir/--tag or remove it explicitly."
        )
    output_dir.mkdir(parents=True, exist_ok=False)

    result = run_transfer_evaluation(
        config,
        checkpoint_path=args.checkpoint,
        experiment=experiment,
        test_seeds=args.test_seeds,
        test_shots=args.test_shots,
        benchmark_decoders=args.decoders,
        timed_runs=args.timed_runs,
    )
    with (output_dir / "results.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (output_dir / "config.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(result["config"], handle, indent=2, sort_keys=True)
        handle.write("\n")
    _write_summary_csv(output_dir / "summary.csv", result)

    print(
        json.dumps(
            {
                "output_dir": str(output_dir.resolve()),
                "transfer": result["transfer"],
                "decoders": [
                    {
                        "name": entry["decoder"],
                        "logical_errors": entry["logical_errors"],
                        "ler": entry["logical_error_rate"],
                        "status": entry.get("status", "ok"),
                        "us_per_shot": entry.get("latency", {}).get("mean_per_shot_microseconds"),
                    }
                    for entry in result["decoders"]
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
