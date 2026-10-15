"""Validated configuration for the M2 GNN reweighting experiments."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .config import ExperimentConfig


SCHEMA_VERSION = 1

SUPPORTED_BENCHMARK_DECODERS = frozenset(
    {
        "mwpm",
        "union_find",
        "bp",
        "bp_osd",
        "bp_gnn",
        "bp_gnn_osd",
        "bp_gnn_osd_learned_order",
        "osd_bp",
        "osd_gnn",
    }
)


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field!r} must be an object")
    return value


def _int(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field!r} must be an integer")
    if value < minimum:
        raise ValueError(f"{field!r} must be >= {minimum}")
    return value


def _float(value: Any, field: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field!r} must be numeric")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"{field!r} must be >= {minimum}")
    return result


def _int_sequence(value: Any, field: str) -> tuple[int, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field!r} must be a list of integers")
    if not value:
        raise ValueError(f"{field!r} must not be empty")
    return tuple(_int(item, field, minimum=0) for item in value)


def _float_sequence(value: Any, field: str) -> tuple[float, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field!r} must be a list of numbers")
    if not value:
        raise ValueError(f"{field!r} must not be empty")
    return tuple(_float(item, field, minimum=0.0) for item in value)


@dataclass(frozen=True, slots=True)
class SplitConfig:
    """Dataset split definition: disjoint seeds generate disjoint datasets."""

    train_seeds: tuple[int, ...]
    validation_seeds: tuple[int, ...]
    test_seeds: tuple[int, ...]
    train_shots: int
    validation_shots: int
    test_shots: int

    def __post_init__(self) -> None:
        train = set(self.train_seeds)
        validation = set(self.validation_seeds)
        test = set(self.test_seeds)
        if train & validation or train & test or validation & test:
            raise ValueError("train/validation/test seeds must be disjoint")
        for name in ("train_shots", "validation_shots", "test_shots"):
            _int(getattr(self, name), name, minimum=1)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SplitConfig":
        payload = _mapping(payload, "splits")
        return cls(
            train_seeds=_int_sequence(payload.get("train_seeds"), "splits.train_seeds"),
            validation_seeds=_int_sequence(
                payload.get("validation_seeds"), "splits.validation_seeds"
            ),
            test_seeds=_int_sequence(payload.get("test_seeds"), "splits.test_seeds"),
            train_shots=_int(payload.get("train_shots"), "splits.train_shots", minimum=1),
            validation_shots=_int(
                payload.get("validation_shots"), "splits.validation_shots", minimum=1
            ),
            test_shots=_int(payload.get("test_shots"), "splits.test_shots", minimum=1),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "train_seeds": list(self.train_seeds),
            "validation_seeds": list(self.validation_seeds),
            "test_seeds": list(self.test_seeds),
            "train_shots": self.train_shots,
            "validation_shots": self.validation_shots,
            "test_shots": self.test_shots,
        }


@dataclass(frozen=True, slots=True)
class ModelConfig:
    hidden_size: int
    num_layers: int
    dropout: float

    def __post_init__(self) -> None:
        _int(self.hidden_size, "model.hidden_size", minimum=1)
        _int(self.num_layers, "model.num_layers", minimum=1)
        dropout = _float(self.dropout, "model.dropout", minimum=0.0)
        if dropout >= 1.0:
            raise ValueError("model.dropout must be in [0, 1)")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ModelConfig":
        payload = _mapping(payload, "model")
        return cls(
            hidden_size=_int(payload.get("hidden_size"), "model.hidden_size", minimum=1),
            num_layers=_int(payload.get("num_layers"), "model.num_layers", minimum=1),
            dropout=_float(payload.get("dropout", 0.0), "model.dropout", minimum=0.0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "hidden_size": self.hidden_size,
            "num_layers": self.num_layers,
            "dropout": self.dropout,
        }


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    epochs: int
    batch_size: int
    learning_rate: float
    weight_decay: float
    seed: int
    max_grad_norm: float
    torch_threads: int

    def __post_init__(self) -> None:
        _int(self.epochs, "training.epochs", minimum=1)
        _int(self.batch_size, "training.batch_size", minimum=1)
        _int(self.seed, "training.seed", minimum=0)
        _int(self.torch_threads, "training.torch_threads", minimum=1)
        if _float(self.learning_rate, "training.learning_rate", minimum=0.0) <= 0.0:
            raise ValueError("training.learning_rate must be positive")
        _float(self.weight_decay, "training.weight_decay", minimum=0.0)
        _float(self.max_grad_norm, "training.max_grad_norm", minimum=0.0)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingConfig":
        payload = _mapping(payload, "training")
        return cls(
            epochs=_int(payload.get("epochs"), "training.epochs", minimum=1),
            batch_size=_int(payload.get("batch_size"), "training.batch_size", minimum=1),
            learning_rate=_float(
                payload.get("learning_rate"), "training.learning_rate", minimum=0.0
            ),
            weight_decay=_float(payload.get("weight_decay", 0.0), "training.weight_decay"),
            seed=_int(payload.get("seed"), "training.seed", minimum=0),
            max_grad_norm=_float(payload.get("max_grad_norm", 1.0), "training.max_grad_norm"),
            torch_threads=_int(payload.get("torch_threads", 4), "training.torch_threads", minimum=1),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "seed": self.seed,
            "max_grad_norm": self.max_grad_norm,
            "torch_threads": self.torch_threads,
        }


@dataclass(frozen=True, slots=True)
class ReweightConfig:
    """BP parameters plus the learned-prior interpolation grid."""

    max_iterations: int
    min_sum_scaling: float
    damping: float
    reweight_strengths: tuple[float, ...]

    def __post_init__(self) -> None:
        _int(self.max_iterations, "decoder.max_iterations", minimum=1)
        scaling = _float(self.min_sum_scaling, "decoder.min_sum_scaling")
        if not 0.0 < scaling <= 1.0:
            raise ValueError("decoder.min_sum_scaling must be in (0, 1]")
        damping = _float(self.damping, "decoder.damping", minimum=0.0)
        if damping >= 1.0:
            raise ValueError("decoder.damping must be in [0, 1)")
        if 0.0 not in self.reweight_strengths:
            raise ValueError("decoder.reweight_strengths must include 0.0 (the BP baseline)")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReweightConfig":
        payload = _mapping(payload, "decoder")
        return cls(
            max_iterations=_int(payload.get("max_iterations"), "decoder.max_iterations", minimum=1),
            min_sum_scaling=_float(payload.get("min_sum_scaling"), "decoder.min_sum_scaling"),
            damping=_float(payload.get("damping", 0.0), "decoder.damping"),
            reweight_strengths=_float_sequence(
                payload.get("reweight_strengths"), "decoder.reweight_strengths"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_iterations": self.max_iterations,
            "min_sum_scaling": self.min_sum_scaling,
            "damping": self.damping,
            "reweight_strengths": list(self.reweight_strengths),
        }


def _decoder_sequence(value: Any, field: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field!r} must be a list of decoder names")
    if not value:
        raise ValueError(f"{field!r} must not be empty")
    names: list[str] = []
    for item in value:
        if not isinstance(item, str) or item not in SUPPORTED_BENCHMARK_DECODERS:
            raise ValueError(
                f"{field!r} entries must be one of {sorted(SUPPORTED_BENCHMARK_DECODERS)}"
            )
        names.append(item)
    if len(set(names)) != len(names):
        raise ValueError(f"{field!r} must not contain duplicates")
    return tuple(names)


@dataclass(frozen=True, slots=True)
class M2Config:
    """Everything needed to train and evaluate a GNN-reweighted BP decoder."""

    name: str
    experiment: ExperimentConfig
    splits: SplitConfig
    model: ModelConfig
    training: TrainingConfig
    decoder: ReweightConfig
    benchmark_decoders: tuple[str, ...] = ("mwpm", "bp", "bp_gnn")
    benchmark_timed_runs: int = 3

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("'name' must be a non-empty string")
        _int(self.benchmark_timed_runs, "benchmark.timed_runs", minimum=1)
        for name in self.benchmark_decoders:
            if name not in SUPPORTED_BENCHMARK_DECODERS:
                raise ValueError(f"unsupported benchmark decoder: {name!r}")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "M2Config":
        payload = _mapping(payload, "config")
        schema_version = _int(payload.get("schema_version"), "schema_version", minimum=1)
        if schema_version != SCHEMA_VERSION:
            raise ValueError(f"unsupported schema_version: {schema_version}")
        return cls(
            name=payload.get("name"),
            experiment=ExperimentConfig.from_dict(_mapping(payload.get("experiment"), "experiment")),
            splits=SplitConfig.from_dict(_mapping(payload.get("splits"), "splits")),
            model=ModelConfig.from_dict(_mapping(payload.get("model"), "model")),
            training=TrainingConfig.from_dict(_mapping(payload.get("training"), "training")),
            decoder=ReweightConfig.from_dict(_mapping(payload.get("decoder"), "decoder")),
            benchmark_decoders=(
                _decoder_sequence(payload["benchmark"]["decoders"], "benchmark.decoders")
                if "benchmark" in payload
                else ("mwpm", "bp", "bp_gnn")
            ),
            benchmark_timed_runs=(
                _int(payload["benchmark"].get("timed_runs", 3), "benchmark.timed_runs", minimum=1)
                if "benchmark" in payload
                else 3
            ),
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> "M2Config":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "experiment": self.experiment.to_dict(),
            "splits": self.splits.to_dict(),
            "model": self.model.to_dict(),
            "training": self.training.to_dict(),
            "decoder": self.decoder.to_dict(),
            "benchmark": {
                "decoders": list(self.benchmark_decoders),
                "timed_runs": self.benchmark_timed_runs,
            },
        }

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def artifact_name(self) -> str:
        distance = self.experiment.distance
        probability = f"{self.experiment.physical_error_rate:g}".replace(".", "p")
        return f"{self.name}__d{distance}__{self.experiment.noise_model}__p{probability}"
