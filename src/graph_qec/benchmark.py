"""LER, latency, throughput, and memory benchmarking for M1 decoders."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import math
import os
from pathlib import Path
import platform
import threading
import time
import tracemalloc
from typing import Any

import numpy as np
import stim

from .benchmark_config import BenchmarkConfig
from .data_pipeline import GeneratedDataset
from .decoders import (
    DEMSystem,
    BPDecoder,
    BPOSDDecoder,
    DecodeResult,
    Decoder,
    MWPMDecoder,
    UnionFindDecoder,
)


_SYSTEM = platform.system()

if _SYSTEM == "Windows":
    class _ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _PSAPI = ctypes.WinDLL("psapi", use_last_error=True)
    _KERNEL32.GetCurrentProcess.restype = wintypes.HANDLE
    _PSAPI.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_ProcessMemoryCounters),
        wintypes.DWORD,
    ]
    _PSAPI.GetProcessMemoryInfo.restype = wintypes.BOOL


def _current_rss_bytes() -> int | None:
    if _SYSTEM == "Windows":
        counters = _ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        process = _KERNEL32.GetCurrentProcess()
        success = _PSAPI.GetProcessMemoryInfo(
            process, ctypes.byref(counters), counters.cb
        )
        return int(counters.WorkingSetSize) if success else None

    if _SYSTEM == "Linux":
        try:
            resident_pages = int(Path("/proc/self/statm").read_text().split()[1])
            return resident_pages * int(os.sysconf("SC_PAGE_SIZE"))
        except (OSError, ValueError, IndexError):
            return None

    return None


class _MemorySampler:
    """Samples current process working-set size while an operation runs."""

    def __init__(self, interval_seconds: float = 0.001) -> None:
        self.interval_seconds = interval_seconds
        self.start_rss = _current_rss_bytes()
        self.peak_rss = self.start_rss
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _sample(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            current = _current_rss_bytes()
            if current is not None:
                self.peak_rss = max(self.peak_rss, current)

    def __enter__(self) -> "_MemorySampler":
        if self.start_rss is not None:
            self._thread = threading.Thread(target=self._sample, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        current = _current_rss_bytes()
        if current is not None:
            self.peak_rss = max(self.peak_rss or 0, current)


def _decoder_factory(
    name: str,
    raw_dem: stim.DetectorErrorModel,
    matching_dem: stim.DetectorErrorModel,
    parameters: dict[str, Any],
) -> Decoder:
    if name == "mwpm":
        return MWPMDecoder(matching_dem)
    if name == "union_find":
        return UnionFindDecoder(matching_dem)
    if name == "bp":
        return BPDecoder(raw_dem, **parameters)
    if name == "bp_osd":
        return BPOSDDecoder(raw_dem, **parameters)
    raise ValueError(f"Unsupported decoder: {name!r}")


def _sha256_array(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def _json_diagnostics(diagnostics: dict[str, Any]) -> dict[str, Any]:
    serialized: dict[str, Any] = {}
    for key, value in diagnostics.items():
        if isinstance(value, np.generic):
            serialized[key] = value.item()
        elif isinstance(value, (int, float, str, bool)) or value is None:
            serialized[key] = value
        else:
            serialized[key] = str(value)
    return serialized


def _time_decode(
    decoder: Decoder,
    detections: np.ndarray,
    timed_runs: int,
) -> tuple[list[float], DecodeResult]:
    run_seconds: list[float] = []
    result: DecodeResult | None = None
    for _ in range(timed_runs):
        start = time.perf_counter_ns()
        result = decoder.decode_batch(detections)
        run_seconds.append((time.perf_counter_ns() - start) / 1_000_000_000.0)
    assert result is not None
    return run_seconds, result


def _measure_memory(decoder: Decoder, detections: np.ndarray) -> dict[str, int | None]:
    tracemalloc.start()
    sampler = _MemorySampler()
    with sampler:
        decoder.decode_batch(detections)
    _, peak_python_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_rss_delta = None
    if sampler.start_rss is not None and sampler.peak_rss is not None:
        peak_rss_delta = max(0, sampler.peak_rss - sampler.start_rss)
    return {
        "start_rss_bytes": sampler.start_rss,
        "peak_rss_bytes": sampler.peak_rss,
        "peak_rss_delta_bytes": peak_rss_delta,
        "peak_python_bytes": int(peak_python_bytes),
    }


def benchmark_decoder(
    name: str,
    dataset: GeneratedDataset,
    config: BenchmarkConfig,
    detections: np.ndarray,
    observables: np.ndarray,
) -> dict[str, Any]:
    parameters = dict(config.decoder_parameters.get(name, {}))
    decoder = _decoder_factory(
        name,
        dataset.raw_dem,
        dataset.matching_dem,
        parameters,
    )

    for _ in range(config.warmup_runs):
        decoder.decode_batch(detections)

    run_seconds, accuracy_result = _time_decode(
        decoder, detections, config.timed_runs
    )
    predictions = accuracy_result.predictions
    logical_errors = int(np.count_nonzero(np.any(predictions != observables, axis=1)))
    shots = detections.shape[0]
    logical_error_rate = logical_errors / shots
    standard_error = math.sqrt(
        logical_error_rate * (1.0 - logical_error_rate) / shots
    )
    memory = _measure_memory(decoder, detections)

    diagnostics = _json_diagnostics(accuracy_result.diagnostics)
    if accuracy_result.corrections is not None:
        system = DEMSystem.from_detector_error_model(dataset.raw_dem)
        residual = (
            system.check_matrix.astype(np.int64)
            @ accuracy_result.corrections.T.astype(np.int64)
        ) % 2
        consistent_shots = int(np.count_nonzero(np.all(residual.T == detections, axis=1)))
        diagnostics["syndrome_consistent_shots"] = consistent_shots
        diagnostics["syndrome_consistency_rate"] = consistent_shots / shots

    mean_seconds = float(np.mean(run_seconds))
    return {
        "decoder": name,
        "parameters": parameters,
        "shots": shots,
        "logical_errors": logical_errors,
        "logical_error_rate": logical_error_rate,
        "logical_error_rate_standard_error": standard_error,
        "prediction_sha256": _sha256_array(predictions),
        "latency": {
            "timed_runs": config.timed_runs,
            "run_seconds": run_seconds,
            "mean_total_seconds": mean_seconds,
            "mean_per_shot_microseconds": mean_seconds * 1_000_000.0 / shots,
            "throughput_shots_per_second": shots / mean_seconds,
        },
        "memory": memory,
        "diagnostics": diagnostics,
    }


def run_benchmark(
    dataset: GeneratedDataset,
    config: BenchmarkConfig,
) -> dict[str, Any]:
    shots = dataset.shots
    if config.max_shots is not None:
        shots = min(shots, config.max_shots)
    detections = dataset.detections[:shots]
    observables = dataset.observables[:shots]

    decoder_results = [
        benchmark_decoder(
            decoder_name,
            dataset,
            config,
            detections,
            observables,
        )
        for decoder_name in config.decoders
    ]
    return {
        "schema_version": 1,
        "stage": "M1",
        "benchmark_name": config.name,
        "config_sha256": config.sha256(),
        "config": config.to_dict(),
        "dataset": {
            "shots": shots,
            "num_detectors": dataset.raw_dem.num_detectors,
            "num_dem_errors": dataset.raw_dem.num_errors,
            "num_observables": dataset.raw_dem.num_observables,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "stim": stim.__version__,
        },
        "decoders": decoder_results,
    }
