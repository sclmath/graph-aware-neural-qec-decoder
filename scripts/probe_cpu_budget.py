#!/usr/bin/env python3
r"""Probe the CPU wall-clock budget for the surface-code sweeps (BP + GNN).

Both M3 and M4 assumed that d>=7 "requires GPU batch processing". This probe
measures the actual per-shot cost of the vectorized BP engine and of the
bipartite GNN on this machine, so the no-GPU phase can be planned from numbers
instead of guesses.

Run:

    $env:PYTHONPATH = "src"
    .\.venv\Scripts\python.exe scripts\probe_cpu_budget.py

Add ``--json results/m5/cpu_budget.json`` to persist the measurements.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import torch

from graph_qec.benchmark import _current_rss_bytes
from graph_qec.circuits import build_rotated_surface_code_circuit
from graph_qec.config import ExperimentConfig
from graph_qec.decoders.bp import BPDecoder
from graph_qec.decoders.dem import DEMSystem
from graph_qec.graph_features import build_graph_tensor
from graph_qec.models import BipartiteSyndromeGNN, graph_to_tensors

DEFAULT_P = 0.005
DEFAULT_BP_SHOTS = {3: 1024, 5: 256, 7: 64, 9: 32}
DEFAULT_GNN_BATCHES = {5: (128, 512), 7: (64, 256)}
REPORT_SHOT_SIZES = (8192, 32768)


@dataclass
class BPRow:
    distance: int
    detectors: int
    mechanisms: int
    edges: int
    max_check_degree: int
    shots: int
    microseconds_per_shot: float
    convergence_rate: float
    average_iterations: float
    estimate_seconds: dict[str, float] = field(default_factory=dict)


@dataclass
class GNNRow:
    distance: int
    edges: int
    parameters: int
    batch: int
    forward_microseconds_per_shot: float
    peak_rss_mb: float
    training_step_seconds: float | None = None
    training_epoch_seconds_8192: float | None = None
    training_peak_rss_mb: float | None = None


def _experiment(distance: int, probability: float, shots: int) -> ExperimentConfig:
    return ExperimentConfig(
        name="cpu_budget_probe",
        seed=20261015,
        family="rotated_surface_code",
        distance=distance,
        rounds=distance,
        noise_model="circuit_level",
        physical_error_rate=probability,
        shots=shots,
    )


def _detector_error_model(config: ExperimentConfig):
    circuit = build_rotated_surface_code_circuit(config)
    return circuit, circuit.detector_error_model(decompose_errors=True)


def probe_bp(distances: Sequence[int], probability: float) -> list[BPRow]:
    """Times the batched min-sum BP decoder on sampled detector data."""

    rows: list[BPRow] = []
    for distance in distances:
        shots = DEFAULT_BP_SHOTS.get(distance, 32)
        config = _experiment(distance, probability, shots)
        circuit, dem = _detector_error_model(config)
        decoder = BPDecoder(dem, max_iterations=32, min_sum_scaling=0.75)
        sampler = circuit.compile_detector_sampler(seed=config.seed)
        detections, _ = sampler.sample(shots=shots, separate_observables=True)
        detections = np.asarray(detections, dtype=np.uint8)

        decoder.decode_batch(detections[: min(8, shots)])  # warm up the engine
        started = time.perf_counter()
        result = decoder.decode_batch(detections)
        elapsed = time.perf_counter() - started
        per_shot = elapsed / shots

        rows.append(
            BPRow(
                distance=distance,
                detectors=int(decoder.system.num_detectors),
                mechanisms=int(decoder.system.num_errors),
                edges=int(decoder.system.check_matrix.sum()),
                max_check_degree=int(decoder.system.check_matrix.sum(axis=1).max()),
                shots=shots,
                microseconds_per_shot=per_shot * 1e6,
                convergence_rate=float(result.diagnostics["convergence_rate"]),
                average_iterations=float(result.diagnostics["average_iterations"]),
                estimate_seconds={
                    str(size): per_shot * size for size in REPORT_SHOT_SIZES
                },
            )
        )
    return rows


def probe_gnn(distances: Sequence[int], probability: float) -> list[GNNRow]:
    """Times GNN inference (and one training step) on the same DEMs."""

    rows: list[GNNRow] = []
    for distance in distances:
        config = _experiment(distance, probability, 1)
        _circuit, dem = _detector_error_model(config)
        graph = build_graph_tensor(DEMSystem.from_detector_error_model(dem))
        tensors = graph_to_tensors(graph)
        model = BipartiteSyndromeGNN(
            variable_feature_dim=graph.variable_feature_dim,
            check_feature_dim=graph.check_feature_dim,
            edge_feature_dim=graph.edge_feature_dim,
            hidden_size=32,
            num_layers=3,
            dropout=0.0,
        )
        parameters = sum(parameter.numel() for parameter in model.parameters())
        static = {
            "variable_features": tensors["variable_features"],
            "check_features": tensors["check_features"],
            "edge_index": tensors["edge_index"],
            "edge_features": tensors["edge_features"],
        }
        batches = DEFAULT_GNN_BATCHES.get(distance, (32,))

        for batch in batches:
            syndrome = torch.zeros(batch, graph.num_checks)
            with torch.no_grad():
                model(syndrome=syndrome, **static)
                started = time.perf_counter()
                model(syndrome=syndrome, **static)
                elapsed = time.perf_counter() - started
            rows.append(
                GNNRow(
                    distance=distance,
                    edges=graph.num_edges,
                    parameters=parameters,
                    batch=batch,
                    forward_microseconds_per_shot=elapsed / batch * 1e6,
                    peak_rss_mb=_current_rss_bytes() / 1e6,
                )
            )

        train_batch = batches[0]
        syndrome = torch.zeros(train_batch, graph.num_checks)
        model.zero_grad(set_to_none=True)
        started = time.perf_counter()
        logits = model(syndrome=syndrome, **static)
        logits.float().pow(2).mean().backward()
        step = time.perf_counter() - started
        rows[-1].training_step_seconds = step
        rows[-1].training_epoch_seconds_8192 = step * (8192 / train_batch)
        rows[-1].training_peak_rss_mb = _current_rss_bytes() / 1e6
        model.zero_grad(set_to_none=True)
    return rows


def render(bp_rows: Sequence[BPRow], gnn_rows: Sequence[GNNRow], probability: float) -> str:
    lines = [
        f"# CPU 预算实测（rotated surface code, circuit-level p={probability:g}）",
        "",
        "## BP（vectorized min-sum, max_iterations=32, scaling=0.75）",
        "",
        "| d | detectors | mechanisms | edges | max check deg | shots | µs/shot | convergence | avg iters | 8192 shots | 32768 shots |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in bp_rows:
        lines.append(
            f"| {row.distance} | {row.detectors} | {row.mechanisms} | {row.edges} |"
            f" {row.max_check_degree} | {row.shots} | {row.microseconds_per_shot:,.1f} |"
            f" {row.convergence_rate:.3f} | {row.average_iterations:.2f} |"
            f" {row.estimate_seconds['8192']:.1f} s | {row.estimate_seconds['32768']:.1f} s |"
        )
    lines += [
        "",
        "## GNN（hidden=32, layers=3）",
        "",
        "| d | edges | params | batch | µs/shot (fwd) | peak RSS | train step | est. epoch @8192 shots | train peak RSS |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in gnn_rows:
        step = f"{row.training_step_seconds:.3f} s" if row.training_step_seconds else "-"
        epoch = (
            f"{row.training_epoch_seconds_8192:.1f} s"
            if row.training_epoch_seconds_8192
            else "-"
        )
        rss = f"{row.training_peak_rss_mb:.0f} MB" if row.training_peak_rss_mb else "-"
        lines.append(
            f"| {row.distance} | {row.edges} | {row.parameters} | {row.batch} |"
            f" {row.forward_microseconds_per_shot:,.1f} | {row.peak_rss_mb:.0f} MB |"
            f" {step} | {epoch} | {rss} |"
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distances", type=int, nargs="+", default=[3, 5, 7, 9])
    parser.add_argument("--gnn-distances", type=int, nargs="+", default=[5, 7])
    parser.add_argument("--probability", type=float, default=DEFAULT_P)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--json", type=Path, default=None)
    arguments = parser.parse_args(argv)

    torch.set_num_threads(arguments.threads)
    bp_rows = probe_bp(arguments.distances, arguments.probability)
    gnn_rows = probe_gnn(arguments.gnn_distances, arguments.probability)
    report = render(bp_rows, gnn_rows, arguments.probability)
    print(report)

    if arguments.json is not None:
        payload: dict[str, Any] = {
            "probability": arguments.probability,
            "torch_threads": arguments.threads,
            "bp": [asdict(row) for row in bp_rows],
            "gnn": [asdict(row) for row in gnn_rows],
        }
        arguments.json.parent.mkdir(parents=True, exist_ok=True)
        arguments.json.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"\nwrote {arguments.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())