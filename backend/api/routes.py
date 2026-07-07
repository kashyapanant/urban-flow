"""REST API endpoints for simulation control."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictInt

from ..simulation.engine import ControlResult, SimulationEngine
from .serialization import serialize_snapshot


def _require_number(value: Any) -> Any:
    """Accept only real numeric JSON values, excluding booleans and strings."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("Numeric config fields require int or float values.")
    return value


StrictNumericFloat = Annotated[float, BeforeValidator(_require_number)]


class ConfigUpdateRequest(BaseModel):
    """Request model for updating simulation configuration."""

    model_config = ConfigDict(extra="forbid")

    tick_speed: StrictInt | None = Field(
        None, ge=1, le=10, description="Ticks per second"
    )
    spawn_rate: StrictNumericFloat | None = Field(
        None, ge=0.0, le=1.0, description="Probability per edge cell per tick"
    )
    emergency_probability: StrictNumericFloat | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Probability that spawned vehicle is emergency",
    )
    phase_duration: StrictInt | None = Field(
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


async def _broadcast_snapshot(request: Request, engine: SimulationEngine) -> None:
    """Broadcast the current engine snapshot when a websocket manager exists."""
    ws_manager = getattr(request.app.state, "ws_manager", None)
    if ws_manager is None:
        return
    await ws_manager.broadcast(
        {"type": "tick", "data": serialize_snapshot(engine.snapshot())}
    )


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
    request: Request,
    engine: EngineDependency,
) -> dict[str, Any]:
    """Initialize and start the simulation."""
    result = await engine.start()
    await _broadcast_snapshot(request, engine)
    return _control_response(result)


@router.post("/reset")
async def reset_simulation(
    request: Request,
    engine: EngineDependency,
) -> dict[str, Any]:
    """Reset the simulation world and leave it stopped."""
    result = await engine.reset()
    await _broadcast_snapshot(request, engine)
    return _control_response(result)


@router.post("/config/reset")
async def reset_config(
    request: Request,
    engine: EngineDependency,
) -> dict[str, Any]:
    """Restore runtime configuration defaults without changing lifecycle."""
    engine.reset_config()
    await _broadcast_snapshot(request, engine)
    return {
        "message": "Configuration reset to defaults.",
        "config": engine.config.model_dump(),
    }


@router.post("/pause")
async def pause_simulation(
    request: Request,
    engine: EngineDependency,
) -> dict[str, Any]:
    """Pause the tick loop."""
    result = engine.pause()
    await _broadcast_snapshot(request, engine)
    return _control_response(result)


@router.post("/resume")
async def resume_simulation(
    request: Request,
    engine: EngineDependency,
) -> dict[str, Any]:
    """Resume the tick loop."""
    result = engine.resume()
    await _broadcast_snapshot(request, engine)
    return _control_response(result)


@router.put("/config")
async def update_config(
    request: Request,
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
        engine.update_config(**updates)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    await _broadcast_snapshot(request, engine)
    return {
        "message": f"Updated: {', '.join(updates.keys())}.",
        "config": engine.config.model_dump(),
    }


@router.get("/state")
async def get_state(
    engine: EngineDependency,
) -> dict[str, Any]:
    """Return current state snapshot as a polling fallback."""
    return serialize_snapshot(engine.snapshot())


@router.get("/metrics")
async def get_metrics(
    engine: EngineDependency,
) -> dict[str, Any]:
    """Return current metrics."""
    return engine.get_metrics().to_dict()
