r"""M4: structural comparison of the detector graphs of each code family.

Usage:
    .\.venv\Scripts\python.exe scripts\m4_graph_structure.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from graph_qec.codes.hgp import small_hgp_codes
from graph_qec.config import ExperimentConfig
from graph_qec.data_pipeline import generate_dataset
from graph_qec.decoders import DEMSystem


def _hyperedge_sizes(check_matrix: np.ndarray) -> dict[str, int]:
    sizes = check_matrix.sum(axis=1)
    unique, counts = np.unique(sizes, return_counts=True)
    return {str(int(size)): int(count) for size, count in zip(unique, counts)}


def _four_cycles(check_matrix: np.ndarray) -> int:
    """Number of pairs of checks sharing at least two variables (a 4-cycle)."""

    overlap = check_matrix.astype(np.int64) @ check_matrix.T.astype(np.int64)
    np.fill_diagonal(overlap, 0)
    return int((overlap * (overlap - 1) // 2).sum() // 2)


def _summarize(check_matrix: np.ndarray) -> dict[str, Any]:
    check_degree = check_matrix.sum(axis=1)
    variable_degree = check_matrix.sum(axis=0)
    return {
        "num_detectors": int(check_matrix.shape[0]),
        "num_mechanisms": int(check_matrix.shape[1]),
        "num_edges": int(check_matrix.sum()),
        "check_degree_max": int(check_degree.max()) if check_degree.size else 0,
        "check_degree_mean": float(check_degree.mean()) if check_degree.size else 0.0,
        "check_degree_histogram": _hyperedge_sizes(check_matrix),
        "variable_degree_max": int(variable_degree.max()) if variable_degree.size else 0,
        "variable_degree_mean": float(variable_degree.mean()) if variable_degree.size else 0.0,
        "variable_degree_histogram": _hyperedge_sizes(check_matrix.T),
        "four_cycles": _four_cycles(check_matrix),
    }


def _circuit_entry(family: str, distance: int, rounds: int, model: str, p: float) -> dict[str, Any]:
    config = ExperimentConfig(
        name="structure", seed=1, family=family, distance=distance, rounds=rounds,
        noise_model=model, physical_error_rate=p, shots=64,
    )
    dataset = generate_dataset(config)
    system = DEMSystem.from_detector_error_model(dataset.raw_dem)
    entry = {"family": family, "noise_model": model, "p": p, "source": "stim_circuit"}
    entry.update(_summarize(system.check_matrix))
    try:
        import pymatching

        pymatching.Matching.from_detector_error_model(dataset.matching_dem)
        entry["matchable"] = True
    except Exception:  # noqa: BLE001 - any failure means "no matching decoder"
        entry["matchable"] = False
    return entry


def _hgp_entry(family: str, p: float) -> dict[str, Any]:
    code = small_hgp_codes()[family]
    dem = code.detector_error_model(p)
    system = DEMSystem.from_detector_error_model(dem)
    entry = {
        "family": family,
        "noise_model": "code_capacity",
        "p": p,
        "source": "hgp_dem",
        "code_parameters": code.summary(),
        "matchable": False,
        "num_qubits": code.num_qubits,
        "k": code.k,
    }
    entry.update(_summarize(system.check_matrix))
    return entry


def build_entries() -> list[dict[str, Any]]:
    entries = [
        _circuit_entry("repetition_code", 3, 3, "circuit_level", 0.01),
        _circuit_entry("rotated_surface_code", 3, 3, "code_capacity", 0.005),
        _circuit_entry("rotated_surface_code", 3, 3, "circuit_level", 0.005),
        _circuit_entry("rotated_surface_code", 5, 5, "circuit_level", 0.005),
        _hgp_entry("hgp_rep3x3", 0.05),
        _hgp_entry("hgp_hamming7x7", 0.05),
    ]
    return entries


def render(entries: Sequence[dict[str, Any]]) -> str:
    lines = [
        "# M4 detector-graph structure comparison",
        "",
        "| code | noise | detectors | mechanisms | edges | check deg max/mean | variable deg max/mean | 4-cycles | matchable |",
        "|---|---|---:|---:|---:|---|---|---:|---|",
    ]
    for entry in entries:
        lines.append(
            "| {family} | {noise_model} | {num_detectors} | {num_mechanisms} | {num_edges} | "
            "{check_degree_max} / {check_degree_mean:.2f} | {variable_degree_max} / "
            "{variable_degree_mean:.2f} | {four_cycles} | {matchable} |".format(**entry)
        )
    lines.append("")
    lines.append("Check-degree histograms (degree -> number of detectors):")
    lines.append("")
    for entry in entries:
        lines.append(
            "- **{family}** ({noise_model}): {check_degree_histogram}".format(**entry)
        )
    lines.append("")
    lines.append(
        "`matchable` records whether a minimum-weight matching decoder applies at all "
        "(surface codes decompose into a degree-<=2 matching graph; HGP codes do not)."
    )
    lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare detector-graph structure across code families.")
    parser.add_argument("--output-dir", type=Path, default=Path("results/m4"))
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    entries = build_entries()
    (args.output_dir / "graph_structure.json").write_text(
        json.dumps(entries, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown = args.output_dir / "GRAPH_STRUCTURE.md"
    markdown.write_text(render(entries), encoding="utf-8")
    print(render(entries))
    print("wrote", markdown.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
