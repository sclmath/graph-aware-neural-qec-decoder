r"""M3 failure analysis: where the OSD-0 fallback cancels the learned-prior gain.

Rebuilds the test split of a trained checkpoint and decodes every shot with the
same BP/OSD machinery the pipeline uses, but keeps the per-shot logical outcomes
so that the change can be attributed to

* the learned prior (``bp`` -> ``bp_gnn``),
* the OSD-0 fallback (``bp_gnn`` -> ``bp_gnn_osd``),
* the OSD candidate ordering (``bp_gnn_osd`` -> ``bp_gnn_osd_learned_order``).

Usage:
    .\.venv\Scripts\python.exe scripts\m3_failure_analysis.py `
        --config configs\m3_learned_basis_repetition_circuit_level_d3.json `
        --checkpoint results\m3\<run>\model_state.pt
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from graph_qec.decoders import BPDecoder, BPOSDDecoder, DEMSystem
from graph_qec.graph_features import prior_log_odds
from graph_qec.m2_config import M2Config
from graph_qec.m2_pipeline import build_experiment_graph, combined_logits, generate_split
from graph_qec.m3_pipeline import load_reweighting_checkpoint, target_experiment
from graph_qec.models import graph_to_tensors, predict_logits


from graph_qec.stats import mcnemar  # noqa: E402  (shared with the T8 study)


def _logical_errors(corrections: np.ndarray, observables: np.ndarray, system: DEMSystem) -> np.ndarray:
    predictions = (system.observable_matrix @ corrections.T) % 2
    predictions = np.ascontiguousarray(predictions.T, dtype=np.uint8)
    return np.any(predictions != observables, axis=1)


def _consistent(corrections: np.ndarray, detections: np.ndarray, system: DEMSystem) -> np.ndarray:
    residual = (system.check_matrix @ corrections.T) % 2
    return np.all(residual.T == detections, axis=1)


def _pair(label_a: str, a: np.ndarray, label_b: str, b: np.ndarray, mask: np.ndarray | None = None) -> dict[str, Any]:
    if mask is not None:
        a = a[mask]
        b = b[mask]
    only_a = int(np.count_nonzero(a & ~b))
    only_b = int(np.count_nonzero(b & ~a))
    test = mcnemar(only_a, only_b)
    return {
        "a": label_a,
        "b": label_b,
        "shots": int(a.size),
        "errors_a": int(np.count_nonzero(a)),
        "errors_b": int(np.count_nonzero(b)),
        "only_a": only_a,
        "only_b": only_b,
        "mcnemar": test,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M3 failure analysis for the OSD fallback.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--target-physical-error-rate", type=float, default=None)
    parser.add_argument("--output", type=Path, default=Path("results/m3/failure_analysis.json"))
    parser.add_argument("--markdown", type=Path, default=Path("results/m3/FAILURE_ANALYSIS.md"))
    args = parser.parse_args(argv)

    config = M2Config.from_json_file(args.config)
    experiment = (
        None
        if args.target_physical_error_rate is None
        else target_experiment(
            config.experiment, physical_error_rate=args.target_physical_error_rate
        )
    )
    test_split, reference = generate_split(
        config, config.splits.test_seeds, config.splits.test_shots, experiment
    )
    graph = build_experiment_graph(reference)
    system = DEMSystem.from_detector_error_model(reference.raw_dem)
    tensors = graph_to_tensors(graph)
    base_log_odds = prior_log_odds(system.priors)
    model, _ = load_reweighting_checkpoint(config, graph, args.checkpoint)
    logits = predict_logits(model, tensors, test_split.detections)
    strength = float(config.decoder.reweight_strengths[-1])
    priors = combined_logits(base_log_odds, logits, strength)

    test_split_reference_distance = (experiment or config.experiment).distance
    detections = test_split.detections
    observables = test_split.observables

    bp = BPDecoder(
        reference.raw_dem,
        max_iterations=config.decoder.max_iterations,
        min_sum_scaling=config.decoder.min_sum_scaling,
        damping=config.decoder.damping,
    )
    bp_osd = BPOSDDecoder(
        reference.raw_dem,
        max_iterations=config.decoder.max_iterations,
        min_sum_scaling=config.decoder.min_sum_scaling,
        damping=config.decoder.damping,
        osd_order=0,
    )

    plain = bp.decode_batch(detections)
    learned = bp.decode_batch(detections, prior_llr=priors)
    osd_plain = bp_osd.decode_batch(detections)
    osd_learned = bp_osd.decode_batch(detections, prior_llr=priors)
    osd_learned_order = bp_osd.decode_batch(
        detections, prior_llr=priors, osd_ordering_llr=logits
    )

    variants = {
        "bp": plain.corrections,
        "bp_gnn": learned.corrections,
        "bp_osd": osd_plain.corrections,
        "bp_gnn_osd": osd_learned.corrections,
        "bp_gnn_osd_learned_order": osd_learned_order.corrections,
    }
    errors = {name: _logical_errors(c, observables, system) for name, c in variants.items()}
    consistent = {name: _consistent(c, detections, system) for name, c in variants.items()}

    converged_gnn = consistent["bp_gnn"]
    non_converged = ~converged_gnn

    summary = {
        "shots": int(detections.shape[0]),
        "target_experiment": {
            "distance": test_split_reference_distance,
            "noise_model": (experiment or config.experiment).noise_model,
            "physical_error_rate": (experiment or config.experiment).physical_error_rate,
        },
        "reweight_strength": strength,
        "checkpoint": str(args.checkpoint),
        "per_decoder": {
            name: {
                "logical_errors": int(np.count_nonzero(errors[name])),
                "logical_error_rate": float(np.mean(errors[name])),
                "syndrome_consistency_rate": float(np.mean(consistent[name])),
            }
            for name in variants
        },
        "bp_gnn_convergence_rate": float(np.mean(converged_gnn)),
        "non_converged_shots": int(np.count_nonzero(non_converged)),
        "subgroups": {
            "converged_under_bp_gnn": {
                "shots": int(np.count_nonzero(converged_gnn)),
                "errors": {
                    name: int(np.count_nonzero(errors[name][converged_gnn]))
                    for name in ("bp_gnn", "bp_gnn_osd", "bp_gnn_osd_learned_order")
                },
            },
            "non_converged_under_bp_gnn": {
                "shots": int(np.count_nonzero(non_converged)),
                "errors": {
                    name: int(np.count_nonzero(errors[name][non_converged]))
                    for name in (
                        "bp",
                        "bp_gnn",
                        "bp_osd",
                        "bp_gnn_osd",
                        "bp_gnn_osd_learned_order",
                    )
                },
            },
        },
        "osd_effect_on_non_converged_shots": {
            "flips": int(
                np.count_nonzero(errors["bp_gnn"][non_converged] != errors["bp_gnn_osd"][non_converged])
            ),
            "rescued": int(
                np.count_nonzero(errors["bp_gnn"][non_converged] & ~errors["bp_gnn_osd"][non_converged])
            ),
            "broken": int(
                np.count_nonzero(~errors["bp_gnn"][non_converged] & errors["bp_gnn_osd"][non_converged])
            ),
            "still_wrong": int(
                np.count_nonzero(errors["bp_gnn"][non_converged] & errors["bp_gnn_osd"][non_converged])
            ),
        },
        "pairwise": [
            _pair("bp", errors["bp"], "bp_gnn", errors["bp_gnn"]),
            _pair("bp_gnn", errors["bp_gnn"], "bp_gnn_osd", errors["bp_gnn_osd"]),
            _pair("bp_osd", errors["bp_osd"], "bp_gnn_osd", errors["bp_gnn_osd"]),
            _pair("bp_gnn_osd", errors["bp_gnn_osd"], "bp_gnn_osd_learned_order", errors["bp_gnn_osd_learned_order"]),
            _pair(
                "bp_gnn",
                errors["bp_gnn"],
                "bp_gnn_osd",
                errors["bp_gnn_osd"],
                mask=non_converged,
            ),
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    non_converged_block = summary["subgroups"]["non_converged_under_bp_gnn"]
    lines = [
        "# M3 failure analysis: OSD-0 fallback versus the learned prior",
        "",
        "Source: `{}`".format(args.config),
        "Checkpoint: `{}`".format(args.checkpoint),
        "Test shots: {} (reweight strength {:.2f})".format(summary["shots"], strength),
        "",
        "| decoder | logical errors | LER | syndrome consistency |",
        "|---|---:|---:|---:|",
    ]
    for name in variants:
        entry = summary["per_decoder"][name]
        lines.append(
            "| {} | {} | {:.5f} | {:.4f} |".format(
                name, entry["logical_errors"], entry["logical_error_rate"], entry["syndrome_consistency_rate"]
            )
        )
    lines += [
        "",
        "Under the learned prior, {:.2f}% of shots converge inside BP ({} non-converged).".format(
            100.0 * summary["bp_gnn_convergence_rate"], summary["non_converged_shots"]
        ),
        "",
        "On the {} non-converged shots:".format(non_converged_block["shots"]),
        "",
        "| decoder | logical errors in subgroup |",
        "|---|---:|",
    ]
    for name, count in non_converged_block["errors"].items():
        lines.append("| {} | {} |".format(name, count))
    lines += [
        "",
        "OSD-0 effect inside that subgroup: {} flips ({} rescued, {} broken, {} still wrong).".format(
            summary["osd_effect_on_non_converged_shots"]["flips"],
            summary["osd_effect_on_non_converged_shots"]["rescued"],
            summary["osd_effect_on_non_converged_shots"]["broken"],
            summary["osd_effect_on_non_converged_shots"]["still_wrong"],
        ),
        "",
        "| comparison | only A | only B | McNemar z | p (normal) | p (exact) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for pair in summary["pairwise"]:
        lines.append(
            "| {} vs {} ({} shots) | {} | {} | {:.2f} | {:.3g} | {:.3g} |".format(
                pair["a"],
                pair["b"],
                pair["shots"],
                pair["only_a"],
                pair["only_b"],
                pair["mcnemar"]["z"],
                pair["mcnemar"]["p_normal"],
                pair["mcnemar"]["p_exact"],
            )
        )
    lines.append("")
    args.markdown.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary["per_decoder"], indent=2, sort_keys=True))
    print("wrote", args.output.resolve())
    print("wrote", args.markdown.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
