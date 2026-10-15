r"""M5+ PROTOTYPE (NOT VALID FOR REPORTING): learned posterior -> MWPM.

CONTROL EXPERIMENT: rewriting the DEM with its own probabilities already degrades
MWPM (0.0439 -> 0.0679), because Stim's `^` decomposition of >2-detector
mechanisms is lost and PyMatching cannot represent those hyperedges.
Any LER from this script is therefore an implementation artifact; see
`docs/M5_ENGINEERING.md` section 5.

Original description: does the learned posterior help when fed to MWPM instead of BP?

MWPM is the strongest decoder on matchable codes, and the M4 report argues the
learned reweighting should target the *matching graph* there rather than the BP
prior. This script tests exactly that: the GNN's syndrome-conditioned mechanism
posteriors replace the DEM probabilities, a matching graph is rebuilt for that
shot, and MWPM decodes it. Baseline: plain MWPM on the unmodified DEM.

Usage:
    .\.venv\Scripts\python.exe scripts\m5_gnn_mwpm.py `
        --config configs\m4_rotated_surface_code_circuit_level_d3.json `
        --checkpoint results\m4_surface\<run>\model_state.pt --shots 2048
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pymatching
import stim

from graph_qec.config import ExperimentConfig
from graph_qec.data_pipeline import generate_dataset
from graph_qec.decoders import BPDecoder, DEMSystem, MWPMDecoder
from graph_qec.graph_features import build_graph_tensor, prior_log_odds
from graph_qec.m2_config import M2Config
from graph_qec.m2_pipeline import _decode_with_priors, _evaluate, combined_logits
from graph_qec.m3_pipeline import load_reweighting_checkpoint
from graph_qec.models import graph_to_tensors, predict_logits


def dem_from_system(system: DEMSystem, probabilities: np.ndarray) -> stim.DetectorErrorModel:
    """Rebuilds a detector error model with per-mechanism probabilities."""

    probabilities = np.clip(np.asarray(probabilities, dtype=np.float64), 1e-9, 1.0 - 1e-9)
    lines: list[str] = []
    for column in range(system.num_errors):
        detectors = np.flatnonzero(system.check_matrix[:, column]).tolist()
        observables = np.flatnonzero(system.observable_matrix[:, column]).tolist()
        if not detectors and not observables:
            continue
        targets = [f"D{index}" for index in detectors] + [f"L{index}" for index in observables]
        lines.append(f"error({float(probabilities[column])}) " + " ".join(targets))
    declarations = [f"detector D{index}" for index in range(system.num_detectors)]
    declarations += [f"logical_observable L{index}" for index in range(system.num_observables)]
    return stim.DetectorErrorModel("\n".join(lines + declarations))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GNN-reweighted MWPM on a matchable code.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--shots", type=int, default=2048)
    parser.add_argument("--strength", type=float, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("results/m5"))
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
    strength = float(config.decoder.reweight_strengths[-1] if args.strength is None else args.strength)
    combined = combined_logits(base_log_odds, logits, strength)
    probabilities = 1.0 / (1.0 + np.exp(-combined))

    # Baselines.
    plain_mwpm = MWPMDecoder(dataset.matching_dem)
    plain = _evaluate(
        plain_mwpm.decode_batch,
        detections=dataset.detections,
        observables=dataset.observables,
        system=system,
        timed_runs=1,
    )
    bp = BPDecoder(dataset.raw_dem, max_iterations=config.decoder.max_iterations,
                   min_sum_scaling=config.decoder.min_sum_scaling)
    bp_gnn = _evaluate(
        lambda detections: _decode_with_priors(bp, detections, combined),
        detections=dataset.detections,
        observables=dataset.observables,
        system=system,
        timed_runs=1,
    )

    # Per-shot reweighted matching graph.
    predictions: list[np.ndarray] = []
    started = time.perf_counter()
    for shot, syndrome in enumerate(dataset.detections):
        dem = dem_from_system(system, probabilities[shot])
        matching = pymatching.Matching.from_detector_error_model(dem)
        predictions.append(np.asarray(matching.decode(syndrome), dtype=np.uint8))
    elapsed = time.perf_counter() - started
    predictions_array = np.ascontiguousarray(np.vstack(predictions), dtype=np.uint8)
    errors = int(np.count_nonzero(np.any(predictions_array != dataset.observables, axis=1)))
    rate = errors / dataset.shots

    summary: dict[str, Any] = {
        "config": str(args.config),
        "checkpoint": str(args.checkpoint),
        "shots": dataset.shots,
        "reweight_strength": strength,
        "decoders": {
            "mwpm": {"logical_errors": plain["logical_errors"], "ler": plain["logical_error_rate"],
                     "us_per_shot": plain["latency"]["mean_per_shot_microseconds"]},
            "mwpm_gnn": {"logical_errors": errors, "ler": rate,
                         "us_per_shot": elapsed * 1e6 / dataset.shots,
                         "standard_error": float(np.sqrt(rate * (1 - rate) / dataset.shots))},
            "bp_gnn": {"logical_errors": bp_gnn["logical_errors"], "ler": bp_gnn["logical_error_rate"],
                       "us_per_shot": bp_gnn["latency"]["mean_per_shot_microseconds"]},
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "gnn_mwpm.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# M5+: learned posterior fed to MWPM (rather than BP)",
        "",
        f"Checkpoint: `{args.checkpoint}`  ",
        f"{dataset.shots} test shots, reweight strength {strength:.2f}, "
        "per-shot matching graph rebuilt from the learned mechanism posteriors.",
        "",
        "| decoder | logical errors | LER | s.e. | us/shot |",
        "|---|---:|---:|---:|---:|",
        "| mwpm (DEM prior) | {mwpm[logical_errors]} | {mwpm[ler]:.5f} | - | {mwpm[us_per_shot]:.1f} |".format(**summary["decoders"]),
        "| mwpm + GNN posteriors | {mwpm_gnn[logical_errors]} | {mwpm_gnn[ler]:.5f} | {mwpm_gnn[standard_error]:.5f} | {mwpm_gnn[us_per_shot]:.1f} |".format(**summary["decoders"]),
        "| bp + GNN prior | {bp_gnn[logical_errors]} | {bp_gnn[ler]:.5f} | - | {bp_gnn[us_per_shot]:.1f} |".format(**summary["decoders"]),
        "",
    ]
    (args.output_dir / "GNN_MWPM.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary["decoders"], indent=2, sort_keys=True))
    print("wrote", (args.output_dir / "GNN_MWPM.md").resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
