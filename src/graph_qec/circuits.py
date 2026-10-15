"""Stim circuit construction for supported code families."""

from __future__ import annotations

import stim

from .config import HGP_FAMILIES, ExperimentConfig


def build_repetition_circuit(config: ExperimentConfig) -> stim.Circuit:
    """Builds a repetition-code memory experiment for one noise model.

    ``code_capacity`` applies data depolarization only. ``circuit_level``
    additionally applies gate, measurement, and reset noise at the same rate.
    """

    p = config.physical_error_rate
    noise_kwargs: dict[str, float] = {}
    if config.noise_model == "code_capacity":
        noise_kwargs["before_round_data_depolarization"] = p
    elif config.noise_model == "circuit_level":
        noise_kwargs.update(
            {
                "after_clifford_depolarization": p,
                "before_round_data_depolarization": p,
                "before_measure_flip_probability": p,
                "after_reset_flip_probability": p,
            }
        )
    else:  # Defensive guard if callers bypass ExperimentConfig validation.
        raise ValueError(f"Unsupported noise model: {config.noise_model!r}")

    return stim.Circuit.generated(
        "repetition_code:memory",
        distance=config.distance,
        rounds=config.rounds,
        **noise_kwargs,
    )


def _noise_kwargs(config: ExperimentConfig) -> dict[str, float]:
    """Maps the configured noise model onto Stim's generated-circuit knobs."""

    p = config.physical_error_rate
    if config.noise_model == "code_capacity":
        return {"before_round_data_depolarization": p}
    if config.noise_model == "circuit_level":
        return {
            "after_clifford_depolarization": p,
            "before_round_data_depolarization": p,
            "before_measure_flip_probability": p,
            "after_reset_flip_probability": p,
        }
    # Defensive guard if callers bypass ExperimentConfig validation.
    raise ValueError(f"Unsupported noise model: {config.noise_model!r}")


def build_rotated_surface_code_circuit(config: ExperimentConfig) -> stim.Circuit:
    """Builds a rotated surface code Z-memory experiment for one noise model.

    The logical observable is the final Z-memory parity, so a logical error is
    a logical-X flip. Circuit-level noise uses the same four Stim knobs as the
    repetition code, which keeps the M1/M2 comparisons apples-to-apples.
    """

    return stim.Circuit.generated(
        "surface_code:rotated_memory_z",
        distance=config.distance,
        rounds=config.rounds,
        **_noise_kwargs(config),
    )


def build_circuit(config: ExperimentConfig) -> stim.Circuit:
    """Dispatches circuit construction by code family."""

    if config.family == "repetition_code":
        return build_repetition_circuit(config)
    if config.family == "rotated_surface_code":
        return build_rotated_surface_code_circuit(config)
    if config.family in HGP_FAMILIES:
        raise ValueError(
            f"{config.family!r} is a detector-error-model-level code family (M4); "
            "it has no Stim circuit. Build its dataset with graph_qec.m4 instead."
        )
    raise ValueError(f"Unsupported code family: {config.family!r}")
