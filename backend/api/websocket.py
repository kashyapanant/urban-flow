"""WebSocket handler for real-time simulation updates."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol, TypeGuard

from fastapi import WebSocketDisconnect
from pydantic import ValidationError

from ..simulation.engine import SimulationEngine
from .serialization import serialize_snapshot

logger = logging.getLogger(__name__)


class WebSocketConnection(Protocol):
    """Minimal WebSocket interface used by the API layer."""

    async def accept(self) -> None: ...

    async def send_json(self, message: dict[str, Any]) -> None: ...

    async def receive_json(self) -> dict[str, Any]: ...


_SEND_TIMEOUT_SECONDS = 1.0

_RUNTIME_CONFIG_ERROR_MESSAGES = {
    "tick_speed": "tick_speed must be between 1 and 10.",
    "spawn_rate": "spawn_rate must be between 0.0 and 1.0.",
    "phase_duration": "phase_duration must be between 1 and 20.",
    "emergency_probability": "emergency_probability must be between 0.0 and 1.0.",
}


class WebSocketManager:
    """Manages WebSocket connections for real-time simulation updates."""

    def __init__(self) -> None:
        """Initialize the WebSocket manager."""
        self.active_connections: list[WebSocketConnection] = []
        self._send_locks: dict[WebSocketConnection, asyncio.Lock] = {}

    async def connect(self, websocket: WebSocketConnection) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self._send_locks[websocket] = asyncio.Lock()

    def disconnect(self, websocket: WebSocketConnection) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self._send_locks.pop(websocket, None)

    def _send_lock(self, websocket: WebSocketConnection) -> asyncio.Lock:
        """Return the per-connection lock used to serialize outbound sends."""
        lock = self._send_locks.get(websocket)
        if lock is None:
            lock = asyncio.Lock()
            self._send_locks[websocket] = lock
        return lock

    async def _send_serialized(
        self, websocket: WebSocketConnection, message: dict[str, Any]
    ) -> None:
        """Send a message while holding the socket's outbound send lock."""
        async with self._send_lock(websocket):
            await websocket.send_json(message)

    async def _send_serialized_with_timeout(
        self, websocket: WebSocketConnection, message: dict[str, Any]
    ) -> None:
        """Send a message with serialization and the broadcast timeout."""
        async with self._send_lock(websocket):
            await asyncio.wait_for(
                websocket.send_json(message),
                timeout=_SEND_TIMEOUT_SECONDS,
            )

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast message to all connected clients.

        Automatically removes stale connections that fail to receive.

        Args:
            message: JSON-serializable dict to broadcast.
        """

        async def send_to_connection(
            connection: WebSocketConnection,
        ) -> WebSocketConnection | None:
            try:
                await self._send_serialized_with_timeout(connection, message)
                return None
            except TimeoutError:
                logger.warning("WebSocket send timed out; dropping connection.")
                return connection
            except WebSocketDisconnect:
                logger.debug("Client disconnected during broadcast.")
                return connection
            except RuntimeError as exc:
                # Raised when WebSocket is closed but not formally disconnected
                logger.warning("WebSocket send failed (connection closed): %s", exc)
                return connection
            except Exception as exc:
                logger.error(
                    "Unexpected error broadcasting to WebSocket: %s", exc, exc_info=True
                )
                return connection

        connections = list(self.active_connections)
        if not connections:
            return

        results = await asyncio.gather(
            *(send_to_connection(connection) for connection in connections)
        )
        for connection in results:
            if connection is not None:
                self.disconnect(connection)

    async def send_personal_message(
        self, message: dict[str, Any], websocket: WebSocketConnection
    ) -> None:
        """Send a message to a specific client."""
        await self._send_serialized(websocket, message)


async def websocket_endpoint(
    websocket: WebSocketConnection,
    engine: SimulationEngine,
    manager: WebSocketManager,
) -> None:
    """WebSocket endpoint for real-time simulation communication."""
    await manager.connect(websocket)
    try:
        await manager.send_personal_message(_tick_message(engine), websocket)
        while True:
            message = await websocket.receive_json()
            response = await handle_client_message(message, engine)
            await manager.send_personal_message(response, websocket)
    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected.")
    except Exception as exc:
        logger.error("WebSocket error: %s", exc, exc_info=True)
        try:
            await manager.send_personal_message(_error_message(str(exc)), websocket)
        except Exception:
            logger.debug("Failed to send WebSocket error payload.", exc_info=True)
    finally:
        manager.disconnect(websocket)


async def handle_client_message(
    message: dict[str, Any], engine: SimulationEngine
) -> dict[str, Any]:
    """Handle a client command and return the outbound WebSocket payload.
    Args:
        message: Parsed JSON message from the client.
        engine: Simulation engine to apply commands to.

    Returns:
        Standard ``tick`` payload when the command succeeds, or a standard
        ``error`` payload when the message is invalid or runtime config
        validation fails.
    """
    if not isinstance(message, dict):
        return _error_message("WebSocket message must be a JSON object.")

    message_type = message.get("type")
    raw_data = message.get("data")
    data = {} if raw_data is None else raw_data
    if not isinstance(data, dict):
        return _error_message("WebSocket message data must be an object.")

    try:
        match message_type:
            case "pause":
                engine.pause()
            case "resume":
                engine.resume()
            case "set_speed":
                speed = data.get("speed")
                if not _is_strict_int(speed):
                    return _error_message("set_speed requires integer data.speed.")
                engine.set_tick_speed(speed)
            case "set_spawn_rate":
                rate = data.get("rate")
                if not _is_strict_number(rate):
                    return _error_message("set_spawn_rate requires numeric data.rate.")
                engine.set_spawn_rate(float(rate))
            case "set_emergency_probability":
                probability = data.get("probability")
                if not _is_strict_number(probability):
                    return _error_message(
                        "set_emergency_probability requires numeric data.probability."
                    )
                engine.set_emergency_probability(float(probability))
            case "set_phase_duration":
                duration = data.get("duration")
                if not _is_strict_int(duration):
                    return _error_message(
                        "set_phase_duration requires integer data.duration."
                    )
                engine.set_phase_duration(duration)
            case _:
                return _error_message(
                    f"Unsupported WebSocket message type: {message_type!r}."
                )
    except (ValidationError, ValueError) as exc:
        return _error_message(_format_runtime_config_error(exc))

    return _tick_message(engine)


def _is_strict_int(value: Any) -> TypeGuard[int]:
    """Return whether the value is exactly an int, excluding bool."""
    return type(value) is int


def _is_strict_number(value: Any) -> TypeGuard[int | float]:
    """Return whether the value is exactly an int or float, excluding bool."""
    return type(value) in (int, float)


def _tick_message(engine: SimulationEngine) -> dict[str, Any]:
    """Return a standard WebSocket tick payload for the current engine state."""
    return {"type": "tick", "data": serialize_snapshot(engine.snapshot())}


def _format_runtime_config_error(exc: ValidationError | ValueError) -> str:
    """Return a stable client-facing message for runtime config errors."""
    if isinstance(exc, ValidationError):
        for error in exc.errors():
            loc = error.get("loc")
            if isinstance(loc, tuple) and loc:
                field_name = loc[0]
                if isinstance(field_name, str):
                    message = _RUNTIME_CONFIG_ERROR_MESSAGES.get(field_name)
                    if message is not None:
                        return message
        return "Invalid simulation config value."

    message = str(exc).strip()
    return message or "Invalid simulation config value."


async def broadcast_simulation_state(
    engine: SimulationEngine, manager: WebSocketManager
) -> None:
    """Broadcast current simulation state to all connected clients."""
    await manager.broadcast(_tick_message(engine))


def _error_message(message: str) -> dict[str, Any]:
    """Return a standard WebSocket error payload."""
    return {"type": "error", "data": {"message": message}}
