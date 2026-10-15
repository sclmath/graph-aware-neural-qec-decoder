"""Command-line entry point for M4 HGP / DEM-level code experiments."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .m2 import _save_result
from .m2_config import M2Config
from .m4_pipeline import run_m4


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train and evaluate GNN-reweighted BP on HGP (DEM-level) code families."
    )
    parser.add_argument("--config", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


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
        result = run_m4(config, artifact_dir=output_dir)
        _save_result(result, output_dir)
        summaries.append(
            {
                "output_dir": str(output_dir.resolve()),
                "code": result["code"],
                "selected_reweight_strength": result["selected_reweight_strength"],
                "decoders": [
                    {
                        "name": entry["decoder"],
                        "logical_errors": entry["logical_errors"],
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
    sys.exit(main())
