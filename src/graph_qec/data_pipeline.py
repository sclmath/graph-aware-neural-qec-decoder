"""Deterministic sampling, artifact persistence, and DEM verification."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import platform
from typing import Any

import numpy as np
import pymatching
import stim

from .circuits import build_circuit
from .config import ExperimentConfig


SCHEMA_VERSION = 1


@dataclass(slots=True)
class GeneratedDataset:
    """In-memory M0 dataset and the artifacts derived from its circuit."""

    config: ExperimentConfig
    circuit: stim.Circuit
    raw_dem: stim.DetectorErrorModel
    matching_dem: stim.DetectorErrorModel
    detections: np.ndarray
    observables: np.ndarray
    error_mechanisms: np.ndarray
    matching_num_edges: int
    matching_num_nodes: int
    logical_errors: int

    @property
    def shots(self) -> int:
        return int(self.detections.shape[0])

    @property
    def logical_error_rate(self) -> float:
        return self.logical_errors / self.shots


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _sha256_array(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    return _sha256_bytes(contiguous.tobytes(order="C"))


def _write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def generate_dataset(config: ExperimentConfig) -> GeneratedDataset:
    """Generates a deterministic dataset from an exact detector error model.

    Sampling errors, syndromes, and observables together from the raw DEM keeps
    mechanism labels aligned with each shot. The separately decomposed DEM is
    used for the MWPM smoke check.
    """

    circuit = build_circuit(config)
    raw_dem = circuit.detector_error_model(decompose_errors=False)
    matching_dem = circuit.detector_error_model(decompose_errors=True)

    sampler = raw_dem.compile_sampler(seed=config.seed)
    detections, observables, error_mechanisms = sampler.sample(
        config.shots,
        return_errors=True,
    )
    detections = np.ascontiguousarray(detections, dtype=np.uint8)
    observables = np.ascontiguousarray(observables, dtype=np.uint8)
    error_mechanisms = np.ascontiguousarray(error_mechanisms, dtype=np.uint8)

    expected_detection_shape = (config.shots, raw_dem.num_detectors)
    expected_observable_shape = (config.shots, raw_dem.num_observables)
    expected_error_shape = (config.shots, raw_dem.num_errors)
    if detections.shape != expected_detection_shape:
        raise RuntimeError(
            f"Unexpected detection shape {detections.shape}; "
            f"expected {expected_detection_shape}"
        )
    if observables.shape != expected_observable_shape:
        raise RuntimeError(
            f"Unexpected observable shape {observables.shape}; "
            f"expected {expected_observable_shape}"
        )
    if error_mechanisms.shape != expected_error_shape:
        raise RuntimeError(
            f"Unexpected error-mechanism shape {error_mechanisms.shape}; "
            f"expected {expected_error_shape}"
        )

    matching = pymatching.Matching.from_detector_error_model(matching_dem)
    predicted_observables = matching.decode_batch(detections)
    logical_errors = int(np.count_nonzero(np.any(predicted_observables != observables, axis=1)))

    return GeneratedDataset(
        config=config,
        circuit=circuit,
        raw_dem=raw_dem,
        matching_dem=matching_dem,
        detections=detections,
        observables=observables,
        error_mechanisms=error_mechanisms,
        matching_num_edges=int(matching.num_edges),
        matching_num_nodes=int(matching.num_nodes),
        logical_errors=logical_errors,
    )


def _sample_summary(dataset: GeneratedDataset) -> dict[str, Any]:
    return {
        "shots": dataset.shots,
        "detections": {
            "shape": list(dataset.detections.shape),
            "dtype": str(dataset.detections.dtype),
            "sha256": _sha256_array(dataset.detections),
            "mean_event_rate": float(dataset.detections.mean()),
        },
        "observables": {
            "shape": list(dataset.observables.shape),
            "dtype": str(dataset.observables.dtype),
            "sha256": _sha256_array(dataset.observables),
            "mean_flip_rate": float(dataset.observables.mean()),
        },
        "error_mechanisms": {
            "shape": list(dataset.error_mechanisms.shape),
            "dtype": str(dataset.error_mechanisms.dtype),
            "sha256": _sha256_array(dataset.error_mechanisms),
            "mean_mechanism_rate": float(dataset.error_mechanisms.mean()),
        },
    }


def build_manifest(dataset: GeneratedDataset) -> dict[str, Any]:
    """Builds a deterministic manifest without wall-clock timestamps."""

    raw_dem_text = str(dataset.raw_dem)
    matching_dem_text = str(dataset.matching_dem)
    circuit_text = str(dataset.circuit)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "M0",
        "config_sha256": dataset.config.sha256(),
        "config": dataset.config.to_dict(),
        "environment": {
            "python": platform.python_version(),
            "stim": stim.__version__,
            "pymatching": pymatching.__version__,
            "numpy": np.__version__,
        },
        "circuit": {
            "num_qubits": dataset.circuit.num_qubits,
            "num_detectors": dataset.circuit.num_detectors,
            "num_observables": dataset.circuit.num_observables,
            "num_ticks": dataset.circuit.num_ticks,
            "sha256": _sha256_text(circuit_text),
        },
        "detector_error_model": {
            "num_errors": dataset.raw_dem.num_errors,
            "num_detectors": dataset.raw_dem.num_detectors,
            "num_observables": dataset.raw_dem.num_observables,
            "sha256": _sha256_text(raw_dem_text),
            "decomposed_sha256": _sha256_text(matching_dem_text),
        },
        "samples": _sample_summary(dataset),
        "pymatching_smoke": {
            "decoded_shots": dataset.shots,
            "num_edges": dataset.matching_num_edges,
            "num_nodes": dataset.matching_num_nodes,
            "logical_errors": dataset.logical_errors,
            "logical_error_rate": dataset.logical_error_rate,
        },
    }


def save_dataset(dataset: GeneratedDataset, output_dir: str | Path) -> dict[str, Any]:
    """Writes a dataset directory and returns its manifest."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=False)

    _write_text(output_path / "circuit.stim", str(dataset.circuit))
    _write_text(output_path / "detector_error_model.dem", str(dataset.raw_dem))
    _write_text(
        output_path / "detector_error_model.decomposed.dem",
        str(dataset.matching_dem),
    )
    np.savez_compressed(
        output_path / "samples.npz",
        detections=dataset.detections,
        observables=dataset.observables,
        error_mechanisms=dataset.error_mechanisms,
    )

    manifest = build_manifest(dataset)
    with (output_path / "manifest.json").open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return manifest


def load_samples(output_dir: str | Path) -> dict[str, np.ndarray]:
    """Loads sample arrays from an artifact directory."""

    with np.load(Path(output_dir) / "samples.npz") as archive:
        return {name: archive[name] for name in archive.files}


def load_manifest(output_dir: str | Path) -> dict[str, Any]:
    """Loads an artifact manifest."""

    with (Path(output_dir) / "manifest.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


def verify_manifest(output_dir: str | Path) -> None:
    """Checks artifact hashes against the manifest, raising on mismatch."""

    artifact_dir = Path(output_dir)
    manifest = load_manifest(artifact_dir)
    samples = load_samples(artifact_dir)

    expected_sample_fields = {
        "detections": "detections",
        "observables": "observables",
        "error_mechanisms": "error_mechanisms",
    }
    for manifest_key, sample_key in expected_sample_fields.items():
        expected = manifest["samples"][manifest_key]["sha256"]
        actual = _sha256_array(samples[sample_key])
        if actual != expected:
            raise ValueError(
                f"Sample hash mismatch for {sample_key}: {actual} != {expected}"
            )

    text_artifacts = (
        ("circuit.stim", manifest["circuit"]["sha256"]),
        (
            "detector_error_model.dem",
            manifest["detector_error_model"]["sha256"],
        ),
        (
            "detector_error_model.decomposed.dem",
            manifest["detector_error_model"]["decomposed_sha256"],
        ),
    )
    for filename, expected in text_artifacts:
        actual = _sha256_text((artifact_dir / filename).read_text(encoding="utf-8"))
        if actual != expected:
            raise ValueError(
                f"Artifact hash mismatch for {filename}: {actual} != {expected}"
            )
