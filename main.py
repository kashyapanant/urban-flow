"""Main FastAPI application for Urban Flow simulation."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router, set_engine
from backend.api.serialization import serialize_snapshot
from backend.api.websocket import manager, websocket_endpoint
from backend.simulation.engine import SimulationEngine, SimulationSnapshot


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    async def broadcast_snapshot(snapshot: SimulationSnapshot) -> None:
        await manager.broadcast({"type": "tick", "data": serialize_snapshot(snapshot)})

    engine = SimulationEngine(broadcast_callback=broadcast_snapshot)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await app.state.engine.stop()

    app = FastAPI(title="Urban Flow", lifespan=lifespan)
    app.state.engine = engine
    setup_cors(app)
    setup_routes(app, engine)
    setup_static_files(app)
    return app


def setup_cors(app: FastAPI) -> None:
    """Configure CORS middleware for local browser development."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_routes(app: FastAPI, engine: SimulationEngine) -> None:
    """Setup API routes and WebSocket endpoints."""
    set_engine(engine)
    app.include_router(router)

    @app.websocket("/ws")
    async def simulation_websocket(websocket: WebSocket) -> None:
        await websocket_endpoint(websocket, engine)


def setup_static_files(app: FastAPI) -> None:
    """Setup static file serving for the frontend when files exist."""
    frontend_dir = Path(__file__).parent / "frontend"
    if frontend_dir.exists():
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


# Create the FastAPI app
app = create_app()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
