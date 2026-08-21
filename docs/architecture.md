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
└──┬────────┬────────┬─────────┬──┘
   │        │        │         │
   ▼        ▼        ▼         ▼
┌──────┐ ┌────────┐ ┌────────┐ ┌────────────┐
│ Grid │ │Vehicle │ │Traffic │ │RoadSegment │
│World │ │Manager │ │ Light  │ │  Manager   │
└──────┘ └───┬────┘ │Manager │ └────────────┘
             │      └────────┘
        ┌────┴─────┐
        │Pathfinder│
        │   (A*)   │
        └──────────┘
```

**Dependency rules:**
- Arrows point from consumer → dependency.
- The Simulation Engine orchestrates Grid, VehicleManager, and TrafficLightManager. It is the only module that mutates world state.
- The Simulation Engine also orchestrates RoadSegmentManager, which owns dynamic segment admission state.
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

A Vehicle is an entity with an id, type (normal/emergency), pre-computed path, and status (moving/waiting/arrived). The VehicleManager owns the collection of active vehicles and handles spawning, movement, segment admission, and arrival cleanup.

**Spawning:**
1. Roll spawn_rate once per tick; a successful roll creates at most one demand attempt.
2. Choose vehicle type before admission so emergency reserve capacity applies.
3. Count each demand attempt once: reject an active network that made no movement; otherwise reject at the type-specific active cap, counting only vehicles not marked `arrived` after movement; otherwise proceed to origin, path, and transactional-admission checks. A failure of those checks is a no-admissible-entry rejection.
4. Search shuffled edge origins and destinations for a valid fixed path and derive the applicable origin segment. Exclude occupied origins, first downstream road cells reserved by committed intersection crossings, and, for normal candidates, intersections with active emergency preemption claims.
5. For an intersection origin, use the first downstream road segment as the origin admission target and require its first road cell to be available. An emergency spawned there holds a signal-less reservation for that segment and does not preempt its origin intersection.
6. Submit the candidate as a transient request in transactional spawn arbitration. An empty, unreserved segment may switch direction when the candidate wins; commit direction admission and placement atomically. For an intersection origin, also commit and reserve the candidate's first downstream road cell until it enters that cell. A road-origin candidate has no crossing grant or downstream-cell reservation. Discard all candidate-only state if placement fails.

Rejected demand is discarded rather than queued outside the grid. The default 10x10
network admits at most 30 active vehicles and reserves three positions for
emergency arrivals. Normal traffic stops at 27 active vehicles. The cap scales
from the default traversable-cell ratio for other grid sizes.

**Movement (per tick):**
1. Refresh persistent segment requests and arbitrate direction/reservations.
2. Apply emergency signal preemption, then advance traffic lights.
3. Sort vehicles by the existing priority order and move sequentially.
4. A vehicle may enter a non-terminal intersection only when the signal, empty intersection, downstream segment grant, and downstream space permit the move. A terminal intersection destination requires only the permissive signal and empty intersection; it bypasses segment admission and downstream-space checks.
5. Record every applicable blocker in the vehicle wait_reasons list, including `preemption_claim_contention` when an emergency loses an exclusive preemption claim.
6. Reconcile segment occupancy and reservations after movement, preserving each grant committed during arbitration and its reserved downstream entry cell until its vehicle reaches that cell, and releasing reservations whose holders arrived or left the active vehicle set.

### 3.3 RoadSegmentManager

The RoadSegmentManager owns dynamic admission state for maximal straight road runs. It derives deterministic segment geometry from the Grid, persists normal and emergency requests, controls one active direction per segment, retains committed crossing grants and their reserved downstream entry cells, and exposes additive snapshot records. It does not change pathfinding or mutate traffic lights directly; the SimulationEngine coordinates segment grants with signal preemption.

After direction selection, select one claimant by vehicle type (emergency before normal), then request creation tick, then arbitration coordinate (row, column): the pre-intersection road-cell coordinate for an on-grid claimant or the origin coordinate for a spawn candidate, then vehicle.id. An intersection-crossing claimant receives the committed grant and reserves the downstream entry cell; a road-origin spawn claimant receives direction admission and atomic origin placement.

A persistent segment request is scheduler metadata for a lead vehicle already on the grid, not an external spawn queue. Spawn candidates submit transient requests that participate once in transactional arbitration and are discarded if spawning fails. On an empty segment, emergency requests take precedence over normal requests and emergencies retain first-come-first-served order. Normal-only opposing requests choose the direction holding the oldest request; equal creation ticks use deterministic last-served fairness.

### 3.4 TrafficLight & TrafficLightManager (`simulation/traffic_light.py`)

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
2. The look-ahead may reserve only the vehicle's next road segment and its associated entry signal; it cannot claim multiple intersections or future segments. A terminal-intersection destination instead uses a signal-only claim. An emergency already spawned inside the entry intersection holds a signal-less reservation for its first downstream segment, with no associated preemption claim.
3. For each intersection, select at most one eligible emergency preemption claim across approaching segment reservations and terminal signal-only claims, ordered by claim creation tick, then the claimant's pre-intersection road-cell coordinate `(row, column)`, then `vehicle.id`. Call `request_preemption(intersection, vehicle)` only for that selected claim, after the RoadSegmentManager grants its next-segment reservation or after a terminal signal-only claim is issued.
4. If the intersection is already serving the emergency vehicle's axis, no change.
5. If the intersection is serving the cross axis, it immediately transitions to **yellow** (2 ticks), then **red** (instant), then flips the active axis to **green** for the emergency direction.
6. The `preemptedBy` field is set to the reservation-holding emergency vehicle, or to a terminal-bound emergency's signal-only claim. A second emergency vehicle approaching the same intersection waits and records `preemption_claim_contention` (first-come-first-served per edge case #2).
7. Vehicles already ahead of the reservation holder may continue through the reserved segment. No new normal entry or spawn placement is permitted anywhere in an emergency-reserved segment.
8. When the emergency vehicle clears the intersection or arrives before doing so, `release_preemption` is called and normal cycling resumes from the current axis's green phase. A terminal signal-only claim releases when its vehicle enters and arrives. Segment reconciliation separately releases a reservation when its holder clears the segment, arrives, or leaves the active vehicle set. Signal-preemption reconciliation runs after movement and after arrival cleanup, before the snapshot is broadcast.

### 3.5 Pathfinder (`simulation/pathfinder.py`)

A stateless A\* implementation.

**Normal vehicles** — shortest path:
- Cost per cell: 1
- Heuristic: Manhattan distance to destination
- Constraint: cell must be traversable (`road` or `intersection`) and not permanently blocked

**Emergency vehicles** — fastest path considering signal state:
- Cost per cell: 1 + penalty for intersections with an unfavorable current light phase (e.g., +2 for red/yellow in the vehicle's travel axis)
- This biases emergency vehicles toward routes with currently-green corridors
- Path is computed once at spawn time (no mid-journey rerouting per requirements)

### 3.6 Simulation Engine (`simulation/engine.py`)

The orchestrator. Owns the Grid, VehicleManager, RoadSegmentManager, TrafficLightManager, and Metrics. Runs a tick loop driven by `asyncio`.

**Tick execution order (critical for determinism):**

```
refresh segment requests -> arbitrate segment reservations
-> apply emergency preemption -> advance lights
-> move vehicles and count progress -> reconcile segments and signal preemption
-> attempt spawning with transactional arbitration
-> collect arrivals and update metrics
-> reconcile segments and signal preemption after arrival cleanup
-> increment tick and broadcast
```

Persistent segment requests are resolved before movement. Spawning observes the
current movement result, so an active network with zero movement does not
receive new vehicles, then performs one transactional arbitration for its
candidate. Spawn admission excludes every downstream entry cell reserved by a
committed crossing. The complete operation remains atomic from the snapshot
consumer perspective.

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

### 3.7 API Layer (`api/routes.py`, `api/websocket.py`)

**REST endpoints:**

| Method | Path                      | Purpose                                      |
|--------|---------------------------|----------------------------------------------|
| POST   | `/api/simulation/start`   | Start the simulation                         |
| POST   | `/api/simulation/reset`   | Reset the simulation state and leave it stopped |
| POST   | `/api/simulation/config/reset` | Restore mutable runtime config defaults without rebuilding state |
| POST   | `/api/simulation/pause`   | Pause the tick loop                          |
| POST   | `/api/simulation/resume`  | Resume the tick loop                         |
| PUT    | `/api/simulation/config`  | Update runtime config (tick speed, spawn rate, emergency probability, phase duration) |
| GET    | `/api/simulation/state`   | Return current state snapshot (polling fallback) |
| GET    | `/api/simulation/metrics` | Return current metrics                       |

**WebSocket (`/ws`):**

| Direction | Message Type | Payload |
|-----------|-------------|---------|
| Server → Client | `tick` | Full SimulationState snapshot (grid, vehicles, road segments, lights, metrics, tick_count) |
| Client → Server | `pause` | — |
| Client → Server | `resume` | — |
| Client → Server | `set_speed` | `{ speed: int }` |
| Client → Server | `set_spawn_rate` | `{ rate: float }` |
| Client → Server | `set_phase_duration` | `{ duration: int }` |

The REST endpoints exist as a fallback and for tooling (curl, tests). The primary real-time channel is WebSocket.

### 3.8 Frontend (`frontend/`)

A zero-build-step browser application: one HTML file, vanilla JavaScript, and HTML5 Canvas.

**Components:**
- **Renderer** (`renderer.js`): Draws the grid on a `<canvas>`. Cells are colored by type; vehicles are drawn as colored shapes (blue = normal, red = emergency); traffic lights are rendered as colored dots at intersections.
- **Controls** (`controls.js`): Pause/resume button, tick-speed slider (1–10), spawn-rate input, phase-duration input. Sends commands over the WebSocket.
- **Metrics display** (`metrics.js`): Shows averages, improvement, completion and spawn counters, active/waiting counts, capacity, movement progress, and gridlock status. Updated every tick.
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
    wait_reasons: list[WaitReason]
```

### VehicleManager

```
class SpawnAdmission:
    moves_this_tick: int
    active_vehicle_count: int
    active_vehicle_cap: int
    emergency_reserved_slots: int

class VehicleManager:
    spawn_vehicles(grid, pathfinder, traffic_lights, road_segments, spawn_rate, emergency_probability, admission: SpawnAdmission) -> list[Vehicle]
    move_vehicles(grid, traffic_light_manager, road_segments) -> int
    collect_arrived() -> list[Vehicle]
    get_all() -> list[Vehicle]
```

### RoadSegmentManager

```
class RoadSegmentManager:
    __init__(grid)
    request(vehicle, segment) -> None
    arbitrate() -> None
    try_admit_spawn(candidate, segment) -> bool
    can_enter(vehicle, segment) -> bool
    reconcile(active_vehicle_ids) -> None
    snapshot() -> list[dict]
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
    road_segments: RoadSegmentManager
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
    active_vehicles: int
    waiting_vehicles: int
    moves_this_tick: int
    consecutive_zero_move_ticks: int
    gridlock_suspected: bool
    spawn_attempts: int
    spawn_admitted: int
    spawn_rejected_capacity: int
    spawn_rejected_network_stalled: int
    spawn_rejected_no_admissible_entry: int
    active_vehicle_cap: int
    emergency_reserved_slots: int

    record_arrival(vehicle: Vehicle) -> None
```

### SimulationConfig

```
class SimulationConfig:
    grid_width: int = 10
    grid_height: int = 10
    tick_speed: int = 1           # ticks per second (1–10)
    spawn_rate: float = 0.1       # one demand roll per tick
    phase_duration: int = 3       # ticks per traffic light phase
    emergency_probability: float = 0.1
```

---

## 5. State Management

There is a single authoritative state object inside the Simulation Engine. The rules:

1. **Atomic ticks** — No partial state is ever visible. The engine completes all admission-aware tick phases before producing a snapshot.
2. **No shared mutable state across threads** — The simulation runs on the asyncio event loop. The API layer reads state only via `engine.snapshot()`, which returns a deep copy / serialized dict.
3. **Config changes are deferred** — Calling `set_tick_speed(5)` stores the new value; the engine picks it up at the start of the next tick. This avoids mid-tick inconsistency.
4. **Config reset is settings-only** — `POST /api/simulation/config/reset` restores the mutable runtime settings to defaults, preserves structural grid dimensions, and does not rebuild world state or change lifecycle.
5. **Frontend is eventually consistent** — The browser receives state snapshots at tick frequency. Between ticks, the frontend displays the last-known state.

---

## 6. Error Handling Strategy

| Scenario | Strategy |
|----------|----------|
| Pathfinding failure (no valid path) | Re-roll origin/destination up to 10 times; log warning if all retries fail |
| Active cap reached or network made no movement | Reject the spawn demand for this tick and record the rejection reason. |
| Suspected gridlock | Keep the engine running, pause spawning, expose liveness metrics, and log the state transition. Do not remove or reroute vehicles. |
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

Current repo note: `main.py` currently lives at the repository root, and the browser frontend is still a planned Phase 1 deliverable. The tree below shows the intended layout once the remaining Phase 1 app wiring is complete.

```
urban-flow/
├── main.py                    # FastAPI app, startup, CORS, static files
├── backend/
│   ├── config.py              # SimulationConfig defaults and validation
│   ├── simulation/
│   │   ├── __init__.py
│   │   ├── engine.py          # SimulationEngine (tick loop + orchestration)
│   │   ├── grid.py            # Grid, Cell, CellType
│   │   ├── vehicle.py         # Vehicle, VehicleManager, VehicleType
│   │   ├── traffic_light.py   # TrafficLight, TrafficLightManager, Phase, Axis
│   │   ├── pathfinder.py      # A* implementation
│   │   └── metrics.py         # Metrics accumulator
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py          # REST endpoints
│   │   └── websocket.py       # WebSocket handler
│   └── tests/
│       ├── test_grid.py
│       ├── test_vehicle.py
│       ├── test_traffic_light.py
│       ├── test_pathfinder.py
│       ├── test_engine.py
│       └── test_api.py
├── frontend/                   # Planned in remaining Phase 1 work
│   ├── index.html             # Single HTML page
│   ├── css/
│   │   └── style.css          # Optional styling if needed
│   └── js/
│       ├── app.js              # WebSocket lifecycle, message dispatch
│       ├── renderer.js         # Canvas-based grid rendering
│       ├── controls.js         # UI controls (pause, speed, config)
│       └── metrics.js          # Metrics display panel
├── docs/
│   ├── requirements.md
│   ├── architecture.md        # (this document)
│   └── decisions.md           # Architectural Decision Records
├── prompts/
│   └── product-owner.md       # Requirement elicitation history / notes
├── pyproject.toml             # Project configuration and dependencies
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
