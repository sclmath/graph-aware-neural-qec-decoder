r"""M5: GNN inference cost under float32 versus dynamic int8 quantization.

The batched BP rewrite is the other half of M5 and lives in
``src/graph_qec/decoders/bp_engine.py``; this script covers the neural part:
what does dynamic quantization buy on CPU, and what does it cost in posterior
quality and in decoder LER?

Usage:
    .\.venv\Scripts\python.exe scripts\m5_quantization.py `
        --config configs\m3_learned_basis_repetition_circuit_level_d3.json `
        --checkpoint results\m3\<run>\model_state.pt
"""

from __future__ import annotations

import argparse
import copy
import json
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import torch
from torch import nn

from graph_qec.config import ExperimentConfig
from graph_qec.data_pipeline import generate_dataset
from graph_qec.decoders import BPDecoder, DEMSystem
from graph_qec.graph_features import build_graph_tensor, prior_log_odds
from graph_qec.m2_config import M2Config
from graph_qec.m2_pipeline import _decode_with_priors, _evaluate, combined_logits
from graph_qec.models import BipartiteSyndromeGNN, graph_to_tensors, predict_logits
from graph_qec.m3_pipeline import load_reweighting_checkpoint


def _model_size_mb(module: nn.Module) -> float:
    """Serialized weight size in MB.

    Dynamically quantized layers keep their weights in packed-parameter objects
    rather than ``nn.Parameter``s, so walking ``parameters()`` alone reports zero
    for them; the quantized accessors are read explicitly instead.
    """

    total = 0
    for parameter in module.parameters():
        total += parameter.numel() * parameter.element_size()
    for buffer in module.buffers():
        if hasattr(buffer, "numel"):
            total += buffer.numel() * buffer.element_size()
    for child in module.modules():
        weight = getattr(child, "weight", None)
        bias = getattr(child, "bias", None)
        if isinstance(child, nn.quantized.dynamic.Linear):
            packed_weight = child.weight()
            packed_bias = child.bias()
            total += packed_weight.numel() * packed_weight.element_size()
            if packed_bias is not None:
                total += packed_bias.numel() * packed_bias.element_size()
    return total / 1e6


def _timed_predict(model, tensors, detections, batch_size: int, runs: int = 3) -> tuple[np.ndarray, float]:
    logits = predict_logits(model, tensors, detections, batch_size=batch_size)
    best = float("inf")
    for _ in range(runs):
        started = time.perf_counter()
        predict_logits(model, tensors, detections, batch_size=batch_size)
        best = min(best, time.perf_counter() - started)
    return logits, best


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Float32 versus int8 GNN inference (M5).")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("results/m5"))
    parser.add_argument("--test-shots", type=int, default=16384)
    parser.add_argument("--timed-runs", type=int, default=3)
    args = parser.parse_args(argv)

    config = M2Config.from_json_file(args.config)
    experiment = ExperimentConfig(
        name=config.experiment.name,
        seed=config.experiment.seed,
        family=config.experiment.family,
        distance=config.experiment.distance,
        rounds=config.experiment.rounds,
        noise_model=config.experiment.noise_model,
        physical_error_rate=config.experiment.physical_error_rate,
        shots=args.test_shots,
    )
    dataset = generate_dataset(experiment)
    system = DEMSystem.from_detector_error_model(dataset.raw_dem)
    graph = build_graph_tensor(
        system, detector_coordinates=dataset.circuit.get_detector_coordinates()
    )
    tensors = graph_to_tensors(graph)
    base_log_odds = prior_log_odds(system.priors)
    model, metadata = load_reweighting_checkpoint(config, graph, args.checkpoint)

    float_logits, float_seconds = _timed_predict(
        model, tensors, dataset.detections, config.training.batch_size, args.timed_runs
    )
    quantized = torch.ao.quantization.quantize_dynamic(
        copy.deepcopy(model), {nn.Linear}, dtype=torch.qint8
    )
    quantized.eval()
    with torch.no_grad():
        int8_logits, int8_seconds = _timed_predict(
            quantized, tensors, dataset.detections, config.training.batch_size, args.timed_runs
        )

    mechanisms = dataset.error_mechanisms.astype(np.float64)
    log_loss = lambda logits: float(  # noqa: E731
        np.mean(
            np.maximum(logits, 0.0)
            - logits * mechanisms
            + np.log1p(np.exp(-np.abs(logits)))
        )
    )
    agreement = float(
        np.mean((float_logits > 0.0).astype(np.uint8) == (int8_logits > 0.0).astype(np.uint8))
    )
    max_abs_delta = float(np.max(np.abs(float_logits - int8_logits)))

    strength = float(config.decoder.reweight_strengths[-1])
    decoder = BPDecoder(
        dataset.raw_dem,
        max_iterations=config.decoder.max_iterations,
        min_sum_scaling=config.decoder.min_sum_scaling,
        damping=config.decoder.damping,
    )
    variants: dict[str, Any] = {}
    for label, logits in (("float32", float_logits), ("int8", int8_logits)):
        priors = combined_logits(base_log_odds, logits, strength)
        metrics = _evaluate(
            lambda detections, p=priors: _decode_with_priors(decoder, detections, p),
            detections=dataset.detections,
            observables=dataset.observables,
            system=system,
            timed_runs=1,
        )
        variants[label] = {
            "logical_errors": metrics["logical_errors"],
            "logical_error_rate": metrics["logical_error_rate"],
            "syndrome_consistency_rate": metrics["syndrome_consistency_rate"],
        }
    plain = _evaluate(
        decoder.decode_batch,
        detections=dataset.detections,
        observables=dataset.observables,
        system=system,
        timed_runs=1,
    )
    variants["bp_no_prior"] = {
        "logical_errors": plain["logical_errors"],
        "logical_error_rate": plain["logical_error_rate"],
        "syndrome_consistency_rate": plain["syndrome_consistency_rate"],
    }

    shots = dataset.shots
    summary = {
        "config": str(args.config),
        "checkpoint": metadata,
        "shots": shots,
        "batch_size": config.training.batch_size,
        "float32": {
            "model_size_mb": _model_size_mb(model),
            "inference_seconds": float_seconds,
            "microseconds_per_shot": float_seconds * 1e6 / shots,
            "mechanism_log_loss": log_loss(float_logits),
        },
        "int8_dynamic": {
            "model_size_mb": _model_size_mb(quantized),
            "inference_seconds": int8_seconds,
            "microseconds_per_shot": int8_seconds * 1e6 / shots,
            "mechanism_log_loss": log_loss(int8_logits),
        },
        "speedup": float_seconds / int8_seconds if int8_seconds else None,
        "size_ratio": _model_size_mb(quantized) / _model_size_mb(model),
        "sign_agreement": agreement,
        "max_abs_logit_delta": max_abs_delta,
        "decoders": variants,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "quantization.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lines = [
        "# M5: float32 versus dynamic int8 GNN inference",
        "",
        f"Checkpoint: `{args.checkpoint}`  ",
        f"Test shots: {shots}, batch size {config.training.batch_size}, best of {args.timed_runs} runs.",
        "",
        "| model | parameters (MB) | inference (s) | us/shot | mechanism log loss |",
        "|---|---:|---:|---:|---:|",
        "| float32 | {:.4f} | {:.3f} | {:.2f} | {:.5f} |".format(
            summary["float32"]["model_size_mb"], summary["float32"]["inference_seconds"],
            summary["float32"]["microseconds_per_shot"], summary["float32"]["mechanism_log_loss"],
        ),
        "| int8 (dynamic) | {:.4f} | {:.3f} | {:.2f} | {:.5f} |".format(
            summary["int8_dynamic"]["model_size_mb"], summary["int8_dynamic"]["inference_seconds"],
            summary["int8_dynamic"]["microseconds_per_shot"], summary["int8_dynamic"]["mechanism_log_loss"],
        ),
        "",
        "- speedup (float / int8): {:.2f}x".format(summary["speedup"]),
        "- parameter compression: {}".format(
            "{:.2f}x".format(1.0 / summary["size_ratio"]) if summary["size_ratio"] else "n/a"
        ),
        "- mechanism sign agreement: {:.4f} (max |logit delta| {:.3f})".format(
            agreement, max_abs_delta
        ),
        "",
        "| decoder | logical errors | LER | syndrome consistency |",
        "|---|---:|---:|---:|",
    ]
    for label, entry in variants.items():
        lines.append(
            "| {} | {} | {:.5f} | {:.4f} |".format(
                label, entry["logical_errors"], entry["logical_error_rate"],
                entry["syndrome_consistency_rate"],
            )
        )
    lines.append("")
    (args.output_dir / "QUANTIZATION.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "checkpoint"}, indent=2, sort_keys=True, default=str))
    print("wrote", (args.output_dir / "QUANTIZATION.md").resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
