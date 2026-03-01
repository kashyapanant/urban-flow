"""Main FastAPI application for Urban Flow simulation."""

import uvicorn
from fastapi import FastAPI

from backend.simulation.engine import SimulationEngine


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app instance
    """
    pass


def setup_cors(app: FastAPI) -> None:
    """Configure CORS middleware.

    Args:
        app: FastAPI application instance
    """
    pass


def setup_routes(app: FastAPI, engine: SimulationEngine) -> None:
    """Setup API routes and WebSocket endpoints.

    Args:
        app: FastAPI application instance
        engine: Simulation engine instance
    """
    pass


def setup_static_files(app: FastAPI) -> None:
    """Setup static file serving for frontend.

    Args:
        app: FastAPI application instance
    """
    pass


# Create the FastAPI app
app = create_app()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
