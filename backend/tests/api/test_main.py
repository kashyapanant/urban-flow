"""Tests for FastAPI app bootstrap."""

from __future__ import annotations

import asyncio
import runpy
from typing import Any

import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from backend.api.serialization import serialize_snapshot
from backend.simulation.engine import SimulationEngine


def cors_middleware_for(app: FastAPI) -> Any:
    """Return the configured CORS middleware entry for an app."""
    return next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls is CORSMiddleware
    )


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

    def test_create_app_broadcast_callback_sends_tick_payload(self) -> None:
        """The engine callback created by the app broadcasts serialized snapshots."""
        from main import create_app

        captured: list[dict[str, Any]] = []

        async def fake_broadcast(message: dict[str, Any]) -> None:
            captured.append(message)

        app = create_app()
        app.state.ws_manager.broadcast = fake_broadcast

        asyncio.run(app.state.engine._broadcast_callback(app.state.engine.snapshot()))

        assert captured == [
            {
                "type": "tick",
                "data": serialize_snapshot(app.state.engine.snapshot()),
            }
        ]

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
