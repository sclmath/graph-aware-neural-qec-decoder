r"""T9 ablation: which graph features actually carry the reweighting signal?

For each feature group the script masks the corresponding columns of the
``GraphTensor`` (zeroes them), retrains the same GNN with the same seed, and
reports the mechanism-level AUC and the resulting ``bp_gnn`` logical error rate.
Masking keeps the architecture identical between arms, so the comparison
isolates the *information* contributed by the group.

Usage:
    .\.venv\Scripts\python.exe scripts\t9_feature_ablation.py `
        --config configs\m2_learned_basis_repetition_circuit_level_d3.json `
        --checkpoint results\m2\...\model_state.pt `
        --output-dir results\t9\repetition_d3_circuit_level
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from graph_qec.decoders import BPDecoder
from graph_qec.graph_features import (
    CHECK_FEATURE_NAMES,
    EDGE_FEATURE_NAMES,
    VARIABLE_FEATURE_NAMES,
    prior_log_odds,
)
from graph_qec.m2_config import M2Config
from graph_qec.m2_pipeline import (
    build_experiment_graph,
    combined_logits,
    generate_split,
    roc_auc,
    train_reweighting_model,
)
from graph_qec.models import graph_to_tensors, predict_logits

#: Arm name -> (variable columns to zero, check columns to zero, edge columns to zero)
ARMS: dict[str, tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]] = {
    "all": ((), (), ()),
    "no_check_features": ((), tuple(range(len(CHECK_FEATURE_NAMES))), ()),
    "no_variable_geometry": ((), (), ()),
    "no_check_geometry": ((), (), ()),
    "no_edge_degree": ((), (), ()),
    "prior_only": ((), (), ()),
}

_EDGE_PRIOR = EDGE_FEATURE_NAMES.index("prior_log_odds_scaled")
_VARIABLE_PRIOR = (
    VARIABLE_FEATURE_NAMES.index("prior_log_odds"),
    VARIABLE_FEATURE_NAMES.index("prior_probability"),
)
_VARIABLE_GEOMETRY = tuple(
    index
    for index, name in enumerate(VARIABLE_FEATURE_NAMES)
    if name in ("detector_index_mean", "detector_time_mean")
)
_CHECK_GEOMETRY = tuple(
    index
    for index, name in enumerate(CHECK_FEATURE_NAMES)
    if name in ("detector_index", "detector_time")
)

ARMS["no_variable_geometry"] = (_VARIABLE_GEOMETRY, (), ())
ARMS["no_check_geometry"] = ((), _CHECK_GEOMETRY, ())
ARMS["no_edge_degree"] = (
    (),
    (),
    tuple(
        index
        for index, name in enumerate(EDGE_FEATURE_NAMES)
        if name.startswith("inverse_")
    ),
)
ARMS["prior_only"] = (
    tuple(
        index
        for index in range(len(VARIABLE_FEATURE_NAMES))
        if index not in _VARIABLE_PRIOR
    ),
    tuple(range(len(CHECK_FEATURE_NAMES))),
    tuple(
        index
        for index in range(len(EDGE_FEATURE_NAMES))
        if index != _EDGE_PRIOR
    ),
)


def _mask(graph, columns):
    variable_columns, check_columns, edge_columns = columns
    updates = {}
    if edge_columns:
        features = graph.edge_features.copy()
        features[:, list(edge_columns)] = 0.0
        updates["edge_features"] = features
    if variable_columns:
        features = graph.variable_features.copy()
        features[:, list(variable_columns)] = 0.0
        updates["variable_features"] = features
    if check_columns:
        features = graph.check_features.copy()
        features[:, list(check_columns)] = 0.0
        updates["check_features"] = features
    return dataclasses.replace(graph, **updates)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--arms", nargs="+", default=list(ARMS))
    parser.add_argument("--torch-threads", type=int, default=3)
    parser.add_argument("--max-epochs", type=int, default=None)
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge the freshly measured arms into an existing ablation.json "
        "instead of overwriting it (used to complete a seed in several passes).",
    )
    parser.add_argument(
        "--seed-offset",
        type=int,
        default=0,
        help="Shift the training seed and every split seed by this amount, so "
        "the same arm set can be repeated over independent seeds.",
    )
    args = parser.parse_args(argv)

    config = M2Config.from_json_file(args.config)
    if args.torch_threads:
        config = dataclasses.replace(
            config,
            training=dataclasses.replace(config.training, torch_threads=args.torch_threads),
        )
    if args.max_epochs is not None:
        config = dataclasses.replace(
            config,
            training=dataclasses.replace(config.training, epochs=args.max_epochs),
        )
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

    train_split, reference = generate_split(
        config, config.splits.train_seeds, config.splits.train_shots
    )
    validation_split, _ = generate_split(
        config, config.splits.validation_seeds, config.splits.validation_shots
    )
    test_split, _ = generate_split(
        config, config.splits.test_seeds, config.splits.test_shots
    )
    graph = build_experiment_graph(reference)
    base_log_odds = prior_log_odds(reference_system_priors(reference))
    strength = float(config.decoder.reweight_strengths[-1])

    bp = BPDecoder(
        reference.raw_dem,
        max_iterations=config.decoder.max_iterations,
        min_sum_scaling=config.decoder.min_sum_scaling,
        damping=config.decoder.damping,
    )
    observables = test_split.observables

    rows: list[dict[str, Any]] = []
    existing_rows: list[dict[str, Any]] = []
    if args.merge:
        ablation_path = args.output_dir / "ablation.json"
        if ablation_path.exists():
            stored = json.loads(ablation_path.read_text(encoding="utf-8"))
            existing_rows = list(stored.get("rows", []))

    for arm in args.arms:
        masked = _mask(graph, ARMS[arm])
        model, history = train_reweighting_model(config, masked, train_split, validation_split)
        tensors = graph_to_tensors(masked)
        logits = predict_logits(model, tensors, test_split.detections)
        priors = combined_logits(base_log_odds, logits, strength)
        result = bp.decode_batch(test_split.detections, prior_llr=priors)
        errors = int(np.count_nonzero(np.any(result.predictions != observables, axis=1)))
        auc = roc_auc(logits, test_split.error_mechanisms)
        rows.append(
            {
                "arm": arm,
                "masked_variable": list(ARMS[arm][0]),
                "masked_check": list(ARMS[arm][1]),
                "masked_edge": list(ARMS[arm][2]),
                "mechanism_auc": float(auc),
                "logical_errors": errors,
                "logical_error_rate": float(errors / test_split.shots),
                "best_validation_log_loss": float(
                    history["best_validation_log_loss"]
                ),
                "shots": int(test_split.shots),
            }
        )
        print(
            "%-22s AUC=%.4f  LER=%.5f (%d/%d)"
            % (arm, auc, errors / test_split.shots, errors, test_split.shots),
            flush=True,
        )

    if args.merge:
        fresh = {row["arm"] for row in rows}
        existing_rows = [
            row for row in existing_rows if row["arm"] not in fresh
        ]
    merged_rows = existing_rows + rows

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "ablation.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(
            {"config": str(args.config), "seed_offset": args.seed_offset, "rows": merged_rows},
            handle,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")
    markdown = [
        "# T9 · 图特征组合消融",
        "",
        f"- 配置：`{args.config}`；测试集 {merged_rows[0]['shots']} shots",
        "- 做法：把对应特征列**置零**后用同一 seed 重训，架构不变，因此比较的是该组特征携带的**信息量**",
        "",
        "| 消融臂 | 机制 AUC | bp_gnn LER | 逻辑错误 | Δ LER（相对 all） |",
        "|---|---:|---:|---:|---:|",
    ]
    baseline = next(
        (row["logical_error_rate"] for row in merged_rows if row["arm"] == "all"), None
    )
    for row in merged_rows:
        delta = "" if baseline is None else f"{row['logical_error_rate'] - baseline:+.5f}"
        markdown.append(
            f"| {row['arm']} | {row['mechanism_auc']:.4f} | {row['logical_error_rate']:.5f} "
            f"| {row['logical_errors']} | {delta} |"
        )
    with (args.output_dir / "ABLATION.md").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(markdown) + "\n")
    return 0


def reference_system_priors(reference):
    from graph_qec.decoders import DEMSystem

    return DEMSystem.from_detector_error_model(reference.raw_dem).priors


if __name__ == "__main__":
    raise SystemExit(main())
