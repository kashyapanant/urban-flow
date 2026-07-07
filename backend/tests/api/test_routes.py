"""Tests for REST API routes and request validation."""

from __future__ import annotations

import inspect
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.api.routes import (
    ConfigUpdateRequest,
    get_metrics,
    get_state,
    pause_simulation,
    reset_config,
    resume_simulation,
    update_config,
)
from backend.simulation.engine import SimulationState


def validate_config(payload: object) -> ConfigUpdateRequest:
    """Validate a config payload through the Pydantic model API."""
    return ConfigUpdateRequest.model_validate(payload)


def app_for(client: TestClient) -> FastAPI:
    """Return the typed FastAPI app owned by a test client."""
    return cast(FastAPI, client.app)


class TestConfigUpdateRequest:
    """Test cases for ConfigUpdateRequest validation."""

    def test_valid_config_all_fields(self) -> None:
        """Test valid configuration with all fields provided."""
        config = validate_config(
            {"tick_speed": 5, "spawn_rate": 0.3, "phase_duration": 5}
        )

        assert config.tick_speed == 5
        assert config.spawn_rate == 0.3
        assert config.phase_duration == 5

    def test_valid_config_partial_fields(self) -> None:
        """Test valid configuration with only some fields provided."""
        config = validate_config({"tick_speed": 8})

        assert config.tick_speed == 8
        assert config.spawn_rate is None
        assert config.phase_duration is None

    def test_valid_config_empty(self) -> None:
        """Test valid configuration with no fields provided."""
        config = validate_config({})

        assert config.tick_speed is None
        assert config.spawn_rate is None
        assert config.phase_duration is None

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("tick_speed", 1),
            ("tick_speed", 5),
            ("tick_speed", 10),
            ("spawn_rate", 0.0),
            ("spawn_rate", 0.5),
            ("spawn_rate", 1.0),
            ("emergency_probability", 0.0),
            ("emergency_probability", 0.5),
            ("emergency_probability", 1.0),
            ("phase_duration", 1),
            ("phase_duration", 10),
            ("phase_duration", 20),
        ],
    )
    def test_valid_boundary_values(self, field_name: str, value: int | float) -> None:
        """Test valid boundary and mid-range values for all configuration fields."""
        config = validate_config({field_name: value})

        assert getattr(config, field_name) == value

    @pytest.mark.parametrize(
        ("field_name", "invalid_value"),
        [
            ("tick_speed", 0),
            ("tick_speed", -1),
            ("tick_speed", 11),
            ("tick_speed", 100),
            ("spawn_rate", -0.1),
            ("spawn_rate", -1.0),
            ("spawn_rate", 1.1),
            ("spawn_rate", 2.0),
            ("emergency_probability", -0.1),
            ("emergency_probability", -1.0),
            ("emergency_probability", 1.1),
            ("emergency_probability", 2.0),
            ("phase_duration", 0),
            ("phase_duration", -1),
            ("phase_duration", 21),
            ("phase_duration", 100),
        ],
    )
    def test_invalid_values_out_of_bounds(
        self, field_name: str, invalid_value: int | float
    ) -> None:
        """Test invalid values outside allowed ranges for all configuration fields."""
        with pytest.raises(ValidationError) as exc_info:
            validate_config({field_name: invalid_value})

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == (field_name,)

        error_msg = str(errors[0]["msg"])
        assert (
            "greater than or equal to" in error_msg
            or "less than or equal to" in error_msg
        )

    @pytest.mark.parametrize(
        ("field_name", "invalid_value"),
        [
            ("tick_speed", "not_a_number"),
            ("tick_speed", 5.5),
            ("tick_speed", True),
            ("spawn_rate", "invalid"),
            ("spawn_rate", [1, 2, 3]),
            ("spawn_rate", True),
            ("emergency_probability", "invalid"),
            ("emergency_probability", [1, 2, 3]),
            ("emergency_probability", False),
            ("phase_duration", "string"),
            ("phase_duration", 3.14),
            ("phase_duration", False),
        ],
    )
    def test_invalid_field_types(self, field_name: str, invalid_value: object) -> None:
        """Test invalid field types for configuration parameters."""
        with pytest.raises(ValidationError) as exc_info:
            validate_config({field_name: invalid_value})

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == (field_name,)

    def test_multiple_invalid_fields_all_reported(self) -> None:
        """Test that validation errors for multiple fields are all reported together."""
        with pytest.raises(ValidationError) as exc_info:
            validate_config(
                {
                    "tick_speed": 15,
                    "spawn_rate": -0.5,
                    "emergency_probability": 1.5,
                    "phase_duration": 25,
                }
            )

        errors = exc_info.value.errors()
        assert len(errors) == 4, "All field validation errors should be reported"

        error_fields = {error["loc"][0] for error in errors}
        assert error_fields == {
            "tick_speed",
            "spawn_rate",
            "emergency_probability",
            "phase_duration",
        }

    def test_config_serialization(self) -> None:
        """Test that valid config can be serialized to dict."""
        config = validate_config(
            {"tick_speed": 7, "spawn_rate": 0.2, "phase_duration": 4}
        )

        config_dict = config.model_dump()

        expected = {
            "tick_speed": 7,
            "spawn_rate": 0.2,
            "emergency_probability": None,
            "phase_duration": 4,
        }
        assert config_dict == expected

    def test_config_serialization_with_none_values(self) -> None:
        """Test serialization with None values."""
        config = validate_config({"tick_speed": 3})

        config_dict = config.model_dump()

        expected = {
            "tick_speed": 3,
            "spawn_rate": None,
            "emergency_probability": None,
            "phase_duration": None,
        }
        assert config_dict == expected

    @pytest.mark.parametrize(
        ("extra_field_name", "extra_field_value"),
        [
            ("unknown_field", "should_fail"),
            ("invalid_param", "test"),
            ("extra_config", 123),
            ("typo_tick_speed", 5),
            ("spawn_rats", 0.5),
            ("phase_durations", 10),
        ],
    )
    def test_extra_fields_forbidden(
        self, extra_field_name: str, extra_field_value: object
    ) -> None:
        """Test that extra/unknown fields are rejected due to extra='forbid'."""
        request_data = {
            "tick_speed": 5,
            extra_field_name: extra_field_value,
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_config(request_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "extra_forbidden"
        assert extra_field_name in str(errors[0])

    def test_multiple_extra_fields_all_reported(self) -> None:
        """Test that multiple extra fields are all reported in validation errors."""
        request_data = {
            "tick_speed": 5,
            "unknown_field1": "test",
            "unknown_field2": 123,
            "unknown_field3": True,
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_config(request_data)

        errors = exc_info.value.errors()
        assert len(errors) == 3, "All extra field errors should be reported"

        for error in errors:
            assert error["type"] == "extra_forbidden"

        error_messages = [str(error) for error in errors]
        full_error_text = " ".join(error_messages)
        assert "unknown_field1" in full_error_text
        assert "unknown_field2" in full_error_text
        assert "unknown_field3" in full_error_text


class TestAPIRoutes:
    """Test cases for REST API endpoints."""

    def test_engine_touching_route_handlers_are_async(self) -> None:
        """Engine-touching handlers stay on the event loop thread."""
        assert inspect.iscoroutinefunction(reset_config)
        assert inspect.iscoroutinefunction(pause_simulation)
        assert inspect.iscoroutinefunction(resume_simulation)
        assert inspect.iscoroutinefunction(update_config)
        assert inspect.iscoroutinefunction(get_state)
        assert inspect.iscoroutinefunction(get_metrics)

    @pytest.mark.parametrize(
        ("method", "path", "payload"),
        [
            ("post", "/api/simulation/start", None),
            ("post", "/api/simulation/reset", None),
            ("post", "/api/simulation/config/reset", None),
            ("post", "/api/simulation/pause", None),
            ("post", "/api/simulation/resume", None),
            ("put", "/api/simulation/config", {"tick_speed": 1}),
            ("get", "/api/simulation/state", None),
            ("get", "/api/simulation/metrics", None),
        ],
    )
    def test_routes_return_503_when_engine_is_not_configured(
        self,
        bare_client: TestClient,
        method: str,
        path: str,
        payload: dict[str, int] | None,
    ) -> None:
        """Simulation routes fail clearly before app bootstrap injects the engine."""
        request_kwargs = {"json": payload} if payload is not None else {}
        response = getattr(bare_client, method)(path, **request_kwargs)

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

    def test_start_route_returns_started_result(self, wired_client: TestClient) -> None:
        """Start returns the engine lifecycle response for a stopped simulation."""
        engine = app_for(wired_client).state.engine

        response = wired_client.post("/api/simulation/start")

        assert response.status_code == 200
        assert response.json() == {
            "action": "start",
            "applied": True,
            "state": "running",
            "message": "Simulation started.",
        }
        engine.state = SimulationState.STOPPED

    @pytest.mark.parametrize(
        (
            "method",
            "path",
            "payload",
            "prepare_engine",
            "expected_state",
            "expected_tick_speed",
            "expected_tick_count",
        ),
        [
            ("post", "/api/simulation/start", None, None, "running", 1, 0),
            (
                "post",
                "/api/simulation/reset",
                None,
                lambda engine: setattr(engine, "tick_count", 9),
                "stopped",
                1,
                0,
            ),
            (
                "post",
                "/api/simulation/config/reset",
                None,
                lambda engine: engine.set_tick_speed(7),
                "stopped",
                1,
                0,
            ),
            (
                "post",
                "/api/simulation/pause",
                None,
                lambda engine: setattr(engine, "state", SimulationState.RUNNING),
                "paused",
                1,
                0,
            ),
            (
                "post",
                "/api/simulation/resume",
                None,
                lambda engine: setattr(engine, "state", SimulationState.PAUSED),
                "running",
                1,
                0,
            ),
            (
                "put",
                "/api/simulation/config",
                {"tick_speed": 7},
                None,
                "stopped",
                7,
                0,
            ),
        ],
    )
    def test_state_changing_routes_broadcast_fresh_tick_snapshots(
        self,
        wired_client: TestClient,
        method: str,
        path: str,
        payload: dict[str, int] | None,
        prepare_engine: object,
        expected_state: str,
        expected_tick_speed: int,
        expected_tick_count: int,
    ) -> None:
        """State-changing REST routes broadcast the post-mutation snapshot."""
        app = app_for(wired_client)
        engine = app.state.engine
        captured: list[dict[str, Any]] = []

        class StubWebSocketManager:
            async def broadcast(self, message: dict[str, Any]) -> None:
                captured.append(message)

        app.state.ws_manager = StubWebSocketManager()

        if callable(prepare_engine):
            prepare_engine(engine)

        request_kwargs = {"json": payload} if payload is not None else {}
        response = getattr(wired_client, method)(path, **request_kwargs)

        assert response.status_code == 200
        assert len(captured) == 1
        assert captured[0]["type"] == "tick"
        snapshot = captured[0]["data"]
        assert snapshot["state"] == expected_state
        assert snapshot["config"]["tick_speed"] == expected_tick_speed
        assert snapshot["tick_count"] == expected_tick_count

        engine.state = SimulationState.STOPPED

    def test_pause_route_returns_paused_result(self, wired_client: TestClient) -> None:
        """Pause returns the engine lifecycle response for a running simulation."""
        engine = app_for(wired_client).state.engine
        engine.state = SimulationState.RUNNING

        response = wired_client.post("/api/simulation/pause")

        assert response.status_code == 200
        assert response.json() == {
            "action": "pause",
            "applied": True,
            "state": "paused",
            "message": "Simulation paused.",
        }
        engine.state = SimulationState.STOPPED

    def test_resume_route_returns_resumed_result(
        self, wired_client: TestClient
    ) -> None:
        """Resume returns the engine lifecycle response for a paused simulation."""
        engine = app_for(wired_client).state.engine
        engine.state = SimulationState.PAUSED

        response = wired_client.post("/api/simulation/resume")

        assert response.status_code == 200
        assert response.json() == {
            "action": "resume",
            "applied": True,
            "state": "running",
            "message": "Simulation resumed.",
        }
        engine.state = SimulationState.STOPPED

    def test_reset_route_returns_reset_result(self, wired_client: TestClient) -> None:
        """Reset returns the lifecycle response for the default stopped engine."""
        engine = app_for(wired_client).state.engine
        assert engine.state is SimulationState.STOPPED
        engine.tick_count = 9

        response = wired_client.post("/api/simulation/reset")

        assert response.status_code == 200
        assert response.json() == {
            "action": "reset",
            "applied": True,
            "state": "stopped",
            "message": "Simulation reset.",
        }
        assert engine.state is SimulationState.STOPPED
        assert engine.tick_count == 0

    def test_reset_config_route_restores_default_values(
        self, wired_client: TestClient
    ) -> None:
        """Config reset restores default settings without touching world state."""
        engine = app_for(wired_client).state.engine
        original_grid = engine.grid
        engine.set_tick_speed(7)
        engine.set_spawn_rate(0.4)
        engine.set_phase_duration(5)
        engine.set_emergency_probability(0.25)

        response = wired_client.post("/api/simulation/config/reset")

        assert response.status_code == 200
        assert response.json() == {
            "message": "Configuration reset to defaults.",
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
        assert engine.grid is original_grid

    def test_reset_config_route_preserves_lifecycle_state(
        self, wired_client: TestClient
    ) -> None:
        """Config reset is settings-only and does not stop or rebuild the run."""
        engine = app_for(wired_client).state.engine
        original_grid = engine.grid
        engine.state = SimulationState.RUNNING
        engine.tick_count = 4
        engine.set_tick_speed(7)

        response = wired_client.post("/api/simulation/config/reset")

        assert response.status_code == 200
        assert engine.state is SimulationState.RUNNING
        assert engine.tick_count == 4
        assert engine.grid is original_grid

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

    def test_update_config_is_atomic_when_runtime_validation_fails_mid_update(
        self,
        wired_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Multi-field config updates leave runtime settings unchanged on failure."""
        engine = app_for(wired_client).state.engine
        original_validated_config_copy = engine._validated_config_copy

        def fail_when_spawn_rate_present(**updates: int | float):
            if "spawn_rate" in updates:
                raise ValueError("spawn rate update failed")
            return original_validated_config_copy(**updates)

        monkeypatch.setattr(
            engine,
            "_validated_config_copy",
            fail_when_spawn_rate_present,
        )

        response = wired_client.put(
            "/api/simulation/config",
            json={"tick_speed": 6, "spawn_rate": 0.3},
        )

        assert response.status_code == 422
        assert response.json() == {"detail": "spawn rate update failed"}
        assert engine.config.model_dump() == {
            "grid_width": 10,
            "grid_height": 10,
            "tick_speed": 1,
            "spawn_rate": 0.1,
            "emergency_probability": 0.1,
            "phase_duration": 3,
        }

    @pytest.mark.parametrize(
        ("payload", "error_message"),
        [
            ({"tick_speed": 6}, "tick speed update failed"),
            ({"spawn_rate": 0.3}, "spawn rate update failed"),
            ({"phase_duration": 4}, "phase duration update failed"),
            (
                {"emergency_probability": 0.4},
                "emergency probability update failed",
            ),
        ],
    )
    def test_update_config_returns_422_when_engine_update_fails(
        self,
        wired_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        payload: dict[str, int | float],
        error_message: str,
    ) -> None:
        """Any engine config update ValueError is surfaced as an API
        validation error."""
        engine = app_for(wired_client).state.engine

        def fail_update(**_: int | float) -> None:
            raise ValueError(error_message)

        monkeypatch.setattr(engine, "update_config", fail_update)

        response = wired_client.put("/api/simulation/config", json=payload)

        assert response.status_code == 422
        assert response.json() == {"detail": error_message}
        assert engine.config.model_dump() == {
            "grid_width": 10,
            "grid_height": 10,
            "tick_speed": 1,
            "spawn_rate": 0.1,
            "emergency_probability": 0.1,
            "phase_duration": 3,
        }

    @pytest.mark.parametrize(
        ("payload", "field_name"),
        [
            ({"tick_speed": True}, "tick_speed"),
            ({"spawn_rate": True}, "spawn_rate"),
            ({"emergency_probability": False}, "emergency_probability"),
            ({"phase_duration": False}, "phase_duration"),
        ],
    )
    def test_update_config_returns_422_for_boolean_numeric_fields(
        self, wired_client: TestClient, payload: dict[str, bool], field_name: str
    ) -> None:
        """REST config rejects boolean values for numeric runtime fields."""
        response = wired_client.put("/api/simulation/config", json=payload)

        assert response.status_code == 422
        errors = response.json()["detail"]
        assert len(errors) == 1
        assert errors[0]["loc"][-1] == field_name

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
