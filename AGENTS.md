# AGENTS.md

## Project Identity

Urban Flow is a local-first traffic-signal and emergency-response simulation platform.

The current project is in Phase 1 integration. The core deterministic simulation modules are partly implemented and tested:

- Grid
- Pathfinder
- Vehicle / VehicleManager
- TrafficLight

The remaining Phase 1 goal is to complete the runnable end-to-end MVP:

- Metrics
- SimulationEngine
- REST API wiring
- WebSocket simulation stream
- FastAPI app bootstrap
- Browser frontend
- basic docs and validation

The project must remain deterministic, local-first, provider-agnostic, and rule-based. 


## Core Product Direction

Urban Flow should demonstrate:
1. A deterministic 10x10 grid traffic simulation.
2. Vehicles moving through the grid using pathfinding.
3. Traffic lights controlling intersections.
4. Emergency vehicles receiving priority behavior.
5. Metrics that make the simulation understandable.
6. A browser UI that visually shows movement, lights, and simulation state.
7. REST/WebSocket integration that makes the simulation controllable and observable.

The goal is not to build a perfect traffic simulator yet. The goal is to build a clean, impressive, explainable MVP that can grow into real-road networks and live traffic later.

## Phase Discipline

Always respect the roadmap:

- Phase 1: grid MVP and browser UI.
- Phase 2: shared road-network abstraction and OpenStreetMap import.
- Phase 3: local containers and persistence.
- Phase 4: live traffic integration.
- Later optional phase: adaptive optimization, analytics, production deployment.

When working on Phase 1, do not prematurely implement Phase 2/3/4 concepts. You may leave clean extension points, but avoid over-engineering.

## Local-First Principles

Every milestone must be demonstrable locally.

Rules:
- No cloud dependency for core simulation.
- No paid provider dependency in core logic.
- Provider-specific integrations must sit behind adapters.
- The core simulation model must remain provider-agnostic.
- Prefer reproducible local commands over hosted services.
- Prefer simple local persistence later, not now, unless the current task explicitly requires it.

## Tech Stack

Backend:
- Python 3.12+
- uv package manager
- FastAPI planned for app/API layer
- pytest for tests
- ruff for linting/format checks

Frontend:
- JavaScript browser frontend planned for Phase 1
- Keep frontend simple unless a framework already exists in the repository
- Do not introduce React/Vue/Svelte unless explicitly requested or already present

Important commands:

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
make lint
make format
make test
make test-cov
