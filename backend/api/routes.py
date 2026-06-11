"""REST API endpoints for simulation control."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
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
    emergency_probability: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Probability that spawned vehicle is emergency",
    )
    phase_duration: int | None = Field(
        None, ge=1, le=20, description="Ticks per traffic light phase"
    )


# Router for simulation endpoints
router = APIRouter(prefix="/api/simulation", tags=["simulation"])


def get_engine(request: Request) -> SimulationEngine:
    """FastAPI dependency: get simulation engine from app state.

    Args:
        request: FastAPI request object (injected automatically).

    Returns:
        The configured SimulationEngine instance.

    Raises:
        HTTPException: 503 if engine is not configured on app state.
    """
    sim_engine = getattr(request.app.state, "engine", None)
    if sim_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Simulation engine is not configured.",
        )
    return sim_engine


EngineDependency = Annotated[SimulationEngine, Depends(get_engine)]
ConfigUpdateBody = Annotated[ConfigUpdateRequest, Body()]


def _control_response(result: ControlResult) -> dict[str, Any]:
    """Serialize a simulation control result for API clients."""
    return {
        "action": result.action,
        "applied": result.applied,
        "state": result.state.value,
        "message": result.message,
    }


@router.post("/start")
async def start_simulation(
    engine: EngineDependency,
) -> dict[str, Any]:
    """Initialize and start the simulation."""
    result = await engine.start()
    return _control_response(result)


@router.post("/pause")
def pause_simulation(
    engine: EngineDependency,
) -> dict[str, Any]:
    """Pause the tick loop."""
    result = engine.pause()
    return _control_response(result)


@router.post("/resume")
def resume_simulation(
    engine: EngineDependency,
) -> dict[str, Any]:
    """Resume the tick loop."""
    result = engine.resume()
    return _control_response(result)


@router.put("/config")
def update_config(
    engine: EngineDependency,
    config: ConfigUpdateBody,
) -> dict[str, Any]:
    """Update runtime simulation configuration.

    Accepts partial updates; only provided fields are changed.
    """
    updates = config.model_dump(exclude_none=True)

    if not updates:
        return {
            "message": "No configuration changes provided.",
            "config": engine.config.model_dump(),
        }
    try:
        if "tick_speed" in updates:
            engine.set_tick_speed(updates["tick_speed"])
        if "spawn_rate" in updates:
            engine.set_spawn_rate(updates["spawn_rate"])
        if "phase_duration" in updates:
            engine.set_phase_duration(updates["phase_duration"])
        if "emergency_probability" in updates:
            engine.set_emergency_probability(updates["emergency_probability"])
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return {
        "message": f"Updated: {', '.join(updates.keys())}.",
        "config": engine.config.model_dump(),
    }


@router.get("/state")
def get_state(
    engine: EngineDependency,
) -> dict[str, Any]:
    """Return current state snapshot as a polling fallback."""
    return serialize_snapshot(engine.snapshot())


@router.get("/metrics")
def get_metrics(
    engine: EngineDependency,
) -> dict[str, Any]:
    """Return current metrics."""
    return engine.get_metrics().to_dict()
