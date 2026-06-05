# Urban Flow - Development Tasks

This file is optimized for **review-sized AI handoffs**.

Use the **Phase 1 Review-Sized Task Queue** below as the single source of truth for:

- what is done
- what is next
- what size of work should be handed to an agent

The goal is to avoid method-sized tasks. Each open task should be large enough to be worth a focused review, but still small enough to finish in one coherent implementation pass.

---

## Task Sizing Rules

- One task should usually correspond to one coherent code review.
- A task may span multiple related methods or files when they form one usable slice.
- Do not split work into tiny method-only tasks unless the change is unusually risky.
- If older docs mention smaller legacy task IDs, use the mapping in this file instead of creating new micro-tasks.

---

## ID Format

- `P1-` = Phase 1 (Grid Simulation MVP)
- `GRID`, `PATH`, `VEH`, `TL`, `MET`, `ENG`, `API`, `FE` = major areas
- `NN` = two-digit sequence number

Example: `P1-ENG-01`

---

## Phase 1 Review-Sized Task Queue

This table is the **authoritative queue** for developer and tester handoffs.

| ID | Task | Includes | Depends On | Status |
|----|------|----------|------------|--------|
| P1-GRID-01 | Grid foundation + serialization | Grid layout, traversal, occupancy helpers, edge/intersection queries, snapshot payloads | - | ✅ |
| P1-PATH-01 | Pathfinder module | Path node helpers, A* search, emergency light-aware costs | P1-GRID-01 | ✅ |
| P1-VEH-01 | Vehicle + VehicleManager core | Vehicle path progression, spawning, movement, arrival cleanup, snapshots | P1-GRID-01, P1-PATH-01 | ✅ |
| P1-TL-01 | TrafficLight core | Phase cycling, entry rules, preemption, serialization | P1-VEH-01 | ✅ |
| P1-API-01 | Config request validation | `ConfigUpdateRequest` bounds and API-facing validation | - | ✅ |
| P1-TL-02 | TrafficLightManager + grid light wiring | Create all intersection lights, lookups, movement permission bridge, phase-duration updates, light snapshots | P1-TL-01 | ✅ |
| P1-MET-01 | Metrics module complete | KPI calculations, `record_arrival`, batch updates, reset, `to_dict` | P1-VEH-01 | ✅ |
| P1-ENG-01 | SimulationEngine complete | Initialization, six-phase tick order, config setters, preemption scan, cleanup, snapshot, `get_metrics` | P1-TL-02, P1-MET-01 | ✅ |
| P1-API-02 | Runtime interface layer | REST route wiring, WebSocket manager/handler, app bootstrap, static files, startup lifecycle | P1-ENG-01 | ⬜ |
| P1-FE-01 | Browser MVP | `index.html`, renderer, controls, metrics panel, `app.js`, end-to-end UI wiring | P1-API-02 | ⬜ |

---

## Current Status

- Phase 1 foundations are complete through `P1-ENG-01`, including `P1-TL-02`, `P1-MET-01`, and `P1-API-01`.
- The remaining work is integration-heavy and should be tackled as the larger slices above.
- **Next task:** `P1-API-02`

### What "done" means for an open task

- The full slice in the queue row is implemented, not just one method.
- Lint passes.
- Relevant tests pass, or any testing gap is explicitly called out.
- `docs/tasks.md` is updated before handoff.

---

## Legacy ID Mapping

Older docs, notes, and design-decision anchors may still reference smaller task IDs. Use this mapping when reading them.

| Review-Sized Task | Legacy IDs Rolled Into It |
|-------------------|---------------------------|
| P1-GRID-01 | P1-GRID-01 through P1-GRID-08 |
| P1-PATH-01 | P1-PATH-01 through P1-PATH-03 |
| P1-VEH-01 | P1-VEH-01 through P1-VEH-04 |
| P1-TL-01 | P1-TL-01 |
| P1-API-01 | P1-API-01 |
| P1-TL-02 | P1-TL-02 |
| P1-MET-01 | P1-MET-01, P1-MET-02 |
| P1-ENG-01 | P1-ENG-01, P1-ENG-02, P1-ENG-03 |
| P1-API-02 | P1-API-02, P1-WS-01, P1-APP-01 |
| P1-FE-01 | P1-FE-01 through P1-FE-05 |

---

## Design Decision References

Use `docs/design-decisions.md` for detailed trade-offs. The links below are the most relevant existing anchors.

| Task | Design Decision References |
|------|----------------------------|
| P1-GRID-01 | [Cell Layout](design-decisions.md#decision-grid-initialization--cell-layout-task-p1-grid-01), [Street Spacing](design-decisions.md#decision-grid-streetavenue-spacing-task-p1-grid-01), [Dimension Validation](design-decisions.md#decision-grid-dimension-validation-constants-task-p1-grid-01), [Dual-Level API](design-decisions.md#decision-dual-level-is_traversable--is_occupied-api-task-p1-grid-06) |
| P1-PATH-01 | [Pathfinding Cost Values](design-decisions.md#decision-pathfinding-cost-values) |
| P1-VEH-01 | [Validation Caching Deferral](design-decisions.md#decision-defer-vehicle-validation-caching-until-integrated-profiling-task-p1-veh-01) |
| P1-API-01 | [API Input Validation for ConfigUpdateRequest](design-decisions.md#decision-api-input-validation-for-configupdaterequest-task-api-001) |

---

## Active Watches

- **DESIGN-WATCH-TL-01:** During `P1-ENG-01`, explicitly enforce that only emergency vehicles trigger preemption. The enforcement point can live either in `SimulationEngine` or `TrafficLight.request_preemption`, but the choice should be intentional and documented if needed.
- **PERF-WATCH-VEH-01:** Re-check `Vehicle._validate_path_state()` hot-path cost after `P1-ENG-01` is done and the engine can be profiled under realistic load.
- **PERF-WATCH-SNAP-01:** Re-evaluate per-tick snapshot payload size during `P1-API-02` / `P1-FE-01`. The current full-grid snapshot is acceptable for the Phase 1 `10x10` MVP, but larger grids may require splitting static grid layout from dynamic tick state instead of serializing the full `cells` matrix every tick.

---

## Handoff Notes

- Developer and tester prompts should use the **review-sized queue only**, not the rolled-up legacy IDs, when deciding what to do next.
- If you finish a task, mark its row `✅` and move the next row into the active slot.
- If a task grows beyond a sane review size, split it once into two clear slices rather than creating many micro-tasks.
