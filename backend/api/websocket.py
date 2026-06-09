"""WebSocket handler for real-time simulation updates."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from ..simulation.engine import SimulationEngine


class WebSocketManager:
    """Manages WebSocket connections for real-time simulation updates."""

    def __init__(self) -> None:
        """Initialize the WebSocket manager."""
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        stale_connections: list[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                stale_connections.append(connection)

        for connection in stale_connections:
            self.disconnect(connection)

    async def send_personal_message(
        self, message: dict[str, Any], websocket: WebSocket
    ) -> None:
        """Send a message to a specific client."""
        await websocket.send_json(message)


# Global WebSocket manager instance
manager = WebSocketManager()


async def websocket_endpoint(websocket: WebSocket, engine: SimulationEngine) -> None:
    """WebSocket endpoint for real-time simulation communication."""
    await manager.connect(websocket)
    try:
        await broadcast_simulation_state(engine)
        while True:
            message = await websocket.receive_json()
            response = await handle_client_message(message, engine)
            if response is not None:
                await manager.send_personal_message(response, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        await manager.send_personal_message(_error_message(str(exc)), websocket)
        manager.disconnect(websocket)


async def handle_client_message(
    message: dict[str, Any], engine: SimulationEngine
) -> dict[str, Any] | None:
    """Handle incoming messages from WebSocket clients."""
    if not isinstance(message, dict):
        return _error_message("WebSocket message must be a JSON object.")

    message_type = message.get("type")
    data = message.get("data") or {}
    if not isinstance(data, dict):
        return _error_message("WebSocket message data must be an object.")

    match message_type:
        case "pause":
            engine.pause()
        case "resume":
            engine.resume()
        case "set_speed":
            speed = data.get("speed")
            if not isinstance(speed, int):
                return _error_message("set_speed requires integer data.speed.")
            engine.set_tick_speed(speed)
        case "set_spawn_rate":
            rate = data.get("rate")
            if not isinstance(rate, int | float):
                return _error_message("set_spawn_rate requires numeric data.rate.")
            engine.set_spawn_rate(float(rate))
        case "set_phase_duration":
            duration = data.get("duration")
            if not isinstance(duration, int):
                return _error_message(
                    "set_phase_duration requires integer data.duration."
                )
            engine.set_phase_duration(duration)
        case _:
            return _error_message(
                f"Unsupported WebSocket message type: {message_type!r}."
            )

    return None


async def broadcast_simulation_state(engine: SimulationEngine) -> None:
    """Broadcast current simulation state to all connected clients."""
    await manager.broadcast({"type": "tick", "data": asdict(engine.snapshot())})


def _error_message(message: str) -> dict[str, Any]:
    """Return a standard WebSocket error payload."""
    return {"type": "error", "data": {"message": message}}
