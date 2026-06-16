"""Tests for WebSocket management and command handling."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any

import pytest
from fastapi import WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError

import backend.api.websocket as websocket_module
from backend.api.serialization import serialize_snapshot
from backend.api.websocket import (
    WebSocketManager,
    _format_runtime_config_error,
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
        send_delay: float = 0.0,
        received_messages: list[dict[str, Any]] | None = None,
        receive_exception: Exception | None = None,
    ) -> None:
        self.accepted = False
        self.sent_messages: list[dict[str, Any]] = []
        self.send_exception = send_exception
        self.send_delay = send_delay
        self.received_messages = list(received_messages or [])
        self.receive_exception = receive_exception

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, message: dict[str, Any]) -> None:
        if self.send_delay:
            await asyncio.sleep(self.send_delay)
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
    async def test_manager_drops_timed_out_connections_during_broadcast(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Broadcast drops stalled sockets after the send timeout expires."""
        websocket_manager = WebSocketManager()
        healthy = FakeWebSocket()
        stalled = FakeWebSocket(send_delay=0.05)
        await websocket_manager.connect(healthy)
        await websocket_manager.connect(stalled)
        monkeypatch.setattr(websocket_module, "_SEND_TIMEOUT_SECONDS", 0.01)

        await websocket_manager.broadcast({"type": "tick", "data": {"tick_count": 5}})

        assert healthy.sent_messages == [{"type": "tick", "data": {"tick_count": 5}}]
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
        """Client control messages return an updated simulation snapshot."""
        engine = SimulationEngine()
        engine.state = initial_state

        response = await handle_client_message(message, engine)

        assert engine.state is expected_state
        assert response == {
            "type": "tick",
            "data": serialize_snapshot(engine.snapshot()),
        }

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
        """Client config messages return an updated simulation snapshot."""
        engine = SimulationEngine()

        response = await handle_client_message(message, engine)

        assert getattr(engine.config, field_name) == expected_value
        assert response == {
            "type": "tick",
            "data": serialize_snapshot(engine.snapshot()),
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("message", "expected_message"),
        [
            (
                [],
                "WebSocket message must be a JSON object.",
            ),
            (
                {"type": "pause", "data": []},
                "WebSocket message data must be an object.",
            ),
            (
                {"type": "pause", "data": 0},
                "WebSocket message data must be an object.",
            ),
            (
                {"type": "pause", "data": ""},
                "WebSocket message data must be an object.",
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
    @pytest.mark.parametrize(
        ("message", "expected_message"),
        [
            (
                {"type": "set_speed", "data": {"speed": 0}},
                "tick_speed must be between 1 and 10.",
            ),
            (
                {"type": "set_spawn_rate", "data": {"rate": 2.0}},
                "spawn_rate must be between 0.0 and 1.0.",
            ),
            (
                {"type": "set_phase_duration", "data": {"duration": 0}},
                "phase_duration must be between 1 and 20.",
            ),
            (
                {
                    "type": "set_emergency_probability",
                    "data": {"probability": 2.0},
                },
                "emergency_probability must be between 0.0 and 1.0.",
            ),
        ],
    )
    async def test_handle_client_message_returns_error_for_runtime_validation_failure(
        self,
        message: dict[str, Any],
        expected_message: str,
    ) -> None:
        """Invalid runtime config values return an error payload instead of raising."""
        engine = SimulationEngine()

        response = await handle_client_message(message, engine)

        assert response == {
            "type": "error",
            "data": {"message": expected_message},
        }

    def test_format_runtime_config_error_falls_back_for_unknown_validation_field(
        self,
    ) -> None:
        """Unknown validation fields return the generic client-facing message."""

        class UnknownConfigModel(BaseModel):
            unknown_rate: int = Field(ge=1)

        with pytest.raises(ValidationError) as exc_info:
            UnknownConfigModel.model_validate({"unknown_rate": 0})

        assert (
            _format_runtime_config_error(exc_info.value)
            == "Invalid simulation config value."
        )

    def test_format_runtime_config_error_falls_back_for_blank_value_error(
        self,
    ) -> None:
        """Blank ValueError messages fall back to the generic client-facing text."""
        assert (
            _format_runtime_config_error(ValueError("   "))
            == "Invalid simulation config value."
        )

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
    async def test_websocket_endpoint_sends_updated_snapshot_after_pause(self) -> None:
        """Successful control messages are acknowledged with a fresh tick snapshot."""
        websocket_manager = WebSocketManager()
        websocket = FakeWebSocket(received_messages=[{"type": "pause"}])
        engine = SimulationEngine()
        engine.state = SimulationState.RUNNING
        initial_snapshot = serialize_snapshot(engine.snapshot())

        await websocket_endpoint(websocket, engine, websocket_manager)

        assert websocket.accepted is True
        assert websocket.sent_messages == [
            {"type": "tick", "data": initial_snapshot},
            {"type": "tick", "data": serialize_snapshot(engine.snapshot())},
        ]
        assert websocket.sent_messages[1]["data"]["state"] == "paused"
        assert websocket_manager.active_connections == []

    @pytest.mark.asyncio
    async def test_websocket_endpoint_keeps_session_alive_after_invalid_config(
        self,
    ) -> None:
        """Invalid config commands report an error and do not end the session."""
        websocket_manager = WebSocketManager()
        websocket = FakeWebSocket(
            received_messages=[
                {"type": "set_speed", "data": {"speed": 0}},
                {"type": "set_speed", "data": {"speed": 2}},
            ]
        )
        engine = SimulationEngine()

        await websocket_endpoint(websocket, engine, websocket_manager)

        assert websocket.accepted is True
        assert websocket.sent_messages[0]["type"] == "tick"
        assert websocket.sent_messages[1] == {
            "type": "error",
            "data": {"message": "tick_speed must be between 1 and 10."},
        }
        assert engine.config.tick_speed == 2
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
