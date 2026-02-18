# UrbanFlow 🚦

UrbanFlow is a modular traffic signal and emergency response simulation platform designed to model, analyze, and optimize urban traffic systems using algorithmic and AI-driven approaches.

The system evolves from a deterministic traffic simulator into an AI-powered emergency-priority traffic optimization engine.

---
## 🚀 Vision

Modern cities struggle with:
- Traffic congestion
- Emergency vehicle delays
- Inefficient signal timing
- Lack of adaptive control systems

UrbanFlow aims to simulate and optimize traffic networks by integrating:

- Discrete-time traffic simulation
- Adaptive signal control
- Emergency vehicle prioritization
- Reinforcement learning-based optimization
- Real-time monitoring and metrics

---

## 🏗 Architecture Overview

UrbanFlow is designed using clean architecture principles with a layered
module structure. See [`docs/architecture.md`](docs/architecture.md) for the
full design document.

```
src/urban_flow/
├── core/           # Pure domain models (Grid, Road, Vehicle, Signal)
├── engine/         # Discrete-time simulation loop
├── signals/        # Pluggable signal controllers (Strategy pattern)
├── emergency/      # Emergency detection, routing, signal preemption
├── metrics/        # Metrics collection and reporting
├── config/         # Dataclass-based configuration
├── api/            # REST API + WebSocket (Phase 4+)
└── ai/             # RL-based optimization (Phase 6)
```

**Key architectural decisions:**
- **Cellular automaton** traffic model (roads divided into cells, one vehicle per cell)
- **Strategy pattern** for signal controllers (fixed-time, adaptive, AI -- swappable per intersection)
- **Event bus** for loose coupling between components (publish-subscribe)
- **Graph-based** road network (supports grids and arbitrary topologies)
- **Signal preemption** with look-ahead for emergency green wave corridors

---

## 🗺 Rollout Phases

| Phase | Focus | Modules |
|-------|-------|---------|
| 1 | Basic grid simulation (pure Python) | `core/`, `engine/` |
| 2 | Traffic light logic | `signals/`, `core/signal.py` |
| 3 | Emergency vehicle priority | `emergency/` |
| 4 | Backend API + visualization | `api/`, `metrics/` |
| 5 | Real-time engine | `engine/` (async) |
| 6 | AI optimization layer | `ai/` |
| 7 | Production deployment | `infra/` |

---

## 🚀 Quick Start

```bash
# Clone and install (requires Python 3.12+ and uv)
git clone <repo-url>
cd urban-flow
uv sync

# Run tests
uv run pytest

# Run a basic simulation (available after Phase 1)
uv run python -m urban_flow
```

---

## 📐 Design Documents

- [Architecture](docs/architecture.md) -- full system design
- [Design Decisions](docs/decisions.md) -- ADR-style decision log

