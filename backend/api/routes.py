"""REST API endpoints for simulation control."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from ..simulation.engine import ControlResult, SimulationEngine
from .serialization import serialize_snapshot


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

# Global simulation engine instance (injected during app bootstrap)
engine: SimulationEngine | None = None


def set_engine(simulation_engine: SimulationEngine) -> None:
    """Set the global simulation engine instance."""
    global engine
    engine = simulation_engine


def get_engine() -> SimulationEngine:
    """Return the configured simulation engine or fail with a clear API error."""
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Simulation engine is not configured.",
        )
    return engine


def _control_response(result: ControlResult) -> dict[str, Any]:
    """Serialize a simulation control result for API clients."""
    return {
        "action": result.action,
        "applied": result.applied,
        "state": result.state.value,
        "message": result.message,
    }


@router.post("/start")
async def start_simulation() -> dict[str, Any]:
    """Initialize and start the simulation."""
    result = await get_engine().start()
    return _control_response(result)


@router.post("/pause")
def pause_simulation() -> dict[str, Any]:
    """Pause the tick loop."""
    result = get_engine().pause()
    return _control_response(result)


@router.post("/resume")
def resume_simulation() -> dict[str, Any]:
    """Resume the tick loop."""
    result = get_engine().resume()
    return _control_response(result)


@router.put("/config")
def update_config(config: ConfigUpdateRequest) -> dict[str, Any]:
    """Update runtime configuration."""
    simulation_engine = get_engine()
    updates = config.model_dump(exclude_none=True)

    if "tick_speed" in updates:
        simulation_engine.set_tick_speed(updates["tick_speed"])
    if "spawn_rate" in updates:
        simulation_engine.set_spawn_rate(updates["spawn_rate"])
    if "phase_duration" in updates:
        simulation_engine.set_phase_duration(updates["phase_duration"])

    return {
        "message": "Simulation configuration updated.",
        "config": simulation_engine.config.model_dump(),
    }


@router.get("/state")
def get_state() -> dict[str, Any]:
    """Return current state snapshot as a polling fallback."""
    return serialize_snapshot(get_engine().snapshot())


@router.get("/metrics")
def get_metrics() -> dict[str, Any]:
    """Return current metrics."""
    return get_engine().get_metrics().to_dict()
