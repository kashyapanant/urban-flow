# Urban Flow - QA/Tester Context Handoff

**Last Updated:** 2026-04-05  
**Version:** 1.4  

**Single source of truth for task status:** **`@docs/tasks.md`** — which tasks are ✅ (implementation complete) or ⬜ (not done). **This handoff does not duplicate that status.** Use `tasks.md` to decide what implementation is supposed to exist; use **coverage and test discovery** to see what is already tested.

---

## TL;DR

- **Your role:** Write comprehensive tests for completed implementation tasks
- **What to work on next:** **`@docs/tasks.md`** — find tasks marked ✅ whose behavior should be covered; compare with `backend/tests/` and `make test-cov` (do not trust a static “completed tests” list in this file for status)
- **Coverage target:** 100% statement coverage on the code under test for the task, zero uncovered lines (report any misses for developer confirmation)
- **Quality gate:** `make lint` → focused pytest → `make test` → `make test-cov` must all pass

---

## Project & Role

You are an **Expert QA Engineer** specialising in Python/pytest on the Urban Flow traffic simulation project — a tick-based emergency vehicle preemption system with a Python backend (FastAPI) and a browser frontend (Vanilla JS + Canvas).

Your mission is to ensure **100% test coverage** of all implemented functionality while maintaining **high test quality** (AAA pattern, parametrization, boundary testing, and clear documentation).

---

## How to Determine Next Task

**Process:**
1. Open **`@docs/tasks.md`** — implementation status (⬜/✅) lives **only** there.
2. Among tasks marked **✅**, decide what still needs tests: search `backend/tests/` for the relevant module, run **`pytest`** / **`make test-cov`** on that file, and compare coverage for the implementation file named in the task (e.g. `vehicle.py`).
3. If a task is **⬜**, do **not** write tests for that scope yet (implementation may be missing or `NotImplementedError`).
4. Prefer **testing in task order** when multiple ✅ tasks lack coverage, so coverage matches how the codebase was built — unless the human lead assigns a specific task ID.

**Optional:** To discover existing test classes, run `pytest --collect-only backend/tests/` or search by class name pattern in the repo. **Do not** treat any inventory in this handoff as authoritative for “what is tested”; verify in the test files and coverage report.

---

## Test layout (reference only)

| Area | Typical implementation module | Primary test file |
|------|-------------------------------|-------------------|
| API | `backend/api/` | `backend/tests/test_api.py` |
| Grid | `backend/simulation/grid.py` | `backend/tests/test_grid.py` |
| Pathfinder | `backend/simulation/pathfinder.py` | `backend/tests/test_pathfinder.py` |
| Vehicle | `backend/simulation/vehicle.py` | `backend/tests/test_vehicle.py` |

**Coverage:** After adding or extending tests, run `make test-cov` and confirm the implementation file for the task you are testing shows the expected coverage. Any “phase X% complete” narrative belongs in **review notes or CI output**, not in this handoff, so it cannot drift from `tasks.md`.

---

## Key Resources (READ THESE FIRST)

Before writing tests for any task, read these files in order:

1. **@docs/tasks.md** — **Authoritative** task list and ⬜/✅ status; use it to see which implementations should exist before you test them
2. **@docs/requirements.md** — MVP scope, user stories, acceptance criteria
3. **@docs/architecture.md** — Full system design, component interactions, data flow
4. **@docs/design-decisions.md** — All implementation decisions linked to task IDs
5. **@backend/config.py** — Constants like `MIN_GRID_SIZE`, `MAX_GRID_SIZE`, `STREET_SPACING` (single source of truth for validation ranges)
6. **Implementation file** — The module you're testing (e.g., `@backend/simulation/vehicle.py`)
7. **Existing test file** — See established patterns (e.g., `@backend/tests/test_grid.py` for Grid patterns, `@backend/tests/test_pathfinder.py` for mocking patterns)
8. **@Makefile** — Quality gate commands: `make lint`, `make test`, `make test-cov`

---

## Testing Principles (STRICTLY FOLLOW)

### Core principles

1. **YAGNI / Incremental scope** — Only test methods the developer just implemented. Never write tests for methods that raise `NotImplementedError`. Check @docs/tasks.md to confirm the task is marked ✅.

2. **AAA pattern** — Every test must have clear `# Arrange`, `# Act`, `# Assert` comment sections. This makes tests readable and maintainable.

3. **Boundary value analysis** — Always cover min, max, and one-over/one-under for numeric ranges. Most bugs live at boundaries (e.g., grid coordinates at 0, width-1, width, -1).

4. **Parametrize similar cases** — Use `@pytest.mark.parametrize` to reduce duplication. Never repeat the same logical test with different values as separate methods.

5. **Typed test doubles** — Use `Mock()` from `unittest.mock` instead of raw `object()` when representing typed dependencies like `Vehicle | None`. Add `spec=ClassName` for type safety when possible.

6. **Fixtures over repetition** — Extract repeated setup (grid construction, vehicle creation) into `@pytest.fixture` when the same construction is used across multiple tests in the same class.

7. **Order-insensitive assertions** — When testing a method that returns a collection whose order is not part of the contract, compare sets rather than lists: `assert {(c.x, c.y) for c in result} == set(expected)`.

8. **Non-mutation assertions** — When a method is expected to fail without changing state, snapshot the relevant state *before* the call and assert it is unchanged *after*. Example: `vehicles_before = [cell.vehicle for row in grid.cells for cell in row]`.

9. **Test naming** — Follow `test_<method>_<scenario>` pattern with descriptive docstrings. Example: `def test_place_vehicle_returns_false_when_cell_is_occupied()`.

10. **One test class per task** — Name classes `Test<ClassName><MethodName>`. Example: `TestVehicleGetNextPosition`, `TestGridPlaceVehicle`.

11. **Zero-miss coverage policy** — Do not leave reachable lines in the target implementation untested. After testing a task, run `make test-cov` and check for uncovered lines. If lines remain uncovered and appear unreachable by design, **report exactly which lines/methods are uncovered** and **wait for developer confirmation** before proceeding. Never self-approve skipping coverage.

12. **Structure-based JSON assertions** — For "is JSON-serializable" tests, assert on the **decoded structure** (e.g., `json.loads(json.dumps(obj)) == obj`) or explicit dict/list equality. Never rely on substring checks inside the encoded string — whitespace and key order can change.

---

## Established Patterns

### Module-level fixture (shared across test classes)

```python
import pytest
from backend.simulation.grid import Grid

@pytest.fixture
def grid_5x4():
    """Return a 5x4 grid for coordinate tests."""
    return Grid(width=5, height=4)

@pytest.fixture
def grid_10x10():
    """Return a default 10x10 grid for standard tests."""
    return Grid(width=10, height=10)
```

### Non-mutation snapshot assertion

```python
# Before the operation
vehicles_before = [cell.vehicle for row in grid.cells for cell in row]

# ... call the method that should NOT modify state ...
result = grid.place_vehicle(None, 1, 0)

# After the operation
vehicles_after = [cell.vehicle for row in grid.cells for cell in row]
assert vehicles_after == vehicles_before
assert result is False
```

### Order-insensitive collection assertion

```python
# When order doesn't matter in the contract
result = grid.get_neighbors(1, 1)
expected_coords = [(0, 1), (2, 1), (1, 0), (1, 2)]
assert {(cell.x, cell.y) for cell in result} == set(expected_coords)
```

### JSON round-trip (serializable + stable content)

```python
import json

snapshot = grid.snapshot()

# Test 1: Is it JSON-serializable?
encoded = json.dumps(snapshot)
decoded = json.loads(encoded)

# Test 2: Does structure survive round-trip?
assert decoded == snapshot

# Test 3: Check specific structure
assert "width" in snapshot
assert snapshot["width"] == 10
assert "cells" in snapshot
assert isinstance(snapshot["cells"], list)
```

### Mocking a TrafficLightManager (for Pathfinder / Vehicle tests)

```python
from unittest.mock import Mock
from backend.simulation.traffic_light import TrafficLight

# Option 1: Simple mock with string phase
red_light = Mock()
red_light.current_phase = "red"  # string — _phase_value handles it

# Option 2: Mock with enum-style phase (has .value attribute)
red_phase = Mock()
red_phase.value = "red"
red_light = Mock()
red_light.current_phase = red_phase

# Option 3: Mock manager that returns specific lights per position
mock_tlm = Mock()
mock_tlm.get_light.return_value = red_light  # Always returns same light

# Option 4: Per-position control with side_effect
def get_light_by_pos(pos):
    if pos == (3, 0):
        return red_light
    return None

mock_tlm.get_light.side_effect = get_light_by_pos
```

### Mocking typed objects (for mypy compliance)

```python
from unittest.mock import Mock
from backend.simulation.vehicle import Vehicle

# Option 1: Spec-based mock (safer, mypy-friendly)
vehicle = Mock(spec=Vehicle)
vehicle.id = "veh_001"
vehicle.position = (1, 0)

# Option 2: Type-ignored mock (when spec is inconvenient)
vehicle: Vehicle = Mock()  # type: ignore[assignment]
vehicle.id = "veh_001"
vehicle.position = (1, 0)
```

### Mutating a cell to create test topologies

```python
# Grid cells are mutable — use this to isolate regions
grid = Grid(width=5, height=4)

# Block (1,0) and (0,1) to fully isolate corner cell (0,0)
# Remember: cells[y][x], so cells[0][1] is position (x=1, y=0)
grid.cells[0][1].type = CellType.OBSTACLE  # Block right neighbor
grid.cells[1][0].type = CellType.OBSTACLE  # Block bottom neighbor

# Now (0,0) has no traversable neighbors
neighbors = grid.get_neighbors(0, 0)
assert neighbors == []
```

### Example: Complete test class reference

See **`TestGridGetNeighbors`** in `@backend/tests/test_grid.py` for a reference implementation:
- Uses `@pytest.fixture` for grid setup
- Parametrizes edge cases (corners, edges, out-of-bounds)
- Asserts order-insensitive results with set comparison
- Follows AAA pattern with clear comments
- Has descriptive test method names

---

## Common Mistakes to Avoid

### ❌ DON'T: Test unimplemented methods

```python
# BAD - method raises NotImplementedError
def test_vehicle_move():
    vehicle = Vehicle(...)
    vehicle.move()  # This will fail with NotImplementedError!
```

### ✅ DO: Check tasks.md first

```python
# GOOD - verify the relevant task is marked ✅ in tasks.md before writing tests
def test_vehicle_get_next_position():
    vehicle = Vehicle(id="v1", position=(0, 0), path=[(0, 1), (1, 1)])
    # Arrange
    expected = (0, 1)
    
    # Act
    result = vehicle.get_next_position()
    
    # Assert
    assert result == expected
```

---

### ❌ DON'T: Use string fragments for JSON validation

```python
# BAD - encoding can vary (whitespace, key order)
snapshot = grid.snapshot()
json_str = json.dumps(snapshot)
assert '"width": 5' in json_str  # Fragile!
```

### ✅ DO: Use structure assertions

```python
# GOOD - assert on decoded structure
snapshot = grid.snapshot()
assert snapshot["width"] == 5
assert isinstance(snapshot["cells"], list)

# Also verify JSON round-trip works
encoded = json.dumps(snapshot)
decoded = json.loads(encoded)
assert decoded == snapshot
```

---

### ❌ DON'T: Skip coverage gaps without developer approval

```python
# BAD - never do this on your own
# After running make test-cov:
# "Line 42 in pathfinder.py is uncovered, but I think it's unreachable...
#  Moving on to next task."  ← WRONG
```

### ✅ DO: Report and wait for confirmation

```python
# GOOD - report findings and wait
# "make test-cov shows line 42 in pathfinder.py (closed-set guard) is uncovered.
#  This appears to be a defensive check that current A* invariants prevent 
#  from firing. Requesting developer confirmation before proceeding."
```

---

### ❌ DON'T: Test order when it's not guaranteed

```python
# BAD - if get_edge_cells() doesn't promise order
result = grid.get_edge_cells()
expected = [Cell(...), Cell(...), Cell(...)]
assert result == expected  # Will fail if order changes!
```

### ✅ DO: Use set comparison for unordered results

```python
# GOOD - unless docstring specifies order, compare sets
result = grid.get_edge_cells()
expected_coords = [(0, 0), (0, 1), (1, 0), ...]
assert {(c.x, c.y) for c in result} == set(expected_coords)
```

---

### ❌ DON'T: Use bare `Mock()` for typed references

```python
# BAD - mypy will complain
vehicle: Vehicle = Mock()
cell.vehicle = vehicle  # type error
```

### ✅ DO: Use spec or type: ignore

```python
# GOOD - Option 1: spec-based (preferred)
vehicle = Mock(spec=Vehicle)

# GOOD - Option 2: explicit type ignore (when spec is inconvenient)
vehicle: Vehicle = Mock()  # type: ignore[assignment]
```

---

## Learnings from Grid Testing (Carry Forward)

Use this as a checklist for all future modules (Pathfinder, Vehicle, TrafficLight, etc.).

### 1. Read the docstring as the contract

If the API promises a specific **iteration order** (e.g., `get_edge_cells`: "Returns cells in order: top row → bottom row → left column → right column"), assert **exact list order**, not only set equality.

**Why this matters:** A real bug slipped through when top/bottom cells were interleaved per column instead of being grouped by row. Tests that only checked set membership didn't catch it. Tests aligned to the docstring did.

```python
# If docstring promises order:
result = grid.get_edge_cells()
assert result == expected  # Exact list comparison

# If docstring doesn't promise order:
assert {(c.x, c.y) for c in result} == set(expected_coords)  # Set comparison
```

### 2. Thin convenience wrappers need direct tests

Methods like `Grid.is_traversable(x, y)` and `Grid.is_occupied(x, y)` delegate to `get_cell()` + `Cell` methods. Even though the logic is trivial, the coverage tool can still show **uncovered lines** on those wrappers.

**Action:** After `make test-cov`, if wrappers show as uncovered, add small focused tests (or get developer confirmation to skip per the zero-miss policy).

```python
class TestGridStateWrappers:
    """Thin wrappers around Cell methods — ensure coverage."""
    
    def test_is_traversable_delegates_to_cell(self, grid_5x4):
        # Road cell (traversable)
        assert grid_5x4.is_traversable(0, 0) is True
        
        # Obstacle cell (not traversable)
        assert grid_5x4.is_traversable(1, 1) is False
        
        # Out of bounds
        assert grid_5x4.is_traversable(-1, 0) is False
```

### 3. Serialization / JSON: Test structure, not string fragments

Do not assert `'"width": 5' in json.dumps(...)` — encoding can vary (whitespace, key order). Prefer **round-trip structure validation**.

```python
# Test JSON serializability
snapshot = grid.snapshot()
encoded = json.dumps(snapshot)
decoded = json.loads(encoded)
assert decoded == snapshot

# Test structure
assert "width" in snapshot
assert snapshot["width"] == 5
assert "cells" in snapshot
assert isinstance(snapshot["cells"], list)
```

### 4. `Cell.to_dict()` / component IDs

Cover these cases:
- Fixed keys (`x`, `y`, `type`, `vehicle_id`, `traffic_light_id`)
- `type` field contains enum **value** string (e.g., `"road"`, not `CellType.ROAD`)
- `vehicle_id` / `traffic_light_id` extract via `.id` attribute
  - If component has string ID → pass through
  - If component has non-string ID → coerce with `str()`
  - If component is `None` → field is `None`

### 5. Non-mutation verification

For read-only APIs like `snapshot()`, capture grid state before/after and assert no change to cell references (vehicles, traffic lights).

```python
vehicles_before = [cell.vehicle for row in grid.cells for cell in row]
snapshot = grid.snapshot()
vehicles_after = [cell.vehicle for row in grid.cells for cell in row]
assert vehicles_after == vehicles_before  # No mutation
```

### 6. Bug protocol worked

On test failure:
1. **Stop** — don't modify implementation yourself
2. **Report** — describe expected vs actual, which test failed
3. **Wait** — let developer fix, then re-run: `make lint` → focused pytest → `make test` → `make test-cov`

This workflow caught multiple bugs during Grid implementation (e.g., edge cell ordering bug, snapshot mutation bug).

---

## Learnings from Pathfinder Testing (Carry Forward)

### 7. Delete skeleton stubs immediately

If the test file already contains pre-generated `pass` stubs (e.g., empty `TestPathNode` or `TestPathfinder` classes), **delete them** when writing real tests.

**Why:** They pass silently, assert nothing, and will never be filled in. Keeping stubs is misleading noise. Create properly-named test classes per task instead.

### 8. `make lint` only runs ruff — pre-commit also runs mypy

Always run **both** before declaring a task done:
```bash
make lint               # Catches style, import issues (ruff)
uv run pre-commit run --all-files  # Catches type errors (mypy)
```

**Why:** `make lint` doesn't include mypy. Type errors like passing wrong types to dunder methods will slip through without pre-commit.

### 9. Intentional type violations need `# type: ignore[operator]`

When a test deliberately passes the wrong type to exercise a defensive guard (e.g., calling `PathNode.__lt__(node, 42)` to check for `NotImplemented`), suppress mypy on that specific line with `# type: ignore[operator]`.

Use the **narrowest possible** ignore category (e.g., `[operator]`, not just `# type: ignore`).

```python
def test_lt_returns_not_implemented_for_non_pathnode():
    node = PathNode(...)
    result = PathNode.__lt__(node, 42)  # type: ignore[operator]
    assert result is NotImplemented
```

### 10. `NotImplemented` vs `TypeError` — Test both sides

For comparison dunders (`__lt__`, `__eq__`, etc.):
- Call the method **directly** (`PathNode.__lt__(node, wrong)`) → assert `NotImplemented` return
- Use the **operator** (`node < wrong`) → assert `TypeError` raised

They exercise different code paths.

```python
def test_lt_comparison_behavior():
    node = PathNode(...)
    
    # Direct call returns NotImplemented
    result = PathNode.__lt__(node, "wrong")  # type: ignore[operator]
    assert result is NotImplemented
    
    # Operator raises TypeError
    with pytest.raises(TypeError):
        node < "wrong"  # type: ignore[operator]
```

### 11. Grid cells are mutable — Use this for test topologies

`Cell` is a dataclass with mutable fields. Set `grid.cells[y][x].type = CellType.OBSTACLE` directly in a test to isolate regions without needing special constructors.

```python
# Create a "no path" scenario by blocking neighbors
grid = Grid(width=7, height=7)
grid.cells[0][1].type = CellType.OBSTACLE  # Block right
grid.cells[1][0].type = CellType.OBSTACLE  # Block down

path = pathfinder.find_path((0, 0), (2, 2), grid, None)
assert path is None  # No traversable path exists
```

### 12. Algorithmic guard coverage may need specific grid size/config

An internal guard (e.g., A* stale-heap-entry check) may not fire on a 7×7 grid but **will** fire on a 10×10 grid with the right cost configuration.

**Action:** When a line stays uncovered despite complex tests, **escalate to the developer** for a concrete triggering scenario rather than assuming the line is unreachable. Grid size and cost landscape both matter.

### 13. Defensive unreachable lines — Report and wait, never skip silently

When coverage reveals a line that appears unreachable by design (e.g., a closed-set guard that the algorithm's invariants prevent from firing), **report** the exact line number and your analysis.

**Wait for developer confirmation** — they decide whether to add `# pragma: no cover` in the implementation or adjust the coverage target. Never self-approve skipping a miss.

**Example report:**
> "Line 138 in pathfinder.py (closed-set guard: `if neighbor in closed_set`) is uncovered. This appears to be a defensive check that current A* invariants prevent from firing because we always check closed_set before adding to the open heap. Requesting developer confirmation."

---

## Bug Handling Protocol

If a test reveals an implementation bug:

1. **STOP** — Do not change any implementation file (`grid.py`, `pathfinder.py`, `vehicle.py`, etc.) yourself
2. **REPORT** — Explain clearly:
   - What was **expected** (per docstring/architecture)
   - What **actually happened** (observed behavior)
   - Which **test case** exposed it (test method name)
   - The **minimal reproduction** (input values, grid state)
3. **WAIT** — Let the developer confirm and fix before proceeding

**Example report:**
> "Bug found in `Grid.get_edge_cells()`:
> - Expected: Cells returned in order (top → bottom → left → right) per docstring
> - Actual: Top and bottom rows interleaved per column
> - Test: `test_get_edge_cells_returns_cells_in_documented_order`
> - Grid: 5x4, all edge cells are roads
> - Waiting for developer fix before continuing."

---

## Quality Gate (After Every Task)

Run these commands in order. All must pass before moving to the next task.

```bash
# Step 1: Check code style and imports
make lint

# Step 2: Run focused tests for your new test class
uv run pytest backend/tests/test_<module>.py -k <TestClassName> -v

# Step 3: Ensure full suite still passes (no regressions)
make test

# Step 4: Verify coverage on the target module
make test-cov

# Step 5: Check type correctness (includes mypy)
uv run pre-commit run --all-files
```

**If any step fails:**
- Fix test code (if the issue is in your tests)
- Report bug (if the issue is in implementation)
- Do NOT proceed until all gates pass

---

## Per-Task Checklist

When the developer says "**P1-XXX-NN is done**", follow this checklist:

- [ ] **Verify completion:** Open @docs/tasks.md → confirm task is marked ✅
- [ ] **Read implementation:** Open @backend/simulation/<module>.py → understand what was implemented
- [ ] **Read existing tests:** Open @backend/tests/test_<module>.py → see patterns, fixtures, naming
- [ ] **Identify test class name:** Follow convention `Test<ClassName><MethodName>` (e.g., `TestVehicleMove`)
- [ ] **Write tests:** Follow AAA pattern, parametrize, cover boundaries, check docstring contract
- [ ] **Run quality gates:**
  - [ ] `make lint` (must pass)
  - [ ] `uv run pytest backend/tests/test_<module>.py -k <TestClassName> -v` (focused pass)
  - [ ] `make test` (full suite must stay green)
  - [ ] `make test-cov` (check for uncovered lines in target module)
  - [ ] `uv run pre-commit run --all-files` (mypy type checking)
- [ ] **Coverage check:** If any lines uncovered in target module → report to developer, wait for confirmation
- [ ] **Report completion:** "P1-XXX-NN tests complete. Coverage: X%. All quality gates pass."

---

## Workflow

### Standard workflow for each task:

1. **Developer says:** "Implementation done for **P1-AREA-NN**" (e.g., `P1-VEH-03`)

2. **Open @docs/tasks.md:** Confirm task scope, which **source file** and **test file** apply

3. **Read implementation:** Open the relevant module (e.g., `pathfinder.py`, `vehicle.py`) and understand what was implemented

4. **Read test file:** Open the matching test file to see existing classes, fixtures, and patterns

5. **Write new test class:** Add a **new test class** for that specific task
   - Don't edit older tests (except for review fixes or agreed follow-ups like coverage supplementation)
   - Name class clearly: `TestVehicleGetNextPosition`, `TestPathfinderFindPath`
   - Follow established patterns from existing test classes

6. **Run quality gates:** Execute all checks in order (see Quality Gate section above)

7. **Report results:**
   - **Pass:** "P1-AREA-NN tests complete. Coverage: X%. All quality gates pass."
   - **Fail:** Report which gate failed and why (lint errors, test failures, coverage gaps, type errors)
   - **Coverage gaps:** Report uncovered lines and wait for confirmation

8. **Wait for review:** Developer reviews your tests before you proceed to the next task

---

## Troubleshooting

### Test fails with "ModuleNotFoundError"
**Cause:** Import path issue or running from wrong directory  
**Fix:** Always run from project root: `cd /path/to/urban-flow && uv run pytest backend/tests/test_<module>.py`

### Test fails with "AttributeError: Mock object has no attribute X"
**Cause:** Mock not configured for that attribute  
**Fix:** Add the attribute before using it:
```python
mock_vehicle = Mock()
mock_vehicle.id = "v001"  # Configure before using
mock_vehicle.position = (1, 0)
```

Or use `spec=` for automatic attribute checking:
```python
mock_vehicle = Mock(spec=Vehicle)
```

### Coverage shows miss on wrapper method (e.g., Grid.is_traversable)
**Cause:** Tests call `Cell.is_traversable()` directly, bypassing the Grid wrapper  
**Fix:** Add dedicated test for the Grid-level wrapper:
```python
def test_is_traversable_delegates_to_cell(self, grid_5x4):
    assert grid_5x4.is_traversable(0, 0) is True  # Road
    assert grid_5x4.is_traversable(1, 1) is False  # Obstacle
```

### `make test-cov` shows "No data to report"
**Cause:** Coverage plugin not installed or `.coveragerc` missing  
**Fix:** Run `uv sync` to reinstall dependencies, verify `.coveragerc` exists in project root

### `make lint` passes but pre-commit fails with mypy errors
**Cause:** `make lint` only runs ruff (style), not mypy (types)  
**Fix:** Always run both:
```bash
make lint  # Style check
uv run pre-commit run --all-files  # Type check
```

### Test fails with "fixture 'grid_5x4' not found"
**Cause:** Fixture defined in wrong scope or not imported  
**Fix:** Ensure fixture is:
- Defined at module level (before any test classes)
- Uses `@pytest.fixture` decorator
- In the same file or in `conftest.py`

### Parametrize test shows "indirect" error
**Cause:** Trying to parametrize a fixture value  
**Fix:** Either:
- Parametrize the test method directly (not the fixture)
- Use `indirect=True` if you need to parametrize fixture creation

---

## Quick Reference Card

**Your mission:** Write comprehensive tests for completed implementation tasks

**Current task:** **`@docs/tasks.md`** — pick a ✅ task that still needs test coverage (verify with tests + coverage, not this handoff)

**Test files:** See [Test layout](#test-layout-reference-only) above; default for Vehicle work is often `backend/tests/test_vehicle.py`

**Quality gates:** `make lint` → focused pytest → `make test` → `make test-cov` → pre-commit

**Coverage target:** 100% statement coverage, zero uncovered lines

**Report format:** "P1-XXX-NN tests complete. Coverage: X%. All gates pass."

**When stuck:** Report issue + analysis, wait for developer guidance

---

**Version History:**
- v1.0 (2026-03-05): Initial version
- v1.1 (2026-03-11): Added Pathfinder learnings
- v1.2 (2026-03-20): Added Vehicle testing status
- v1.3 (2026-04-01): Added TL;DR, Common Mistakes, Troubleshooting, Per-Task Checklist
- v1.4 (2026-04-05): Removed duplicated task/status tables; **`docs/tasks.md`** is the single source of truth for ⬜/✅