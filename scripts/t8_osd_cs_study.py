r"""T8 study: does an OSD combination sweep beat the OSD-0 fallback?

Motivation (three independent M2/M3/M5 results): reweighting *per-mechanism
marginals* does not help candidate-basis selection, and the OSD-0 fallback
trades LER against syndrome consistency along a steep Pareto front. This study
tests the alternative the roadmap points at: make the *candidate basis* smarter
via OSD-CS(lambda) -- a combination sweep over the least reliable non-pivot
columns -- instead of making the marginals smarter.

Usage:
    .\.venv\Scripts\python.exe scripts\t8_osd_cs_study.py `
        --config results\m2\<run>\config.json `
        --checkpoint results\m2\<run>\model_state.pt `
        --sweeps 0 2 4 6 8 `
        --output-dir results\t8\repetition_d3_circuit_level
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from graph_qec.decoders import BPDecoder, BPOSDDecoder, DEMSystem, MWPMDecoder
from graph_qec.graph_features import prior_log_odds
from graph_qec.m2_config import M2Config
from graph_qec.m2_pipeline import build_experiment_graph, combined_logits, generate_split
from graph_qec.m3_pipeline import load_reweighting_checkpoint
from graph_qec.models import graph_to_tensors, predict_logits
from graph_qec.stats import pair_comparison


def _logical_errors(corrections, observables, system) -> np.ndarray:
    predictions = (system.observable_matrix @ corrections.T) % 2
    return np.any(np.ascontiguousarray(predictions.T, dtype=np.uint8) != observables, axis=1)


def _consistent(corrections, detections, system) -> np.ndarray:
    residual = (system.check_matrix @ corrections.T) % 2
    return np.all(residual.T == detections, axis=1)


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# OSD 候选集学习（OSD-CS）",
        "",
        f"- 配置：`{summary['config']}`",
        f"- 检查点：`{summary['checkpoint']}`",
        f"- 测试集：{summary['shots']} shots（seed {summary['test_seeds']}）",
        f"- 先验插值强度：{summary['reweight_strength']}",
        "",
        "## 1. 逐解码器",
        "",
        "| decoder | logical errors | LER | s.e. | syndrome 一致率 |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, entry in summary["per_decoder"].items():
        lines.append(
            f"| {name} | {entry['logical_errors']} | {entry['logical_error_rate']:.5f} | "
            f"{entry['standard_error']:.5f} | {entry['syndrome_consistency_rate']:.4f} |"
        )
    lines += [
        "",
        "## 2. 配对检验（McNemar，双侧）",
        "",
        "| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for pair in summary["pairwise"]:
        m = pair["mcnemar"]
        lines.append(
            f"| {pair['a']} | {pair['b']} | {pair['only_a']} | {pair['only_b']} | "
            f"{m['z']:.2f} | {m['p_normal']:.4f} | {m['p_exact']:.4f} |"
        )
    if summary.get("non_converged_shots"):
        lines += [
            "",
            "## 3. 未收敛子集（BP+GNN 未收敛的 shot）",
            "",
            f"- 未收敛 shot 数：{summary['non_converged_shots']} / {summary['shots']}",
            "",
            "| decoder | 未收敛子集上的逻辑错误 |",
            "|---|---:|",
        ]
        for name, value in summary["non_converged_errors"].items():
            lines.append(f"| {name} | {value} |")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--sweeps", type=int, nargs="+", default=[0, 2, 4, 6, 8])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tag", type=str, default=None)
    parser.add_argument(
        "--seed-offset",
        type=int,
        default=0,
        help="Shift the training seed and every split seed, so the same study "
        "can be repeated over independent seeds.",
    )
    parser.add_argument(
        "--test-shots",
        type=int,
        default=None,
        help="Override the config's test split size (useful for a cheap "
        "directional probe on an expensive distance such as d=7).",
    )
    args = parser.parse_args(argv)

    config = M2Config.from_json_file(args.config)
    if args.seed_offset:
        offset = args.seed_offset
        config = dataclasses.replace(
            config,
            training=dataclasses.replace(
                config.training, seed=config.training.seed + offset
            ),
            splits=dataclasses.replace(
                config.splits,
                train_seeds=tuple(seed + offset for seed in config.splits.train_seeds),
                validation_seeds=tuple(
                    seed + offset for seed in config.splits.validation_seeds
                ),
                test_seeds=tuple(seed + offset for seed in config.splits.test_seeds),
            ),
        )
    test_shots = config.splits.test_shots if args.test_shots is None else args.test_shots
    test_split, reference = generate_split(
        config, config.splits.test_seeds, test_shots
    )
    system = DEMSystem.from_detector_error_model(reference.raw_dem)
    detections = test_split.detections
    observables = test_split.observables

    strengths = np.asarray(config.decoder.reweight_strengths, dtype=float)
    strength = float(strengths[-1])
    priors = None
    logits = None
    if args.checkpoint is not None:
        graph = build_experiment_graph(reference)
        model, _ = load_reweighting_checkpoint(config, graph, args.checkpoint)
        logits = predict_logits(model, graph_to_tensors(graph), detections)
        priors = combined_logits(prior_log_odds(system.priors), logits, strength)

    bp = BPDecoder(
        reference.raw_dem,
        max_iterations=config.decoder.max_iterations,
        min_sum_scaling=config.decoder.min_sum_scaling,
        damping=config.decoder.damping,
    )
    osd_decoders = {
        sweep: BPOSDDecoder(
            reference.raw_dem,
            max_iterations=config.decoder.max_iterations,
            min_sum_scaling=config.decoder.min_sum_scaling,
            damping=config.decoder.damping,
            osd_order=0,
            combination_sweep_order=sweep,
        )
        for sweep in sorted(set(args.sweeps))
    }

    corrections: dict[str, np.ndarray] = {}
    corrections["mwpm"] = None  # MWPM exposes predictions only
    decoders: dict[str, Any] = {}
    decoders["mwpm"] = MWPMDecoder(reference.matching_dem).decode_batch(detections)
    decoders["bp"] = bp.decode_batch(detections)
    for sweep, decoder in osd_decoders.items():
        decoders[f"bp_osd_cs{sweep}"] = decoder.decode_batch(detections)
    if priors is not None:
        decoders["bp_gnn"] = bp.decode_batch(detections, prior_llr=priors)
        for sweep, decoder in osd_decoders.items():
            decoders[f"bp_gnn_osd_cs{sweep}"] = decoder.decode_batch(
                detections, prior_llr=priors
            )

    errors: dict[str, np.ndarray] = {}
    consistent: dict[str, np.ndarray] = {}
    for name, result in decoders.items():
        if result.corrections is not None:
            errors[name] = _logical_errors(result.corrections, observables, system)
            consistent[name] = _consistent(result.corrections, detections, system)
        else:
            errors[name] = np.any(result.predictions != observables, axis=1)
            consistent[name] = np.ones(detections.shape[0], dtype=bool)

    positive = [sweep for sweep in sorted(set(args.sweeps)) if sweep > 0]
    pairs: list[tuple[str, str]] = [("bp", "bp_osd_cs0")]
    pairs += [("bp_osd_cs0", f"bp_osd_cs{sweep}") for sweep in positive]
    pairs += [("bp", f"bp_osd_cs{sweep}") for sweep in positive]
    if priors is not None:
        pairs += [("bp_gnn", "bp_gnn_osd_cs0")]
        pairs += [("bp_gnn_osd_cs0", f"bp_gnn_osd_cs{sweep}") for sweep in positive]
        pairs += [("bp_gnn", f"bp_gnn_osd_cs{sweep}") for sweep in positive]
        pairs += [
            (f"bp_osd_cs{sweep}", f"bp_gnn_osd_cs{sweep}") for sweep in sorted(set(args.sweeps))
        ]
    pairwise = [
        pair_comparison(a, errors[a], b, errors[b])
        for a, b in pairs
        if a in errors and b in errors
    ]

    non_converged = None
    if priors is not None and "bp_gnn" in consistent:
        non_converged = ~consistent["bp_gnn"]
    summary: dict[str, Any] = {
        "config": str(args.config),
        "checkpoint": None if args.checkpoint is None else str(args.checkpoint),
        "shots": int(detections.shape[0]),
        "test_shots_override": args.test_shots,
        "seed_offset": args.seed_offset,
        "test_seeds": list(config.splits.test_seeds),
        "reweight_strength": strength,
        "sweeps": sorted(set(args.sweeps)),
        "per_decoder": {
            name: {
                "logical_errors": int(np.count_nonzero(errors[name])),
                "logical_error_rate": float(np.mean(errors[name])),
                "standard_error": float(np.sqrt(
                    np.mean(errors[name]) * (1 - np.mean(errors[name])) / errors[name].size
                )),
                "syndrome_consistency_rate": float(np.mean(consistent[name])),
            }
            for name in errors
        },
        "pairwise": pairwise,
    }
    if non_converged is not None:
        subset = {
            name: int(np.count_nonzero(errors[name][non_converged]))
            for name in errors
        }
        summary["non_converged_shots"] = int(np.count_nonzero(non_converged))
        summary["non_converged_errors"] = subset
        summary["pairwise_non_converged"] = [
            pair_comparison(a, errors[a], b, errors[b], mask=non_converged)
            for a, b in pairs
            if a in errors and b in errors
        ]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "study.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (args.output_dir / "STUDY.md").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(_markdown(summary))

    print(json.dumps(summary["per_decoder"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
