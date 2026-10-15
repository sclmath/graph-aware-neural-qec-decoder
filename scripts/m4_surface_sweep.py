r"""M4: rotated surface code baseline sweep (LER versus physical error rate).

Trains nothing: this is the classical baseline curve the learned decoders are
measured against, run with the corrected batched BP.

Usage:
    .\.venv\Scripts\python.exe scripts\m4_surface_sweep.py --distances 3 5
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from graph_qec.config import ExperimentConfig
from graph_qec.data_pipeline import generate_dataset
from graph_qec.decoders import BPDecoder, BPOSDDecoder, MWPMDecoder, UnionFindDecoder

DEFAULT_RATES = (0.002, 0.003, 0.005, 0.008, 0.01, 0.015)


def _evaluate(decode, detections, observables, system, timed_runs: int = 1) -> dict[str, Any]:
    started = time.perf_counter()
    result = decode(detections)
    elapsed = time.perf_counter() - started
    errors = int(np.count_nonzero(np.any(result.predictions != observables, axis=1)))
    shots = detections.shape[0]
    if result.corrections is None:
        # Matching decoders return observable predictions only.
        consistent = None
    else:
        residual = (
            system.check_matrix.astype(np.int64) @ result.corrections.T.astype(np.int64)
        ) % 2
        consistent = float(np.mean(np.all(residual.T == detections, axis=1)))
    rate = errors / shots
    return {
        "logical_errors": errors,
        "logical_error_rate": rate,
        "logical_error_rate_standard_error": float(np.sqrt(rate * (1 - rate) / shots)),
        "syndrome_consistency_rate": consistent,
        "microseconds_per_shot": elapsed * 1e6 / shots,
        "mean_iterations": result.diagnostics.get("average_iterations"),
        "convergence_rate": result.diagnostics.get("convergence_rate"),
        "osd_rate": result.diagnostics.get("osd_rate"),
    }


def run_point(distance: int, rounds: int, noise_model: str, probability: float, shots: int) -> list[dict[str, Any]]:
    config = ExperimentConfig(
        name="surface_sweep", seed=20261013, family="rotated_surface_code",
        distance=distance, rounds=rounds, noise_model=noise_model,
        physical_error_rate=probability, shots=shots,
    )
    dataset = generate_dataset(config)
    from graph_qec.decoders import DEMSystem

    system = DEMSystem.from_detector_error_model(dataset.raw_dem)
    decoders = {
        "mwpm": MWPMDecoder(dataset.matching_dem),
        "union_find": UnionFindDecoder(dataset.matching_dem),
        "bp": BPDecoder(dataset.raw_dem, max_iterations=32, min_sum_scaling=0.75),
        "bp_osd": BPOSDDecoder(dataset.raw_dem, max_iterations=32, min_sum_scaling=0.75, osd_order=0),
    }
    rows: list[dict[str, Any]] = []
    for name, decoder in decoders.items():
        metrics = _evaluate(decoder.decode_batch, dataset.detections, dataset.observables, system)
        rows.append(
            {
                "distance": distance,
                "rounds": rounds,
                "noise_model": noise_model,
                "physical_error_rate": probability,
                "shots": shots,
                "decoder": name,
                "num_detectors": int(dataset.raw_dem.num_detectors),
                "num_mechanisms": int(dataset.raw_dem.num_errors),
                **metrics,
            }
        )
        print(
            "  {:11s} d={} {} p={:g}: LER={:.5f} ({}) {:.1f} us/shot".format(
                name, distance, noise_model, probability,
                metrics["logical_error_rate"], metrics["logical_errors"],
                metrics["microseconds_per_shot"],
            ),
            flush=True,
        )
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Surface code baseline sweep.")
    parser.add_argument("--distances", type=int, nargs="+", default=[3, 5])
    parser.add_argument("--rates", type=float, nargs="+", default=list(DEFAULT_RATES))
    parser.add_argument("--noise-models", nargs="+", default=["code_capacity", "circuit_level"])
    parser.add_argument("--shots", type=int, default=16384)
    parser.add_argument("--output-dir", type=Path, default=Path("results/m4"))
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for distance in args.distances:
        for noise_model in args.noise_models:
            for probability in args.rates:
                print(f"d={distance} {noise_model} p={probability:g}", flush=True)
                rows.extend(
                    run_point(distance, distance, noise_model, float(probability), args.shots)
                )

    csv_path = args.output_dir / "surface_sweep.csv"
    exists = csv_path.exists()
    with csv_path.open("a" if exists else "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        if not exists:
            writer.writeheader()
        writer.writerows(rows)
    json_path = args.output_dir / "surface_sweep.json"
    existing = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else []
    json_path.write_text(
        json.dumps(existing + rows, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("wrote", csv_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
