r"""M5+: learned mechanism posteriors -> MWPM, with Stim's decomposition kept.

Fixes two defects of the ``scripts/m5_gnn_mwpm.py`` prototype:

1. **Structural.** The prototype rebuilt a DEM from the binary ``(H, L)``
   system, which drops Stim's ``^`` decomposition.  Hyperedges stayed
   hyperedges and PyMatching silently built a denser, wrong matching graph.
   Here the *decomposed* DEM's instruction list is preserved verbatim and only
   the per-instruction probabilities are substituted.
2. **Convention.** The prototype used ``p = sigmoid(+llr)``; the project's LLR
   convention is ``llr = log((1-p)/p)``, so it fed ``1 - p`` into the graph.

Controls run in the same process so the numbers are comparable:

* ``mwpm``               - baseline on Stim's decomposed DEM;
* ``mwpm_rebuilt``       - same probabilities pushed through the rewrite path
                           (must reproduce the baseline exactly);
* ``mwpm_naive_raw``     - the prototype's raw-hyperedge graph (structure bug);
* ``mwpm_map_prior``     - raw DEM priors pushed through the raw->decomposed
                           map (isolates mapping error from reweighting);
* ``mwpm_map_learned``   - the actual question, swept over reweight strengths.

Usage:
    .\.venv\Scripts\python.exe scripts\m5_gnn_mwpm_decomposed.py `
        --config configs\m4_rotated_surface_code_code_capacity_d3.json `
        --checkpoint results\m4_surface_cc\<run>\model_state.pt --shots 4096
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from graph_qec.config import ExperimentConfig
from graph_qec.data_pipeline import generate_dataset
from graph_qec.decoders import BPDecoder, DEMSystem, MWPMDecoder
from graph_qec.graph_features import build_graph_tensor, prior_log_odds
from graph_qec.m2_config import M2Config
from graph_qec.m2_pipeline import _decode_with_priors, _evaluate, combined_logits
from graph_qec.m3_pipeline import load_reweighting_checkpoint
from graph_qec.m5 import (
    apply_relative_shift,
    collapse_to_instructions,
    error_instructions,
    log_odds_to_probabilities,
    map_decomposed_to_raw,
    matching_from_probabilities,
    rewrite_probabilities,
)
from graph_qec.models import graph_to_tensors, predict_logits


def _logical_errors(predictions: np.ndarray, observables: np.ndarray) -> int:
    return int(np.count_nonzero(np.any(predictions != observables, axis=1)))


def _decode_per_shot(
    matching_dem, detections: np.ndarray, probabilities: np.ndarray
) -> tuple[np.ndarray, float]:
    predictions = np.empty((detections.shape[0], 1), dtype=np.uint8)
    started = time.perf_counter()
    for shot in range(detections.shape[0]):
        matching = matching_from_probabilities(matching_dem, probabilities[shot])
        predictions[shot] = matching.decode(detections[shot])
    elapsed = time.perf_counter() - started
    return predictions, elapsed


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Decompose-preserving GNN->MWPM reweighting")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--output-dir", type=Path, default=Path("results/m5"))
    parser.add_argument("--tag", type=str, default=None)
    args = parser.parse_args(argv)

    config = M2Config.from_json_file(args.config)
    experiment = ExperimentConfig(
        name=config.experiment.name, seed=config.experiment.seed,
        family=config.experiment.family, distance=config.experiment.distance,
        rounds=config.experiment.rounds, noise_model=config.experiment.noise_model,
        physical_error_rate=config.experiment.physical_error_rate, shots=args.shots,
    )
    dataset = generate_dataset(experiment)
    system = DEMSystem.from_detector_error_model(dataset.raw_dem)
    graph = build_graph_tensor(
        system, detector_coordinates=dataset.circuit.get_detector_coordinates()
    )
    base_log_odds = prior_log_odds(system.priors)
    model, _ = load_reweighting_checkpoint(config, graph, args.checkpoint)
    logits = predict_logits(model, graph_to_tensors(graph), dataset.detections)

    raw_instructions = error_instructions(dataset.raw_dem)
    decomposed_instructions = error_instructions(dataset.matching_dem)
    decomposed_priors = np.array([item.probability for item in decomposed_instructions])
    raw_priors = np.array([item.probability for item in raw_instructions])
    parents, mapping_stats = map_decomposed_to_raw(dataset.raw_dem, dataset.matching_dem)

    shots = dataset.shots
    observables = dataset.observables
    summary: dict[str, Any] = {
        "config": str(args.config),
        "checkpoint": str(args.checkpoint),
        "shots": shots,
        "raw_mechanisms": len(raw_instructions),
        "decomposed_instructions": len(decomposed_instructions),
        "mapping": mapping_stats,
        "decoders": {},
    }

    # --- Baseline: Stim's decomposed DEM, unmodified. -------------------------
    baseline_decoder = MWPMDecoder(dataset.matching_dem)
    baseline = baseline_decoder.decode_batch(dataset.detections)
    summary["decoders"]["mwpm"] = {
        "logical_errors": _logical_errors(baseline.predictions, observables),
        "num_edges": baseline.diagnostics["num_edges"],
    }

    # --- Control 1: rewrite path with Stim's own decomposed probabilities. ----
    rebuilt = matching_from_probabilities(dataset.matching_dem, decomposed_priors)
    rebuilt_predictions = rebuilt.decode_batch(dataset.detections)
    summary["decoders"]["mwpm_rebuilt"] = {
        "logical_errors": _logical_errors(rebuilt_predictions, observables),
        "num_edges": int(rebuilt.num_edges),
    }

    # --- Control 2: the prototype's raw-hyperedge graph. ---------------------
    naive = matching_from_probabilities(dataset.raw_dem, raw_priors)
    naive_predictions = naive.decode_batch(dataset.detections)
    summary["decoders"]["mwpm_naive_raw"] = {
        "logical_errors": _logical_errors(naive_predictions, observables),
        "num_edges": int(naive.num_edges),
    }

    # --- Control 3: verbatim substitution of the parent's prior (NOT scale
    # preserving: Stim re-scales a mechanism's probability across its pieces,
    # so this changes the graph even with the mechanism's own prior). --------
    absolute = collapse_to_instructions(parents, raw_priors, fallback=decomposed_priors)[0]
    absolute_matching = matching_from_probabilities(dataset.matching_dem, absolute)
    absolute_predictions = absolute_matching.decode_batch(dataset.detections)
    summary["decoders"]["mwpm_map_prior_absolute"] = {
        "logical_errors": _logical_errors(absolute_predictions, observables),
        "num_edges": int(absolute_matching.num_edges),
        "max_abs_prior_shift": float(np.max(np.abs(absolute - decomposed_priors))),
    }

    # --- Control 4: the relative (scale-preserving) formulation at strength 0.
    zero_shift = np.zeros((shots, system.num_errors), dtype=np.float64)
    control = apply_relative_shift(decomposed_priors, parents, zero_shift)
    control_matching = matching_from_probabilities(dataset.matching_dem, control[0])
    control_predictions = control_matching.decode_batch(dataset.detections)
    summary["decoders"]["mwpm_shift_zero"] = {
        "logical_errors": _logical_errors(control_predictions, observables),
        "num_edges": int(control_matching.num_edges),
        "matches_baseline": bool(
            np.array_equal(control_predictions, baseline.predictions)
        ),
    }

    # --- Learned reweighting sweep. -----------------------------------------
    strength_errors: dict[str, int] = {}
    for strength in config.decoder.reweight_strengths:
        combined = combined_logits(base_log_odds, logits, float(strength))
        shifts = combined - base_log_odds
        probabilities = apply_relative_shift(decomposed_priors, parents, shifts)
        predictions, elapsed = _decode_per_shot(
            dataset.matching_dem, dataset.detections, probabilities
        )
        errors = _logical_errors(predictions, observables)
        strength_errors[f"{float(strength):.2f}"] = errors
        summary["decoders"][f"mwpm_map_learned_s{float(strength):.2f}"] = {
            "logical_errors": errors,
            "us_per_shot": elapsed * 1e6 / shots,
        }
    summary["learned_sweep"] = strength_errors

    # --- BP references, for context. -----------------------------------------
    bp = BPDecoder(
        dataset.raw_dem, max_iterations=config.decoder.max_iterations,
        min_sum_scaling=config.decoder.min_sum_scaling,
    )
    bp_plain = _evaluate(
        bp.decode_batch, detections=dataset.detections, observables=observables,
        system=system, timed_runs=1,
    )
    top_strength = float(config.decoder.reweight_strengths[-1])
    top_combined = combined_logits(base_log_odds, logits, top_strength)
    bp_learned = _evaluate(
        lambda detections: _decode_with_priors(bp, detections, top_combined),
        detections=dataset.detections, observables=observables, system=system, timed_runs=1,
    )
    summary["decoders"]["bp"] = {
        "logical_errors": bp_plain["logical_errors"],
        "us_per_shot": bp_plain["latency"]["mean_per_shot_microseconds"],
    }
    summary["decoders"]["bp_gnn"] = {
        "logical_errors": bp_learned["logical_errors"],
        "us_per_shot": bp_learned["latency"]["mean_per_shot_microseconds"],
        "strength": top_strength,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    tag = args.tag or args.output_dir.name
    (args.output_dir / f"gnn_mwpm_decomposed_{tag}.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary["decoders"], indent=2, sort_keys=True))
    print("mapping:", json.dumps(summary["mapping"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

