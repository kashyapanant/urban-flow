# Urban Flow

Urban Flow is a local-first traffic-signal and emergency-response simulation platform. The project starts with a deterministic 10x10 grid simulation, then grows toward real-road networks, replayable traffic scenarios, and eventually live traffic integration.

The current roadmap is intentionally **rule-based and provider-agnostic**, not ML-first:

- Phase 1 finishes the grid MVP and browser UI.
- Phase 2 introduces a shared road-network abstraction plus OpenStreetMap import.
- Phase 3 adds local containerization and persistence without requiring cloud services.
- Phase 4 makes live traffic the final core milestone.
- A later optional phase can add adaptive optimization, analytics, and production-scale deployment features.

See [`docs/project_phases.md`](docs/project_phases.md) for the full roadmap and [`docs/tasks.md`](docs/tasks.md) for the Phase 1 task tracker.

## Current Status

Urban Flow is still in Phase 1 integration. The deterministic simulation core and backend runtime interface are implemented and tested:

- `Grid`
- `Pathfinder`
- `Vehicle` / `VehicleManager`
- `TrafficLight` / `TrafficLightManager`
- `Metrics`
- `SimulationEngine`
- FastAPI REST/WebSocket runtime wiring

The remaining Phase 1 work is backend congestion stabilization followed by the browser frontend MVP.

## Local-First Principles

- Every major milestone should be demonstrable locally.
- Paid providers should sit behind adapters, not define the core simulation model.
- Cloud-ready means reproducible containers and portable persistence before it means Kubernetes.

## Setup

### Prerequisites

- Python 3.12+
- UV package manager

### Installation

```bash
git clone <repository-url>
cd urban-flow
uv sync --group dev
```

## Development Workflow

### Run Tests

```bash
uv run pytest
```

### Run Lint Checks

```bash
uv run ruff check .
uv run ruff format --check .
```

### Common Make Targets

- `make lint`
- `make format`
- `make test`
- `make test-cov`

### Application Startup

Run the local FastAPI app with REST endpoints and the WebSocket stream:

```bash
uv run python main.py
```

The browser frontend files are still part of the remaining Phase 1 work. Before that, the `P1-ENG-04` through `P1-ENG-07` congestion-stabilization sequence reduces avoidable congestion and detects whole-network standstill in long-running demo simulations.

## Project Structure

```text
urban-flow/
├── main.py                    # FastAPI app entry point
├── backend/
│   ├── config.py              # Simulation configuration
│   ├── simulation/            # Core simulation modules
│   ├── api/                   # REST and WebSocket runtime interface
│   └── tests/                 # Test suite
├── docs/                      # Requirements, architecture, roadmap, tasks
├── prompts/                   # Historical requirement elicitation notes
├── pyproject.toml             # Project configuration and dependencies
└── Makefile                   # Common development commands
```

The browser frontend files are planned as Phase 1 deliverables and are tracked in [`docs/tasks.md`](docs/tasks.md).
