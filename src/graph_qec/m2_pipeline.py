"""M2 pipeline: GNN-based prior reweighting for BP.

The stage trains a bipartite syndrome GNN that predicts syndrome-conditioned
error-mechanism marginals and feeds the predicted log-odds into BP as a learned
prior. Everything is driven by :class:`~graph_qec.m2_config.M2Config`; datasets
are split by random seed so that no training shot can leak into validation or
test.
"""

from __future__ import annotations

import hashlib
import math
import platform
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

import numpy as np
import stim
import torch
from torch import nn

from .config import ExperimentConfig
from .data_pipeline import GeneratedDataset, generate_dataset
from .decoders import BPDecoder, BPOSDDecoder, DecodeResult, DEMSystem, MWPMDecoder, UnionFindDecoder
from .graph_features import GraphTensor, build_graph_tensor, prior_log_odds
from .m2_config import M2Config
from .models import BipartiteSyndromeGNN, graph_to_tensors, predict_logits


def _log(message: str) -> None:
    """Writes progress to stderr so results stay machine-readable on stdout."""

    print(f"[m2] {message}", file=sys.stderr, flush=True)


@dataclass(slots=True)
class SplitData:
    """Concatenated shots for one split plus the shared DEM structure."""

    detections: np.ndarray
    observables: np.ndarray
    error_mechanisms: np.ndarray
    seeds: tuple[int, ...]

    @property
    def shots(self) -> int:
        return int(self.detections.shape[0])

    @property
    def mechanism_rate(self) -> float:
        return float(self.error_mechanisms.mean())


def _sha256_array(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def _split_experiment(
    config: M2Config,
    seed: int,
    shots: int,
    experiment: ExperimentConfig | None = None,
) -> ExperimentConfig:
    base = config.experiment if experiment is None else experiment
    return ExperimentConfig(
        name=base.name,
        seed=seed,
        family=base.family,
        distance=base.distance,
        rounds=base.rounds,
        noise_model=base.noise_model,
        physical_error_rate=base.physical_error_rate,
        shots=shots,
    )


def generate_split(
    config: M2Config,
    seeds: tuple[int, ...],
    shots: int,
    experiment: ExperimentConfig | None = None,
) -> tuple[SplitData, GeneratedDataset]:
    """Generates one split from disjoint seeds and returns a reference dataset.

    ``experiment`` optionally replaces the code/noise parameters while keeping
    the config-derived graph and split bookkeeping, which is how M3 evaluates a
    checkpoint on a different noise rate or code distance.
    """

    detections: list[np.ndarray] = []
    observables: list[np.ndarray] = []
    mechanisms: list[np.ndarray] = []
    reference: GeneratedDataset | None = None
    reference_dem: str | None = None

    for seed in seeds:
        dataset = generate_dataset(_split_experiment(config, seed, shots, experiment))
        dem_text = str(dataset.raw_dem)
        if reference_dem is None:
            reference = dataset
            reference_dem = dem_text
        elif dem_text != reference_dem:
            raise RuntimeError(
                "Seed-specific datasets produced different detector error models; "
                "the GNN reweighting requires one fixed graph per experiment."
            )
        detections.append(dataset.detections)
        observables.append(dataset.observables)
        mechanisms.append(dataset.error_mechanisms)

    assert reference is not None
    return (
        SplitData(
            detections=np.ascontiguousarray(np.concatenate(detections, axis=0)),
            observables=np.ascontiguousarray(np.concatenate(observables, axis=0)),
            error_mechanisms=np.ascontiguousarray(np.concatenate(mechanisms, axis=0)),
            seeds=tuple(int(seed) for seed in seeds),
        ),
        reference,
    )


def build_experiment_graph(reference: GeneratedDataset) -> GraphTensor:
    """Builds the fixed bipartite graph shared by every shot of an experiment."""

    system = DEMSystem.from_detector_error_model(reference.raw_dem)
    coordinates = reference.circuit.get_detector_coordinates()
    return build_graph_tensor(system, detector_coordinates=coordinates)


def _train_epoch(
    model: BipartiteSyndromeGNN,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    tensors: Mapping[str, torch.Tensor],
    detections: np.ndarray,
    mechanisms: np.ndarray,
    *,
    batch_size: int,
    max_grad_norm: float,
    generator: np.random.Generator,
) -> float:
    model.train()
    order = generator.permutation(detections.shape[0])
    total_loss = 0.0
    total_shots = 0
    for start in range(0, order.size, batch_size):
        index = order[start : start + batch_size]
        syndrome = torch.as_tensor(
            detections[index], dtype=torch.float32, device=tensors["variable_features"].device
        )
        targets = torch.as_tensor(
            mechanisms[index], dtype=torch.float32, device=tensors["variable_features"].device
        )
        logits = model(syndrome=syndrome, **tensors)
        loss = criterion(logits, targets)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        if max_grad_norm > 0.0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
        optimizer.step()
        total_loss += float(loss.detach()) * index.size
        total_shots += int(index.size)
    return total_loss / max(total_shots, 1)


@torch.no_grad()
def _mean_log_loss(
    model: BipartiteSyndromeGNN,
    criterion: nn.Module,
    tensors: Mapping[str, torch.Tensor],
    detections: np.ndarray,
    mechanisms: np.ndarray,
    *,
    batch_size: int,
) -> float:
    model.eval()
    device = tensors["variable_features"].device
    total = 0.0
    shots = 0
    for start in range(0, detections.shape[0], batch_size):
        stop = min(start + batch_size, detections.shape[0])
        syndrome = torch.as_tensor(detections[start:stop], dtype=torch.float32, device=device)
        targets = torch.as_tensor(mechanisms[start:stop], dtype=torch.float32, device=device)
        total += float(criterion(model(syndrome=syndrome, **tensors), targets)) * (stop - start)
        shots += stop - start
    return total / max(shots, 1)


def train_reweighting_model(
    config: M2Config,
    graph: GraphTensor,
    train: SplitData,
    validation: SplitData,
) -> tuple[BipartiteSyndromeGNN, dict[str, Any]]:
    """Trains the syndrome GNN and returns the best-validation checkpoint."""

    torch.manual_seed(config.training.seed)
    torch.set_num_threads(config.training.torch_threads)
    tensors = graph_to_tensors(graph)
    model = BipartiteSyndromeGNN(
        variable_feature_dim=graph.variable_feature_dim,
        check_feature_dim=graph.check_feature_dim,
        edge_feature_dim=graph.edge_feature_dim,
        hidden_size=config.model.hidden_size,
        num_layers=config.model.num_layers,
        dropout=config.model.dropout,
    )
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config.training.learning_rate,
        weight_decay=config.training.weight_decay,
    )
    criterion = nn.BCEWithLogitsLoss()
    generator = np.random.default_rng(config.training.seed)

    history: list[dict[str, Any]] = []
    best_state: dict[str, torch.Tensor] | None = None
    best_validation_loss = math.inf

    for epoch in range(1, config.training.epochs + 1):
        started = time.perf_counter()
        train_loss = _train_epoch(
            model,
            optimizer,
            criterion,
            tensors,
            train.detections,
            train.error_mechanisms,
            batch_size=config.training.batch_size,
            max_grad_norm=config.training.max_grad_norm,
            generator=generator,
        )
        validation_loss = _mean_log_loss(
            model,
            criterion,
            tensors,
            validation.detections,
            validation.error_mechanisms,
            batch_size=config.training.batch_size,
        )
        elapsed = time.perf_counter() - started
        _log(
            f"epoch {epoch}/{config.training.epochs}: train={train_loss:.5f} "
            f"validation={validation_loss:.5f} ({elapsed:.1f}s)"
        )
        history.append(
            {
                "epoch": epoch,
                "train_log_loss": train_loss,
                "validation_log_loss": validation_loss,
                "seconds": elapsed,
            }
        )
        if validation_loss < best_validation_loss:
            best_validation_loss = validation_loss
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)

    summary = {
        "parameters": int(sum(p.numel() for p in model.parameters())),
        "epochs": config.training.epochs,
        "best_validation_log_loss": best_validation_loss,
        "final_train_log_loss": history[-1]["train_log_loss"],
        "total_training_seconds": float(sum(item["seconds"] for item in history)),
        "history": history,
    }
    return model, summary


def roc_auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Rank-based ROC AUC for binary labels and real-valued scores."""

    labels = np.asarray(labels, dtype=np.float64).ravel()
    scores = np.asarray(scores, dtype=np.float64).ravel()
    positives = labels > 0.5
    num_positive = int(positives.sum())
    num_negative = int(labels.size - num_positive)
    if num_positive == 0 or num_negative == 0:
        return float("nan")
    order = np.argsort(scores, kind="stable")
    sorted_scores = scores[order]
    sorted_ranks = np.empty(scores.size, dtype=np.float64)
    start = 0
    while start < scores.size:
        stop = start
        while stop + 1 < scores.size and sorted_scores[stop + 1] == sorted_scores[start]:
            stop += 1
        sorted_ranks[start : stop + 1] = 0.5 * (start + stop) + 1.0
        start = stop + 1
    ranks = np.empty(scores.size, dtype=np.float64)
    ranks[order] = sorted_ranks
    return float(
        (ranks[positives].sum() - num_positive * (num_positive + 1) / 2.0)
        / (num_positive * num_negative)
    )


def mechanism_baselines(
    base_log_odds: np.ndarray,
    mechanisms: np.ndarray,
) -> dict[str, float]:
    """Trivial mechanism-prediction baselines for one split.

    Because DEM error mechanisms fire rarely, raw accuracy is dominated by true
    negatives; the DEM-prior log loss and the all-zeros accuracy are reported so
    the learned model can be compared against predictors that ignore syndrome.
    """

    mechanisms = np.asarray(mechanisms, dtype=np.float64)
    positive_rate = float(mechanisms.mean())
    probabilities = 1.0 / (1.0 + np.exp(np.asarray(base_log_odds, dtype=np.float64)))
    probabilities = np.clip(probabilities, 1e-12, 1.0 - 1e-12)
    probabilities = np.broadcast_to(probabilities, mechanisms.shape)
    prior_log_loss = float(
        -np.mean(
            mechanisms * np.log(probabilities)
            + (1.0 - mechanisms) * np.log(1.0 - probabilities)
        )
    )
    return {
        "positive_rate": positive_rate,
        "all_zeros_accuracy": 1.0 - positive_rate,
        "dem_prior_log_loss": prior_log_loss,
        "dem_prior_roc_auc": roc_auc(probabilities, mechanisms),
    }


def learned_logits_to_llr(learned_logits: np.ndarray) -> np.ndarray:
    """Converts model log-odds ``log P(e=1)/P(e=0)`` to BP LLR ``log P(e=0)/P(e=1)``.

    The GNN head is trained with ``BCEWithLogitsLoss`` on the indicator
    ``e_i = 1``, so its output is the log-odds that mechanism ``i`` fired. BP and
    the DEM prior use the opposite convention (``prior_log_odds`` returns
    ``log((1-p)/p)``), so the sign must be flipped before the two are combined.
    """

    return -np.asarray(learned_logits, dtype=np.float64)


def combined_logits(base_log_odds: np.ndarray, learned_logits: np.ndarray, strength: float) -> np.ndarray:
    """Interpolates between the DEM prior LLR (0.0) and the learned LLR (1.0).

    ``learned_logits`` are model outputs (log-odds of ``e_i = 1``) and are
    converted to the BP LLR convention before interpolation.
    """

    if not 0.0 <= strength <= 1.0:
        raise ValueError("strength must be in [0, 1]")
    learned_llr = learned_logits_to_llr(learned_logits)
    return base_log_odds + strength * (learned_llr - base_log_odds)


def _decode_with_priors(
    decoder: BPDecoder,
    detections: np.ndarray,
    prior_llr: np.ndarray | None,
) -> DecodeResult:
    return decoder.decode_batch(detections, prior_llr=prior_llr)


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return str(value)


def _evaluate(
    decode: Callable[[np.ndarray], DecodeResult],
    *,
    detections: np.ndarray,
    observables: np.ndarray,
    system: DEMSystem,
    timed_runs: int = 3,
) -> dict[str, Any]:
    """Evaluates one decoding function on a fixed shot set."""

    result = decode(detections)
    logical_errors = int(np.count_nonzero(np.any(result.predictions != observables, axis=1)))
    shots = detections.shape[0]
    rate = logical_errors / shots

    if result.corrections is not None:
        residual = (system.check_matrix.astype(np.int64) @ result.corrections.T.astype(np.int64)) % 2
        consistent = int(np.count_nonzero(np.all(residual.T == detections, axis=1)))
        syndrome_consistency = consistent / shots
    else:
        syndrome_consistency = None

    run_seconds: list[float] = []
    for _ in range(timed_runs):
        started = time.perf_counter()
        decode(detections)
        run_seconds.append(time.perf_counter() - started)
    mean_seconds = float(np.mean(run_seconds))

    return {
        "logical_errors": logical_errors,
        "logical_error_rate": rate,
        "logical_error_rate_standard_error": math.sqrt(rate * (1.0 - rate) / shots),
        "syndrome_consistency_rate": syndrome_consistency,
        "latency": {
            "timed_runs": timed_runs,
            "run_seconds": run_seconds,
            "mean_total_seconds": mean_seconds,
            "mean_per_shot_microseconds": mean_seconds * 1e6 / shots,
            "throughput_shots_per_second": shots / mean_seconds,
        },
        "prediction_sha256": _sha256_array(result.predictions),
        "diagnostics": {key: _json_safe(value) for key, value in result.diagnostics.items()},
    }


def run_m2(
    config: M2Config,
    *,
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    """Runs the full M2 train/select/test pipeline for one configuration.

    When ``artifact_dir`` is given, the trained checkpoint is written there so
    the learned reweighting can be reloaded without retraining.
    """

    overall_started = time.perf_counter()
    _log(f"generating splits for {config.name}")
    train_split, reference = generate_split(
        config, config.splits.train_seeds, config.splits.train_shots
    )
    validation_split, _ = generate_split(
        config, config.splits.validation_seeds, config.splits.validation_shots
    )
    test_split, _ = generate_split(config, config.splits.test_seeds, config.splits.test_shots)
    _log(
        f"splits ready: train={train_split.shots} validation={validation_split.shots} "
        f"test={test_split.shots} ({time.perf_counter() - overall_started:.1f}s)"
    )

    graph = build_experiment_graph(reference)
    system = DEMSystem.from_detector_error_model(reference.raw_dem)
    tensors = graph_to_tensors(graph)
    base_log_odds = prior_log_odds(system.priors)

    _log(
        f"graph: {graph.num_checks} detectors, {graph.num_variables} mechanisms, "
        f"{graph.num_edges} edges"
    )
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
        f"training done: best validation log loss {training_summary['best_validation_log_loss']:.5f} "
        f"in {training_summary['total_training_seconds']:.1f}s"
    )

    validation_logits = predict_logits(
        model, tensors, validation_split.detections, batch_size=config.training.batch_size
    )
    validation_selection: list[dict[str, Any]] = []
    bp_decoder = BPDecoder(
        reference.raw_dem,
        max_iterations=config.decoder.max_iterations,
        min_sum_scaling=config.decoder.min_sum_scaling,
        damping=config.decoder.damping,
    )
    for strength in config.decoder.reweight_strengths:
        priors = combined_logits(base_log_odds, validation_logits, strength)
        metrics = _evaluate(
            lambda detections, priors=priors: _decode_with_priors(bp_decoder, detections, priors),
            detections=validation_split.detections,
            observables=validation_split.observables,
            system=system,
            timed_runs=1,
        )
        validation_selection.append(
            {
                "reweight_strength": strength,
                "logical_error_rate": metrics["logical_error_rate"],
                "logical_errors": metrics["logical_errors"],
                "mean_iterations": metrics["diagnostics"].get("average_iterations"),
                "convergence_rate": metrics["diagnostics"].get("convergence_rate"),
                "syndrome_consistency_rate": metrics["syndrome_consistency_rate"],
            }
        )

    selected = min(
        validation_selection,
        key=lambda item: (
            item["logical_error_rate"],
            item["mean_iterations"] if item["mean_iterations"] is not None else math.inf,
        ),
    )
    selected_strength = float(selected["reweight_strength"])
    _log(
        "validation sweep: "
        + ", ".join(
            f"s={item['reweight_strength']}:ler={item['logical_error_rate']:.5f}"
            for item in validation_selection
        )
    )
    _log(f"selected reweight strength {selected_strength}")

    test_logits = predict_logits(
        model, tensors, test_split.detections, batch_size=config.training.batch_size
    )
    test_priors = combined_logits(base_log_odds, test_logits, selected_strength)

    gnn_predictions = (test_logits > 0.0).astype(np.uint8)
    mechanism_accuracy = float(np.mean(gnn_predictions == test_split.error_mechanisms))
    bce = float(
        np.mean(
            np.maximum(test_logits, 0.0)
            - test_logits * test_split.error_mechanisms
            + np.log1p(np.exp(-np.abs(test_logits)))
        )
    )
    baselines = mechanism_baselines(base_log_odds, test_split.error_mechanisms)
    learned_auc = roc_auc(test_logits, test_split.error_mechanisms)

    bp_osd_decoder = BPOSDDecoder(
        reference.raw_dem,
        max_iterations=config.decoder.max_iterations,
        min_sum_scaling=config.decoder.min_sum_scaling,
        damping=config.decoder.damping,
        osd_order=0,
    )
    forced_osd_decoder = BPOSDDecoder(
        reference.raw_dem,
        max_iterations=config.decoder.max_iterations,
        min_sum_scaling=config.decoder.min_sum_scaling,
        damping=config.decoder.damping,
        osd_order=0,
        force_osd=True,
    )
    bp_osd_cs_decoder = BPOSDDecoder(
        reference.raw_dem,
        max_iterations=config.decoder.max_iterations,
        min_sum_scaling=config.decoder.min_sum_scaling,
        damping=config.decoder.damping,
        osd_order=0,
        combination_sweep_order=config.decoder.osd_combination_sweep,
    )
    decoders: list[dict[str, Any]] = []
    decode_functions: dict[str, Callable[[np.ndarray], DecodeResult]] = {
        "mwpm": MWPMDecoder(reference.matching_dem).decode_batch,
        "union_find": UnionFindDecoder(reference.matching_dem).decode_batch,
        "bp": bp_decoder.decode_batch,
        "bp_osd": bp_osd_decoder.decode_batch,
        "bp_gnn": lambda detections: _decode_with_priors(bp_decoder, detections, test_priors),
        "bp_gnn_osd": lambda detections: bp_osd_decoder.decode_batch(
            detections, prior_llr=test_priors
        ),
        "bp_gnn_osd_learned_order": lambda detections: bp_osd_decoder.decode_batch(
            detections, prior_llr=test_priors, osd_ordering_llr=test_logits
        ),
        "osd_bp": forced_osd_decoder.decode_batch,
        "osd_gnn": lambda detections: forced_osd_decoder.decode_batch(
            detections, osd_ordering_llr=test_logits
        ),
        "bp_osd_cs": bp_osd_cs_decoder.decode_batch,
        "bp_gnn_osd_cs": lambda detections: bp_osd_cs_decoder.decode_batch(
            detections, prior_llr=test_priors
        ),
        "bp_gnn_osd_cs_learned_order": lambda detections: bp_osd_cs_decoder.decode_batch(
            detections, prior_llr=test_priors, osd_ordering_llr=test_logits
        ),
    }

    for name in config.benchmark_decoders:
        _log(f"evaluating {name} on {test_split.shots} test shots")
        metrics = _evaluate(
            decode_functions[name],
            detections=test_split.detections,
            observables=test_split.observables,
            system=system,
            timed_runs=config.benchmark_timed_runs,
        )
        decoder_entry = dict(metrics)
        decoder_entry["decoder"] = name
        decoders.append(decoder_entry)

    gnn_latency_start = time.perf_counter()
    predict_logits(model, tensors, test_split.detections, batch_size=config.training.batch_size)
    gnn_inference_seconds = time.perf_counter() - gnn_latency_start

    return {
        "schema_version": 1,
        "stage": "M2",
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
        "graph": {
            "num_detectors": graph.num_checks,
            "num_errors": graph.num_variables,
            "num_edges": graph.num_edges,
            "variable_feature_names": list(graph.variable_feature_names),
            "check_feature_names": list(graph.check_feature_names),
            "edge_feature_names": list(graph.edge_feature_names),
            "num_observables": system.num_observables,
        },
        "splits": {
            "train": {
                "seeds": list(train_split.seeds),
                "shots": train_split.shots,
                "detections_sha256": _sha256_array(train_split.detections),
                "mechanism_rate": train_split.mechanism_rate,
            },
            "validation": {
                "seeds": list(validation_split.seeds),
                "shots": validation_split.shots,
                "detections_sha256": _sha256_array(validation_split.detections),
                "mechanism_rate": validation_split.mechanism_rate,
            },
            "test": {
                "seeds": list(test_split.seeds),
                "shots": test_split.shots,
                "detections_sha256": _sha256_array(test_split.detections),
                "mechanism_rate": test_split.mechanism_rate,
            },
        },
        "training": training_summary,
        "mechanism_prediction": {
            "test_log_loss": bce,
            "test_binary_accuracy": mechanism_accuracy,
            "test_roc_auc": learned_auc,
            "positive_rate": baselines["positive_rate"],
            "all_zeros_accuracy": baselines["all_zeros_accuracy"],
            "dem_prior_log_loss": baselines["dem_prior_log_loss"],
            "dem_prior_roc_auc": baselines["dem_prior_roc_auc"],
        },
        "validation_selection": validation_selection,
        "selected_reweight_strength": selected_strength,
        "gnn_inference": {
            "shots": test_split.shots,
            "total_seconds": gnn_inference_seconds,
            "mean_per_shot_microseconds": gnn_inference_seconds * 1e6 / test_split.shots,
        },
        "decoders": decoders,
        "total_seconds": time.perf_counter() - overall_started,
    }
