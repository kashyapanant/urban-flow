"""Simulation configuration -- dataclass-based settings with sensible defaults."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SimulationConfig:
    """Top-level configuration for a simulation run.

    All values have sensible defaults so a simulation can be started
    with zero configuration.
    """

    # Grid dimensions
    grid_rows: int = 4
    grid_cols: int = 4
    road_length: int = 10

    # Time
    tick_duration_seconds: float = 1.0
    default_run_ticks: int = 500

    # Vehicle spawning
    spawn_probability: float = 0.3
    emergency_probability: float = 0.02

    # Signal timing (ticks)
    green_duration: int = 30
    yellow_duration: int = 5

    # Emergency preemption
    preemption_lookahead: int = 2
    detection_range: int = 20

    # Reproducibility
    seed: int | None = 42
