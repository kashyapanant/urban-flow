# Urban Flow — System Architecture

## 1. Overview

Urban Flow is a tick-based traffic simulation that models emergency vehicle signal preemption on a 10×10 grid. The system has two main runtime components: a **Python backend** (simulation engine + API server) and a **browser-based frontend** (real-time grid visualization + controls).

The simulation is deterministic and single-threaded. Each tick produces a complete, consistent state snapshot that is broadcast to connected clients over WebSocket.

---

## 2. Module Dependency Graph

```
┌──────────────────────────────┐
│         Frontend             │
│  (Vanilla JS + HTML5 Canvas) │
└──────────────┬───────────────┘
               │ WebSocket / REST
┌──────────────┴───────────────┐
│          API Layer           │
│    (FastAPI + WebSocket)     │
└──────────────┬───────────────┘
               │
┌──────────────┴───────────────┐
│      Simulation Engine       │
│      (tick orchestrator)     │
└──┬─────────┬─────────┬───┬──┘
   │         │         │   │
   ▼         ▼         ▼   │
┌──────┐ ┌────────┐ ┌─────┴────┐
│ Grid │ │Vehicle │ │ Traffic  │
│World │ │Manager │ │  Light   │
└──────┘ └───┬────┘ │ Manager  │
             │      └──────────┘
        ┌────┴─────┐
        │Pathfinder│
        │   (A*)   │
        └──────────┘
```

**Dependency rules:**
- Arrows point from consumer → dependency.
- The Simulation Engine orchestrates Grid, VehicleManager, and TrafficLightManager. It is the only module that mutates world state.
- The API Layer holds a reference to the Simulation Engine but never mutates simulation objects directly — it calls engine methods.
- The Pathfinder is a stateless utility consumed by VehicleManager.
- The Frontend has zero backend imports; it communicates exclusively via WebSocket and REST.

---

## 3. Core Modules

### 3.1 Grid (`simulation/grid.py`)

The world model. A 10×10 2D array of cells. Each cell has a type (`road`, `intersection`, `obstacle`), an optional occupying vehicle reference, and an optional traffic light reference (intersections only).

**Responsibilities:**
- Store and query cell state
- Provide neighbor lookups (up/down/left/right traversable cells)
- Track vehicle placement (one vehicle per cell invariant)
- Expose edge cells for vehicle spawning
- Produce serializable snapshots for the frontend

**Default grid layout — "city blocks" pattern:**

Streets run East–West at rows `{0, 3, 6, 9}`. Avenues run North–South at columns `{0, 3, 6, 9}`. Their crossings are intersections; remaining road-row/column cells are roads; everything else is an obstacle (building).

```
I · · I · · I · · I     I = intersection
· O O · O O · O O ·     · = road (on a street or avenue)
· O O · O O · O O ·     O = obstacle / building
I · · I · · I · · I
· O O · O O · O O ·
· O O · O O · O O ·
I · · I · · I · · I
· O O · O O · O O ·
· O O · O O · O O ·
I · · I · · I · · I
```

This yields 16 intersections, 48 road cells, and 36 obstacle cells. All 36 perimeter cells are traversable (roads or intersections), providing abundant spawn points.

### 3.2 Vehicle & VehicleManager (`simulation/vehicle.py`)

A Vehicle is an entity with an id, type (normal/emergency), pre-computed path, and status (moving/waiting/arrived). The VehicleManager owns the collection of active vehicles and handles spawning, movement, and removal.

**Spawning:**
1. For each eligible edge cell (traversable and unoccupied), roll against `spawnRate`.
2. Pick a random destination on a different edge.
3. Compute a path via Pathfinder. If no valid path, retry with a new destination (max 10 retries).
4. Vehicle type is `emergency` with a configurable probability (e.g., 10%), otherwise `normal`.

**Movement (per tick):**
1. Sort vehicles by priority: emergency vehicles first, then by fewest cells remaining to destination (tiebreak: random).
2. For each vehicle in priority order:
   - Look at the next cell on its path.
   - If the cell is unoccupied **and** traffic-light permits entry → move (claim the cell, release the old one).
   - Otherwise → stay (status = `waiting`).
3. Mark vehicles that reached their destination as `arrived`.

The priority ordering plus sequential claim resolution ensures that edge-case #1 (two vehicles targeting the same cell) is handled deterministically without a separate conflict-resolution pass.

### 3.3 TrafficLight & TrafficLightManager (`simulation/traffic_light.py`)

Each intersection has a TrafficLight with two axes (NS and EW). At any moment, one axis is the **active axis**; the other axis is red.

**Four-phase cycle per axis:**

| Phase      | Duration (default) | Meaning                                 |
|------------|--------------------|-----------------------------------------|
| `green`    | 3 ticks            | Straight-through traffic may proceed    |
| `leftTurn` | 3 ticks            | Turning traffic may proceed             |
| `yellow`   | 3 ticks            | Warning — vehicles should not enter     |
| `red`      | 3 ticks            | Stop (other axis becomes active)        |

When the active axis completes its red phase, the active axis flips (NS ↔ EW) and the new axis begins its green phase.  Full cycle: **24 ticks** (4 phases × 3 ticks × 2 axes).

**Movement permission logic:**
A vehicle approaching an intersection from direction D is on axis A (NS if traveling North or South, EW if traveling East or West). It may enter if:
- Axis A is the active axis **and** the current phase is `green` or `leftTurn`.
- Yellow means *do not enter* (vehicles already inside may exit).

**Preemption model:**

1. An emergency vehicle's path is scanned up to 3 cells ahead each tick.
2. For each intersection within that look-ahead, `request_preemption(intersection, vehicle)` is called.
3. If the intersection is already serving the emergency vehicle's axis, no change.
4. If the intersection is serving the cross axis, it immediately transitions to **yellow** (2 ticks), then **red** (instant), then flips the active axis to **green** for the emergency direction.
5. The `preemptedBy` field is set to the claiming emergency vehicle. A second emergency vehicle approaching the same intersection waits (first-come-first-served per edge case #2).
6. When the emergency vehicle clears the intersection (moves past it), `release_preemption` is called and normal cycling resumes from the current axis's green phase.

### 3.4 Pathfinder (`simulation/pathfinder.py`)

A stateless A\* implementation.

**Normal vehicles** — shortest path:
- Cost per cell: 1
- Heuristic: Manhattan distance to destination
- Constraint: cell must be traversable (`road` or `intersection`) and not permanently blocked

**Emergency vehicles** — fastest path considering signal state:
- Cost per cell: 1 + penalty for intersections with an unfavorable current light phase (e.g., +2 for red/yellow in the vehicle's travel axis)
- This biases emergency vehicles toward routes with currently-green corridors
- Path is computed once at spawn time (no mid-journey rerouting per requirements)

### 3.5 Simulation Engine (`simulation/engine.py`)

The orchestrator. Owns the Grid, VehicleManager, TrafficLightManager, and Metrics. Runs a tick loop driven by `asyncio`.

**Tick execution order (critical for determinism):**

```
┌─ 1. Preemption scan ────────────────────────────────────┐
│  For each emergency vehicle, scan up to 3 cells ahead.  │
│  Request preemption on upcoming intersections.           │
└─────────────────────────────────────────────────────────┘
         │
┌─ 2. Traffic light update ──────────────────────────────┐
│  Advance all lights by one tick.                        │
│  Process preemption transitions (yellow → red → green). │
│  Release preemptions for cleared intersections.         │
└─────────────────────────────────────────────────────────┘
         │
┌─ 3. Vehicle movement ─────────────────────────────────┐
│  Sort vehicles by priority (emergency first, then by   │
│  remaining distance, then random tiebreak).             │
│  Move or wait each vehicle in order.                    │
└─────────────────────────────────────────────────────────┘
         │
┌─ 4. Vehicle spawning ─────────────────────────────────┐
│  For each unoccupied edge cell, probabilistically      │
│  spawn a new vehicle with a valid path.                 │
└─────────────────────────────────────────────────────────┘
         │
┌─ 5. Cleanup & metrics ────────────────────────────────┐
│  Remove arrived vehicles from grid and active list.     │
│  Update running averages and improvement percentage.    │
└─────────────────────────────────────────────────────────┘
         │
┌─ 6. Broadcast ────────────────────────────────────────┐
│  Snapshot full state → push to all WebSocket clients.  │
└─────────────────────────────────────────────────────────┘
```

**Tick loop:**
```
async def run():
    while simulation.state != "stopped":
        if simulation.state == "paused":
            await asyncio.sleep(0.05)  # yield without busy-waiting
            continue
        simulation.tick()
        await broadcast(simulation.snapshot())
        await asyncio.sleep(1.0 / simulation.tick_speed)
```

The engine exposes methods for pause, resume, speed adjustment, spawn rate changes, and phase duration changes — all of which take effect on the **next** tick (no partial-tick mutations).

### 3.6 API Layer (`api/routes.py`, `api/websocket.py`)

**REST endpoints:**

| Method | Path                      | Purpose                                      |
|--------|---------------------------|----------------------------------------------|
| POST   | `/api/simulation/start`   | Initialize and start (or reset) the simulation |
| POST   | `/api/simulation/pause`   | Pause the tick loop                          |
| POST   | `/api/simulation/resume`  | Resume the tick loop                         |
| PUT    | `/api/simulation/config`  | Update runtime config (tick speed, spawn rate, phase duration) |
| GET    | `/api/simulation/state`   | Return current state snapshot (polling fallback) |
| GET    | `/api/simulation/metrics` | Return current metrics                       |

**WebSocket (`/ws`):**

| Direction | Message Type | Payload |
|-----------|-------------|---------|
| Server → Client | `tick` | Full `SimulationState` snapshot (grid, vehicles, lights, metrics, tickCount) |
| Client → Server | `pause` | — |
| Client → Server | `resume` | — |
| Client → Server | `set_speed` | `{ speed: int }` |
| Client → Server | `set_spawn_rate` | `{ rate: float }` |
| Client → Server | `set_phase_duration` | `{ duration: int }` |

The REST endpoints exist as a fallback and for tooling (curl, tests). The primary real-time channel is WebSocket.

### 3.7 Frontend (`frontend/`)

A zero-build-step browser application: one HTML file, vanilla JavaScript, and HTML5 Canvas.

**Components:**
- **Renderer** (`renderer.js`): Draws the grid on a `<canvas>`. Cells are colored by type; vehicles are drawn as colored shapes (blue = normal, red = emergency); traffic lights are rendered as colored dots at intersections.
- **Controls** (`controls.js`): Pause/resume button, tick-speed slider (1–10), spawn-rate input, phase-duration input. Sends commands over the WebSocket.
- **Metrics display** (`metrics.js`): Shows normal avg ticks, emergency avg ticks, improvement %, and total completed vehicles. Updated every tick.
- **App** (`app.js`): WebSocket lifecycle (connect, reconnect with exponential backoff), message dispatch to renderer/controls/metrics.

---

## 4. Interface Definitions (Pseudocode)

### Grid

```
class Grid:
    __init__(width, height, layout)
    get_cell(x, y) -> Cell
    get_neighbors(x, y) -> list[Cell]
    is_traversable(x, y) -> bool
    is_occupied(x, y) -> bool
    place_vehicle(vehicle, x, y) -> bool
    remove_vehicle(x, y) -> Vehicle | None
    get_edge_cells() -> list[Cell]
    snapshot() -> dict
```

### Cell

```
class Cell:
    x: int
    y: int
    type: CellType           # road | intersection | obstacle
    vehicle: Vehicle | None
    traffic_light: TrafficLight | None
```

### Vehicle

```
class Vehicle:
    id: str
    type: VehicleType        # normal | emergency
    position: tuple[int, int]
    origin: tuple[int, int]
    destination: tuple[int, int]
    path: list[tuple[int, int]]
    path_index: int
    status: VehicleStatus    # moving | waiting | arrived
    ticks_elapsed: int
```

### VehicleManager

```
class VehicleManager:
    spawn_vehicles(grid, pathfinder, traffic_lights, spawn_rate, emergency_probability) -> list[Vehicle]
    move_vehicles(grid, traffic_light_manager) -> None
    collect_arrived() -> list[Vehicle]
    get_all() -> list[Vehicle]
```

### TrafficLight

```
class TrafficLight:
    id: str
    position: tuple[int, int]
    active_axis: Axis            # NS | EW
    current_phase: Phase         # green | leftTurn | yellow | red
    phase_duration: int
    ticks_in_phase: int
    preempted_by: Vehicle | None

    tick() -> None
    can_enter(direction: Direction) -> bool
    request_preemption(vehicle, axis) -> None
    release_preemption() -> None
```

### TrafficLightManager

```
class TrafficLightManager:
    __init__(intersections, phase_duration)
    tick() -> None
    request_preemption(position, vehicle, axis) -> None
    release_preemption(position) -> None
    get_light(position) -> TrafficLight
    get_all() -> list[TrafficLight]
```

### Pathfinder

```
class Pathfinder:
    @staticmethod
    find_path(grid, start, end, vehicle_type, traffic_lights=None) -> list[tuple] | None
```

### SimulationEngine

```
class SimulationEngine:
    __init__(config: SimulationConfig)
    tick() -> SimulationState
    pause() -> None
    resume() -> None
    set_tick_speed(speed: int) -> None
    set_spawn_rate(rate: float) -> None
    set_phase_duration(duration: int) -> None
    snapshot() -> SimulationState
    get_metrics() -> Metrics
```

### Metrics

```
class Metrics:
    normal_avg_ticks: float
    emergency_avg_ticks: float
    improvement: float          # percentage fewer ticks for emergency
    total_completed: int

    record_arrival(vehicle: Vehicle) -> None
```

### SimulationConfig

```
class SimulationConfig:
    grid_width: int = 10
    grid_height: int = 10
    tick_speed: int = 1           # ticks per second (1–10)
    spawn_rate: float = 0.1       # probability per edge cell per tick
    phase_duration: int = 3       # ticks per traffic light phase
    emergency_probability: float = 0.1
```

---

## 5. State Management

There is a single authoritative state object inside the Simulation Engine. The rules:

1. **Atomic ticks** — No partial state is ever visible. The engine completes all six tick phases before producing a snapshot.
2. **No shared mutable state across threads** — The simulation runs on the asyncio event loop. The API layer reads state only via `engine.snapshot()`, which returns a deep copy / serialized dict.
3. **Config changes are deferred** — Calling `set_tick_speed(5)` stores the new value; the engine picks it up at the start of the next tick. This avoids mid-tick inconsistency.
4. **Frontend is eventually consistent** — The browser receives state snapshots at tick frequency. Between ticks, the frontend displays the last-known state.

---

## 6. Error Handling Strategy

| Scenario | Strategy |
|----------|----------|
| Pathfinding failure (no valid path) | Re-roll origin/destination up to 10 times; log warning if all retries fail |
| Grid fully congested | Skip spawning for this tick; log info |
| WebSocket disconnect | Client reconnects with exponential backoff (1s, 2s, 4s, max 30s); server sends current full state on reconnect |
| Invalid config values via API | Pydantic validation rejects with 422; return human-readable error |
| Unexpected error inside tick | Log full traceback, skip the problematic operation, continue the tick loop |
| Vehicle references stale cell state | The engine is the sole mutator; no stale references possible in single-threaded model |

---

## 7. Observability

- **Structured logging** via Python `logging` module at INFO level for: tick count, vehicle spawn/arrival events, preemption requests/releases, config changes.
- **DEBUG level** for: per-vehicle movement decisions, pathfinding details, traffic light phase transitions.
- **Metrics endpoint** (`GET /api/simulation/metrics`) for external monitoring.
- **Tick timing**: if a tick takes longer than the configured interval (e.g., >100ms at 10 ticks/sec), log a warning. This is our early signal for performance problems as grid size grows.

---

## 8. Project Structure

```
urban-flow/
├── backend/
│   ├── main.py                  # FastAPI app, startup, CORS, static files
│   ├── config.py                # SimulationConfig defaults and validation
│   ├── simulation/
│   │   ├── __init__.py
│   │   ├── engine.py            # SimulationEngine (tick loop + orchestration)
│   │   ├── grid.py              # Grid, Cell, CellType
│   │   ├── vehicle.py           # Vehicle, VehicleManager, VehicleType
│   │   ├── traffic_light.py     # TrafficLight, TrafficLightManager, Phase, Axis
│   │   ├── pathfinder.py        # A* implementation
│   │   └── metrics.py           # Metrics accumulator
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py            # REST endpoints
│   │   └── websocket.py         # WebSocket handler
│   └── tests/
│       ├── test_grid.py
│       ├── test_vehicle.py
│       ├── test_traffic_light.py
│       ├── test_pathfinder.py
│       ├── test_engine.py
│       └── test_api.py
├── frontend/
│   ├── index.html               # Single HTML page
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js               # WebSocket lifecycle, message dispatch
│       ├── renderer.js          # Canvas-based grid rendering
│       ├── controls.js          # UI controls (pause, speed, config)
│       └── metrics.js           # Metrics display panel
├── docs/
│   ├── requirements.md
│   ├── architecture.md          # (this document)
│   └── decisions.md             # Architectural Decision Records
├── requirements.txt
└── README.md
```

---

## 9. Technology Summary

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Language (backend) | Python 3.12+ | Strong ecosystem, fast prototyping, adequate perf for 10×10 grid |
| Web framework | FastAPI | Native async, WebSocket support, Pydantic validation, auto OpenAPI docs |
| Simulation model | Tick-based synchronous loop | Matches requirements; deterministic; trivial pause/resume |
| Concurrency | Single-threaded asyncio | No parallelism needed; avoids locks and race conditions |
| Grid representation | 2D array (`list[list[Cell]]`) | Natural fit for fixed-size rectangular grid |
| Pathfinding | A\* | Optimal for grid-based shortest/fastest path |
| Real-time transport | WebSocket | Bidirectional; low overhead for per-tick state pushes |
| Frontend | Vanilla JS + Canvas | Zero build step; Canvas is performant for 2D grid rendering |
| Persistence | In-memory only | No requirements for persistence, history, or multi-session state |
| Testing | pytest + pytest-asyncio | Standard Python testing; async support for API tests |

See `docs/decisions.md` for detailed rationale and tradeoff analysis for each choice.
