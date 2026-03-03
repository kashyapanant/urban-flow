# Urban Flow

A modular traffic signal and emergency response simulation platform with AI-driven optimization and real-time control.

## Phase 1: Core Simulation Engine

This phase implements a tick-based traffic simulation on a 10×10 grid with emergency vehicle signal preemption.

## Setup Instructions

### Prerequisites
- Python 3.12+
- UV package manager

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd urban-flow
```

2. Create and activate virtual environment:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
uv sync
```

### Running the Application

1. Start the backend server:
```bash
python main.py
```

2. Open your browser and navigate to:
- Application: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

### Running Tests

```bash
pytest backend/tests/
```

### Development

- Use `make lint` to run code formatting and linting
- Use `make test` to run the test suite
- See `Makefile` for all available commands

## Project Structure

```
urban-flow/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Configuration settings
│   ├── simulation/              # Core simulation engine
│   │   ├── engine.py            # Main orchestrator
│   │   ├── grid.py              # Grid world model
│   │   ├── vehicle.py           # Vehicle entities and management
│   │   ├── traffic_light.py     # Traffic light system
│   │   ├── pathfinder.py        # A* pathfinding
│   │   └── metrics.py           # Performance metrics
│   ├── api/                     # REST and WebSocket API
│   │   ├── routes.py            # REST endpoints
│   │   └── websocket.py         # WebSocket handlers
│   └── tests/                   # Test suite
├── docs/                        # Documentation
└── pyproject.toml              # Project configuration
```

## Architecture

See `docs/architecture.md` for detailed system architecture and design decisions.
