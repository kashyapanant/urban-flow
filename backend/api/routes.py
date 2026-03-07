"""REST API endpoints for simulation control."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from ..simulation.engine import SimulationEngine


class ConfigUpdateRequest(BaseModel):
    """Request model for updating simulation configuration."""

    model_config = ConfigDict(extra="forbid")

    tick_speed: int | None = Field(None, ge=1, le=10, description="Ticks per second")
    spawn_rate: float | None = Field(
        None, ge=0.0, le=1.0, description="Probability per edge cell per tick"
    )
    phase_duration: int | None = Field(
        None, ge=1, le=20, description="Ticks per traffic light phase"
    )


# Router for simulation endpoints
router = APIRouter(prefix="/api/simulation", tags=["simulation"])

# Global simulation engine instance (will be injected)
engine: SimulationEngine | None = None


def set_engine(simulation_engine: SimulationEngine) -> None:
    """Set the global simulation engine instance.

    Args:
        simulation_engine: The engine instance to use
    """
    raise NotImplementedError("set_engine(")


@router.post("/start")
async def start_simulation() -> dict[str, str]:
    """Initialize and start (or reset) the simulation.

    Returns:
        Status message
    """
    raise NotImplementedError("start_simulation(")


@router.post("/pause")
def pause_simulation() -> dict[str, str]:
    """Pause the tick loop.

    Returns:
        Status message
    """
    raise NotImplementedError("pause_simulation(")


@router.post("/resume")
def resume_simulation() -> dict[str, str]:
    """Resume the tick loop.

    Returns:
        Status message
    """
    raise NotImplementedError("resume_simulation(")


@router.put("/config")
def update_config(config: ConfigUpdateRequest) -> dict[str, str]:
    """Update runtime configuration.

    Args:
        config: Configuration updates

    Returns:
        Status message
    """
    raise NotImplementedError("update_config(")


@router.get("/state")
def get_state() -> dict[str, Any]:
    """Return current state snapshot (polling fallback).

    Returns:
        Current simulation state
    """
    raise NotImplementedError("get_state(")


@router.get("/metrics")
def get_metrics() -> dict[str, Any]:
    """Return current metrics.

    Returns:
        Current simulation metrics
    """
    raise NotImplementedError("get_metrics(")
