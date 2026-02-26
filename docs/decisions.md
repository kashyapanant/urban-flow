# Urban Flow — Architectural Decision Records

---

## Decision: Grid Representation — 2D Array

**Date:** 2026-02-21
**Status:** Accepted

**Context:** The simulation world is a 10×10 grid of cells. We need a data structure that supports fast cell lookups by (x, y), neighbor traversal, and vehicle placement/removal. Two natural candidates exist: a 2D array or an adjacency-list graph.

**Decision:** Use a 2D array (`list[list[Cell]]`).

**Alternatives considered:**
- **Graph (adjacency list):** Each cell is a node; edges connect traversable neighbors. Better for irregular topologies (real city maps with one-way streets, curves, dead ends). Would future-proof the data structure for later phases.

**Consequences:**
- (+) Direct O(1) cell access by coordinates — trivially maps to the visual grid.
- (+) Neighbor lookups are simple arithmetic (±1 on x or y), no need to store edge lists.
- (+) Lower memory overhead and simpler serialization for frontend snapshots.
- (−) When the project evolves to real city maps (irregular road networks), we will need to refactor to a graph representation. However, the simulation logic (A\* pathfinding, movement along a path) is already graph-compatible — A\* works on any structure that provides neighbors and costs.
- (−) Does not naturally represent one-way streets or weighted edges. Acceptable for MVP since all roads are bidirectional single-lane.

---

## Decision: Simulation Model — Tick-Based Synchronous Loop

**Date:** 2026-02-21
**Status:** Accepted

**Context:** The simulation needs a temporal model. Requirements specify tick-based timing: vehicles move 1 cell per tick, traffic light phases last N ticks, tick speed is configurable.

**Decision:** Use a synchronous tick-based loop where one call to `tick()` advances the entire world by one discrete time step.

**Alternatives considered:**
- **Event-driven (discrete event simulation with priority queue):** Each event (vehicle arrives at cell, light changes phase) is scheduled at a future time. The engine processes events in chronological order. Better for heterogeneous timing (e.g., vehicles with different speeds, variable-duration events).

**Consequences:**
- (+) Deterministic — given the same initial state and random seed, the simulation produces identical results.
- (+) Trivial pause/resume — just stop calling `tick()`.
- (+) Easy to reason about state: after each tick, the world is in a consistent state.
- (+) Naturally matches the requirements (everything is defined in tick units).
- (−) All entities share the same time granularity. If future phases need vehicles with different speeds (e.g., trucks at 0.5 cells/tick), we'd need fractional tick handling or sub-tick scheduling.
- (−) Tick processing is O(vehicles + intersections) per tick — fine for 10×10 but could become a concern for very large grids. Profiling will tell us when/if we need to optimize.

---

## Decision: Concurrency Model — Single-Threaded asyncio

**Date:** 2026-02-21
**Status:** Accepted

**Context:** The backend needs to run a simulation tick loop *and* serve HTTP/WebSocket requests concurrently.

**Decision:** Run everything on a single Python asyncio event loop. The simulation tick loop is an async coroutine that `await`s between ticks. The FastAPI web server runs on the same loop.

**Alternatives considered:**
- **Threading (simulation thread + web server thread):** The simulation runs in a background thread; the web server runs in the main thread. Shared state protected by locks.
- **Multiprocessing:** Simulation in a separate process, communicating via IPC (queues, shared memory).

**Consequences:**
- (+) No locks, no race conditions, no shared mutable state between threads — the single-threaded model eliminates an entire class of bugs.
- (+) asyncio is a natural fit for I/O-bound work (WebSocket sends, HTTP responses).
- (+) Simpler deployment — one process, one event loop.
- (−) A slow tick could block the event loop and delay WebSocket sends. Mitigation: the 10×10 grid with <100 vehicles will process a tick in <1ms. If future grid sizes cause tick times to exceed the tick interval, we can offload computation to a thread pool via `asyncio.to_thread()`.
- (−) Cannot utilize multiple CPU cores. Acceptable — no CPU-bound parallelism is needed at this scale.

---

## Decision: Web Framework — FastAPI

**Date:** 2026-02-21
**Status:** Accepted

**Context:** We need an HTTP + WebSocket server to expose the simulation state and controls to the browser frontend.

**Decision:** Use FastAPI (with Uvicorn as the ASGI server).

**Alternatives considered:**
- **Flask + Flask-SocketIO:** Mature, large ecosystem. However, Flask is WSGI (synchronous by default). WebSocket support requires Flask-SocketIO which uses its own event loop (eventlet or gevent), adding complexity and a mismatch with native asyncio.
- **Starlette (bare):** FastAPI is built on Starlette. Using Starlette directly would avoid the Pydantic dependency but lose automatic request validation, OpenAPI docs, and dependency injection.

**Consequences:**
- (+) Native `async`/`await` — aligns with our single-threaded asyncio model.
- (+) Built-in WebSocket support via Starlette.
- (+) Pydantic models for request/response validation (catches bad config values at the API boundary).
- (+) Auto-generated OpenAPI docs at `/docs` — useful for development and testing.
- (−) Slightly heavier than bare Starlette.
- (−) Team must be comfortable with async Python patterns. Acceptable for this project.

---

## Decision: Real-Time Communication — WebSocket

**Date:** 2026-02-21
**Status:** Accepted

**Context:** The frontend needs real-time state updates every tick (up to 10 times/second). The frontend also needs to send commands (pause, resume, speed changes) to the backend.

**Decision:** Use a single WebSocket connection for bidirectional communication.

**Alternatives considered:**
- **Server-Sent Events (SSE) + REST:** SSE for server→client state pushes; REST POST endpoints for client→server commands. Simpler server-side (SSE is just a long-lived HTTP response), but requires two separate channels and SSE has a ~6 connection limit per domain in some browsers.
- **Polling:** Client polls `GET /state` every 100ms. Simple but wasteful and introduces latency jitter.

**Consequences:**
- (+) Single bidirectional channel — both state updates and commands flow over one connection.
- (+) Lower per-message overhead than HTTP (no headers per message after handshake).
- (+) Well supported in all modern browsers via the native `WebSocket` API.
- (−) Slightly more complex connection lifecycle (open, close, error, reconnect). Mitigated by implementing exponential-backoff reconnect in the frontend.
- (−) Harder to debug than REST (no browser dev tools "replay" for WebSocket messages). Mitigated by structured logging on the server side.

---

## Decision: Frontend Technology — Vanilla JS + HTML5 Canvas

**Date:** 2026-02-21
**Status:** Accepted

**Context:** The frontend needs to render a 10×10 grid with colored cells, vehicle shapes, and traffic light indicators, updating up to 10 times per second. It also needs simple controls (button, slider, input fields) and a metrics display panel.

**Decision:** Vanilla JavaScript (no framework, no build step) with HTML5 Canvas for grid rendering and standard HTML/CSS for controls.

**Alternatives considered:**
- **React / Vue / Svelte:** Component-based frameworks. Provide state management, reactivity, and reusable components. However, the UI is simple (one canvas + a few controls), and a framework adds a build step (Node.js, bundler), dependency management, and cognitive overhead disproportionate to the UI complexity.
- **Three.js / PixiJS:** 2D/3D rendering libraries. Overkill for a 10×10 colored grid.
- **SVG-based rendering:** Render each cell as an SVG element. Works well for small grids and is easier to make interactive (click events on cells). However, SVG DOM manipulation at 10 fps with 100 elements could cause layout thrashing, and Canvas gives us more rendering control.

**Consequences:**
- (+) Zero build step — open `index.html` in a browser (or serve via FastAPI static files).
- (+) Canvas is highly performant for 2D rendering; 100 cells at 10 fps is trivial.
- (+) No framework lock-in; easy to understand for any JavaScript developer.
- (−) No component abstraction — if the UI grows significantly (e.g., multiple panels, interactive grid editing), we'll feel the lack of a component model. At that point, migrating to a lightweight framework (Svelte or Preact) would be appropriate.
- (−) Manual DOM manipulation for controls and metrics. Acceptable given the small number of UI elements.

---

## Decision: Persistence — In-Memory Only

**Date:** 2026-02-21
**Status:** Accepted

**Context:** We need to decide whether and how to persist simulation state (grid layout, vehicle histories, metrics over time).

**Decision:** All state lives in Python objects in memory. No database, no file-based persistence.

**Alternatives considered:**
- **SQLite:** Persist metrics history, completed vehicle records, simulation snapshots for replay. Adds disk I/O, schema management, and migration complexity.
- **Redis:** In-memory store with optional persistence. Could serve as a pub/sub broker between simulation and API. Adds an external dependency (Redis server).

**Consequences:**
- (+) Simplest possible approach — no external dependencies, no schema, no connection management.
- (+) Fast — no serialization/deserialization overhead beyond WebSocket JSON encoding.
- (+) Appropriate for an ephemeral simulation with no persistence requirements.
- (−) State is lost on server restart. Users must re-start the simulation.
- (−) No historical metrics (can't graph improvement % over time). If this becomes a requirement, we can add SQLite for metrics storage without changing the simulation core.

---

## Decision: Pathfinding Algorithm — A*

**Date:** 2026-02-21
**Status:** Accepted

**Context:** Vehicles need to find paths from origin to destination on the grid. Normal vehicles need shortest paths; emergency vehicles need fastest paths considering traffic light states.

**Decision:** Use A\* with Manhattan distance heuristic.

**Alternatives considered:**
- **Dijkstra's algorithm:** Equivalent to A\* with heuristic = 0. Finds optimal paths but explores more nodes (no heuristic guidance). On a 10×10 grid the difference is negligible, but A\* is conceptually cleaner for grid pathfinding.
- **BFS (Breadth-First Search):** Finds shortest path in unweighted graphs. Works for normal vehicles but cannot handle weighted edges (traffic light penalties for emergency vehicles).

**Consequences:**
- (+) Optimal — guaranteed to find the shortest/fastest path given an admissible heuristic.
- (+) Efficient on grids — Manhattan distance is a tight, admissible heuristic that prunes the search space significantly.
- (+) Flexible — the same algorithm handles both vehicle types by varying the cost function.
- (−) Emergency vehicle cost function depends on current traffic light state at path-computation time. Since paths are pre-computed at spawn (no rerouting), the path may become suboptimal as lights change. This is acceptable per requirements ("fixed pre-computed path, no mid-journey rerouting") and the preemption mechanism compensates by turning lights green ahead of the emergency vehicle.

---

## Decision: Tick Execution Order

**Date:** 2026-02-21
**Status:** Accepted

**Context:** Within a single tick, multiple systems must update (traffic lights, vehicles, spawning, metrics). The order affects correctness — e.g., should a vehicle see the light state *before* or *after* lights tick?

**Decision:** Fixed six-phase order: (1) preemption scan → (2) traffic light update → (3) vehicle movement → (4) spawning → (5) cleanup & metrics → (6) broadcast.

**Alternatives considered:**
- **Simultaneous resolution:** All vehicles compute their desired next cell, then resolve conflicts in a separate pass. More physically realistic but significantly more complex.
- **Random order:** Process vehicles in random order each tick. Avoids systematic bias but makes the simulation non-deterministic.

**Consequences:**
- (+) Deterministic and easy to reason about.
- (+) Preemption scan before light update ensures that an emergency vehicle's preemption request takes effect in the same tick.
- (+) Light update before vehicle movement ensures vehicles see the current tick's light state (not the previous tick's).
- (+) Spawning after movement ensures newly spawned vehicles don't block existing vehicles that want to exit the grid edge.
- (−) Priority-ordered movement gives a systematic advantage to emergency vehicles and vehicles closer to their destination. This is by design (requirements specify this priority), but means two normal vehicles in a head-on conflict will always resolve the same way.

---

## Decision: Traffic Light Phase Model — Dual-Axis Four-Phase

**Date:** 2026-02-21
**Status:** Accepted

**Context:** Requirements specify "a full four-phase cycle (green, yellow, red, left-turn arrow), each phase lasting 3 ticks." We need to define how this maps to a grid intersection with two traffic axes (NS and EW).

**Decision:** Each intersection has two axes. The active axis cycles through four phases: green → leftTurn → yellow → red. When the active axis completes red, the other axis becomes active and starts its green phase. Full cycle = 24 ticks.

**Alternatives considered:**
- **Single-axis model:** The intersection has one global phase (green/yellow/red/leftTurn) and a separate "active direction" flag. Simpler to implement but conflates phase and direction.
- **Simplified two-phase:** Just green/red for each axis (drop leftTurn and yellow). Simpler but doesn't match requirements.

**Consequences:**
- (+) Matches the four-phase requirement exactly.
- (+) The yellow phase provides a natural preemption transition window.
- (+) Left-turn phase adds realism; vehicles turning at intersections have a dedicated phase.
- (−) 24-tick full cycle means each direction gets 6 ticks of "go" time (3 green + 3 leftTurn) out of every 24 ticks. This could cause congestion if vehicle density is high. Tunable via the `phase_duration` config.
- (−) Distinguishing "straight-through" vs "turning" in vehicle movement logic adds implementation complexity. Simplification: during MVP, both green and leftTurn phases allow all movement through the intersection for the active axis. The visual distinction exists (the frontend renders different phase colors) but the movement rule is the same.
