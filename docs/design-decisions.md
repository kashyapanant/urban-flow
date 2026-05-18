# Urban Flow — Implementation Design Decisions

This document records design decisions made during the implementation of the backend skeleton that were not fully specified in the architecture document.

---

## Decision: Vehicle ID Generation Format

**Date:** 2026-02-28
**Updated:** 2026-03-25
**Context:** The architecture specifies that vehicles need unique IDs but doesn't specify the format.
**Decision:** Use full UUID4 hex strings for vehicle IDs.
**Rationale:** 
- Full UUID strings greatly reduce collision risk in long-running simulations
- UUID4 is cryptographically random, avoiding predictable patterns
- IDs remain plain strings and are JSON-safe without additional conversion

---

## Decision: Configuration Parameter Ranges

**Date:** 2026-02-28
**Context:** The architecture mentions configurable parameters but doesn't specify validation ranges.
**Decision:** 
- `tick_speed`: 1-10 ticks per second
- `spawn_rate`: 0.0-1.0 probability per edge cell per tick
- `phase_duration`: 1-20 ticks per phase
- `emergency_probability`: 0.0-1.0 (default 0.1)

**Rationale:**
- Tick speed range balances observability (1 tps) with performance testing (10 tps)
- Spawn rate as probability allows fine-grained control
- Phase duration range accommodates both fast testing and realistic timing
- 10% emergency probability matches architecture example

---

## Decision: Grid Layout Constants

**Date:** 2026-02-28
**Context:** Architecture specifies "city blocks" pattern with streets at {0, 3, 6, 9} but implementation needs to be flexible.
**Decision:** Store street rows and avenue columns as instance variables in Grid class.
**Rationale:**
- Allows future customization of grid patterns
- Makes the layout explicit and testable
- Maintains the specified default pattern

---

## Decision: Pathfinding Cost Values

**Date:** 2026-02-28
**Context:** Architecture mentions "+2 for red/yellow" penalty but needs specific cost structure.
**Decision:**
- Base cost per cell: 1.0
- Red intersection penalty: +2.0 (total 3.0)
- Yellow intersection penalty: +1.0 (total 2.0)
- Green/left-turn: no penalty (total 1.0)

**Rationale:**
- Simple integer costs for predictable behavior
- Red penalty significantly higher than yellow
- Matches architecture's "+2 for red" specification

---

## Decision: WebSocket Message Format

**Date:** 2026-02-28
**Context:** Architecture specifies WebSocket for real-time updates but not message structure.
**Decision:** Use JSON messages with `type` field and `data` payload:
```json
{
  "type": "tick",
  "data": {
    "tick_count": 123,
    "state": "running",
    "grid": {...},
    "vehicles": [...],
    "traffic_lights": [...],
    "metrics": {...}
  }
}
```
**Rationale:**
- Standard pattern for WebSocket message routing
- Extensible for future message types
- Clear separation of message metadata and payload

---

## Decision: Error Handling Strategy

**Date:** 2026-02-28
**Context:** Architecture outlines error scenarios but implementation needs specific exception handling.
**Decision:**
- Use Pydantic for API validation (automatic 422 responses)
- Log errors at appropriate levels (INFO for expected, ERROR for unexpected)
- Continue simulation on non-critical errors (log and skip operation)
- Use HTTPException for API error responses

**Rationale:**
- Pydantic provides consistent validation with clear error messages
- Logging strategy balances observability with noise
- Resilient simulation continues despite individual operation failures
- FastAPI HTTPException provides standard HTTP error responses

---

## Decision: Test Structure Organization

**Date:** 2026-02-28
**Context:** Need to organize test files to match module structure.
**Decision:** Mirror the backend module structure in tests/ with test_ prefix.
**Rationale:**
- Standard Python testing convention
- Easy to locate tests for specific modules
- Supports pytest auto-discovery
- Clear separation of unit vs integration tests

---

## Decision: Async/Await Usage

**Date:** 2026-02-28
**Context:** Architecture specifies asyncio but implementation needs to decide where async is required.
**Decision:**
- Simulation engine tick loop: async (for sleep between ticks)
- API endpoints that control simulation: async (for engine interaction)
- WebSocket handlers: async (required by FastAPI)
- Core simulation logic: synchronous (single-threaded, no I/O)

**Rationale:**
- Async only where needed for I/O or timing
- Core simulation remains simple and testable
- Matches architecture's single-threaded design
- Enables non-blocking web server operation

---

## Decision: Configuration Change Deferral

**Date:** 2026-02-28
**Context:** Architecture mentions "deferred config changes" but needs implementation approach.
**Decision:** Use `_pending_config_changes` dictionary applied at start of each tick.
**Rationale:**
- Maintains determinism by avoiding mid-tick changes
- Simple dictionary-based approach is easy to understand
- Changes take effect on next tick as specified
- Thread-safe in single-threaded simulation model

---

## Decision: API Input Validation for ConfigUpdateRequest (Task: API-001)

**Date:** 2026-03-05
**Context:** ConfigUpdateRequest model lacked validation constraints, creating security/robustness gap where invalid data could reach simulation engine.
**Decision:** Add Pydantic Field validation to match SimulationConfig constraints exactly.
**Rationale:**
- Prevents invalid configuration values from reaching simulation engine
- Provides clear error messages with 422 HTTP responses for invalid input
- Maintains consistency between API and core config validation
- Follows FastAPI/Pydantic best practices for input validation

---

## Decision: Dual-Level is_traversable / is_occupied API (Task: P1-GRID-06)

**Date:** 2026-03-08
**Context:** Both `Cell` and `Grid` expose `is_traversable` and `is_occupied`. This raised the question of whether having the same concept at two levels is intentional or redundant.
**Decision:** Keep both levels — `Cell.is_traversable()` / `Cell.is_occupied()` for callers that already hold a `Cell` object, and `Grid.is_traversable(x, y)` / `Grid.is_occupied(x, y)` as coordinate-based facade wrappers for callers that think in positions. The `Grid` wrappers always delegate to the `Cell` methods and absorb the out-of-bounds case (returning `False` safely), so there is no logic duplication.
**Rationale:**
- Different callers have different entry points: internal simulation logic traverses `Cell` objects directly; external code (engine, API, tests) works in coordinates.
- The `Grid` wrappers eliminate repetitive `get_cell()` + `None` guard boilerplate at every call site.
- Single source of truth is preserved: logic lives in `Cell`, `Grid` only delegates.
- This is a standard Facade / Convenience API pattern for container + domain-object designs.

---

## Decision: Grid Initialization — Cell Layout (Task: P1-GRID-01)

**Date:** 2026-03-08
**Context:** `Grid.__init__()` needs to build the 2D cell array and define which cells are roads, intersections, or obstacles.
**Decision:**
- Internal storage is row-major: `cells[y][x]`, matching how the ASCII grid is drawn (outer list = rows).
- A cell is an intersection if both its column is in `avenue_cols` and its row is in `street_rows`.
- A cell is a road if its column is in `avenue_cols` OR its row is in `street_rows` (but not both).
- Everything else is an obstacle.

**Rationale:**
- Row-major indexing is consistent with the ASCII grid representation in the architecture doc.
- The three-way classification (intersection / road / obstacle) maps directly to `CellType` and is derived purely from the street/avenue sets.

---

## Decision: Grid Street/Avenue Spacing (Task: P1-GRID-01)

**Date:** 2026-03-08
**Context:** Architecture specifies `{0, 3, 6, 9}` for a 10×10 grid. Implementation needs to be flexible for different grid sizes.
**Decision:**
- Fixed spacing of **3** between streets/avenues, always starting at index 0: `{0, 3, 6, 9, ...}` up to the grid dimension.
- Computed as `range(0, width, 3)` for avenues and `range(0, height, 3)` for streets.
- Stored as instance variables (`avenue_cols`, `street_rows`) on the `Grid` object.

**Rationale:**
- Spacing of 3 matches the architecture's default and keeps the city-blocks pattern consistent across sizes.
- Starting at 0 ensures edge cells are always traversable (important for vehicle spawning).
- Instance variables make the pattern explicit and testable.

**Future note:** Spacing of 3 is a simplification. A future improvement should derive spacing dynamically from grid dimensions (e.g., `max(2, size // 4)`) so that larger grids produce proportionally spaced street grids rather than too-dense patterns.

---

## Decision: Grid Dimension Validation Constants (Task: P1-GRID-01)

**Date:** 2026-03-08
**Context:** `Grid.__init__()` takes raw `int` args and can be called directly, bypassing `SimulationConfig` Pydantic validation. A single source of truth is needed for min/max grid size.
**Decision:**
- Define `MIN_GRID_SIZE = 1` and `MAX_GRID_SIZE = 100` as constants in `backend/config.py`.
- `SimulationConfig` Field bounds (`ge=1, le=100`) reference these same constants.
- `Grid.__init__()` imports and validates against these constants, raising `ValueError` with a descriptive message on violation.

**Rationale:**
- Single source of truth: one place to change the limits, both Pydantic and Grid validation stay in sync.
- Defense-in-depth: Grid rejects invalid dimensions even when called outside the API path.
- `config.py` is the natural home since it already owns all simulation-wide limits.

---

## Decision: Defer Vehicle Validation Caching Until Integrated Profiling (Task: P1-VEH-01)

**Date:** 2026-03-25
**Context:** `Vehicle.to_dict()` currently calls `get_next_position()` and
`get_remaining_distance()`, and both methods validate path state. Review feedback
requested optimization to avoid duplicate validation on serialization hot paths.
At the same time, another review emphasized reusing these public methods for
consistency and maintainability.
**Decision:** Keep the current implementation for now (no validation caching and
no internal no-validation helper yet). Defer optimization until post-integration
profiling once vehicle movement and engine tick orchestration are implemented
(P1-VEH-03 + P1-ENG-02).
**Rationale:**
- Correctness and contract consistency are currently the priority; public methods
  retain defensive validation at their boundaries.
- Premature micro-optimization risks extra complexity (cache invalidation or
  split validation paths) before real runtime evidence exists.
- Integrated runtime behavior (spawn/move/snapshot loop) is required to measure
  meaningful impact; isolated method-call timing is insufficient for this
  decision.
- A dedicated perf watch item (`PERF-WATCH-VEH-01`) already tracks the follow-up
  and decision point.

---

## Decision: Metrics Improvement Requires Both Comparison Groups (Task: P1-MET-01)

**Date:** 2026-05-18
**Context:** The Phase 1 metrics task needed a precise rule for `Metrics.improvement`
when only normal vehicles or only emergency vehicles had completed trips.
Without a guard, the formula could report a misleading non-zero percentage before
both groups had data.
**Decision:** Return `0.0` for `Metrics.improvement` until at least one normal
vehicle and one emergency vehicle have both completed trips. Once both groups
exist, compute improvement as the percentage delta between average normal and
average emergency travel time.
**Rationale:**
- Avoids reporting a misleading partial-baseline improvement value during early
  simulation ticks.
- Keeps the metric interpretable as a comparison rather than a single-group
  placeholder.
- Preserves deterministic, aggregate-only Phase 1 behavior without adding
  historical pairing or route-level normalization.

---

## Implementation Decision Template

For future implementation decisions, use this format and link to task ID from docs/tasks.md:

```markdown
## Decision: [Title] (Task: P1-GRID-01)
**Date:** 2026-XX-XX
**Context:** [What needed deciding]
**Decision:** [What you chose]
**Rationale:** [Why this choice]
```
