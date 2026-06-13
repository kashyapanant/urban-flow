"""Shared fixtures for API tests."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.routes import router
from backend.simulation.engine import SimulationEngine


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
