"""M3: transfer evaluation of a trained syndrome reweighting GNN.

The M3 experiments ask how far the M2 learned reweighting carries over when the
test distribution moves away from training: a different physical error rate, a
different noise model, or a different code distance.  Nothing is retrained here:
a checkpoint produced by :func:`graph_qec.m2_pipeline.run_m2` is reloaded and
evaluated on a freshly generated target distribution, so the numbers measure
extrapolation rather than interpolation.
"""

from __future__ import annotations

import platform
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import stim
import torch

from .config import ExperimentConfig
from .decoders import (
    BPDecoder,
    BPOSDDecoder,
    DecodeResult,
    DEMSystem,
    MWPMDecoder,
    UnionFindDecoder,
)
from .graph_features import GraphTensor, prior_log_odds
from .m2_config import M2Config
from .m2_pipeline import (
    SplitData,
    _decode_with_priors,
    _evaluate,
    _log,
    _sha256_array,
    build_experiment_graph,
    combined_logits,
    generate_split,
    mechanism_baselines,
    roc_auc,
)
from .models import BipartiteSyndromeGNN, graph_to_tensors, predict_logits


TRANSFER_DECODERS = (
    "mwpm",
    "bp",
    "bp_osd",
    "bp_gnn",
    "bp_gnn_osd",
    "bp_gnn_osd_learned_order",
)


class TransferError(RuntimeError):
    """Raised when a checkpoint is incompatible with the target experiment."""


def target_experiment(
    base: ExperimentConfig,
    *,
    distance: int | None = None,
    rounds: int | None = None,
    noise_model: str | None = None,
    physical_error_rate: float | None = None,
) -> ExperimentConfig:
    """Returns ``base`` with the requested M3 transfer axes replaced."""

    return ExperimentConfig(
        name=base.name,
        seed=base.seed,
        family=base.family,
        distance=base.distance if distance is None else distance,
        rounds=base.rounds if rounds is None else rounds,
        noise_model=base.noise_model if noise_model is None else noise_model,
        physical_error_rate=(
            base.physical_error_rate
            if physical_error_rate is None
            else physical_error_rate
        ),
        shots=base.shots,
    )


def load_reweighting_checkpoint(
    config: M2Config,
    graph: GraphTensor,
    checkpoint_path: Path,
) -> tuple[BipartiteSyndromeGNN, dict[str, Any]]:
    """Rebuilds the M2 model architecture and loads its trained weights."""

    payload = torch.load(Path(checkpoint_path), map_location="cpu", weights_only=True)
    if not isinstance(payload, Mapping) or "state_dict" not in payload:
        raise TransferError(f"{checkpoint_path} is not an M2 model checkpoint")

    architecture = {
        "hidden_size": config.model.hidden_size,
        "num_layers": config.model.num_layers,
        "variable_feature_dim": graph.variable_feature_dim,
        "check_feature_dim": graph.check_feature_dim,
        "edge_feature_dim": graph.edge_feature_dim,
    }
    for key, value in architecture.items():
        stored = payload.get(key)
        if stored is not None and int(stored) != int(value):
            raise TransferError(
                f"checkpoint {key}={stored} does not match the target graph "
                f"({key}={value}); retrain the model for this graph"
            )

    model = BipartiteSyndromeGNN(
        variable_feature_dim=graph.variable_feature_dim,
        check_feature_dim=graph.check_feature_dim,
        edge_feature_dim=graph.edge_feature_dim,
        hidden_size=config.model.hidden_size,
        num_layers=config.model.num_layers,
        dropout=config.model.dropout,
    )
    model.load_state_dict(payload["state_dict"])
    model.eval()
    metadata = {
        "checkpoint": str(Path(checkpoint_path).resolve()),
        "checkpoint_config_sha256": payload.get("config_sha256"),
        "architecture": architecture,
    }
    return model, metadata


def run_transfer_evaluation(
    config: M2Config,
    *,
    checkpoint_path: Path,
    experiment: ExperimentConfig | None = None,
    test_seeds: Sequence[int] | None = None,
    test_shots: int | None = None,
    benchmark_decoders: Sequence[str] | None = None,
    timed_runs: int | None = None,
) -> dict[str, Any]:
    """Evaluates a fixed checkpoint on one target distribution."""

    overall_started = time.perf_counter()
    target = config.experiment if experiment is None else experiment
    seeds = tuple(int(seed) for seed in (test_seeds or config.splits.test_seeds))
    shots = int(config.splits.test_shots if test_shots is None else test_shots)
    timed = int(config.benchmark_timed_runs if timed_runs is None else timed_runs)
    decoders = tuple(benchmark_decoders or ("mwpm", "bp", "bp_osd", "bp_gnn", "bp_gnn_osd"))
    for name in decoders:
        if name not in TRANSFER_DECODERS:
            raise TransferError(f"unsupported transfer decoder: {name!r}")

    _log(
        f"transfer evaluation: {config.name} -> d{target.distance} "
        f"{target.noise_model} p={target.physical_error_rate:g} ({shots} shots/seed)"
    )
    test_split, reference = generate_split(config, seeds, shots, target)
    graph = build_experiment_graph(reference)
    system = DEMSystem.from_detector_error_model(reference.raw_dem)
    tensors = graph_to_tensors(graph)
    base_log_odds = prior_log_odds(system.priors)
    model, checkpoint_metadata = load_reweighting_checkpoint(config, graph, checkpoint_path)
    _log(
        f"target graph: {graph.num_checks} detectors, {graph.num_variables} mechanisms, "
        f"{graph.num_edges} edges"
    )

    logits = predict_logits(model, tensors, test_split.detections, batch_size=config.training.batch_size)
    # The interpolation strength is the one selected on the source validation
    # split; re-selecting it here would leak target information into the prior.
    strength = float(config.decoder.reweight_strengths[-1])
    priors = combined_logits(base_log_odds, logits, strength)

    predictions = (logits > 0.0).astype(np.uint8)
    accuracy = float(np.mean(predictions == test_split.error_mechanisms))
    log_loss = float(
        np.mean(
            np.maximum(logits, 0.0)
            - logits * test_split.error_mechanisms
            + np.log1p(np.exp(-np.abs(logits)))
        )
    )
    baselines = mechanism_baselines(base_log_odds, test_split.error_mechanisms)

    bp_decoder = BPDecoder(
        reference.raw_dem,
        max_iterations=config.decoder.max_iterations,
        min_sum_scaling=config.decoder.min_sum_scaling,
        damping=config.decoder.damping,
    )
    bp_osd_decoder = BPOSDDecoder(
        reference.raw_dem,
        max_iterations=config.decoder.max_iterations,
        min_sum_scaling=config.decoder.min_sum_scaling,
        damping=config.decoder.damping,
        osd_order=0,
    )
    decode_functions: dict[str, Callable[[np.ndarray], DecodeResult]] = {
        "mwpm": MWPMDecoder(reference.matching_dem).decode_batch,
        "union_find": UnionFindDecoder(reference.matching_dem).decode_batch,
        "bp": bp_decoder.decode_batch,
        "bp_osd": bp_osd_decoder.decode_batch,
        "bp_gnn": lambda detections: _decode_with_priors(bp_decoder, detections, priors),
        "bp_gnn_osd": lambda detections: bp_osd_decoder.decode_batch(
            detections, prior_llr=priors
        ),
        "bp_gnn_osd_learned_order": lambda detections: bp_osd_decoder.decode_batch(
            detections, prior_llr=priors, osd_ordering_llr=logits
        ),
    }

    entries: list[dict[str, Any]] = []
    for name in decoders:
        _log(f"evaluating {name} on {test_split.shots} shots")
        metrics = _evaluate(
            decode_functions[name],
            detections=test_split.detections,
            observables=test_split.observables,
            system=system,
            timed_runs=timed,
        )
        entry = dict(metrics)
        entry["decoder"] = name
        entries.append(entry)

    return {
        "schema_version": 1,
        "stage": "M3-transfer",
        "name": config.name,
        "config_sha256": config.sha256(),
        "config": config.to_dict(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "stim": stim.__version__,
            "torch": torch.__version__,
        },
        "checkpoint": checkpoint_metadata,
        "transfer": {
            "source_experiment": {
                "family": config.experiment.family,
                "distance": config.experiment.distance,
                "rounds": config.experiment.rounds,
                "noise_model": config.experiment.noise_model,
                "physical_error_rate": config.experiment.physical_error_rate,
            },
            "target_experiment": {
                "family": target.family,
                "distance": target.distance,
                "rounds": target.rounds,
                "noise_model": target.noise_model,
                "physical_error_rate": target.physical_error_rate,
            },
            "reweight_strength": strength,
            "strength_source": "fixed at the source config maximum; not re-selected on target",
        },
        "graph": {
            "num_detectors": graph.num_checks,
            "num_errors": graph.num_variables,
            "num_edges": graph.num_edges,
            "num_observables": system.num_observables,
        },
        "splits": {
            "test": {
                "seeds": list(test_split.seeds),
                "shots": test_split.shots,
                "detections_sha256": _sha256_array(test_split.detections),
                "mechanism_rate": test_split.mechanism_rate,
            }
        },
        "mechanism_prediction": {
            "test_log_loss": log_loss,
            "test_binary_accuracy": accuracy,
            "test_roc_auc": roc_auc(logits, test_split.error_mechanisms),
            "positive_rate": baselines["positive_rate"],
            "all_zeros_accuracy": baselines["all_zeros_accuracy"],
            "dem_prior_log_loss": baselines["dem_prior_log_loss"],
            "dem_prior_roc_auc": baselines["dem_prior_roc_auc"],
        },
        "decoders": entries,
        "total_seconds": time.perf_counter() - overall_started,
    }
