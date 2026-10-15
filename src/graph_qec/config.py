"""Validated, configuration-driven experiment definitions."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


SUPPORTED_CODE_FAMILIES = frozenset(
    {"repetition_code", "rotated_surface_code", "hgp_rep3x3", "hgp_hamming7x7"}
)
SUPPORTED_NOISE_MODELS = frozenset({"code_capacity", "circuit_level"})

#: Code families that only exist at the detector-error-model level (M4).
HGP_FAMILIES = frozenset({"hgp_rep3x3", "hgp_hamming7x7"})


def _as_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field!r} must be an object")
    return value


def _as_int(value: Any, field: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field!r} must be an integer")
    if value < minimum:
        raise ValueError(f"{field!r} must be >= {minimum}")
    return value


def _as_probability(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field!r} must be numeric")
    result = float(value)
    if not 0.0 < result < 1.0:
        raise ValueError(f"{field!r} must be in (0, 1)")
    return result


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    """Inputs required to generate one deterministic QEC dataset."""

    name: str
    seed: int
    family: str
    distance: int
    rounds: int
    noise_model: str
    physical_error_rate: float
    shots: int

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("'name' must be a non-empty string")
        if self.family not in SUPPORTED_CODE_FAMILIES:
            raise ValueError(
                f"'family' must be one of {sorted(SUPPORTED_CODE_FAMILIES)}"
            )
        if self.noise_model not in SUPPORTED_NOISE_MODELS:
            raise ValueError(
                f"'noise_model' must be one of {sorted(SUPPORTED_NOISE_MODELS)}"
            )
        _as_int(self.seed, "seed", minimum=0)
        _as_int(self.distance, "distance", minimum=2)
        _as_int(self.rounds, "rounds", minimum=1)
        _as_int(self.shots, "shots", minimum=1)
        _as_probability(self.physical_error_rate, "physical_error_rate")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ExperimentConfig":
        """Parses and validates a nested experiment configuration."""

        payload = _as_mapping(payload, "config")
        code = _as_mapping(payload.get("code"), "code")
        noise = _as_mapping(payload.get("noise"), "noise")
        sampling = _as_mapping(payload.get("sampling"), "sampling")

        return cls(
            name=payload.get("name"),
            seed=_as_int(payload.get("seed"), "seed", minimum=0),
            family=code.get("family"),
            distance=_as_int(code.get("distance"), "code.distance", minimum=2),
            rounds=_as_int(code.get("rounds"), "code.rounds", minimum=1),
            noise_model=noise.get("model"),
            physical_error_rate=_as_probability(
                noise.get("physical_error_rate"), "noise.physical_error_rate"
            ),
            shots=_as_int(sampling.get("shots"), "sampling.shots", minimum=1),
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> "ExperimentConfig":
        """Loads a configuration from a JSON object."""

        config_path = Path(path)
        with config_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return cls.from_dict(payload)

    def to_dict(self) -> dict[str, Any]:
        """Returns the canonical nested representation."""

        return {
            "name": self.name,
            "seed": self.seed,
            "code": {
                "family": self.family,
                "distance": self.distance,
                "rounds": self.rounds,
            },
            "noise": {
                "model": self.noise_model,
                "physical_error_rate": self.physical_error_rate,
            },
            "sampling": {"shots": self.shots},
        }

    def canonical_json(self) -> str:
        """Returns stable JSON used for hashing and manifests."""

        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def sha256(self) -> str:
        """Returns the SHA-256 digest of the canonical configuration."""

        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def artifact_name(self) -> str:
        """Returns a filesystem-safe, deterministic artifact directory name."""

        probability = f"{self.physical_error_rate:g}".replace(".", "p")
        return (
            f"{self.name}__d{self.distance}__r{self.rounds}__"
            f"{self.noise_model}__p{probability}__seed{self.seed}"
        )
