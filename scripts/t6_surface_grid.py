"""T6 grid driver: rotated-surface-code d=5 / d=7 GNN reweighting sweep.

Generates per-(distance, noise rate, seed) M2 configurations and runs them
sequentially through the M2 pipeline.

Properties
----------
* Resumable: an existing output directory means the run is skipped.
* Priority ordered: points are emitted most-valuable-first (headline p=0.005
  at both distances, three seeds) so a partial run is still a valid dataset.
* Budget bounded: ``--budget-minutes`` stops *starting* new runs once the
  elapsed time exceeds the budget (the in-flight run always finishes).
* Per-run logs under ``results/logs/`` and an append-only progress log.

Usage
-----
    .venv\\Scripts\\python.exe scripts\\t6_surface_grid.py --print-plan
    .venv\\Scripts\\python.exe scripts\\t6_surface_grid.py --budget-minutes 780
    .venv\\Scripts\\python.exe scripts\\t6_surface_grid.py --only d5
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO / "configs" / "t6"
OUT_DIR = REPO / "results" / "m4_surface"
LOG_DIR = REPO / "results" / "logs"
PROGRESS_LOG = LOG_DIR / "t6_progress.log"

#: Noise rates in priority order (headline first).
RATES = (0.005, 0.003, 0.008, 0.01, 0.002)

DISTANCE_SETTINGS = {
    5: dict(rounds=5, train_shots=8192, val_shots=2048, test_shots=8192, epochs=4, batch_size=128),
    7: dict(rounds=7, train_shots=4096, val_shots=1024, test_shots=4096, epochs=2, batch_size=128),
}

SEED_SCHEME = {
    1: dict(train=[101, 102], val=[201], test=[301], training_seed=7, experiment_seed=20261013),
    2: dict(train=[103, 104], val=[202], test=[302], training_seed=17, experiment_seed=20261023),
    3: dict(train=[105, 106], val=[203], test=[303], training_seed=27, experiment_seed=20261033),
}


def rate_tag(p: float) -> str:
    return f"{p:g}".replace(".", "p")


def config_name(distance: int, seed_index: int) -> str:
    return f"m4_rotated_surface_code_circuit_level_d{distance}_s{seed_index}"


def artifact_name(distance: int, p: float, seed_index: int) -> str:
    return f"{config_name(distance, seed_index)}__d{distance}__circuit_level__p{rate_tag(p)}"


def build_config(distance: int, p: float, seed_index: int) -> dict:
    s = DISTANCE_SETTINGS[distance]
    scheme = SEED_SCHEME[seed_index]
    return {
        "schema_version": 1,
        "name": config_name(distance, seed_index),
        "experiment": {
            "name": "surface",
            "seed": scheme["experiment_seed"] + distance,
            "code": {"family": "rotated_surface_code", "distance": distance, "rounds": s["rounds"]},
            "noise": {"model": "circuit_level", "physical_error_rate": p},
            "sampling": {"shots": s["train_shots"]},
        },
        "splits": {
            "train_seeds": scheme["train"],
            "validation_seeds": scheme["val"],
            "test_seeds": scheme["test"],
            "train_shots": s["train_shots"],
            "validation_shots": s["val_shots"],
            "test_shots": s["test_shots"],
        },
        "model": {"hidden_size": 32, "num_layers": 3, "dropout": 0.0},
        "training": {
            "epochs": s["epochs"],
            "batch_size": s["batch_size"],
            "learning_rate": 0.002,
            "weight_decay": 0.0,
            "seed": scheme["training_seed"],
            "max_grad_norm": 1.0,
            "torch_threads": 6,
        },
        "decoder": {
            "max_iterations": 32,
            "min_sum_scaling": 0.75,
            "damping": 0.0,
            "reweight_strengths": [0.0, 0.25, 0.5, 0.75, 1.0],
        },
        "benchmark": {
            "decoders": ["mwpm", "bp", "bp_osd", "bp_gnn", "bp_gnn_osd"],
            "timed_runs": 1,
        },
    }


def build_plan(only: str | None) -> list[tuple[int, float, int]]:
    distances = {"d5": (5,), "d7": (7,), None: (5, 7)}[only]
    plan: list[tuple[int, float, int]] = []
    for p in RATES:
        for distance in distances:
            for seed_index in (1, 2, 3):
                plan.append((distance, p, seed_index))
    return plan


def write_config(distance: int, p: float, seed_index: int) -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path = CONFIG_DIR / f"{config_name(distance, seed_index)}__p{rate_tag(p)}.json"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(build_config(distance, p, seed_index), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    with PROGRESS_LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["d5", "d7"], default=None)
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--budget-minutes", type=float, default=780.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    plan = build_plan(args.only)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.print_plan:
        for distance, p, seed_index in plan:
            done = (OUT_DIR / artifact_name(distance, p, seed_index)).exists()
            print(f"d={distance} p={p:<6g} seed={seed_index}  {'[done]' if done else '[pending]'}")
        return 0

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO / "src")
    env["PYTHONUTF8"] = "1"

    started = time.perf_counter()
    completed = 0
    total = len(plan)
    for index, (distance, p, seed_index) in enumerate(plan, start=1):
        tag = f"d{distance}_p{rate_tag(p)}_s{seed_index}"
        out = OUT_DIR / artifact_name(distance, p, seed_index)
        if out.exists():
            log(f"[{index}/{total}] {tag}: skip (result exists)")
            continue

        elapsed_min = (time.perf_counter() - started) / 60.0
        if completed and elapsed_min >= args.budget_minutes:
            log(f"[{index}/{total}] {tag}: budget {args.budget_minutes:g} min reached "
                f"({elapsed_min:.1f} min elapsed, {completed} runs); stopping")
            break

        cfg_path = write_config(distance, p, seed_index)
        run_log = LOG_DIR / f"t6_{tag}.log"
        log(f"[{index}/{total}] {tag}: start -> {out.name}")
        if args.dry_run:
            log(f"[{index}/{total}] {tag}: dry-run, skipping execution")
            continue

        command = [sys.executable, "-m", "graph_qec.m2", "--config", str(cfg_path),
                   "--output-dir", str(OUT_DIR)]
        run_started = time.perf_counter()
        with run_log.open("w", encoding="utf-8") as handle:
            handle.write(" ".join(command) + "\n\n")
            handle.flush()
            code = subprocess.call(command, cwd=REPO, env=env, stdout=handle, stderr=subprocess.STDOUT)
        run_minutes = (time.perf_counter() - run_started) / 60.0
        completed += 1
        if code != 0 or not out.exists():
            log(f"[{index}/{total}] {tag}: FAILED exit={code} after {run_minutes:.1f} min "
                f"(see {run_log.name})")
        else:
            log(f"[{index}/{total}] {tag}: done in {run_minutes:.1f} min")

    log(f"grid finished: {completed} runs executed, {total} points in plan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
