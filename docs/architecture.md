# UrbanFlow Architecture

## 1. System Overview

UrbanFlow is a discrete-time traffic simulation platform that models vehicles moving
through a network of intersections connected by roads. Its core purpose is to provide
**emergency vehicle signal preemption** — dynamically clearing a green corridor for
emergency vehicles by coordinating traffic signals along their route.

```
┌─────────────────────────────────────────────────────────────────┐
│                        UrbanFlow System                         │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │  Config   │  │  Core    │  │  Engine   │  │  Metrics     │  │
│  │  Layer    │──│  Domain  │──│  Layer    │──│  Layer       │  │
│  └──────────┘  └──────────┘  └───────────┘  └──────────────┘  │
│                      │              │                           │
│               ┌──────┴──────┐       │                          │
│               │             │       │                          │
│          ┌────┴─────┐ ┌─────┴────┐  │                         │
│          │ Signals  │ │Emergency │  │                          │
│          │ Control  │ │ Priority │  │                          │
│          └──────────┘ └──────────┘  │                          │
│                                     │                          │
│          ┌──────────┐  ┌────────────┴──┐                      │
│          │    AI    │  │   API /       │                       │
│          │  Layer   │  │   WebSocket   │                       │
│          └──────────┘  └──────────────-┘                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Architecture Principles

| Principle | Application |
|-----------|-------------|
| **Clean Architecture** | Domain models have zero external dependencies. Outer layers depend inward. |
| **Strategy Pattern** | Signal controllers are interchangeable strategies (fixed-time, adaptive, AI). |
| **Observer / Event Bus** | Components communicate via events, not direct calls, enabling loose coupling. |
| **Configuration-Driven** | Grid topology, timing, spawn rates — all configurable via dataclasses + files. |
| **Phase-Gated Complexity** | Each rollout phase adds a new layer without rewriting existing code. |

---

## 3. Layer Descriptions

### 3.1 Core Domain (`core/`)

Pure Python domain models with no external dependencies. These represent the
fundamental entities of the traffic simulation.

| Module | Responsibility |
|--------|---------------|
| `types.py` | Shared enums (`Direction`, `SignalState`, `VehicleType`), type aliases, `Position` namedtuple |
| `road.py` | `Road` — a directed edge between two intersections, divided into discrete cells for vehicle movement |
| `intersection.py` | `Intersection` — a node in the network, holds signal state and references to connected roads |
| `vehicle.py` | `Vehicle` and `EmergencyVehicle` — entities that move through the network with origin/destination |
| `signal.py` | `SignalPhase`, `SignalPlan` — data structures describing signal timing and phase sequences |
| `grid.py` | `RoadNetwork` — the graph structure (adjacency list) holding all intersections and roads |

**Key design rule:** Nothing in `core/` imports from any other UrbanFlow package.

### 3.2 Simulation Engine (`engine/`)

The discrete-time simulation loop that advances the world state each tick.

| Module | Responsibility |
|--------|---------------|
| `clock.py` | `SimulationClock` — manages current tick, time-step duration, pause/resume |
| `spawner.py` | `VehicleSpawner` — generates vehicles at network entry points based on configurable rates |
| `events.py` | `EventBus` and event dataclasses (`VehicleSpawned`, `VehicleMoved`, `SignalChanged`, `EmergencyDetected`, etc.) |
| `simulator.py` | `Simulator` — orchestrates the tick loop: advance clock → spawn → detect emergencies → update signals → move vehicles → collect metrics |

### 3.3 Signal Control (`signals/`)

Pluggable signal control strategies using the Strategy pattern.

| Module | Responsibility |
|--------|---------------|
| `controller.py` | `SignalController` — abstract protocol defining `update()`, `request_preemption()`, `release_preemption()` |
| `fixed_time.py` | `FixedTimeController` — cycles through phases on a fixed schedule |
| `adaptive.py` | `AdaptiveController` — adjusts phase duration based on queue lengths (future) |

All controllers implement the same `SignalController` protocol, making them
interchangeable at runtime — per intersection if needed.

### 3.4 Emergency Priority (`emergency/`)

Handles detection, routing, and signal preemption for emergency vehicles.

| Module | Responsibility |
|--------|---------------|
| `detector.py` | `EmergencyDetector` — monitors the network for emergency vehicles approaching intersections |
| `router.py` | `EmergencyRouter` — computes shortest/fastest path for emergency vehicles through the network |
| `preemption.py` | `PreemptionManager` — coordinates signal preemption requests: sends preempt commands to signal controllers along the emergency route, and releases them after the vehicle passes |

### 3.5 Metrics (`metrics/`)

Collects and reports simulation performance data.

| Module | Responsibility |
|--------|---------------|
| `collector.py` | `MetricsCollector` — subscribes to events and accumulates metrics (avg wait time, throughput, emergency response time, queue lengths) |
| `reporter.py` | `MetricsReporter` — exports metrics as dicts, JSON, or summaries for API consumption |

### 3.6 Configuration (`config/`)

| Module | Responsibility |
|--------|---------------|
| `settings.py` | `SimulationConfig`, `GridConfig`, `SignalConfig`, `SpawnerConfig` — dataclasses with sensible defaults, loadable from YAML/JSON |

### 3.7 API Layer (`api/`) — Phase 4+

| Module | Responsibility |
|--------|---------------|
| `app.py` | FastAPI application factory |
| `routes.py` | REST endpoints: create simulation, get state, control playback |
| `websocket.py` | WebSocket handler streaming real-time simulation state to frontend |

### 3.8 AI Layer (`ai/`) — Phase 6

| Module | Responsibility |
|--------|---------------|
| `environment.py` | Gymnasium-compatible RL environment wrapping the simulator |
| `agent.py` | RL agent wrapper (PPO, DQN, etc.) |
| `rewards.py` | Reward functions (minimize emergency travel time, minimize avg wait, etc.) |

---

## 4. Simulation Model

### 4.1 Time Model

- **Discrete-time**: simulation advances in fixed-duration ticks (default: 1 second).
- The `SimulationClock` tracks the current tick number and elapsed simulation time.
- All state transitions happen atomically within a tick.

### 4.2 Space Model (Cellular Automaton)

- Roads are divided into **cells** of uniform length (e.g., 7.5m — one vehicle length).
- Each cell is either **empty** or **occupied** by exactly one vehicle.
- Vehicles advance by 1 cell per tick (speed = 1 cell/tick at base speed).
- A vehicle cannot move into an occupied cell (simple car-following).

```
Road: Intersection A ──────────────► Intersection B
      [V1][ ][ ][V2][ ][ ][ ][ ][ ][ ]
       ◄── cells ──────────────────────►
```

### 4.3 Movement Rules

Each tick, vehicles are processed in order (front-to-back on each road):

1. **At intersection entry**: check signal state for the vehicle's direction.
   - GREEN → vehicle enters the intersection and moves to next road.
   - RED/YELLOW → vehicle waits (stays in last cell).
2. **On road**: if next cell is empty, advance. Otherwise, wait.
3. **Reached destination**: vehicle is removed from the network.

### 4.4 Signal Phases

An intersection has a `SignalPlan` consisting of ordered `SignalPhase` entries:

```
SignalPhase(directions={NORTH, SOUTH}, state=GREEN, duration=30)
SignalPhase(directions={NORTH, SOUTH}, state=YELLOW, duration=5)
SignalPhase(directions={EAST, WEST}, state=GREEN, duration=30)
SignalPhase(directions={EAST, WEST}, state=YELLOW, duration=5)
```

The controller cycles through phases, giving green time to one axis at a time.

---

## 5. Emergency Preemption Flow

This is the core feature of UrbanFlow. The sequence:

```
1. Emergency vehicle spawns with a destination
       │
2. EmergencyRouter computes optimal route
       │
       ▼
3. EmergencyDetector monitors vehicle position each tick
       │
       ▼
4. Vehicle approaches intersection (within N cells)
       │
       ▼
5. PreemptionManager sends preemption request to that
   intersection's SignalController
       │
       ▼
6. SignalController overrides current phase → GREEN for
   emergency vehicle's approach direction
       │
       ▼
7. Emergency vehicle passes through
       │
       ▼
8. PreemptionManager releases preemption
       │
       ▼
9. SignalController resumes normal operation
       │
       ▼
10. Repeat steps 4-9 for each intersection along route
```

**Look-ahead preemption**: The system can preempt signals N intersections ahead
of the emergency vehicle, creating a "green wave" corridor.

---

## 6. Event System

Components communicate through an `EventBus` using publish-subscribe:

| Event | Emitted By | Consumed By |
|-------|-----------|-------------|
| `VehicleSpawned` | Spawner | MetricsCollector |
| `VehicleMoved` | Simulator | EmergencyDetector, MetricsCollector |
| `VehicleArrived` | Simulator | MetricsCollector |
| `SignalChanged` | SignalController | MetricsCollector |
| `EmergencyDetected` | EmergencyDetector | PreemptionManager |
| `PreemptionStarted` | PreemptionManager | SignalController, MetricsCollector |
| `PreemptionEnded` | PreemptionManager | SignalController, MetricsCollector |

---

## 7. Data Flow Per Tick

```
┌─────────────┐
│  tick N      │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ 1. Clock.advance()│
└──────┬───────────┘
       ▼
┌──────────────────┐
│ 2. Spawner        │ → generate new vehicles at entry points
│    .spawn()       │
└──────┬───────────┘
       ▼
┌──────────────────┐
│ 3. Emergency      │ → check if emergency vehicles are near intersections
│    Detector       │ → emit EmergencyDetected events
│    .scan()        │
└──────┬───────────┘
       ▼
┌──────────────────┐
│ 4. Preemption     │ → process EmergencyDetected events
│    Manager        │ → send preemption requests to controllers
│    .process()     │
└──────┬───────────┘
       ▼
┌──────────────────┐
│ 5. Signal         │ → each controller updates its intersection's signal
│    Controllers    │ → honor preemption if active
│    .update()      │
└──────┬───────────┘
       ▼
┌──────────────────┐
│ 6. Vehicle        │ → move vehicles forward (respecting signals & occupancy)
│    Movement       │ → remove arrived vehicles
└──────┬───────────┘
       ▼
┌──────────────────┐
│ 7. Metrics        │ → record wait times, throughput, positions
│    .collect()     │
└──────┬───────────┘
       ▼
┌──────────────────┐
│ 8. Emit state     │ → push state snapshot for API/visualization
│    snapshot       │
└──────────────────┘
```

---

## 8. Package Structure

```
src/urban_flow/
├── __init__.py
│
├── core/                        # Domain models — zero external deps
│   ├── __init__.py
│   ├── types.py                 # Enums, type aliases, Position
│   ├── road.py                  # Road (directed edge with cells)
│   ├── intersection.py          # Intersection (node with signal)
│   ├── vehicle.py               # Vehicle, EmergencyVehicle
│   ├── signal.py                # SignalPhase, SignalPlan
│   └── grid.py                  # RoadNetwork (graph)
│
├── engine/                      # Simulation engine
│   ├── __init__.py
│   ├── clock.py                 # SimulationClock
│   ├── spawner.py               # VehicleSpawner
│   ├── events.py                # EventBus + event dataclasses
│   └── simulator.py             # Simulator (tick loop)
│
├── signals/                     # Signal control strategies
│   ├── __init__.py
│   ├── controller.py            # SignalController protocol
│   ├── fixed_time.py            # FixedTimeController
│   └── adaptive.py              # AdaptiveController
│
├── emergency/                   # Emergency vehicle handling
│   ├── __init__.py
│   ├── detector.py              # EmergencyDetector
│   ├── router.py                # EmergencyRouter (shortest path)
│   └── preemption.py            # PreemptionManager
│
├── metrics/                     # Metrics collection & reporting
│   ├── __init__.py
│   ├── collector.py             # MetricsCollector
│   └── reporter.py              # MetricsReporter
│
├── config/                      # Configuration
│   ├── __init__.py
│   └── settings.py              # Dataclass-based settings
│
├── api/                         # REST API + WebSocket (Phase 4+)
│   ├── __init__.py
│   ├── app.py
│   ├── routes.py
│   └── websocket.py
│
└── ai/                          # AI optimization (Phase 6)
    ├── __init__.py
    ├── environment.py
    ├── agent.py
    └── rewards.py
```

---

## 9. Phase-to-Module Mapping

| Phase | Modules Involved | What Gets Built |
|-------|-----------------|-----------------|
| **1. Basic Grid Simulation** | `core/`, `engine/` (clock, spawner, simulator) | Grid network, vehicle movement, basic tick loop |
| **2. Traffic Light Logic** | `signals/`, `core/signal.py` | Signal phases, fixed-time controller, signal-aware movement |
| **3. Emergency Vehicle Priority** | `emergency/`, `engine/events.py` | Detection, routing, preemption, green wave corridor |
| **4. Backend API + Visualization** | `api/`, `metrics/` | FastAPI server, WebSocket streaming, metrics endpoints |
| **5. Real-time Engine** | `engine/` (enhanced) | Async tick loop, real-time clock, playback controls |
| **6. AI Optimization** | `ai/` | RL environment, training pipeline, learned signal control |
| **7. Production Deployment** | `infra/` (new) | Dockerfiles, CI/CD, monitoring, deployment configs |

---

## 10. Key Interfaces (Contracts)

These are the primary interfaces/protocols that define module boundaries:

```python
# --- Signal Controller Protocol ---
class SignalController(Protocol):
    def update(self, intersection: Intersection, tick: int) -> SignalPhase:
        """Determine the current signal phase for an intersection."""
        ...

    def request_preemption(self, direction: Direction) -> None:
        """Request green for the given direction (emergency override)."""
        ...

    def release_preemption(self) -> None:
        """Return to normal signal operation."""
        ...


# --- Simulator Interface ---
class Simulator:
    def setup(self, network: RoadNetwork, config: SimulationConfig) -> None: ...
    def tick(self) -> SimulationState: ...
    def run(self, num_ticks: int) -> SimulationResult: ...
    def subscribe(self, event_type: type, handler: Callable) -> None: ...


# --- Emergency Router Interface ---
class EmergencyRouter:
    def compute_route(
        self, vehicle: EmergencyVehicle, network: RoadNetwork
    ) -> Route: ...


# --- Metrics Collector Interface ---
class MetricsCollector:
    def on_event(self, event: SimulationEvent) -> None: ...
    def get_summary(self) -> MetricsSummary: ...
```

---

## 11. Technology Choices

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Language | Python 3.12+ | Excellent for simulation, data science, ML |
| Package manager | uv | Fast, modern Python package management |
| Domain models | dataclasses | No external deps, built-in, immutable-friendly |
| Graph algorithms | Standard library + custom | Keep core dependency-free; networkx as optional |
| API framework | FastAPI (Phase 4) | Async-native, WebSocket support, auto-docs |
| RL framework | Gymnasium + Stable-Baselines3 (Phase 6) | Industry standard RL interfaces |
| Testing | pytest | De facto standard for Python |
| Visualization | Browser-based (Phase 4) | Canvas/SVG rendered by frontend |
