"""M4 pipeline: learned reweighting on detector-error-model-level code families.

``run_m2`` assumes a Stim circuit (it needs ``matching_dem`` for MWPM/union-find
and a circuit for detector coordinates). HGP codes have neither: they are
defined by classical parity-check matrices, their DEM is built directly, and
their checks have degree > 2 so no matching decoder applies. This module
provides the equivalent train/select/test loop for those families while reusing
the M2 GNN, losses, prior handling and evaluation code.
"""

from __future__ import annotations

import platform
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import stim
import torch

from .codes.hgp import HGPCode, small_hgp_codes
from .config import HGP_FAMILIES, ExperimentConfig
from .decoders import BPDecoder, BPOSDDecoder, DecodeResult, DEMSystem
from .graph_features import GraphTensor, build_graph_tensor, prior_log_odds
from .m2_config import M2Config
from .m2_pipeline import (
    SplitData,
    _decode_with_priors,
    _evaluate,
    _log,
    _sha256_array,
    combined_logits,
    mechanism_baselines,
    predict_logits,
    roc_auc,
    train_reweighting_model,
)
from .models import graph_to_tensors


M4_DECODERS = ("bp", "bp_osd", "bp_gnn", "bp_gnn_osd", "bp_gnn_osd_learned_order")


@dataclass(slots=True)
class DEMReference:
    """Everything the M4 pipeline needs from one code instance."""

    family: str
    code: HGPCode
    raw_dem: stim.DetectorErrorModel
    detector_coordinates: Mapping[int, Sequence[float]]


def hgp_code_for_family(family: str) -> HGPCode:
    """Returns the HGP code registered under ``family``."""

    codes = small_hgp_codes()
    if family not in codes:
        raise ValueError(f"{family!r} is not a known HGP family: {sorted(codes)}")
    return codes[family]


def build_reference(config: M2Config) -> DEMReference:
    """Builds the DEM and detector coordinates for a DEM-level code family."""

    family = config.experiment.family
    if family not in HGP_FAMILIES:
        raise ValueError(f"family {family!r} is not DEM-level; use run_m2 instead")
    code = hgp_code_for_family(family)
    dem = code.detector_error_model(config.experiment.physical_error_rate)
    return DEMReference(
        family=family,
        code=code,
        raw_dem=dem,
        detector_coordinates=code.detector_coordinates(),
    )


def generate_dem_split(
    reference: DEMReference,
    priors: np.ndarray,
    seeds: Sequence[int],
    shots: int,
) -> SplitData:
    """Samples independent error mechanisms, syndromes and observables.

    The sampling model is the DEM's own: every ``error`` instruction fires
    independently with its stated probability. That is exactly the model BP
    assumes, and it is the same model Stim's DEM sampler realises for a circuit
    derived DEM, so M4 stays comparable with M0-M3.
    """

    system = DEMSystem.from_detector_error_model(reference.raw_dem)
    check_matrix = system.check_matrix.astype(np.int64)
    observable_matrix = system.observable_matrix.astype(np.int64)
    detections: list[np.ndarray] = []
    observables: list[np.ndarray] = []
    mechanisms: list[np.ndarray] = []
    for seed in seeds:
        generator = np.random.default_rng(int(seed))
        fired = (
            generator.random((int(shots), system.num_errors)) < priors[None, :]
        ).astype(np.uint8)
        detections.append(((check_matrix @ fired.T) % 2).T.astype(np.uint8))
        observables.append(((observable_matrix @ fired.T) % 2).T.astype(np.uint8))
        mechanisms.append(fired)
    return SplitData(
        detections=np.ascontiguousarray(np.concatenate(detections, axis=0)),
        observables=np.ascontiguousarray(np.concatenate(observables, axis=0)),
        error_mechanisms=np.ascontiguousarray(np.concatenate(mechanisms, axis=0)),
        seeds=tuple(int(seed) for seed in seeds),
    )


def run_m4(config: M2Config, *, artifact_dir: Path | None = None) -> dict[str, Any]:
    """Trains and evaluates the reweighted decoder on one DEM-level code."""

    started = time.perf_counter()
    if config.experiment.noise_model != "code_capacity":
        raise ValueError("M4 currently supports code_capacity noise only")
    reference = build_reference(config)
    system = DEMSystem.from_detector_error_model(reference.raw_dem)
    graph = build_graph_tensor(
        system, detector_coordinates=reference.detector_coordinates
    )
    priors = np.asarray(system.priors, dtype=np.float64)
    base_log_odds = prior_log_odds(priors)
    _log(
        f"{reference.code.name}: {reference.code.num_qubits} qubits, "
        f"{graph.num_checks} detectors, {graph.num_variables} mechanisms, "
        f"{graph.num_edges} edges, k={reference.code.k}"
    )

    train_split = generate_dem_split(reference, priors, config.splits.train_seeds, config.splits.train_shots)
    validation_split = generate_dem_split(
        reference, priors, config.splits.validation_seeds, config.splits.validation_shots
    )
    test_split = generate_dem_split(reference, priors, config.splits.test_seeds, config.splits.test_shots)
    _log(
        f"splits ready: train={train_split.shots} validation={validation_split.shots} "
        f"test={test_split.shots} ({time.perf_counter() - started:.1f}s)"
    )

    tensors = graph_to_tensors(graph)
    model, training_summary = train_reweighting_model(config, graph, train_split, validation_split)
    if artifact_dir is not None:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "state_dict": model.state_dict(),
                "config_sha256": config.sha256(),
                "hidden_size": config.model.hidden_size,
                "num_layers": config.model.num_layers,
                "variable_feature_dim": graph.variable_feature_dim,
                "check_feature_dim": graph.check_feature_dim,
                "edge_feature_dim": graph.edge_feature_dim,
            },
            artifact_dir / "model_state.pt",
        )
    _log(
        f"training done: best validation log loss "
        f"{training_summary['best_validation_log_loss']:.5f} "
        f"in {training_summary['total_training_seconds']:.1f}s"
    )

    validation_logits = predict_logits(
        model, tensors, validation_split.detections, batch_size=config.training.batch_size
    )
    bp_decoder = BPDecoder(
        reference.raw_dem,
        max_iterations=config.decoder.max_iterations,
        min_sum_scaling=config.decoder.min_sum_scaling,
        damping=config.decoder.damping,
    )
    validation_selection: list[dict[str, Any]] = []
    for strength in config.decoder.reweight_strengths:
        selection_priors = combined_logits(base_log_odds, validation_logits, strength)
        metrics = _evaluate(
            lambda detections, p=selection_priors: _decode_with_priors(bp_decoder, detections, p),
            detections=validation_split.detections,
            observables=validation_split.observables,
            system=system,
            timed_runs=1,
        )
        validation_selection.append(
            {
                "reweight_strength": strength,
                "logical_errors": metrics["logical_errors"],
                "logical_error_rate": metrics["logical_error_rate"],
                "mean_iterations": metrics["diagnostics"].get("average_iterations"),
                "convergence_rate": metrics["diagnostics"].get("convergence_rate"),
                "syndrome_consistency_rate": metrics["syndrome_consistency_rate"],
            }
        )
    selected = min(
        validation_selection,
        key=lambda item: (item["logical_error_rate"], item["mean_iterations"] or 0.0),
    )
    selected_strength = float(selected["reweight_strength"])
    _log(
        "validation sweep: "
        + ", ".join(
            f"s={item['reweight_strength']}:ler={item['logical_error_rate']:.5f}"
            for item in validation_selection
        )
    )

    test_logits = predict_logits(
        model, tensors, test_split.detections, batch_size=config.training.batch_size
    )
    test_priors = combined_logits(base_log_odds, test_logits, selected_strength)

    bp_osd_decoder = BPOSDDecoder(
        reference.raw_dem,
        max_iterations=config.decoder.max_iterations,
        min_sum_scaling=config.decoder.min_sum_scaling,
        damping=config.decoder.damping,
        osd_order=0,
    )
    decode_functions: dict[str, Callable[[np.ndarray], DecodeResult]] = {
        "bp": bp_decoder.decode_batch,
        "bp_osd": bp_osd_decoder.decode_batch,
        "bp_gnn": lambda detections: _decode_with_priors(bp_decoder, detections, test_priors),
        "bp_gnn_osd": lambda detections: bp_osd_decoder.decode_batch(
            detections, prior_llr=test_priors
        ),
        "bp_gnn_osd_learned_order": lambda detections: bp_osd_decoder.decode_batch(
            detections, prior_llr=test_priors, osd_ordering_llr=test_logits
        ),
    }
    for name in config.benchmark_decoders:
        if name not in decode_functions:
            raise ValueError(f"unsupported M4 decoder: {name!r}")

    decoders: list[dict[str, Any]] = []
    for name in config.benchmark_decoders:
        _log(f"evaluating {name} on {test_split.shots} shots")
        metrics = _evaluate(
            decode_functions[name],
            detections=test_split.detections,
            observables=test_split.observables,
            system=system,
            timed_runs=config.benchmark_timed_runs,
        )
        entry = dict(metrics)
        entry["decoder"] = name
        decoders.append(entry)

    mechanism_predictions = (test_logits > 0.0).astype(np.uint8)
    log_loss = float(
        np.mean(
            np.maximum(test_logits, 0.0)
            - test_logits * test_split.error_mechanisms
            + np.log1p(np.exp(-np.abs(test_logits)))
        )
    )
    return {
        "schema_version": 1,
        "stage": "M4",
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
        "code": reference.code.summary(),
        "graph": {
            "num_detectors": graph.num_checks,
            "num_errors": graph.num_variables,
            "num_edges": graph.num_edges,
            "num_observables": system.num_observables,
        },
        "splits": {
            "train": {"seeds": list(train_split.seeds), "shots": train_split.shots,
                      "detections_sha256": _sha256_array(train_split.detections),
                      "mechanism_rate": train_split.mechanism_rate},
            "validation": {"seeds": list(validation_split.seeds), "shots": validation_split.shots,
                           "detections_sha256": _sha256_array(validation_split.detections),
                           "mechanism_rate": validation_split.mechanism_rate},
            "test": {"seeds": list(test_split.seeds), "shots": test_split.shots,
                     "detections_sha256": _sha256_array(test_split.detections),
                     "mechanism_rate": test_split.mechanism_rate},
        },
        "training": training_summary,
        "validation_selection": validation_selection,
        "selected_reweight_strength": selected_strength,
        "mechanism_prediction": {
            "test_log_loss": log_loss,
            "test_binary_accuracy": float(
                np.mean(mechanism_predictions == test_split.error_mechanisms)
            ),
            "test_roc_auc": roc_auc(test_logits, test_split.error_mechanisms),
            **mechanism_baselines(base_log_odds, test_split.error_mechanisms),
        },
        "decoders": decoders,
        "total_seconds": time.perf_counter() - started,
    }


def run_dem_transfer(
    source_config: M2Config,
    *,
    checkpoint_path: Path,
    target_config: M2Config,
    benchmark_decoders: Sequence[str] = ("bp", "bp_gnn", "bp_gnn_osd"),
    test_seeds: Sequence[int] | None = None,
    test_shots: int | None = None,
    timed_runs: int = 1,
) -> dict[str, Any]:
    """Evaluates a checkpoint trained on one DEM-level code on another one.

    The weight is taken from the *source* configuration (never re-selected on the
    target), so the numbers measure transfer rather than target-tuned best case.
    """

    from .m3_pipeline import load_reweighting_checkpoint

    started = time.perf_counter()
    target_reference = build_reference(target_config)
    system = DEMSystem.from_detector_error_model(target_reference.raw_dem)
    graph = build_graph_tensor(
        system, detector_coordinates=target_reference.detector_coordinates
    )
    priors = np.asarray(system.priors, dtype=np.float64)
    base_log_odds = prior_log_odds(priors)
    model, checkpoint_metadata = load_reweighting_checkpoint(
        target_config, graph, Path(checkpoint_path)
    )
    seeds = tuple(int(seed) for seed in (test_seeds or target_config.splits.test_seeds))
    shots = int(target_config.splits.test_shots if test_shots is None else test_shots)
    test_split = generate_dem_split(target_reference, priors, seeds, shots)
    strength = float(source_config.decoder.reweight_strengths[-1])
    _log(
        f"transfer {source_config.experiment.family} -> {target_reference.family} "
        f"({test_split.shots} shots), strength={strength}"
    )

    tensors = graph_to_tensors(graph)
    logits = predict_logits(
        model, tensors, test_split.detections, batch_size=target_config.training.batch_size
    )
    combined = combined_logits(base_log_odds, logits, strength)

    bp_decoder = BPDecoder(
        target_reference.raw_dem,
        max_iterations=target_config.decoder.max_iterations,
        min_sum_scaling=target_config.decoder.min_sum_scaling,
        damping=target_config.decoder.damping,
    )
    bp_osd_decoder = BPOSDDecoder(
        target_reference.raw_dem,
        max_iterations=target_config.decoder.max_iterations,
        min_sum_scaling=target_config.decoder.min_sum_scaling,
        damping=target_config.decoder.damping,
        osd_order=0,
    )
    decode_functions: dict[str, Callable[[np.ndarray], DecodeResult]] = {
        "bp": bp_decoder.decode_batch,
        "bp_gnn": lambda detections: _decode_with_priors(bp_decoder, detections, combined),
        "bp_gnn_osd": lambda detections: bp_osd_decoder.decode_batch(
            detections, prior_llr=combined
        ),
        "bp_gnn_osd_learned_order": lambda detections: bp_osd_decoder.decode_batch(
            detections, prior_llr=combined, osd_ordering_llr=logits
        ),
    }
    entries: list[dict[str, Any]] = []
    for name in benchmark_decoders:
        if name not in decode_functions:
            raise ValueError(f"unsupported M4 transfer decoder: {name!r}")
        metrics = _evaluate(
            decode_functions[name],
            detections=test_split.detections,
            observables=test_split.observables,
            system=system,
            timed_runs=timed_runs,
        )
        entry = dict(metrics)
        entry["decoder"] = name
        entries.append(entry)

    return {
        "schema_version": 1,
        "stage": "M4-transfer",
        "name": f"{source_config.name}->{target_config.name}",
        "checkpoint": checkpoint_metadata,
        "source": {
            "family": source_config.experiment.family,
            "noise_model": source_config.experiment.noise_model,
            "physical_error_rate": source_config.experiment.physical_error_rate,
            "num_qubits": hgp_code_for_family(source_config.experiment.family).num_qubits
            if source_config.experiment.family in HGP_FAMILIES
            else None,
        },
        "target": {
            "family": target_reference.family,
            "noise_model": target_config.experiment.noise_model,
            "physical_error_rate": target_config.experiment.physical_error_rate,
            "num_qubits": target_reference.code.num_qubits,
            "k": target_reference.code.k,
        },
        "reweight_strength": strength,
        "graph": {
            "num_detectors": graph.num_checks,
            "num_errors": graph.num_variables,
            "num_edges": graph.num_edges,
        },
        "splits": {
            "test": {
                "seeds": list(test_split.seeds),
                "shots": test_split.shots,
                "detections_sha256": _sha256_array(test_split.detections),
                "mechanism_rate": test_split.mechanism_rate,
            }
        },
        "decoders": entries,
        "total_seconds": time.perf_counter() - started,
    }
