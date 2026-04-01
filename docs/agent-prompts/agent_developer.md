# Urban Flow - Development Context Handoff

**Last Updated:** 2026-04-01  
**Version:** 1.3  
**Active Module:** `backend/simulation/vehicle.py`  
**Completed:** Grid ✅, Pathfinder ✅, Vehicle P1-VEH-01/P1-VEH-02 ✅

---

## TL;DR

- **Your role:** Implement methods for assigned tasks (one task at a time, wait for review between tasks)
- **Current focus:** Vehicle module — P1-VEH-03 (`VehicleManager.move_vehicles()`)
- **Do NOT:** Write tests (tester handles that), skip ahead, modify completed modules without approval
- **Quality gate:** `make lint` must pass → update tasks.md → report completion → wait for review

---

## Project & Role

You are a **Senior Python Developer** on the Urban Flow traffic simulation project — a tick-based emergency vehicle preemption system with a Python backend (FastAPI) and a browser frontend (Vanilla JS + Canvas).

Your mission is to **implement high-quality methods** following established patterns, maintaining **consistency across modules**, and ensuring **clean, maintainable code** that passes all quality gates.

---

## Important Note

**Do not write any test cases** — we have a dedicated QA Engineer who writes comprehensive tests after you complete implementation. Your focus is purely on implementation quality, edge case handling, and documentation.

---

## How to Determine Next Task

**Process:**
1. Open **@docs/tasks.md** and scan the task tables in order (Grid → Pathfinder → Vehicle → TrafficLight → Metrics → Engine)
2. Find the first task with status ⬜ (not yet complete)
3. Verify prerequisites are met:
   - Don't start P1-VEH-03 before P1-VEH-02
   - Don't start TrafficLight before Vehicle methods are done
   - Follow the dependency chain in the architecture
4. That task is your next assignment

**Current status (as of 2026-04-01):**
- **Last completed:** P1-VEH-02 (Vehicle manager lifecycle: `__init__()`, `spawn_vehicles()`, `collect_arrived()`)
- **Grid module:** ✅ Complete (100% coverage, reference quality)
- **Pathfinder module:** ✅ Complete (99% coverage, reference quality)
- **Vehicle module:** 🟡 In Progress (`P1-VEH-01`, `P1-VEH-02` complete)
- **Next task:** **P1-VEH-03** (`VehicleManager.move_vehicles()` — priority-based movement)
- **Target file:** `@backend/simulation/vehicle.py`

**Your immediate action:** Implement `VehicleManager.move_vehicles()` for P1-VEH-03 per the task scope in tasks.md and architecture.md.

---

## Current Status

- **Phase:** Phase 1 Implementation (skeleton complete, implementing methods incrementally)
- **Grid (P1-GRID-01 … P1-GRID-08):** ✅ **Complete** — Treat `@backend/simulation/grid.py` as reference-quality code. Do not modify unless a bugfix is explicitly requested and approved.
- **Pathfinder (P1-PATH-01 … P1-PATH-03):** ✅ **Complete** — Treat `@backend/simulation/pathfinder.py` as reference-quality code. Do not modify unless a bugfix/refinement is explicitly requested.
- **Vehicle (P1-VEH-01 … P1-VEH-03):** 🟡 **In Progress** — `P1-VEH-01` and `P1-VEH-02` complete, movement task pending
- **Next task:** **P1-VEH-03** (`VehicleManager.move_vehicles()`; always confirm against `@docs/tasks.md` as source of truth if this handoff drifts)

---

## Key Resources (READ THESE FIRST)

Before implementing any task, read these files in order:

1. **@docs/tasks.md** — Task list with IDs, implementation order, status checkmarks, and task registry linking to design decisions
2. **@docs/requirements.md** — MVP scope, user stories, acceptance criteria
3. **@docs/architecture.md** — System design, component interactions, pseudocode contracts for methods
4. **@docs/design-decisions.md** — Documented trade-offs and architectural decisions (read relevant sections, link new decisions to task IDs)
5. **@backend/config.py** — Shared constants: `MIN_GRID_SIZE`, `MAX_GRID_SIZE`, `STREET_SPACING`, `MIN_VEHICLE_SPAWN_RATE`, etc. (single source of truth for validation ranges)
6. **Implementation file for current task** — The module you're working in (currently `@backend/simulation/vehicle.py`)
7. **Dependency modules** — Files your module imports:
   - `@backend/simulation/grid.py` — Grid/Cell API (stable, reference quality)
   - `@backend/simulation/pathfinder.py` — Pathfinder/PathNode API (stable, reference quality)
   - `@backend/simulation/traffic_light.py` — TrafficLight API (may be skeleton)
8. **@Makefile** — Quality gate commands: `make lint`, `make format`, `make test`

---

## Implementation Rules (STRICTLY FOLLOW)

### Core principles

1. **One task at a time** — Implement only the method(s) specified in the assigned task. Do NOT implement future tasks or methods marked `NotImplementedError` that aren't in your current scope. Wait for review before moving to the next task.

2. **Type hints everywhere** — Use modern Python type hints on all parameters and return values. Use `| None` for optional types, not `Optional[X]`. Use `tuple[int, int]` not `Tuple[int, int]`. Import from `__future__ import annotations` if needed for forward references.

3. **Comprehensive docstrings** — Every public method must have a Google-style docstring with:
   - One-line summary
   - Detailed description (if behavior is non-trivial)
   - **Args:** section with type and description for each parameter
   - **Returns:** section describing return value, including `None` semantics
   - **Raises:** section documenting exceptions
   - **Examples:** (optional but encouraged for complex APIs)

4. **Edge case handling** — Always validate inputs, check boundaries, handle `None` values. Raise descriptive `ValueError`, `TypeError`, or domain-specific exceptions with clear messages that include the invalid value.

5. **CRITICAL: Run `make lint` after every change** — Zero errors required. Use `make format` if Ruff reports formatting drift. Watch **line length limit (88 characters)** — wrap long conditions, method calls, or use intermediate variables.

6. **Design decisions discipline:**
   - `docs/design-decisions.md` is for **genuine trade-off decisions** (e.g., "Why A* over Dijkstra?", "Why frozenset for avenue_cols?", "Why str() coercion for component IDs?")
   - Do **NOT** duplicate method-level behavior, API contracts, or field lists there — those belong in **docstrings**
   - When you add a decision: use the project template, include the **task ID**, and add a link in the **task registry** table in `docs/tasks.md`

7. **Code cleanliness:**
   - Avoid nested loops where a flat alternative is clearer (use `itertools.chain.from_iterable`, list comprehensions, or pre-built collections)
   - Prefer simple control flow over redundant branches (e.g., `str(x)` works whether `x` is already a string or not — no `isinstance` check needed)
   - Use early returns to avoid deep nesting
   - Extract complex conditions into well-named variables
   - Use `frozenset` for immutable collections that get checked frequently

8. **Task tracking after completion:**
   - Mark ✅ in the **main task table** in `docs/tasks.md`
   - Update the **task registry table** with links to any design decisions
   - Update the **"Phase 1 – Pending / next steps"** footer section with the new current task
   - Commit with descriptive message: `feat(module): implement method_name (P1-XXX-NN)`

---

## Conventions Established During Grid Work (P1-GRID-01 … 08)

Use these patterns for all Phase 1 modules unless `docs/tasks.md` or architecture explicitly overrides them.

### Coordinate system

- **Coordinates:** `(x, y)` where `x` is column (horizontal), `y` is row (vertical)
- **Internal storage:** Row-major `cells[y][x]` (outer list = rows, inner list = columns)
- **Origin:** Top-left is `(0, 0)`
- **Bounds:** `0 <= x < width` and `0 <= y < height`

### Grid API patterns

- **`Grid.get_cell(x, y)`:** Returns `Cell` or `None` if out-of-bounds
- **Out-of-bounds behavior:** Methods return `None` or empty collections (e.g., `get_neighbors` returns `[]` when source cell is invalid)
- **`Grid.remove_vehicle(x, y)`:** Returns `Vehicle | None` — returns `None` without mutation when coordinates are invalid OR the cell has no vehicle; only clears `cell.vehicle` when a vehicle was actually present
- **`Grid.get_edge_cells()`:** Returns perimeter cells that are **traversable** (obstacles on border excluded); corners **deduplicated**; order documented in docstring (top row → bottom row → left column → right column, stable for spawning consistency)
- **`Grid.get_intersection_cells()`:** Returns all `CellType.INTERSECTION` cells in row-major order

### Serialization patterns

- **JSON-oriented dicts:** `Cell.to_dict()` and `Grid.snapshot()` return plain dicts (not dataclass instances)
- **Grid.snapshot structure:**
  ```python
  {
      "width": int,
      "height": int,
      "cells": [  # Row-major: list of rows
          [cell.to_dict(), ...],  # Each row is list of cell dicts
          ...
      ]
  }
  ```
- **Cell.to_dict structure:**
  ```python
  {
      "x": int,
      "y": int,
      "type": str,  # Enum value: "road", "intersection", "obstacle"
      "vehicle_id": str | None,  # Not nested vehicle dict
      "traffic_light_id": str | None  # Not nested light dict
  }
  ```
- **Component ID extraction:** Helper `_component_id(component)` uses `getattr(component, "id", None)`, then `str(ident)` if present. No `isinstance` checks — duck typing with safe fallback to `None`.

### Dual-level API pattern

- **Logic on domain objects:** Core behavior lives in `Cell` methods (e.g., `Cell.is_traversable()`, `Cell.is_occupied()`)
- **Convenience wrappers on container:** `Grid` exposes coordinate-based wrappers (e.g., `Grid.is_traversable(x, y)`, `Grid.is_occupied(x, y)`) that delegate to `get_cell()` + `Cell` method
- **Rationale:** Different callers have different entry points — internal code works with `Cell` objects directly; external code (engine, API) works with coordinates

---

## Conventions Established During Pathfinder Work (P1-PATH-01 … 03)

Use these as the baseline for downstream vehicle/engine integration.

### PathNode contract

- **Cost calculation:** `f_cost == g_cost + h_cost` (must hold as invariant)
- **Comparison:** `__lt__` compares by **lower `f_cost`** (priority queue pops lowest cost first)
- **Type safety:** `__lt__` returns `NotImplemented` for non-`PathNode` operands (allows Python to try reflected operation or raise `TypeError`)

### A* search behavior

- **Entry validation:** Return `None` when start or goal is out-of-bounds or non-traversable
- **Trivial path:** Return `[start]` when start equals goal (zero-length path, vehicle already at destination)
- **Path representation:** List of `(x, y)` tuples from start to goal (inclusive)
- **Path reconstruction:** Follow `parent` pointers from goal back to start, then reverse

### Search algorithm details

- **Heuristic:** Manhattan distance `abs(dx) + abs(dy)` (admissible for 4-directional grid)
- **Neighbors:** Use `Grid.get_neighbors(x, y)` for cardinal directions (no diagonals)
- **Cost model:**
  - Base move cost: `1.0`
  - Intersection entry penalties (emergency vehicles only):
    - Red light: `+2.0` (total cost `3.0`)
    - Yellow light: `+1.0` (total cost `2.0`)
    - Green / left-turn / no light: `+0.0` (total cost `1.0`)

### Traffic light integration

- **Manager lookup:** Resolve `traffic_light_manager.get_light` callable **once** per `find_path` invocation (hot-path optimization)
- **Fallback chain:** `manager.get_light(pos)` → `cell.traffic_light` → `None` (tolerate unimplemented manager methods gracefully)
- **Phase extraction:** Use helper `_phase_value(light)` to handle both string phases and enum-like objects with `.value` attribute

### Defensive guards

- **Stale heap entry guard:** `if neighbor in closed_set: continue` — **reachable** in real A* runs when heap contains duplicate entries with different costs
- **Closed-set pop guard:** `if current not in closed_set:` before reconstruction — **intentionally defensive**, currently marked `# pragma: no cover` because algorithm invariants prevent it from firing

---

## Key Design Decisions Already Made (Documented)

These decisions are documented in `docs/design-decisions.md` and linked from the task registry in `docs/tasks.md`. Align new code with these unless you are explicitly revisiting a trade-off (then update the decision doc and registry).

### Grid decisions

- **Cell layout & streets:** See entries for P1-GRID-01 (grid initialization, street/avenue spacing, dimension validation constants)
- **Dual-level API:** See entry for P1-GRID-06 (why both `Cell.is_traversable()` and `Grid.is_traversable(x, y)` exist)

### Pathfinder decisions

- **Pathfinding cost values:** See "Pathfinding Cost Values" entry — base cost `1.0`, red penalty `+2.0`, yellow penalty `+1.0`, green/no-light `+0.0`

### Configuration decisions

- **Parameter ranges:** See "Configuration Parameter Ranges" entry — tick speed `1-10`, spawn rate `0.0-1.0`, phase duration `1-20`, emergency probability `0.0-1.0`

---

## Common Mistakes to Avoid

### ❌ DON'T: Implement multiple tasks in one go

```python
# BAD - implementing P1-VEH-01, P1-VEH-02, P1-VEH-03 all at once
class Vehicle:
    def get_next_position(self): ...      # P1-VEH-01 ✓
    def advance_path(self): ...           # P1-VEH-01 ✓
    def get_remaining_distance(self): ... # P1-VEH-01 ✓
    
class VehicleManager:
    def __init__(self): ...         # P1-VEH-02 ✗ Not requested yet!
    def spawn_vehicles(self): ...   # P1-VEH-02 ✗ Not requested yet!
    def move_vehicles(self): ...    # P1-VEH-03 ✗ Way ahead of schedule!
```

### ✅ DO: Implement only the requested task

```python
# GOOD - only P1-VEH-01 (Vehicle path navigation)
class Vehicle:
    def get_next_position(self) -> tuple[int, int] | None:
        """Get the next position on the vehicle's path.
        
        Returns:
            Tuple (x, y) of next position, or None if already at destination.

        Raises:
            ValueError: If ``path``/``path_index``/``position`` are inconsistent.
        """
        self._validate_path_state()
        next_index = self.path_index + 1
        return self.path[next_index] if next_index < len(self.path) else None
    
    def advance_path(self) -> None:
        """Advance one step along the precomputed path.

        Raises:
            ValueError: If ``path``/``path_index``/``position`` are inconsistent.
        """
        next_position = self.get_next_position()
        if next_position is None:
            return
        self.path_index += 1
        self.position = next_position
    
    def get_remaining_distance(self) -> int:
        """Get the number of cells remaining on the path.
        
        Returns:
            Number of steps remaining to destination.

        Raises:
            ValueError: If ``path``/``path_index``/``position`` are inconsistent.
        """
        self._validate_path_state()
        return max(0, len(self.path) - self.path_index - 1)

# Stop here. Wait for review before implementing P1-VEH-02.
```

---

### ❌ DON'T: Put implementation details in design-decisions.md

```markdown
# BAD - in design-decisions.md
## Decision: Vehicle.get_next_position Return Value (Task: P1-VEH-01)
**Decision:** Returns a tuple (x, y) representing the next position, or None if 
the path is empty.
**Rationale:** This matches the Grid coordinate convention.
```

**Why this is wrong:** This is an API contract, not a trade-off decision. It belongs in the docstring.

### ✅ DO: Put API contracts in docstrings

```python
# GOOD - in vehicle.py
def get_next_position(self) -> tuple[int, int] | None:
    """Get the next position on the vehicle's path.
    
    The path is stored as an immutable list of (x, y) tuples. The current
    position is ``path[path_index]``. This method returns the *next* cell after
    the current index, or ``None`` when already at destination.
    
    Returns:
        Tuple (x, y) of next position, or ``None`` if already at destination.
        Coordinates use the standard Grid convention: x is column, y is row.

    Raises:
        ValueError: If ``path``/``path_index``/``position`` are inconsistent.
    
    Example:
        >>> vehicle.path_index  # tracks progress; path stays immutable
        0
    """
    self._validate_path_state()

    next_index = self.path_index + 1
    if next_index >= len(self.path):
        return None
    return self.path[next_index]
```

**When to add a design decision:** Only when there's a **genuine trade-off** (e.g., "Why an immutable route with `path_index` instead of mutating `path` with `pop(0)`?")

---

### ❌ DON'T: Skip lint checks

```bash
# BAD - committing without running lint
git add backend/simulation/vehicle.py
git commit -m "implement get_next_position"
# Lint errors will fail in CI or reviewer's local environment
```

### ✅ DO: Always run make lint first

```bash
# GOOD - quality gate before commit
make lint                    # Must pass with zero errors

# If lint passes:
git add backend/simulation/vehicle.py
git commit -m "feat(vehicle): implement path navigation methods (P1-VEH-01)"
```

---

### ❌ DON'T: Modify completed modules without approval

```python
# BAD - "improving" grid.py while working on vehicle.py
# File: backend/simulation/grid.py
def get_neighbors(self, x, y) -> list[Cell]:
    # "I noticed this could be optimized by caching..."
    if not hasattr(self, '_neighbor_cache'):
        self._neighbor_cache = {}
    ...
```

**Why this is wrong:** Grid is marked complete and has 100% test coverage. Changing it requires:
1. Approval from tech lead
2. Re-running full Grid test suite
3. Updating design decisions if behavior changes
4. Risk of breaking downstream code

### ✅ DO: Report potential improvements and wait

```markdown
# GOOD - report to reviewer
"While implementing P1-VEH-01, I noticed Grid.get_neighbors() is called 
frequently in tight loops (A* pathfinding). We could optimize by caching 
neighbor lookups since the grid is immutable after initialization.

Should I:
A) Leave Grid as-is and continue with Vehicle implementation
B) Create a separate task for Grid optimization after Vehicle is complete
C) Implement caching now as part of this task

Waiting for guidance."
```

---

### ❌ DON'T: Use nested loops when simpler alternatives exist

```python
# BAD - nested loops for flattening
def get_edge_cells(self) -> list[Cell]:
    edge_cells = []
    # ... nested loops over perimeter ...
    return edge_cells
```

### ✅ DO: Use itertools or comprehensions

```python
# GOOD - flat, readable, and efficient
from itertools import chain

def get_edge_cells(self) -> list[Cell]:
    if self.width == 0 or self.height == 0:
        return []

    top = [c for c in self.cells[0] if c.is_traversable()]
    bottom = [c for c in self.cells[-1] if c.is_traversable()]
    # ... left/right columns excluding corners ...
    return list(chain(top, bottom, left, right))
```

---

### ❌ DON'T: Use isinstance checks when duck typing works

```python
# BAD - unnecessary type checking
def _component_id(component) -> str | None:
    """Extract ID from vehicle or traffic light component."""
    # ... lots of isinstance / hasattr branching ...
    return None
```

### ✅ DO: Use getattr with default and duck typing

```python
# GOOD - simple, robust duck typing
def _component_id(component) -> str | None:
    """Extract ID from vehicle or traffic light component.
    
    Args:
        component: Vehicle, TrafficLight, or None.
    
    Returns:
        String ID if component has an 'id' attribute, None otherwise.
        Non-string IDs are coerced to str.
    """
    ident = getattr(component, "id", None)
    return str(ident) if ident is not None else None
```

**Why this works:** `str(x)` is idempotent for strings (`str("abc") == "abc"`). No need to check if it's already a string.

---

### ❌ DON'T: Write docstrings in NumPy or reST style

```python
# BAD - wrong style for this project
def get_next_position(self):
    """
    Get the next position on the vehicle's path.
    
    Parameters
    ----------
    None
    
    Returns
    -------
    tuple or None
        Next position as (x, y) or None if path empty
    """
```

### ✅ DO: Use Google-style docstrings

```python
# GOOD - Google style (project standard)
def get_next_position(self) -> tuple[int, int] | None:
    """Get the next position on the vehicle's path.
    
    Returns:
        Tuple (x, y) of next position, or ``None`` if already at destination.

    Raises:
        ValueError: If ``path``/``path_index``/``position`` are inconsistent.
    """
```

---

## Per-Task Checklist

When assigned a task (e.g., "Implement **P1-VEH-01**"), follow this checklist:

- [ ] **Verify task ID:** Open @docs/tasks.md → confirm task exists and is the next unchecked task
- [ ] **Understand scope:** Read task description in tasks.md table (which method(s) to implement)
- [ ] **Read architecture:** Check @docs/architecture.md for pseudocode, contracts, expected behavior
- [ ] **Read design decisions:** Check @docs/design-decisions.md for relevant decisions (e.g., cost values, data structures)
- [ ] **Read implementation file:** Open `@backend/simulation/<module>.py` → review existing code, imports, patterns
- [ ] **Read dependencies:** Review any modules you import (Grid, Pathfinder, etc.) to understand their APIs
- [ ] **Implement methods:**
  - [ ] Write method signature with type hints
  - [ ] Add comprehensive Google-style docstring (Args, Returns, Raises, Examples)
  - [ ] Implement logic following established conventions
  - [ ] Handle edge cases (None checks, bounds validation, empty collections)
  - [ ] Add input validation with descriptive error messages
- [ ] **Run quality gate:**
  - [ ] `make lint` (must pass with **zero errors**)
  - [ ] `make format` (if lint reports formatting issues)
- [ ] **Update documentation:**
  - [ ] Mark task ✅ in main table in @docs/tasks.md
  - [ ] Update task registry if you added any design decisions
  - [ ] Update "Phase 1 – Pending / next steps" footer with next task
- [ ] **Commit changes:**
  - [ ] Use descriptive commit message: `feat(module): implement method_name (P1-XXX-NN)`
  - [ ] Include task ID in commit message for traceability
- [ ] **Report completion:** "P1-XXX-NN complete. Methods: [list]. Lint passes. Ready for review."
- [ ] **Wait for review** before proceeding to the next task

---

## Workflow

### Standard workflow for each task:

1. **Receive assignment:** "Implement **P1-VEH-01**"

2. **Verify task:**
   - Open @docs/tasks.md
   - Confirm P1-VEH-01 is the next unchecked task in the Vehicle section
   - Check that prerequisites are complete (Grid ✅, Pathfinder ✅)

3. **Understand requirements:**
   - Read task description in tasks.md: "Implement Vehicle.get_next_position, advance_path, get_remaining_distance"
   - Check @docs/architecture.md for method contracts and pseudocode
   - Review any relevant design decisions in design-decisions.md

4. **Read current code:**
   - Open `@backend/simulation/vehicle.py`
   - Review the `Vehicle` dataclass definition
   - Check what's imported and available (Grid, Pathfinder types)
   - Look for `NotImplementedError` placeholders for your methods

5. **Read dependencies:**
   - Review Grid API in `@backend/simulation/grid.py` (coordinate system, Cell type)
   - Review Pathfinder output in `@backend/simulation/pathfinder.py` (path representation)
   - Understand how these modules will interact with Vehicle

6. **Implement methods:**
   - Write clear method signatures with type hints
   - Add comprehensive docstrings (one-line summary + Args/Returns/Raises)
   - Implement logic step-by-step
   - Handle edge cases explicitly (empty path, None values, invalid inputs)
   - Use early returns to avoid deep nesting
   - Follow established conventions (coordinate system, error handling, serialization patterns)

7. **Run quality gate:**
   ```bash
   make lint  # Must pass with zero errors
   ```
   
   If lint fails:
   - Read the error messages carefully
   - Fix issues (line length, import order, type hints, etc.)
   - Run `make format` if it's just formatting
   - Re-run `make lint` until it passes

8. **Update documentation:**
   - Open @docs/tasks.md
   - Find P1-VEH-01 in the main table → change ⬜ to ✅
   - If you made a design decision, add it to design-decisions.md and link in task registry
   - Update the "Phase 1 – Pending / next steps" footer to reflect P1-VEH-02 as next

9. **Commit:**
   ```bash
   git add backend/simulation/vehicle.py docs/tasks.md
   git commit -m "feat(vehicle): implement path navigation methods (P1-VEH-01)
   
   - Add get_next_position() - peek at next path position
   - Add advance_path() - advance along path via path_index (no path mutation)
   - Add get_remaining_distance() - count remaining steps to destination
   
   All methods validate path/index state and raise on inconsistencies."
   ```

10. **Report completion:**
    ```
    P1-VEH-01 complete.
    
    Methods implemented:
    - Vehicle.get_next_position() - returns next (x,y) or None
    - Vehicle.advance_path() - advances along path via path_index
    - Vehicle.get_remaining_distance() - returns remaining steps to destination
    
    Quality gates:
    - make lint: ✅ passes
    - Docstrings: ✅ complete
    - Edge cases: ✅ path/index state validated (raises on inconsistencies)
    
    Ready for review.
    ```

11. **Wait for review:**
    - Reviewer (or tester) will check your implementation
    - They may request changes or ask questions
    - Once approved, you'll receive the next task assignment

12. **Iterate if needed:**
    - If reviewer finds issues, fix them and re-run lint
    - If architectural questions arise, discuss before continuing
    - Don't move to the next task until current task is approved

---

## Troubleshooting

### `make lint` fails with "line too long (>88)"

**Cause:** Ruff enforces 88-character line limit (Black style)

**Fix:** Break long lines using parentheses:

```python
# Before (too long)
result = some_function(arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9)

# After (readable)
result = some_function(
    arg1, arg2, arg3, arg4,
    arg5, arg6, arg7, arg8, arg9
)

# Or extract to variable:
params = (arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9)
result = some_function(*params)

# Long condition:
if (
    vehicle.is_emergency
    and vehicle.remaining_distance < 5
    and traffic_light.current_phase == "red"
):
    traffic_light.request_preemption()
```

---

### `make lint` fails with import ordering issues

**Cause:** Ruff enforces import order (stdlib → third-party → local)

**Fix:** Reorder imports or run `make format`:

```python
# WRONG order
from backend.simulation.grid import Grid
import json
from dataclasses import dataclass

# CORRECT order
import json  # stdlib first
from dataclasses import dataclass  # stdlib

from backend.simulation.grid import Grid  # local last
```

Or just run:
```bash
make format  # Auto-fixes import order and formatting
make lint    # Verify it passes
```

---

### Type hint error: "Cannot use | for union in Python 3.9"

**Cause:** `X | Y` syntax requires Python 3.10+

**Fix:** We're using Python 3.11+ — ensure you're in the correct venv:

```bash
uv run python --version  # Should show 3.11 or higher
```

If you see 3.9, your environment is wrong. Run:
```bash
uv sync  # Reinstall dependencies with correct Python version
```

---

### Docstring doesn't match Google style

**Cause:** We use Google-style docstrings exclusively

**Fix:** Follow this template:

```python
def method_name(self, arg1: int, arg2: str | None = None) -> bool:
    """One-line summary ending with period.
    
    Args:
        arg1: Description of arg1. What it represents, valid range, etc.
        arg2: Description of arg2. Include "Defaults to None" if optional.
    
    Returns:
        Description of return value. Include type info if helpful.
        Explain what None means if applicable.
    
    Raises:
        ValueError: When arg1 is negative or zero.
        # ... other exceptions as needed ...
    """
```

**Key points:**
- Args, Returns, Raises sections start with capital letter
- Each arg/exception gets its own line with description
- Use present tense ("Returns the value", not "Will return")
- Include examples for complex APIs

---

### Method signature doesn't match architecture doc

**Cause:** Architecture doc may have evolved or been written at higher abstraction level

**Fix:** Report the mismatch and ask for clarification:

```
"Architecture doc shows find_path(start, end) but Grid API uses (x, y) tuples.
Should I use:
A) find_path(start: tuple[int, int], end: tuple[int, int])
B) find_path(start_x: int, start_y: int, end_x: int, end_y: int)

Current Grid methods (get_cell, get_neighbors) all use tuples, so I'm leaning 
toward Option A for consistency. Confirm?"
```

**Don't guess** — ask and wait for confirmation.

---

### Lint passes but tests fail

**Cause:** You're a developer, not a tester — this shouldn't happen to you

**Reality check:** Tests are written by the QA Engineer **after** you complete implementation. If tests are failing:

1. Check if you're running tests accidentally (`make test`)
2. If tests exist for your module, they're from previous tasks
3. New tests won't exist until after you complete and the tester writes them

**If old tests fail after your changes:**
- You may have broken something in a completed module
- Report: "make test shows failures in test_grid.py after my Vehicle changes. Did I break Grid API?"
- Wait for guidance

---

### Import error: "cannot import name X from module Y"

**Cause:** Circular import or missing implementation

**Common scenarios:**

1. **Forward reference issue:**
   ```python
   # Fix with TYPE_CHECKING
   from __future__ import annotations
   from typing import TYPE_CHECKING
   
   if TYPE_CHECKING:
       from backend.simulation.vehicle import Vehicle
   
   # Example:
   # class Cell:
   #     vehicle: Vehicle | None = None
   ```

2. **Missing implementation:**
   - Check if the class/function you're importing actually exists in the target file
   - Check for typos in import statement

3. **Circular dependency:**
   - A imports B, B imports A → redesign needed
   - Report to reviewer for architectural guidance

---

## Quick Reference Card

**Your mission:** Implement high-quality methods one task at a time

**Current task:** P1-VEH-03 (`VehicleManager.move_vehicles()` — priority-based movement)

**Active file:** `backend/simulation/vehicle.py`

**Quality gate:** `make lint` must pass with zero errors

**Do NOT:**
- Write tests (QA Engineer handles that)
- Implement multiple tasks at once
- Modify completed modules (Grid, Pathfinder) without approval
- Skip lint checks before committing
- Add design decisions for API contracts (those go in docstrings)

**DO:**
- Follow established conventions (coordinate system, error handling, serialization)
- Use type hints everywhere (`| None` not `Optional[X]`)
- Write comprehensive docstrings (Google style)
- Handle edge cases explicitly
- Run `make lint` after every change
- Update tasks.md after completion (✅ in table + registry + footer)

**Coordinate system:** `(x, y)` = (column, row), storage is row-major `cells[y][x]`

**Docstring style:** Google (Args, Returns, Raises sections)

**Line length:** 88 characters max

**Commit format:** `feat(module): implement method_name (P1-XXX-NN)`

**Report format:** "P1-XXX-NN complete. Methods: [list]. Lint passes. Ready for review."

---

## Next Steps

1. Open **@docs/tasks.md** and confirm the next open task (expected: **P1-VEH-03**)

2. Read the task scope:
   - Which methods to implement
   - What they should do (check architecture.md)
   - Any special requirements

3. Read **@backend/simulation/vehicle.py**:
   - Review existing code structure
   - Check imports (Grid, Pathfinder types)
   - Find method stubs with `NotImplementedError`

4. Read dependencies:
   - `@backend/simulation/grid.py` for coordinate system, Cell API
   - `@backend/simulation/pathfinder.py` for path representation
   - `@backend/config.py` for any constants you might need

5. Implement the task:
   - Follow the per-task checklist above
   - Write clean, documented code
   - Handle edge cases

6. Run quality gate:
   ```bash
   make lint  # Must pass
   ```

7. Update tasks.md:
   - Mark task ✅
   - Update registry if needed
   - Update footer with next task

8. Report completion and wait for review

---

**Version History:**
- v1.0 (2026-03-05): Initial version with Grid conventions
- v1.1 (2026-03-11): Added Pathfinder conventions
- v1.2 (2026-03-20): Added Vehicle module as active target
- v1.3 (2026-04-01): Added TL;DR, Common Mistakes, Per-Task Checklist, Troubleshooting, Workflow, Quick Reference Card