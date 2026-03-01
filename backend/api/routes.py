"""REST API endpoints for simulation control."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ..simulation.engine import SimulationEngine


class ConfigUpdateRequest(BaseModel):
    """Request model for updating simulation configuration."""

    tick_speed: int | None = None
    spawn_rate: float | None = None
    phase_duration: int | None = None


# Router for simulation endpoints
router = APIRouter(prefix="/api/simulation", tags=["simulation"])

# Global simulation engine instance (will be injected)
engine: SimulationEngine | None = None


def set_engine(simulation_engine: SimulationEngine) -> None:
    """Set the global simulation engine instance.

    Args:
        simulation_engine: The engine instance to use
    """
    pass


@router.post("/start")
async def start_simulation() -> dict[str, str]:
    """Initialize and start (or reset) the simulation.

    Returns:
        Status message
    """
    pass


@router.post("/pause")
def pause_simulation() -> dict[str, str]:
    """Pause the tick loop.

    Returns:
        Status message
    """
    pass


@router.post("/resume")
def resume_simulation() -> dict[str, str]:
    """Resume the tick loop.

    Returns:
        Status message
    """
    pass


@router.put("/config")
def update_config(config: ConfigUpdateRequest) -> dict[str, str]:
    """Update runtime configuration.

    Args:
        config: Configuration updates

    Returns:
        Status message
    """
    pass


@router.get("/state")
def get_state() -> dict[str, Any]:
    """Return current state snapshot (polling fallback).

    Returns:
        Current simulation state
    """
    pass


@router.get("/metrics")
def get_metrics() -> dict[str, Any]:
    """Return current metrics.

    Returns:
        Current simulation metrics
    """
    pass
