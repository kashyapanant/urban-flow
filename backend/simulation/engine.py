"""Core simulation engine that orchestrates the traffic simulation."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..config import SimulationConfig
from .metrics import Metrics


class SimulationState(Enum):
    """Current state of the simulation."""

    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


@dataclass
class SimulationSnapshot:
    """Complete state snapshot for frontend consumption."""

    tick_count: int
    state: str
    config: dict[str, Any]
    grid: dict[str, Any]
    vehicles: list[dict[str, Any]]
    traffic_lights: list[dict[str, Any]]
    metrics: dict[str, Any]


class SimulationEngine:
    """Core simulation engine that orchestrates all components.

    Manages the tick loop, coordinates all subsystems, and provides
    the main interface for simulation control.
    """

    def __init__(self, config: SimulationConfig | None = None):
        """Initialize the simulation engine.

        Args:
            config: Simulation configuration (uses defaults if None)
        """
        raise NotImplementedError("__init__()")

    async def start(self) -> None:
        """Start the simulation tick loop."""
        raise NotImplementedError("start()")

    async def stop(self) -> None:
        """Stop the simulation and clean up."""
        raise NotImplementedError("stop()")

    def pause(self) -> None:
        """Pause the simulation (can be resumed)."""
        raise NotImplementedError("pause()")

    def resume(self) -> None:
        """Resume a paused simulation."""
        raise NotImplementedError("resume()")

    def set_tick_speed(self, speed: int) -> None:
        """Set simulation tick speed (takes effect next tick).

        Args:
            speed: Ticks per second (1-10)
        """
        raise NotImplementedError("set_tick_speed()")

    def set_spawn_rate(self, rate: float) -> None:
        """Set vehicle spawn rate (takes effect next tick).

        Args:
            rate: Probability per edge cell per tick (0.0-1.0)
        """
        raise NotImplementedError("set_spawn_rate()")

    def set_phase_duration(self, duration: int) -> None:
        """Set traffic light phase duration (takes effect next tick).

        Args:
            duration: Ticks per phase (1-20)
        """
        raise NotImplementedError("set_phase_duration()")

    def snapshot(self) -> SimulationSnapshot:
        """Create a complete state snapshot for frontend consumption.

        Returns:
            Complete simulation state snapshot
        """
        raise NotImplementedError("snapshot()")

    def get_metrics(self) -> Metrics:
        """Get current simulation metrics.

        Returns:
            Current metrics object
        """
        raise NotImplementedError("get_metrics()")
