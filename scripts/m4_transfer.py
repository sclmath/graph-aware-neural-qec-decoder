r"""M4 cross-code transfer CLI: evaluate a checkpoint on another DEM-level code.

Usage:
    .\.venv\Scripts\python.exe scripts\m4_transfer.py `
        --source-config configs\m4_hgp_rep3x3_code_capacity_p0p05.json `
        --target-config configs\m4_hgp_hamming7x7_code_capacity_p0p05.json `
        --checkpoint results\m4_hgp\<run>\model_state.pt `
        --output-dir results\m4
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from graph_qec.m2_config import M2Config
from graph_qec.m4_pipeline import run_dem_transfer


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cross-code transfer for DEM-level families.")
    parser.add_argument("--source-config", type=Path, required=True)
    parser.add_argument("--target-config", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tag", default=None)
    parser.add_argument("--decoders", nargs="+", default=["bp", "bp_gnn", "bp_gnn_osd"])
    parser.add_argument("--test-shots", type=int, default=None)
    parser.add_argument("--timed-runs", type=int, default=1)
    args = parser.parse_args(argv)

    source = M2Config.from_json_file(args.source_config)
    target = M2Config.from_json_file(args.target_config)
    tag = args.tag or f"{source.experiment.family}_to_{target.experiment.family}"
    output_dir = args.output_dir / tag
    if output_dir.exists():
        raise FileExistsError(f"Result directory already exists: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)

    result = run_dem_transfer(
        source,
        checkpoint_path=args.checkpoint,
        target_config=target,
        benchmark_decoders=args.decoders,
        test_shots=args.test_shots,
        timed_runs=args.timed_runs,
    )
    (output_dir / "results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        f"# M4 transfer: {result['source']['family']} -> {result['target']['family']}",
        "",
        "- source: {family} {noise_model} p={physical_error_rate:g}".format(**result["source"]),
        "- target: {family} {noise_model} p={physical_error_rate:g}, "
        "{num_qubits} qubits, k={k}".format(**result["target"]),
        f"- test shots: {result['splits']['test']['shots']}, "
        f"strength fixed at {result['reweight_strength']:.2f}",
        "",
        "| decoder | logical errors | LER | syndrome consistency | us/shot |",
        "|---|---:|---:|---:|---:|",
    ]
    for entry in result["decoders"]:
        lines.append(
            "| {decoder} | {logical_errors} | {logical_error_rate:.5f} | "
            "{syndrome_consistency_rate:.4f} | {latency:.1f} |".format(
                decoder=entry["decoder"],
                logical_errors=entry["logical_errors"],
                logical_error_rate=entry["logical_error_rate"],
                syndrome_consistency_rate=entry["syndrome_consistency_rate"],
                latency=entry["latency"]["mean_per_shot_microseconds"],
            )
        )
    lines.append("")
    (output_dir / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({entry["decoder"]: entry["logical_errors"] for entry in result["decoders"]}, indent=2))
    print("wrote", output_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
