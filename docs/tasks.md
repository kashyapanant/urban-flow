# Urban Flow - Development Tasks

This document tracks development tasks, issues, and improvements for the Urban Flow project. Each task has a **unique ID** so it can be linked to a git branch, design decision, or PR.

## Task Status Legend

- 🔴 **Critical** - Blocks core functionality or security issue
- 🟡 **High** - Important for robustness/user experience
- 🟢 **Medium** - Nice to have, improves code quality
- 🔵 **Low** - Future enhancement, not urgent

## ID Format

- **P1-** = Phase 1 (Core Simulation Engine)
- **GRID** = Grid class · **PATH** = Pathfinder · **VEH** = Vehicle/VehicleManager · **TL** = TrafficLight · **MET** = Metrics · **ENG** = SimulationEngine · **API** = API layer
- **NN** = Two-digit number (01, 02, …)

Example: `P1-GRID-01` = Phase 1, Grid, first task.

---

## Phase 1: Core Simulation Engine - Implementation Order

Implementation follows a foundation-first approach. Link each task ID to a branch (e.g. `urb-01`) or design decision in the [Task registry](#task-registry) below.

### 1. Grid Class (Foundation)

| ID | Task | Status |
|----|------|--------|
| P1-GRID-01 | `Grid.__init__()` - Initialize grid with city blocks layout | ✅ |
| P1-GRID-02 | `Cell.is_traversable()` - Check if cell allows vehicle movement | ✅ |
| P1-GRID-03 | `Cell.is_occupied()` - Check if cell contains vehicle | ⬜ |
| P1-GRID-04 | `Grid.get_cell()` - Get cell at coordinates | ⬜ |
| P1-GRID-05 | `Grid.get_neighbors()` - Get traversable neighboring cells | ⬜ |
| P1-GRID-06 | `Grid.place_vehicle()` - Place vehicle in cell | ⬜ |
| P1-GRID-07 | `Grid.remove_vehicle()` - Remove vehicle from cell | ⬜ |
| P1-GRID-08 | `Grid.get_edge_cells()` - Get spawn-eligible edge cells | ⬜ |
| P1-GRID-09 | `Grid.get_intersection_cells()` - Get intersection positions | ⬜ |
| P1-GRID-10 | `Grid.snapshot()` - Create serializable state | ⬜ |
| P1-GRID-11 | `Cell.to_dict()` - Serialize cell to dict for frontend | ⬜ |

### 2. Pathfinder Class (Depends: Grid)

| ID | Task | Status |
|----|------|--------|
| P1-PATH-01 | `PathNode.f_cost` - A* total cost calculation | ⬜ |
| P1-PATH-02 | `PathNode.__lt__()` - Priority queue comparison | ⬜ |
| P1-PATH-03 | `Pathfinder.find_path()` - A* pathfinding algorithm | ⬜ |

### 3. Vehicle Classes (Depends: Grid, Pathfinder)

| ID | Task | Status |
|----|------|--------|
| P1-VEH-01 | `Vehicle.get_next_position()` - Get next path position | ⬜ |
| P1-VEH-02 | `Vehicle.advance_path()` - Move to next position | ⬜ |
| P1-VEH-03 | `Vehicle.get_remaining_distance()` - Calculate remaining cells | ⬜ |
| P1-VEH-04 | `VehicleManager.__init__()` - Initialize manager | ⬜ |
| P1-VEH-05 | `VehicleManager.spawn_vehicles()` - Spawn at grid edges | ⬜ |
| P1-VEH-06 | `VehicleManager.move_vehicles()` - Priority-based movement | ⬜ |
| P1-VEH-07 | `VehicleManager.collect_arrived()` - Remove completed vehicles | ⬜ |

### 4. TrafficLight Classes (Depends: Vehicle)

| ID | Task | Status |
|----|------|--------|
| P1-TL-01 | `TrafficLight.tick()` - Advance phase timing | ⬜ |
| P1-TL-02 | `TrafficLight.can_enter()` - Check movement permission | ⬜ |
| P1-TL-03 | `TrafficLight.request_preemption()` - Emergency preemption | ⬜ |
| P1-TL-04 | `TrafficLight.release_preemption()` - Resume normal cycling | ⬜ |
| P1-TL-05 | `TrafficLightManager.__init__()` - Initialize all lights | ⬜ |
| P1-TL-06 | `TrafficLightManager.tick()` - Update all lights | ⬜ |

### 5. Metrics Class (Depends: Vehicle)

| ID | Task | Status |
|----|------|--------|
| P1-MET-01 | `Metrics.normal_avg_ticks` - Calculate normal vehicle average | ⬜ |
| P1-MET-02 | `Metrics.emergency_avg_ticks` - Calculate emergency average | ⬜ |
| P1-MET-03 | `Metrics.improvement` - Calculate percentage improvement | ⬜ |
| P1-MET-04 | `Metrics.record_arrival()` - Record vehicle completion | ⬜ |

### 6. SimulationEngine (Orchestrates All)

| ID | Task | Status |
|----|------|--------|
| P1-ENG-01 | `SimulationEngine.__init__()` - Initialize all components | ⬜ |
| P1-ENG-02 | `SimulationEngine.start()` - Begin tick loop | ⬜ |
| P1-ENG-03 | `SimulationEngine.tick()` - Execute single simulation step | ⬜ |
| P1-ENG-04 | `SimulationEngine.snapshot()` - Create complete state | ⬜ |

---

## Task registry

Use this table to link each task to a **branch** and/or **design decision**. Update as you create branches or add entries to `docs/design-decisions.md`.

| ID | Task (short) | Status | Branch | Design decision |
|----|--------------|--------|--------|------------------|
| P1-GRID-01 | `Grid.__init__` | ✅ | | [Cell Layout](design-decisions.md#decision-grid-initialization--cell-layout-task-p1-grid-01), [Street Spacing](design-decisions.md#decision-grid-streetavenue-spacing-task-p1-grid-01), [Dimension Validation](design-decisions.md#decision-grid-dimension-validation-constants-task-p1-grid-01) |
| P1-GRID-02 | `Cell.is_traversable` | ✅ | | |
| P1-GRID-03 | `Cell.is_occupied` | ⬜ | | |
| P1-GRID-04 | `Grid.get_cell` | ⬜ | | |
| P1-GRID-05 | `Grid.get_neighbors` | ⬜ | | |
| P1-GRID-06 | `Grid.place_vehicle` | ⬜ | | |
| P1-GRID-07 | `Grid.remove_vehicle` | ⬜ | | |
| P1-GRID-08 | `Grid.get_edge_cells` | ⬜ | | |
| P1-GRID-09 | `Grid.get_intersection_cells` | ⬜ | | |
| P1-GRID-10 | `Grid.snapshot` | ⬜ | | |
| P1-GRID-11 | `Cell.to_dict` | ⬜ | | |
| P1-PATH-01 | `PathNode.f_cost` | ⬜ | | e.g. [Pathfinding Cost Values](design-decisions.md#decision-pathfinding-cost-values) |
| P1-PATH-02 | `PathNode.__lt__` | ⬜ | | |
| P1-PATH-03 | `Pathfinder.find_path` | ⬜ | | |
| P1-VEH-01 | `Vehicle.get_next_position` | ⬜ | | |
| P1-VEH-02 | `Vehicle.advance_path` | ⬜ | | |
| P1-VEH-03 | `Vehicle.get_remaining_distance` | ⬜ | | |
| P1-VEH-04 | `VehicleManager.__init__` | ⬜ | | |
| P1-VEH-05 | `VehicleManager.spawn_vehicles` | ⬜ | | |
| P1-VEH-06 | `VehicleManager.move_vehicles` | ⬜ | | |
| P1-VEH-07 | `VehicleManager.collect_arrived` | ⬜ | | |
| P1-TL-01 | `TrafficLight.tick` | ⬜ | | |
| P1-TL-02 | `TrafficLight.can_enter` | ⬜ | | |
| P1-TL-03 | `TrafficLight.request_preemption` | ⬜ | | |
| P1-TL-04 | `TrafficLight.release_preemption` | ⬜ | | |
| P1-TL-05 | `TrafficLightManager.__init__` | ⬜ | | |
| P1-TL-06 | `TrafficLightManager.tick` | ⬜ | | |
| P1-MET-01 | `Metrics.normal_avg_ticks` | ⬜ | | |
| P1-MET-02 | `Metrics.emergency_avg_ticks` | ⬜ | | |
| P1-MET-03 | `Metrics.improvement` | ⬜ | | |
| P1-MET-04 | `Metrics.record_arrival` | ⬜ | | |
| P1-ENG-01 | `SimulationEngine.__init__` | ⬜ | | |
| P1-ENG-02 | `SimulationEngine.start` | ⬜ | | |
| P1-ENG-03 | `SimulationEngine.tick` | ⬜ | | |
| P1-ENG-04 | `SimulationEngine.snapshot` | ⬜ | | |
| P1-API-01 | `ConfigUpdateRequest` validation | ✅ | | [API Input Validation for ConfigUpdateRequest](design-decisions.md#decision-api-input-validation-for-configupdaterequest-task-api-001) |

---

## Active issues & bugs

*Space for logging bugs found during implementation.*

---

## Phase 1 – Pending / next steps

**Current status:** Implementation in progress (foundation-first). Grid foundation: `Grid.__init__()` and `Cell.is_traversable()` done (P1-GRID-01, P1-GRID-02).

**Next task:** P1-GRID-03 – `Cell.is_occupied()` (or next unchecked task in [Task registry](#task-registry)).

---

## Future task categories

- **Testing** – Comprehensive tests
- **Performance** – Optimization and benchmarking
- **Documentation** – Docs and examples
- **Frontend** – Web UI (Phase 1 scope)

---

## Completed tasks

### P1-API-01: Add input validation to ConfigUpdateRequest

**Status:** Completed  
**Priority:** High  
**Component:** API layer (`backend/api/routes.py`)  
**Reported:** 2026-02-28  
**Completed:** 2026-03-05  

**Description:**  
`ConfigUpdateRequest` had no validation, so invalid values could pass through the API. Validation was added so invalid data does not reach the simulation engine.

**Solution:** Pydantic `Field` with `ge`/`le` for `tick_speed`, `spawn_rate`, `phase_duration` (aligned with `SimulationConfig`).

**Changes:**  
- Added Field validation to all `ConfigUpdateRequest` fields  
- Logged decision in `docs/design-decisions.md`  

**Result:** API returns 422 for invalid config; engine no longer receives invalid data.

---

## Notes

- Each task is atomic and has a unique ID for linking (branch, design decision, PR).
- Update the [Task registry](#task-registry) when you create a branch or document a design decision.
- Prefer referencing tasks by ID (e.g. “Implements P1-GRID-01”) in commits and PRs.
