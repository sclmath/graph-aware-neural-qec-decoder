"""Validated configuration for the M1 baseline benchmark."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .config import ExperimentConfig


SUPPORTED_DECODERS = ("mwpm", "union_find", "bp", "bp_osd")


def _positive_int(value: Any, field: str, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field!r} must be an integer")
    minimum = 0 if allow_zero else 1
    if value < minimum:
        raise ValueError(f"{field!r} must be >= {minimum}")
    return value


@dataclass(frozen=True, slots=True)
class BenchmarkConfig:
    """Configuration for one reproducible M1 decoder comparison."""

    name: str
    experiment: ExperimentConfig
    decoders: tuple[str, ...]
    warmup_runs: int
    timed_runs: int
    max_shots: int | None
    decoder_parameters: dict[str, dict[str, Any]]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("'name' must be a non-empty string")
        if not self.decoders:
            raise ValueError("'decoders' must not be empty")
        unknown = set(self.decoders) - set(SUPPORTED_DECODERS)
        if unknown:
            raise ValueError(f"Unsupported decoders: {sorted(unknown)}")
        if len(set(self.decoders)) != len(self.decoders):
            raise ValueError("'decoders' must not contain duplicates")
        _positive_int(self.warmup_runs, "benchmark.warmup_runs", allow_zero=True)
        _positive_int(self.timed_runs, "benchmark.timed_runs")
        if self.max_shots is not None:
            _positive_int(self.max_shots, "benchmark.max_shots")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BenchmarkConfig":
        if payload.get("schema_version") != 1:
            raise ValueError("M1 configuration schema_version must be 1")
        experiment_payload = payload.get("experiment")
        if not isinstance(experiment_payload, Mapping):
            raise ValueError("'experiment' must be an object")
        benchmark = payload.get("benchmark")
        if not isinstance(benchmark, Mapping):
            raise ValueError("'benchmark' must be an object")
        decoder_parameters = payload.get("decoder_parameters", {})
        if not isinstance(decoder_parameters, Mapping):
            raise ValueError("'decoder_parameters' must be an object")

        normalized_parameters: dict[str, dict[str, Any]] = {}
        for decoder, parameters in decoder_parameters.items():
            if decoder not in SUPPORTED_DECODERS:
                raise ValueError(f"Unsupported decoder parameters: {decoder!r}")
            if not isinstance(parameters, Mapping):
                raise ValueError(f"decoder_parameters.{decoder} must be an object")
            normalized_parameters[str(decoder)] = dict(parameters)

        decoders_payload = benchmark.get("decoders")
        if not isinstance(decoders_payload, list) or not all(
            isinstance(item, str) for item in decoders_payload
        ):
            raise ValueError("'benchmark.decoders' must be a list of strings")
        max_shots = benchmark.get("max_shots")

        return cls(
            name=payload.get("name"),
            experiment=ExperimentConfig.from_dict(experiment_payload),
            decoders=tuple(decoders_payload),
            warmup_runs=_positive_int(
                benchmark.get("warmup_runs"), "benchmark.warmup_runs", allow_zero=True
            ),
            timed_runs=_positive_int(
                benchmark.get("timed_runs"), "benchmark.timed_runs"
            ),
            max_shots=None
            if max_shots is None
            else _positive_int(max_shots, "benchmark.max_shots"),
            decoder_parameters=normalized_parameters,
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> "BenchmarkConfig":
        with Path(path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return cls.from_dict(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "name": self.name,
            "experiment": self.experiment.to_dict(),
            "benchmark": {
                "decoders": list(self.decoders),
                "warmup_runs": self.warmup_runs,
                "timed_runs": self.timed_runs,
                "max_shots": self.max_shots,
            },
            "decoder_parameters": self.decoder_parameters,
        }

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def artifact_name(self) -> str:
        return self.name
