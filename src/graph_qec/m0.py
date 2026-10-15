"""Command-line entry point for the M0 data pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .config import ExperimentConfig
from .data_pipeline import generate_dataset, save_dataset, verify_manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate deterministic Stim/PyMatching M0 artifacts."
    )
    parser.add_argument(
        "--config",
        type=Path,
        nargs="+",
        required=True,
        help="One or more JSON experiment configuration files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory in which per-config artifact directories are created.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, object]] = []

    for config_path in args.config:
        config = ExperimentConfig.from_json_file(config_path)
        artifact_dir = args.output_dir / config.artifact_name()
        if artifact_dir.exists():
            raise FileExistsError(
                f"Artifact directory already exists: {artifact_dir}. "
                "Remove it explicitly or choose another --output-dir."
            )

        dataset = generate_dataset(config)
        manifest = save_dataset(dataset, artifact_dir)
        verify_manifest(artifact_dir)
        summaries.append(
            {
                "artifact_dir": str(artifact_dir.resolve()),
                "config_sha256": manifest["config_sha256"],
                "shots": manifest["samples"]["shots"],
                "num_detectors": manifest["detector_error_model"]["num_detectors"],
                "num_dem_errors": manifest["detector_error_model"]["num_errors"],
                "matching_logical_error_rate": manifest["pymatching_smoke"][
                    "logical_error_rate"
                ],
            }
        )

    print(json.dumps(summaries, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
