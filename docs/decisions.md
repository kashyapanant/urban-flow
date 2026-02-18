# Design Decisions Log

Each entry follows a lightweight ADR (Architecture Decision Record) format:
**Context** (why), **Decision** (what), **Alternatives** (what else),
**Consequences** (trade-offs).

---

## ADR-001: Discrete-Time Simulation Model

**Date:** 2026-02-17
**Status:** Accepted

**Context:**
We need a simulation model to advance vehicle positions and signal states.
The two main approaches are discrete-time (fixed tick) and event-driven
(next-event scheduling).

**Decision:**
Use a **discrete-time** model where the world advances in fixed ticks
(default 1 second per tick). All state transitions happen atomically
within a tick.

**Alternatives considered:**
- *Event-driven simulation:* More efficient when traffic is sparse (only
  process events, not empty ticks). However, significantly more complex to
  implement, harder to reason about, and harder to visualize frame-by-frame.

**Consequences:**
- Simpler implementation and debugging.
- Straightforward frame-by-frame visualization (each tick = one frame).
- Slightly less efficient for sparse scenarios (empty ticks still processed).
- Can be optimized later if performance becomes an issue.

---

## ADR-002: Cellular Automaton for Vehicle Movement

**Date:** 2026-02-17
**Status:** Accepted

**Context:**
Vehicles need to move along roads between intersections. We need a spatial
model for roads.

**Decision:**
Divide each road into discrete **cells** of uniform length (~7.5m, roughly
one vehicle length). Each cell holds at most one vehicle. Vehicles advance
by one cell per tick (at base speed).

**Alternatives considered:**
- *Continuous position model:* Vehicles have float positions, move by
  velocity * dt. More realistic but requires collision detection, float
  arithmetic, and is harder to visualize on a grid.
- *Nagel-Schreckenberg model:* Multi-speed cellular automaton with
  acceleration, braking, and randomization. More realistic traffic flow
  but more complex for Phase 1.

**Consequences:**
- Simple car-following: a vehicle waits if the next cell is occupied.
- Easy to compute occupancy and queue lengths.
- Speed is quantized (1 cell/tick at base), limiting realism.
- Can upgrade to Nagel-Schreckenberg in a later phase without changing
  the overall architecture.

---

## ADR-003: Graph-Based Road Network

**Date:** 2026-02-17
**Status:** Accepted

**Context:**
The road network connects intersections. We need a data structure that
supports grid layouts (Phase 1) but is flexible enough for arbitrary
topologies later.

**Decision:**
Represent the network as a **directed graph** using an adjacency list.
Intersections are nodes, roads are directed edges. Provide a factory
method `RoadNetwork.create_grid(rows, cols)` for regular grids.

**Alternatives considered:**
- *2D array:* Simple for grids but cannot represent non-grid topologies
  (T-junctions, one-way streets, highway ramps).
- *NetworkX:* Mature graph library, but adds an external dependency to
  the core domain layer, which we want dependency-free.

**Consequences:**
- Supports arbitrary topologies from day one.
- BFS shortest path works out of the box.
- Slightly more code than a 2D array for simple grids.
- Can integrate NetworkX in outer layers if we need advanced graph
  algorithms later.

---

## ADR-004: Strategy Pattern for Signal Controllers

**Date:** 2026-02-17
**Status:** Accepted

**Context:**
Different intersections may need different signal control strategies
(fixed-time, adaptive, AI-driven). We need a way to swap strategies
without changing the simulation engine.

**Decision:**
Define a `SignalController` **Protocol** (structural typing) with three
methods: `update()`, `request_preemption()`, `release_preemption()`.
Each intersection is assigned a controller instance. Controllers are
interchangeable at runtime.

**Alternatives considered:**
- *Inheritance hierarchy:* Base class with abstract methods. Works but
  is more rigid than a Protocol and couples implementations to a base.
- *Single configurable controller:* One class with mode flags. Simpler
  but harder to extend and test.

**Consequences:**
- New control strategies (adaptive, AI) just implement the protocol.
- Intersections can mix strategies (e.g., AI on main corridors, fixed
  on side streets).
- Emergency preemption is built into the protocol from the start.

---

## ADR-005: Event Bus for Inter-Component Communication

**Date:** 2026-02-17
**Status:** Accepted

**Context:**
The simulator, signal controllers, emergency system, and metrics all need
to communicate. Direct method calls create tight coupling.

**Decision:**
Implement a synchronous **EventBus** (publish-subscribe) for communication.
Components publish typed event dataclasses; interested components subscribe
to specific event types.

**Alternatives considered:**
- *Direct callbacks:* Simpler but creates spaghetti dependencies.
- *Async event bus:* Better for real-time but overkill for Phase 1
  synchronous simulation.

**Consequences:**
- Loose coupling: the simulator doesn't need to know about metrics.
- Easy to add new observers (e.g., logging, visualization) without
  touching existing code.
- Synchronous dispatch means events are processed in-order within a tick.
- Can evolve to async dispatch in Phase 5.

---

## ADR-006: Signal Preemption with Look-Ahead

**Date:** 2026-02-17
**Status:** Accepted

**Context:**
Emergency vehicles need signals turned green before they arrive at an
intersection, not when they're already waiting at a red light.

**Decision:**
Implement **look-ahead preemption**: the system preempts signals N
intersections ahead of the emergency vehicle's current position
(configurable, default N=2). This creates a "green wave" corridor.

**Alternatives considered:**
- *Reactive preemption:* Only preempt the immediate next intersection.
  Simpler but the vehicle may still encounter reds if signal transition
  takes time.
- *Full corridor preemption:* Preempt every intersection on the route at
  once. Disrupts traffic on the entire route simultaneously.

**Consequences:**
- Balance between responsiveness and traffic disruption.
- Signals ahead have time to transition safely (yellow phase before green).
- Configurable look-ahead allows tuning per deployment.
- The AI layer (Phase 6) can learn optimal look-ahead values.

---

## ADR-007: Pure Domain Layer (Zero External Dependencies)

**Date:** 2026-02-17
**Status:** Accepted

**Context:**
The core domain models (Grid, Road, Vehicle, Signal) are the foundation
of the entire system. We want them to be stable, testable, and portable.

**Decision:**
The `core/` package uses **only Python standard library** features
(dataclasses, enums, typing, collections). No external packages.

**Alternatives considered:**
- *Pydantic models:* Automatic validation and serialization, but adds a
  dependency and runtime overhead for hot-path domain objects.
- *attrs:* Lighter than Pydantic but still an external dependency.

**Consequences:**
- Core models are fast (no validation overhead on every instantiation).
- Zero install requirements for the domain layer.
- Validation can be added at the boundary (API layer, config loading).
- Can always wrap core models with Pydantic for API serialization later.

---

## ADR-008: Python 3.12+ with uv Package Manager

**Date:** 2026-02-17
**Status:** Accepted

**Context:**
Need to choose Python version and package management tooling.

**Decision:**
Target **Python 3.12+** and use **uv** for package management and
virtual environments.

**Alternatives considered:**
- *Poetry:* Mature but slower than uv for dependency resolution.
- *pip + venv:* Standard but lacks lockfile and workspace features.

**Consequences:**
- Access to modern Python features (improved type hints, performance).
- Fast dependency resolution and installs via uv.
- pyproject.toml as the single source of project metadata.

---

## ADR-009: Tick-Order Processing (Front-to-Back)

**Date:** 2026-02-17
**Status:** Accepted

**Context:**
When multiple vehicles are on the same road, the order in which they're
processed within a tick matters. Processing back-to-front could cause
vehicles to "teleport" through each other.

**Decision:**
Process vehicles **front-to-back** on each road (highest cell index first).
A vehicle only moves forward if the cell ahead is empty after the vehicle
ahead of it has been processed.

**Alternatives considered:**
- *Simultaneous update:* Compute all new positions, then apply. Avoids
  ordering issues but requires a copy of the entire state each tick.
- *Random order:* Adds stochasticity but can cause unrealistic behavior.

**Consequences:**
- Deterministic, predictable vehicle movement.
- No "teleportation" artifacts.
- Slightly favors vehicles already in front (realistic in traffic flow).

---

## ADR-010: FastAPI for Backend API (Phase 4)

**Date:** 2026-02-17
**Status:** Proposed (for Phase 4)

**Context:**
Phase 4 needs a REST API and real-time WebSocket for the visualization
frontend.

**Decision:**
Use **FastAPI** as the web framework.

**Alternatives considered:**
- *Flask:* Simpler but lacks native async and WebSocket support.
- *Django:* Full-featured but heavyweight for an API-only service.

**Consequences:**
- Native async support aligns with Phase 5 real-time engine.
- Built-in WebSocket support for streaming simulation state.
- Automatic OpenAPI documentation.
- Adds fastapi + uvicorn as dependencies (only in Phase 4+).
