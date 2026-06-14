"""Tests for WebSocket management and command handling."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import pytest
from fastapi import WebSocketDisconnect

from backend.api.serialization import serialize_snapshot
from backend.api.websocket import (
    WebSocketManager,
    broadcast_simulation_state,
    handle_client_message,
    websocket_endpoint,
)
from backend.config import STREET_SPACING
from backend.simulation.engine import SimulationEngine, SimulationState


class FakeWebSocket:
    """Small WebSocket test double for manager unit tests."""

    def __init__(
        self,
        *,
        send_exception: Exception | None = None,
        received_messages: list[dict[str, Any]] | None = None,
        receive_exception: Exception | None = None,
    ) -> None:
        self.accepted = False
        self.sent_messages: list[dict[str, Any]] = []
        self.send_exception = send_exception
        self.received_messages = list(received_messages or [])
        self.receive_exception = receive_exception

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, message: dict[str, Any]) -> None:
        if self.send_exception is not None:
            raise self.send_exception
        self.sent_messages.append(message)

    async def receive_json(self) -> dict[str, Any]:
        if self.receive_exception is not None:
            raise self.receive_exception
        if self.received_messages:
            return self.received_messages.pop(0)
        raise WebSocketDisconnect()


class SnapshotState(Enum):
    """Enum used to prove API snapshots are encoded as JSON values."""

    RUNNING = "running"


@dataclass
class SnapshotWithEnum:
    """Snapshot test double with an enum field at the API boundary."""

    tick_count: int
    state: SnapshotState
    config: dict[str, Any]
    grid: dict[str, Any]
    vehicles: list[dict[str, Any]]
    traffic_lights: list[dict[str, Any]]
    metrics: dict[str, Any]


class TestWebSocketManager:
    """Test cases for WebSocket connection management and commands."""

    @pytest.mark.asyncio
    async def test_manager_connect_disconnect_and_broadcast(self) -> None:
        """Connected clients receive broadcast JSON messages."""
        websocket_manager = WebSocketManager()
        websocket = FakeWebSocket()

        await websocket_manager.connect(websocket)
        await websocket_manager.broadcast({"type": "tick", "data": {"tick_count": 1}})
        websocket_manager.disconnect(websocket)

        assert websocket.accepted is True
        assert websocket.sent_messages == [{"type": "tick", "data": {"tick_count": 1}}]
        assert websocket_manager.active_connections == []

    @pytest.mark.asyncio
    async def test_manager_drops_failed_connections_during_broadcast(self) -> None:
        """Broadcast removes sockets that fail while sending."""
        websocket_manager = WebSocketManager()
        healthy = FakeWebSocket()
        failing = FakeWebSocket(send_exception=RuntimeError("client disconnected"))
        await websocket_manager.connect(healthy)
        await websocket_manager.connect(failing)

        await websocket_manager.broadcast({"type": "tick", "data": {"tick_count": 2}})

        assert healthy.sent_messages == [{"type": "tick", "data": {"tick_count": 2}}]
        assert websocket_manager.active_connections == [healthy]

    @pytest.mark.asyncio
    async def test_manager_drops_disconnected_connections_during_broadcast(
        self,
    ) -> None:
        """Broadcast removes sockets that disconnect during send."""
        websocket_manager = WebSocketManager()
        healthy = FakeWebSocket()
        disconnecting = FakeWebSocket(send_exception=WebSocketDisconnect())
        await websocket_manager.connect(healthy)
        await websocket_manager.connect(disconnecting)

        await websocket_manager.broadcast({"type": "tick", "data": {"tick_count": 3}})

        assert healthy.sent_messages == [{"type": "tick", "data": {"tick_count": 3}}]
        assert websocket_manager.active_connections == [healthy]

    @pytest.mark.asyncio
    async def test_manager_drops_unexpected_error_connections_during_broadcast(
        self,
    ) -> None:
        """Broadcast removes sockets that raise unexpected send exceptions."""
        websocket_manager = WebSocketManager()
        healthy = FakeWebSocket()
        failing = FakeWebSocket(send_exception=ValueError("unexpected send failure"))
        await websocket_manager.connect(healthy)
        await websocket_manager.connect(failing)

        await websocket_manager.broadcast({"type": "tick", "data": {"tick_count": 4}})

        assert healthy.sent_messages == [{"type": "tick", "data": {"tick_count": 4}}]
        assert websocket_manager.active_connections == [healthy]

    @pytest.mark.asyncio
    async def test_broadcast_simulation_state_sends_tick_message(self) -> None:
        """Simulation snapshots are wrapped in the agreed tick message shape."""
        websocket_manager = WebSocketManager()
        websocket = FakeWebSocket()
        await websocket_manager.connect(websocket)
        engine = SimulationEngine()

        await broadcast_simulation_state(engine, websocket_manager)

        expected_cells = []
        for y in range(engine.config.grid_height):
            row = []
            for x in range(engine.config.grid_width):
                is_street = y % STREET_SPACING == 0
                is_avenue = x % STREET_SPACING == 0
                is_intersection = is_street and is_avenue
                cell_type = (
                    "intersection"
                    if is_intersection
                    else "road"
                    if is_street or is_avenue
                    else "obstacle"
                )
                row.append(
                    {
                        "x": x,
                        "y": y,
                        "type": cell_type,
                        "vehicle_id": None,
                        "traffic_light_id": f"tl-{x}-{y}" if is_intersection else None,
                    }
                )
            expected_cells.append(row)

        expected_lights = [
            {
                "id": f"tl-{x}-{y}",
                "position": [x, y],
                "active_axis": "north_south",
                "current_phase": "green",
                "phase_duration": engine.config.phase_duration,
                "ticks_in_phase": 0,
                "preempted_by": None,
            }
            for y in range(0, engine.config.grid_height, STREET_SPACING)
            for x in range(0, engine.config.grid_width, STREET_SPACING)
        ]

        assert websocket.sent_messages == [
            {
                "type": "tick",
                "data": {
                    "tick_count": 0,
                    "state": "stopped",
                    "config": {
                        "grid_width": 10,
                        "grid_height": 10,
                        "tick_speed": 1,
                        "spawn_rate": 0.1,
                        "emergency_probability": 0.1,
                        "phase_duration": 3,
                    },
                    "grid": {
                        "width": 10,
                        "height": 10,
                        "cells": expected_cells,
                    },
                    "vehicles": [],
                    "traffic_lights": expected_lights,
                    "metrics": {
                        "normal_avg_ticks": 0.0,
                        "emergency_avg_ticks": 0.0,
                        "improvement": 0.0,
                        "total_completed": 0,
                    },
                },
            }
        ]

    def test_serialize_snapshot_encodes_enum_values(self) -> None:
        """Snapshot enums are converted to JSON values before broadcast."""
        payload = serialize_snapshot(
            SnapshotWithEnum(
                tick_count=1,
                state=SnapshotState.RUNNING,
                config={},
                grid={},
                vehicles=[],
                traffic_lights=[],
                metrics={},
            )
        )

        assert payload["state"] == "running"

    def test_serialize_snapshot_rejects_non_object_payloads(self) -> None:
        """Snapshots must serialize into a JSON object for the API contract."""
        with pytest.raises(
            TypeError,
            match="Simulation snapshot must serialize to a JSON object.",
        ):
            serialize_snapshot([1, 2, 3])

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("message", "initial_state", "expected_state"),
        [
            ({"type": "pause"}, SimulationState.RUNNING, SimulationState.PAUSED),
            ({"type": "resume"}, SimulationState.PAUSED, SimulationState.RUNNING),
        ],
    )
    async def test_handle_client_message_applies_control_commands(
        self,
        message: dict[str, Any],
        initial_state: SimulationState,
        expected_state: SimulationState,
    ) -> None:
        """Client control messages forward to the engine lifecycle methods."""
        engine = SimulationEngine()
        engine.state = initial_state

        assert await handle_client_message(message, engine) is None
        assert engine.state is expected_state

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("message", "field_name", "expected_value"),
        [
            ({"type": "set_speed", "data": {"speed": 6}}, "tick_speed", 6),
            (
                {"type": "set_spawn_rate", "data": {"rate": 0.25}},
                "spawn_rate",
                0.25,
            ),
            (
                {"type": "set_phase_duration", "data": {"duration": 5}},
                "phase_duration",
                5,
            ),
            (
                {
                    "type": "set_emergency_probability",
                    "data": {"probability": 0.4},
                },
                "emergency_probability",
                0.4,
            ),
        ],
    )
    async def test_handle_client_message_applies_config_commands(
        self,
        message: dict[str, Any],
        field_name: str,
        expected_value: int | float,
    ) -> None:
        """Client config messages forward to the matching engine setters."""
        engine = SimulationEngine()

        assert await handle_client_message(message, engine) is None
        assert getattr(engine.config, field_name) == expected_value

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("message", "expected_message"),
        [
            (
                [],
                "WebSocket message must be a JSON object.",
            ),
            (
                {"type": "pause", "data": [1]},
                "WebSocket message data must be an object.",
            ),
            (
                {"type": "set_speed", "data": {}},
                "set_speed requires integer data.speed.",
            ),
            (
                {"type": "set_spawn_rate", "data": {}},
                "set_spawn_rate requires numeric data.rate.",
            ),
            (
                {"type": "set_emergency_probability", "data": {}},
                "set_emergency_probability requires numeric data.probability.",
            ),
            (
                {"type": "set_phase_duration", "data": {}},
                "set_phase_duration requires integer data.duration.",
            ),
            (
                {"type": "bogus"},
                "Unsupported WebSocket message type: 'bogus'.",
            ),
        ],
    )
    async def test_handle_client_message_returns_error_for_invalid_message(
        self,
        message: Any,
        expected_message: str,
    ) -> None:
        """Invalid client messages produce an error payload for the caller to send."""
        engine = SimulationEngine()

        response = await handle_client_message(message, engine)

        assert response == {
            "type": "error",
            "data": {"message": expected_message},
        }

    @pytest.mark.asyncio
    async def test_websocket_endpoint_sends_error_payload_on_unexpected_exception(
        self,
    ) -> None:
        """Unexpected endpoint errors are reported to the client before disconnect."""
        websocket_manager = WebSocketManager()
        websocket = FakeWebSocket(receive_exception=RuntimeError("boom"))
        engine = SimulationEngine()

        await websocket_endpoint(websocket, engine, websocket_manager)

        assert websocket.accepted is True
        assert websocket.sent_messages[0]["type"] == "tick"
        assert websocket.sent_messages[0]["data"]["tick_count"] == 0
        assert websocket.sent_messages[1] == {
            "type": "error",
            "data": {"message": "boom"},
        }
        assert websocket_manager.active_connections == []

    @pytest.mark.asyncio
    async def test_websocket_endpoint_disconnects_when_error_reporting_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Unexpected endpoint errors still clean up the socket
        if error reporting fails."""
        websocket_manager = WebSocketManager()
        websocket = FakeWebSocket(receive_exception=RuntimeError("boom"))
        engine = SimulationEngine()

        send_count = 0
        original_send = websocket_manager.send_personal_message

        async def send_then_fail(
            message: dict[str, Any],
            target_websocket: FakeWebSocket,
        ) -> None:
            nonlocal send_count
            send_count += 1
            if send_count == 2:
                raise RuntimeError("send failed")
            await original_send(message, target_websocket)

        monkeypatch.setattr(websocket_manager, "send_personal_message", send_then_fail)

        await websocket_endpoint(websocket, engine, websocket_manager)

        assert websocket.accepted is True
        assert websocket.sent_messages == [
            {"type": "tick", "data": serialize_snapshot(engine.snapshot())}
        ]
        assert websocket_manager.active_connections == []

    @pytest.mark.asyncio
    async def test_websocket_endpoint_returns_handler_error_payloads(self) -> None:
        """Invalid client messages are returned through the endpoint send path."""
        websocket_manager = WebSocketManager()
        websocket = FakeWebSocket(received_messages=[{"type": "bogus"}])
        engine = SimulationEngine()

        await websocket_endpoint(websocket, engine, websocket_manager)

        assert websocket.accepted is True
        assert websocket.sent_messages[0]["type"] == "tick"
        assert websocket.sent_messages[1] == {
            "type": "error",
            "data": {"message": "Unsupported WebSocket message type: 'bogus'."},
        }
        assert websocket_manager.active_connections == []
