r"""M3 OSD trigger policy: when should the OSD-0 fallback actually run?

Section 4 of the M3 report shows that running OSD-0 on every non-converged shot
is a net loss (52 rescued vs 136 broken).  This script asks whether the damage
is concentrated in BP failures that are *far* from a consistent solution, by
sweeping a threshold on the residual syndrome weight:

    policy(k): converged          -> keep the BP correction
               syndrome weight<=k -> keep the BP correction
               otherwise          -> run OSD-0

k=0 reproduces ``bp_gnn_osd`` (OSD on every non-converged shot); a very large k
reproduces ``bp_gnn`` (never run OSD).

Usage:
    .\.venv\Scripts\python.exe scripts\m3_osd_trigger_policy.py `
        --config configs\m3_learned_basis_repetition_circuit_level_d3.json `
        --checkpoint results\m3\<run>\model_state.pt
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from graph_qec.decoders import BPDecoder, DEMSystem
from graph_qec.decoders.bp import _osd0_correction
from graph_qec.graph_features import prior_log_odds
from graph_qec.m2_config import M2Config
from graph_qec.m2_pipeline import build_experiment_graph, combined_logits, generate_split
from graph_qec.m3_pipeline import load_reweighting_checkpoint, target_experiment
from graph_qec.models import graph_to_tensors, predict_logits


def _observables(corrections: np.ndarray, system: DEMSystem) -> np.ndarray:
    predictions = (system.observable_matrix @ corrections.T) % 2
    return np.ascontiguousarray(predictions.T, dtype=np.uint8)


def _consistent(corrections: np.ndarray, detections: np.ndarray, system: DEMSystem) -> np.ndarray:
    residual = (system.check_matrix @ corrections.T) % 2
    return np.all(residual.T == detections, axis=1)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sweep an OSD-0 trigger threshold.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--thresholds", type=int, nargs="+", default=[0, 1, 2, 3, 4, 6, 8, 12, 10**6])
    parser.add_argument("--target-physical-error-rate", type=float, default=None)
    parser.add_argument("--output", type=Path, default=Path("results/m3/osd_trigger_policy.json"))
    parser.add_argument("--markdown", type=Path, default=Path("results/m3/OSD_TRIGGER_POLICY.md"))
    args = parser.parse_args(argv)

    config = M2Config.from_json_file(args.config)
    experiment = (
        config.experiment
        if args.target_physical_error_rate is None
        else target_experiment(
            config.experiment, physical_error_rate=args.target_physical_error_rate
        )
    )
    split, reference = generate_split(
        config, config.splits.test_seeds, config.splits.test_shots, experiment
    )
    graph = build_experiment_graph(reference)
    system = DEMSystem.from_detector_error_model(reference.raw_dem)
    tensors = graph_to_tensors(graph)
    base_log_odds = prior_log_odds(system.priors)
    model, _ = load_reweighting_checkpoint(config, graph, args.checkpoint)
    logits = predict_logits(model, tensors, split.detections)
    strength = float(config.decoder.reweight_strengths[-1])
    priors = combined_logits(base_log_odds, logits, strength)

    bp = BPDecoder(
        reference.raw_dem,
        max_iterations=config.decoder.max_iterations,
        min_sum_scaling=config.decoder.min_sum_scaling,
        damping=config.decoder.damping,
    )

    shots = split.detections.shape[0]
    corrections_bp = np.zeros((shots, system.num_errors), dtype=np.uint8)
    corrections_osd = np.zeros((shots, system.num_errors), dtype=np.uint8)
    distances = np.zeros(shots, dtype=np.int64)
    converged = np.zeros(shots, dtype=bool)
    for shot, syndrome in enumerate(split.detections):
        state = bp._decode_shot(syndrome, priors[shot])
        corrections_bp[shot] = state.correction
        distances[shot] = state.syndrome_distance
        converged[shot] = state.converged
        correction, _ = _osd0_correction(
            system.check_matrix, syndrome, state.posterior_llr, state.correction
        )
        corrections_osd[shot] = correction

    observables = split.observables
    predictions_bp = _observables(corrections_bp, system)
    predictions_osd = _observables(corrections_osd, system)
    error_bp = np.any(predictions_bp != observables, axis=1)
    error_osd = np.any(predictions_osd != observables, axis=1)
    consistent_bp = _consistent(corrections_bp, split.detections, system)

    policy: list[dict[str, Any]] = []
    for threshold in args.thresholds:
        use_osd = (~converged) & (distances > threshold)
        errors = np.where(use_osd, error_osd, error_bp)
        consistent = np.where(use_osd, True, consistent_bp)
        policy.append(
            {
                "threshold": int(threshold),
                "osd_shots": int(np.count_nonzero(use_osd)),
                "osd_rate": float(np.mean(use_osd)),
                "logical_errors": int(np.count_nonzero(errors)),
                "logical_error_rate": float(np.mean(errors)),
                "syndrome_consistency_rate": float(np.mean(consistent)),
            }
        )

    buckets: list[dict[str, Any]] = []
    non_converged = ~converged
    for low, high, label in [(1, 1, "1"), (2, 2, "2"), (3, 3, "3"), (4, 4, "4"), (5, 10**6, "5+")]:
        mask = non_converged & (distances >= low) & (distances <= high)
        count = int(np.count_nonzero(mask))
        buckets.append(
            {
                "syndrome_weight": label,
                "shots": count,
                "bp_errors": int(np.count_nonzero(error_bp[mask])),
                "osd_errors": int(np.count_nonzero(error_osd[mask])),
                "rescued": int(np.count_nonzero(error_bp[mask] & ~error_osd[mask])),
                "broken": int(np.count_nonzero(~error_bp[mask] & error_osd[mask])),
            }
        )

    summary = {
        "experiment": {
            "distance": experiment.distance,
            "rounds": experiment.rounds,
            "noise_model": experiment.noise_model,
            "physical_error_rate": experiment.physical_error_rate,
        },
        "shots": int(shots),
        "reweight_strength": strength,
        "converged_shots": int(np.count_nonzero(converged)),
        "non_converged_shots": int(np.count_nonzero(non_converged)),
        "policy": policy,
        "non_converged_buckets": buckets,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# M3 OSD-0 trigger policy",
        "",
        "Learned prior at strength {:.2f}; {} test shots; {} non-converged shots.".format(
            strength, shots, summary["non_converged_shots"]
        ),
        "",
        "| OSD trigger threshold k | OSD shots | OSD rate | logical errors | LER | syndrome consistency |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for item in policy:
        label = "never (0 on BP)" if item["threshold"] >= 10**6 else str(item["threshold"])
        lines.append(
            "| {} | {} | {:.4f} | {} | {:.5f} | {:.4f} |".format(
                label,
                item["osd_shots"],
                item["osd_rate"],
                item["logical_errors"],
                item["logical_error_rate"],
                item["syndrome_consistency_rate"],
            )
        )
    lines += [
        "",
        "Outcome of OSD-0 by residual syndrome weight among non-converged shots:",
        "",
        "| residual weight | shots | BP errors | OSD errors | rescued | broken |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for bucket in buckets:
        lines.append(
            "| {} | {} | {} | {} | {} | {} |".format(
                bucket["syndrome_weight"],
                bucket["shots"],
                bucket["bp_errors"],
                bucket["osd_errors"],
                bucket["rescued"],
                bucket["broken"],
            )
        )
    lines.append("")
    args.markdown.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    print("wrote", args.output.resolve())
    print("wrote", args.markdown.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
