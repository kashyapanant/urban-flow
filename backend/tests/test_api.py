"""Tests for the API layer."""

from __future__ import annotations

import runpy
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

import pytest
import uvicorn
from fastapi import FastAPI, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.api.routes import ConfigUpdateRequest, router
from backend.api.serialization import serialize_snapshot
from backend.api.websocket import (
    WebSocketManager,
    broadcast_simulation_state,
    handle_client_message,
    websocket_endpoint,
)
from backend.simulation.engine import SimulationEngine, SimulationState


@pytest.fixture
def bare_client() -> TestClient:
    """Build a minimal app with the simulation router mounted."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def wired_client() -> TestClient:
    """Build an app with the simulation engine pre-wired on app.state."""
    app = FastAPI()
    app.include_router(router)
    app.state.engine = SimulationEngine()
    return TestClient(app)


def app_for(client: TestClient) -> FastAPI:
    """Return the typed FastAPI app owned by a test client."""
    return cast(FastAPI, client.app)


def cors_middleware_for(app: FastAPI) -> Any:
    """Return the configured CORS middleware entry for an app."""
    return next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls is CORSMiddleware
    )


class TestConfigUpdateRequest:
    """Test cases for ConfigUpdateRequest validation."""

    def test_valid_config_all_fields(self):
        """Test valid configuration with all fields provided."""
        # Arrange & Act
        config = ConfigUpdateRequest(tick_speed=5, spawn_rate=0.3, phase_duration=5)

        # Assert
        assert config.tick_speed == 5
        assert config.spawn_rate == 0.3
        assert config.phase_duration == 5

    def test_valid_config_partial_fields(self):
        """Test valid configuration with only some fields provided."""
        # Arrange & Act
        config = ConfigUpdateRequest(tick_speed=8)

        # Assert
        assert config.tick_speed == 8
        assert config.spawn_rate is None
        assert config.phase_duration is None

    def test_valid_config_empty(self):
        """Test valid configuration with no fields provided."""
        # Arrange & Act
        config = ConfigUpdateRequest()

        # Assert
        assert config.tick_speed is None
        assert config.spawn_rate is None
        assert config.phase_duration is None

    @pytest.mark.parametrize(
        "field_name,test_values",
        [
            ("tick_speed", [1, 5, 10]),
            ("spawn_rate", [0.0, 0.5, 1.0]),
            ("emergency_probability", [0.0, 0.5, 1.0]),
            ("phase_duration", [1, 10, 20]),
        ],
    )
    def test_valid_boundary_values(self, field_name, test_values):
        """Test valid boundary and mid-range values for all configuration fields."""
        for value in test_values:
            # Arrange & Act
            config = ConfigUpdateRequest(**{field_name: value})

            # Assert
            assert getattr(config, field_name) == value

    @pytest.mark.parametrize(
        "field_name,invalid_values",
        [
            ("tick_speed", [0, -1, 11, 100]),
            ("spawn_rate", [-0.1, -1.0, 1.1, 2.0]),
            ("emergency_probability", [-0.1, -1.0, 1.1, 2.0]),
            ("phase_duration", [0, -1, 21, 100]),
        ],
    )
    def test_invalid_values_out_of_bounds(self, field_name, invalid_values):
        """Test invalid values outside allowed ranges for all configuration fields."""
        for invalid_value in invalid_values:
            # Arrange & Act - This should raise ValidationError
            with pytest.raises(ValidationError) as exc_info:
                ConfigUpdateRequest(**{field_name: invalid_value})

            # Assert - Verify the validation error details
            errors = exc_info.value.errors()
            assert len(errors) == 1
            assert errors[0]["loc"] == (field_name,)

            # Assert - Verify error message contains boundary information
            error_msg = str(errors[0]["msg"])
            assert (
                "greater than or equal to" in error_msg
                or "less than or equal to" in error_msg
            )

    @pytest.mark.parametrize(
        "field_name,invalid_value",
        [
            ("tick_speed", "not_a_number"),
            ("tick_speed", 5.5),
            ("spawn_rate", "invalid"),
            ("spawn_rate", [1, 2, 3]),  # List is not a valid type
            ("emergency_probability", "invalid"),
            ("emergency_probability", [1, 2, 3]),
            ("phase_duration", "string"),
            ("phase_duration", 3.14),
        ],
    )
    def test_invalid_field_types(self, field_name, invalid_value):
        """Test invalid field types for configuration parameters."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ConfigUpdateRequest(**{field_name: invalid_value})

        # Verify the error is about type validation
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == (field_name,)

    def test_multiple_invalid_fields_all_reported(self):
        """Test that validation errors for multiple fields are all reported together."""
        # Arrange & Act - Send request with all fields invalid
        with pytest.raises(ValidationError) as exc_info:
            ConfigUpdateRequest(
                tick_speed=15,
                spawn_rate=-0.5,
                emergency_probability=1.5,
                phase_duration=25,
            )

        # Assert - All validation errors should be reported, not just the first one
        errors = exc_info.value.errors()
        assert len(errors) == 4, "All field validation errors should be reported"

        # Assert - Each field should have its own error
        error_fields = {error["loc"][0] for error in errors}
        assert error_fields == {
            "tick_speed",
            "spawn_rate",
            "emergency_probability",
            "phase_duration",
        }

    def test_config_serialization(self):
        """Test that valid config can be serialized to dict."""
        # Arrange
        config = ConfigUpdateRequest(tick_speed=7, spawn_rate=0.2, phase_duration=4)

        # Act
        config_dict = config.model_dump()

        # Assert
        expected = {
            "tick_speed": 7,
            "spawn_rate": 0.2,
            "emergency_probability": None,
            "phase_duration": 4,
        }
        assert config_dict == expected

    def test_config_serialization_with_none_values(self):
        """Test serialization with None values."""
        # Arrange
        config = ConfigUpdateRequest(tick_speed=3)

        # Act
        config_dict = config.model_dump()

        # Assert
        expected = {
            "tick_speed": 3,
            "spawn_rate": None,
            "emergency_probability": None,
            "phase_duration": None,
        }
        assert config_dict == expected

    @pytest.mark.parametrize(
        "extra_field_name,extra_field_value",
        [
            ("unknown_field", "should_fail"),
            ("invalid_param", "test"),
            ("extra_config", 123),
            ("typo_tick_speed", 5),  # Common typo
            ("spawn_rats", 0.5),  # Another common typo
            ("phase_durations", 10),  # Plural typo
        ],
    )
    def test_extra_fields_forbidden(self, extra_field_name, extra_field_value):
        """Test that extra/unknown fields are rejected due to extra='forbid'."""
        # Arrange
        request_data = {
            "tick_speed": 5,  # Valid field
            extra_field_name: extra_field_value,  # Invalid extra field
        }

        # Act - This should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ConfigUpdateRequest(**request_data)

        # Assert - Verify the validation error details
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "extra_forbidden"
        assert extra_field_name in str(errors[0])

    def test_multiple_extra_fields_all_reported(self):
        """Test that multiple extra fields are all reported in validation errors."""
        # Arrange
        request_data = {
            "tick_speed": 5,  # Valid
            "unknown_field1": "test",  # Invalid extra field
            "unknown_field2": 123,  # Invalid extra field
            "unknown_field3": True,  # Invalid extra field
        }

        # Act - This should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ConfigUpdateRequest(**request_data)

        # Assert - Verify all extra fields are reported
        errors = exc_info.value.errors()
        assert len(errors) == 3, "All extra field errors should be reported"

        # Assert - Check that all errors are about extra fields
        for error in errors:
            assert error["type"] == "extra_forbidden"

        # Assert - Check that all extra field names are mentioned
        error_messages = [str(error) for error in errors]
        full_error_text = " ".join(error_messages)
        assert "unknown_field1" in full_error_text
        assert "unknown_field2" in full_error_text
        assert "unknown_field3" in full_error_text


class TestAPIRoutes:
    """Test cases for REST API endpoints."""

    def test_routes_return_503_when_engine_is_not_configured(
        self, bare_client: TestClient
    ) -> None:
        """Endpoints fail clearly before app bootstrap injects the engine."""
        response = bare_client.get("/api/simulation/state")

        assert response.status_code == 503
        assert response.json() == {"detail": "Simulation engine is not configured."}

    def test_app_state_engine_makes_state_available(
        self, wired_client: TestClient
    ) -> None:
        """app.state.engine wires a shared engine into REST routes."""
        response = wired_client.get("/api/simulation/state")

        assert response.status_code == 200
        data = response.json()
        assert data["tick_count"] == 0
        assert data["state"] == "stopped"
        assert data["config"]["tick_speed"] == 1
        assert "grid" in data
        assert "vehicles" in data
        assert "traffic_lights" in data
        assert "metrics" in data

    def test_control_routes_return_engine_results(
        self, wired_client: TestClient
    ) -> None:
        """Control routes expose the engine's lifecycle result shape."""
        engine = app_for(wired_client).state.engine

        start_response = wired_client.post("/api/simulation/start")
        engine.state = SimulationState.STOPPED

        engine.state = SimulationState.RUNNING
        pause_response = wired_client.post("/api/simulation/pause")
        resume_response = wired_client.post("/api/simulation/resume")

        assert start_response.status_code == 200
        assert start_response.json() == {
            "action": "start",
            "applied": True,
            "state": "running",
            "message": "Simulation started.",
        }
        assert pause_response.status_code == 200
        assert pause_response.json() == {
            "action": "pause",
            "applied": True,
            "state": "paused",
            "message": "Simulation paused.",
        }
        assert resume_response.status_code == 200
        assert resume_response.json() == {
            "action": "resume",
            "applied": True,
            "state": "running",
            "message": "Simulation resumed.",
        }
        engine.state = SimulationState.STOPPED

    def test_update_config_applies_only_provided_fields(
        self, wired_client: TestClient
    ) -> None:
        """Partial config updates preserve omitted runtime values."""
        engine = app_for(wired_client).state.engine

        response = wired_client.put(
            "/api/simulation/config",
            json={"tick_speed": 7, "phase_duration": 4},
        )

        assert response.status_code == 200
        assert response.json() == {
            "message": "Updated: tick_speed, phase_duration.",
            "config": {
                "grid_width": 10,
                "grid_height": 10,
                "tick_speed": 7,
                "spawn_rate": 0.1,
                "emergency_probability": 0.1,
                "phase_duration": 4,
            },
        }
        assert engine.config.tick_speed == 7
        assert engine.config.spawn_rate == 0.1
        assert engine.config.phase_duration == 4

    def test_update_config_returns_current_config_for_empty_payload(
        self, wired_client: TestClient
    ) -> None:
        """Empty config updates return the current config without changes."""
        engine = app_for(wired_client).state.engine

        response = wired_client.put("/api/simulation/config", json={})

        assert response.status_code == 200
        assert response.json() == {
            "message": "No configuration changes provided.",
            "config": {
                "grid_width": 10,
                "grid_height": 10,
                "tick_speed": 1,
                "spawn_rate": 0.1,
                "emergency_probability": 0.1,
                "phase_duration": 3,
            },
        }
        assert engine.config.model_dump() == {
            "grid_width": 10,
            "grid_height": 10,
            "tick_speed": 1,
            "spawn_rate": 0.1,
            "emergency_probability": 0.1,
            "phase_duration": 3,
        }

    def test_update_config_applies_emergency_probability(
        self, wired_client: TestClient
    ) -> None:
        """Emergency vehicle spawn probability can be updated at runtime."""
        engine = app_for(wired_client).state.engine

        response = wired_client.put(
            "/api/simulation/config",
            json={"emergency_probability": 0.4},
        )

        assert response.status_code == 200
        assert response.json() == {
            "message": "Updated: emergency_probability.",
            "config": {
                "grid_width": 10,
                "grid_height": 10,
                "tick_speed": 1,
                "spawn_rate": 0.1,
                "emergency_probability": 0.4,
                "phase_duration": 3,
            },
        }
        assert engine.config.emergency_probability == 0.4

    def test_update_config_returns_422_when_runtime_validation_fails(
        self, wired_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Runtime setter errors are surfaced as API validation errors."""
        engine = app_for(wired_client).state.engine

        def fail_spawn_rate(_: float) -> None:
            raise ValueError("spawn rate update failed")

        monkeypatch.setattr(engine, "set_spawn_rate", fail_spawn_rate)

        response = wired_client.put(
            "/api/simulation/config",
            json={"spawn_rate": 0.3},
        )

        assert response.status_code == 422
        assert response.json() == {"detail": "spawn rate update failed"}
        assert engine.config.spawn_rate == 0.1

    def test_get_metrics_returns_metrics_payload(
        self, wired_client: TestClient
    ) -> None:
        """The metrics route serializes the engine's metrics object."""
        response = wired_client.get("/api/simulation/metrics")

        assert response.status_code == 200
        assert response.json() == {
            "normal_avg_ticks": 0.0,
            "emergency_avg_ticks": 0.0,
            "improvement": 0.0,
            "total_completed": 0,
        }

    def test_config_route_rejects_invalid_payload(
        self, wired_client: TestClient
    ) -> None:
        """FastAPI/Pydantic validation protects the runtime config endpoint."""
        response = wired_client.put(
            "/api/simulation/config",
            json={"tick_speed": 11, "unknown": True},
        )

        assert response.status_code == 422


class FakeWebSocket:
    """Small WebSocket test double for manager unit tests."""

    def __init__(
        self,
        *,
        fail_send: bool = False,
        send_exception: Exception | None = None,
        received_messages: list[dict[str, Any]] | None = None,
        receive_exception: Exception | None = None,
    ) -> None:
        self.accepted = False
        self.sent_messages: list[dict[str, Any]] = []
        self.fail_send = fail_send
        self.send_exception = send_exception
        self.received_messages = list(received_messages or [])
        self.receive_exception = receive_exception

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, message: dict[str, Any]) -> None:
        if self.send_exception is not None:
            raise self.send_exception
        if self.fail_send:
            raise RuntimeError("client disconnected")
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
        failing = FakeWebSocket(fail_send=True)
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
    async def test_broadcast_simulation_state_sends_tick_message(self) -> None:
        """Simulation snapshots are wrapped in the agreed tick message shape."""
        websocket_manager = WebSocketManager()
        websocket = FakeWebSocket()
        await websocket_manager.connect(websocket)
        engine = SimulationEngine()

        await broadcast_simulation_state(engine, websocket_manager)

        assert websocket.sent_messages[0]["type"] == "tick"
        data = websocket.sent_messages[0]["data"]
        assert isinstance(data, dict)
        assert data["tick_count"] == 0
        assert data["state"] == "stopped"

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

    @pytest.mark.asyncio
    async def test_handle_client_message_applies_runtime_commands(self) -> None:
        """Client command messages forward to engine controls and config setters."""
        engine = SimulationEngine()
        engine.state = SimulationState.RUNNING

        assert await handle_client_message({"type": "pause"}, engine) is None
        assert engine.state is SimulationState.PAUSED

        assert await handle_client_message({"type": "resume"}, engine) is None
        assert engine.state is SimulationState.RUNNING

        assert (
            await handle_client_message(
                {"type": "set_speed", "data": {"speed": 6}}, engine
            )
            is None
        )
        assert (
            await handle_client_message(
                {"type": "set_spawn_rate", "data": {"rate": 0.25}}, engine
            )
            is None
        )
        assert (
            await handle_client_message(
                {"type": "set_phase_duration", "data": {"duration": 5}}, engine
            )
            is None
        )

        assert engine.config.tick_speed == 6
        assert engine.config.spawn_rate == 0.25
        assert engine.config.phase_duration == 5

    @pytest.mark.asyncio
    async def test_handle_client_message_returns_error_for_invalid_message(
        self,
    ) -> None:
        """Invalid client messages produce an error payload for the caller to send."""
        engine = SimulationEngine()

        response = await handle_client_message(
            {"type": "set_speed", "data": {}}, engine
        )

        assert response == {
            "type": "error",
            "data": {"message": "set_speed requires integer data.speed."},
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


class TestAppBootstrap:
    """Test cases for FastAPI app bootstrap."""

    def test_create_app_wires_shared_engine_into_rest_routes(self) -> None:
        """The app factory injects one engine into REST routes."""
        from main import create_app

        app = create_app()

        with TestClient(app) as client:
            response = client.get("/api/simulation/state")

        assert response.status_code == 200
        assert response.json()["state"] == "stopped"
        assert hasattr(app.state, "engine")
        assert hasattr(app.state, "ws_manager")

    def test_create_app_creates_isolated_state_per_app(self) -> None:
        """Each app instance owns its own engine and WebSocket manager."""
        from main import create_app

        first = create_app()
        second = create_app()

        assert first.state.engine is not second.state.engine
        assert first.state.ws_manager is not second.state.ws_manager

    def test_create_app_exposes_websocket_tick_stream(self) -> None:
        """The app exposes /ws and sends an initial tick snapshot."""
        from main import create_app

        app = create_app()

        with TestClient(app) as client:
            with client.websocket_connect("/ws") as websocket:
                message = websocket.receive_json()

        assert message["type"] == "tick"
        assert message["data"]["tick_count"] == 0
        assert message["data"]["state"] == "stopped"

    def test_create_app_uses_default_cors_origins_when_env_is_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """App bootstrap falls back to the local frontend origins."""
        from main import create_app

        monkeypatch.delenv("CORS_ORIGINS", raising=False)

        app = create_app()
        cors_middleware = cors_middleware_for(app)

        assert cors_middleware.kwargs["allow_origins"] == [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

    def test_create_app_reads_cors_origins_from_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Configured origins are trimmed and empty entries are ignored."""
        from main import create_app

        monkeypatch.setenv(
            "CORS_ORIGINS",
            "https://urban-flow.local, http://localhost:5173,   ,",
        )

        app = create_app()
        cors_middleware = cors_middleware_for(app)

        assert cors_middleware.kwargs["allow_origins"] == [
            "https://urban-flow.local",
            "http://localhost:5173",
        ]

    def test_main_module_uses_project_root_uvicorn_target(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Running main.py uses the actual module path for the app import string."""
        captured: dict[str, Any] = {}

        def fake_run(app_target: str, **kwargs: Any) -> None:
            captured["app_target"] = app_target
            captured["kwargs"] = kwargs

        monkeypatch.setattr(uvicorn, "run", fake_run)

        runpy.run_module("main", run_name="__main__")

        assert captured["app_target"] == "main:app"

    def test_app_shutdown_stops_shared_engine(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Application shutdown stops the shared simulation engine."""
        from main import create_app

        stopped_engines: list[SimulationEngine] = []

        async def fake_stop(self: SimulationEngine) -> object:
            stopped_engines.append(self)
            return object()

        monkeypatch.setattr(SimulationEngine, "stop", fake_stop)
        app = create_app()

        with TestClient(app):
            pass

        assert stopped_engines == [app.state.engine]

    def test_app_shutdown_skips_stop_when_engine_is_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Application shutdown tolerates missing engine state."""
        from main import create_app

        async def fail_stop(self: SimulationEngine) -> None:
            raise AssertionError(
                "stop() should not be called when engine state is missing"
            )

        monkeypatch.setattr(SimulationEngine, "stop", fail_stop)
        app = create_app()

        with TestClient(app):
            del app.state.engine

        assert not hasattr(app.state, "engine")
