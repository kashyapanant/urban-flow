# Urban Flow — Implementation Design Decisions

This document records design decisions made during the implementation of the backend skeleton that were not fully specified in the architecture document.

---

## Decision: Vehicle ID Generation Format

**Date:** 2026-02-28
**Context:** The architecture specifies that vehicles need unique IDs but doesn't specify the format.
**Decision:** Use short UUID format (first 8 characters of UUID4) for vehicle IDs.
**Rationale:** 
- UUIDs guarantee uniqueness across simulation runs
- Short format (8 chars) is readable in logs and debugging
- UUID4 is cryptographically random, avoiding predictable patterns

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

## Decision: API Input Validation for ConfigUpdateRequest

**Date:** 2026-03-05
**Context:** ConfigUpdateRequest model lacked validation constraints, creating security/robustness gap where invalid data could reach simulation engine.
**Decision:** Add Pydantic Field validation to match SimulationConfig constraints exactly.
**Rationale:**
- Prevents invalid configuration values from reaching simulation engine
- Provides clear error messages with 422 HTTP responses for invalid input
- Maintains consistency between API and core config validation
- Follows FastAPI/Pydantic best practices for input validation