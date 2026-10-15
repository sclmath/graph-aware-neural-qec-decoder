r"""M3 strength recalibration under noise shift.

The M3 transfer sweep feeds the learned prior into BP with the interpolation
strength that was selected on the *source* validation split (1.0 at
p=0.01).  Under noise shift that stale strength can hurt, so this script
re-selects it on a validation split drawn from the *target* noise rate (a
legitimate, test-free procedure) and measures what that buys on the test split.

Usage:
    .\.venv\Scripts\python.exe scripts\m3_strength_recalibration.py `
        --config configs\m3_learned_basis_repetition_circuit_level_d3.json `
        --checkpoint results\m3\<run>\model_state.pt `
        --targets 0.003 0.005 0.008 0.02
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from graph_qec.decoders import BPDecoder, BPOSDDecoder, DEMSystem
from graph_qec.graph_features import prior_log_odds
from graph_qec.m2_config import M2Config
from graph_qec.m2_pipeline import (
    _decode_with_priors,
    _evaluate,
    build_experiment_graph,
    combined_logits,
    generate_split,
)
from graph_qec.m3_pipeline import load_reweighting_checkpoint, target_experiment
from graph_qec.models import graph_to_tensors, predict_logits


def _log_loss(logits: np.ndarray, targets: np.ndarray) -> float:
    return float(
        np.mean(
            np.maximum(logits, 0.0)
            - logits * targets
            + np.log1p(np.exp(-np.abs(logits)))
        )
    )


def recalibrate(
    config: M2Config,
    checkpoint: Path,
    physical_error_rate: float,
    *,
    validation_shots: int,
    test_shots: int,
    timed_runs: int,
) -> dict[str, Any]:
    experiment = target_experiment(config.experiment, physical_error_rate=physical_error_rate)

    validation, reference = generate_split(
        config, config.splits.validation_seeds, validation_shots, experiment
    )
    graph = build_experiment_graph(reference)
    system = DEMSystem.from_detector_error_model(reference.raw_dem)
    tensors = graph_to_tensors(graph)
    base_log_odds = prior_log_odds(system.priors)
    model, _ = load_reweighting_checkpoint(config, graph, checkpoint)

    validation_logits = predict_logits(model, tensors, validation.detections)
    bp = BPDecoder(
        reference.raw_dem,
        max_iterations=config.decoder.max_iterations,
        min_sum_scaling=config.decoder.min_sum_scaling,
        damping=config.decoder.damping,
    )

    sweep: list[dict[str, Any]] = []
    for strength in config.decoder.reweight_strengths:
        priors = combined_logits(base_log_odds, validation_logits, strength)
        metrics = _evaluate(
            lambda detections, priors=priors: _decode_with_priors(bp, detections, priors),
            detections=validation.detections,
            observables=validation.observables,
            system=system,
            timed_runs=1,
        )
        sweep.append(
            {
                "strength": float(strength),
                "logical_errors": metrics["logical_errors"],
                "logical_error_rate": metrics["logical_error_rate"],
                "mean_iterations": metrics["diagnostics"].get("average_iterations"),
                "convergence_rate": metrics["diagnostics"].get("convergence_rate"),
            }
        )
    selected = min(
        sweep,
        key=lambda item: (
            item["logical_error_rate"],
            item["mean_iterations"] if item["mean_iterations"] is not None else float("inf"),
        ),
    )

    test, test_reference = generate_split(
        config, config.splits.test_seeds, test_shots, experiment
    )
    test_graph = build_experiment_graph(test_reference)
    test_system = DEMSystem.from_detector_error_model(test_reference.raw_dem)
    test_tensors = graph_to_tensors(test_graph)
    test_base = prior_log_odds(test_system.priors)
    test_logits = predict_logits(model, test_tensors, test.detections)
    test_priors = combined_logits(test_base, test_logits, float(selected["strength"]))

    bp_osd = BPOSDDecoder(
        test_reference.raw_dem,
        max_iterations=config.decoder.max_iterations,
        min_sum_scaling=config.decoder.min_sum_scaling,
        damping=config.decoder.damping,
        osd_order=0,
    )
    variants = {
        "bp": bp.decode_batch,
        "bp_gnn_recalibrated": lambda detections: _decode_with_priors(bp, detections, test_priors),
        "bp_gnn_osd_recalibrated": lambda detections: bp_osd.decode_batch(
            detections, prior_llr=test_priors
        ),
    }
    entries: list[dict[str, Any]] = []
    for name, decode in variants.items():
        metrics = _evaluate(
            decode,
            detections=test.detections,
            observables=test.observables,
            system=test_system,
            timed_runs=timed_runs,
        )
        entry = dict(metrics)
        entry["decoder"] = name
        entries.append(entry)

    return {
        "physical_error_rate": float(physical_error_rate),
        "validation_shots": int(validation.shots),
        "test_shots": int(test.shots),
        "selected_strength": float(selected["strength"]),
        "validation_sweep": sweep,
        "mechanism_prediction": {
            "test_log_loss": _log_loss(test_logits, test.error_mechanisms),
            "dem_prior_log_loss": _log_loss(test_base, test.error_mechanisms),
        },
        "decoders": entries,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recalibrate the learned-prior strength under noise shift.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--targets", type=float, nargs="+", required=True)
    parser.add_argument("--validation-shots", type=int, default=16384)
    parser.add_argument("--test-shots", type=int, default=16384)
    parser.add_argument("--timed-runs", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=Path("results/m3/strength_recalibration"))
    args = parser.parse_args(argv)

    config = M2Config.from_json_file(args.config)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "config": str(args.config),
        "checkpoint": str(args.checkpoint),
        "targets": [float(p) for p in args.targets],
        "results": [],
    }
    rows: list[dict[str, Any]] = []
    for probability in args.targets:
        result = recalibrate(
            config,
            args.checkpoint,
            float(probability),
            validation_shots=args.validation_shots,
            test_shots=args.test_shots,
            timed_runs=args.timed_runs,
        )
        payload["results"].append(result)
        for entry in result["decoders"]:
            rows.append(
                {
                    "physical_error_rate": result["physical_error_rate"],
                    "selected_strength": result["selected_strength"],
                    "decoder": entry["decoder"],
                    "logical_errors": entry["logical_errors"],
                    "ler": entry["logical_error_rate"],
                    "ler_standard_error": entry["logical_error_rate_standard_error"],
                    "syndrome_consistency_rate": entry["syndrome_consistency_rate"],
                    "mean_iterations": entry["diagnostics"].get("average_iterations"),
                    "convergence_rate": entry["diagnostics"].get("convergence_rate"),
                    "us_per_shot": entry["latency"]["mean_per_shot_microseconds"],
                }
            )

    (args.output_dir / "results.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (args.output_dir / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# M3 learned-prior strength recalibration under noise shift",
        "",
        "| target p | selected strength | decoder | logical errors | LER | s.e. | syndrome consistency |",
        "|---:|---:|---|---:|---:|---:|---:|",
    ]
    strength_by_p = {result["physical_error_rate"]: result["selected_strength"] for result in payload["results"]}
    for row in rows:
        lines.append(
            "| {:g} | {:.2f} | {} | {} | {:.5f} | {:.5f} | {:.4f} |".format(
                row["physical_error_rate"],
                strength_by_p[row["physical_error_rate"]],
                row["decoder"],
                row["logical_errors"],
                row["ler"],
                row["ler_standard_error"],
                row["syndrome_consistency_rate"],
            )
        )
    lines.append("")
    (args.output_dir / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(
        {f"{result['physical_error_rate']:g}": {
            "selected_strength": result["selected_strength"],
            "sweep": [(item["strength"], item["logical_errors"]) for item in result["validation_sweep"]],
            "test": {entry["decoder"]: entry["logical_errors"] for entry in result["decoders"]},
        } for result in payload["results"]},
        indent=2, sort_keys=True))
    print("wrote", args.output_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
