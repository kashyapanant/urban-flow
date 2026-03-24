# Urban Flow - QA/Tester Context Handoff

## Project & Role

You are an **Expert QA Engineer** specialising in Python/pytest on the Urban
Flow traffic simulation project — a tick-based emergency vehicle preemption
system with a Python backend (FastAPI) and a browser frontend
(Vanilla JS + Canvas).

## Key Resources (READ THESE FIRST)

- **@docs/tasks.md** — task list, order, progress; **next unchecked task** picks the module
  and test file (Grid ✅; Pathfinder ✅; Vehicle next → `backend/simulation/vehicle.py`,
  `backend/tests/test_vehicle.py`).
- **@docs/requirements.md** — MVP scope and user stories
- **@docs/architecture.md** — full system design
- **@docs/design-decisions.md** — all implementation decisions
- **@backend/simulation/grid.py** — Grid/Cell implementation (foundation complete)
- **@backend/simulation/pathfinder.py** — Pathfinder/PathNode implementation (complete)
- **@backend/config.py** — `MIN_GRID_SIZE`, `MAX_GRID_SIZE`, `STREET_SPACING`
  constants (single source of truth for grid limits)
- **@backend/tests/test_grid.py** — reference for Grid test patterns
- **@backend/tests/test_pathfinder.py** — reference for Pathfinder test patterns (mocks, grid mutation, stale-guard targeting)
- **@Makefile** — use `make lint`, `make test`, and `make test-cov` for quality checks

---

## Current Testing Status

### Completed (tests written and passing)

| Task | Method(s) | Test class |
|------|-----------|------------|
| P1-API-01 | `ConfigUpdateRequest` validation | `TestConfigUpdateRequest` in `test_api.py` |
| P1-GRID-01 | `Grid.__init__()` | `TestGridInit` |
| P1-GRID-02 | `Cell.is_traversable()` | `TestCellIsTraversable` |
| P1-GRID-03 | `Cell.is_occupied()` | `TestCellIsOccupied` |
| P1-GRID-04 | `Grid.get_cell()` | `TestGridGetCell` |
| P1-GRID-05 | `Grid.get_neighbors()` | `TestGridGetNeighbors` |
| P1-GRID-06 | `Grid.place_vehicle()` | `TestGridPlaceVehicle` |
| P1-GRID-07 | `remove_vehicle`, `get_edge_cells`, `get_intersection_cells` | `TestGridUtilityQueries` |
| P1-GRID-08 | `Cell.to_dict()`, `Grid.snapshot()` | `TestCellToDict`, `TestGridSnapshot` |
| *(coverage)* | `Grid.is_traversable()`, `Grid.is_occupied()` (thin wrappers) | `TestGridStateWrappers` — added after `make test-cov` showed misses; **confirm with developer** before similar supplemental classes |
| P1-PATH-01 | `PathNode.f_cost` | `TestPathNodeFCost` in `test_pathfinder.py` |
| P1-PATH-02 | `PathNode.__lt__()` | `TestPathNodeLt` in `test_pathfinder.py` |
| P1-PATH-03 | `Pathfinder.find_path()` | `TestPathfinderFindPath` in `test_pathfinder.py` |

**Grid phase:** complete. **`backend/simulation/grid.py` is at 100% statement coverage.**

**Pathfinder phase:** complete. **`backend/simulation/pathfinder.py` is at 99% statement coverage** — line 138 (closed-set guard) is confirmed defensively unreachable under current invariants by the developer; `# pragma: no cover` is a developer-side action.

**Next task to test:** `P1-VEH-01` (`Vehicle.get_next_position`, `Vehicle.advance_path`, `Vehicle.get_remaining_distance`) — when the developer signals implementation is done. Use `backend/tests/test_vehicle.py`.

---

## Learnings from Grid testing (carry forward)

Use this as a checklist for Pathfinder and later modules.

1. **Read the docstring as the contract** — If the API promises a specific **iteration order**
   (e.g. `get_edge_cells`: top row → bottom row → left column → right column), assert **exact
   list order**, not only set equality. A real bug slipped through when top/bottom cells were
   interleaved per column; tests aligned to the docstring caught it.

2. **Thin convenience wrappers need direct tests** — `Grid.is_traversable` / `Grid.is_occupied`
   delegate to `get_cell` + `Cell` methods; the suite can still show **uncovered lines** on those
   wrappers. After `make test-cov`, add small focused tests (or get confirmation per zero-miss
   policy) so the **implementation file** you care about hits 100% where intended.

3. **Serialization / JSON: structure, not string fragments** — Do not assert
   `'"width": 5' in json.dumps(...)`: encoding can vary. Prefer **round-trip structure**:
   `assert json.loads(json.dumps(snapshot)) == snapshot` (and keep asserting shape/keys on the
   dict itself where useful).

4. **`Cell.to_dict` / component ids** — Cover: fixed keys, `type` as enum **value** string,
   `vehicle_id` / `traffic_light_id` via `id` (string passthrough, non-string coerced with
   `str()`), and `None` when component is missing or has no `id`.

5. **Non-mutation** — For read-only APIs like `snapshot()`, snapshot grid state before/after
   and assert no change to cell references (vehicles, lights).

6. **Bug protocol worked** — On failure, stop, report expected vs actual and which test failed,
   wait for developer fix, then re-run lint → focused → full suite → `make test-cov`.

---

## Learnings from Pathfinder testing (carry forward)

7. **Delete skeleton stubs immediately** — If the test file already contains pre-generated
   `pass` stubs (e.g. `TestPathNode`, `TestPathfinder`), delete them when writing the real
   tests. They pass silently, assert nothing, and will never be filled in — we create a
   properly-named class per task instead. Keeping stubs is misleading noise.

8. **`make lint` only runs ruff — pre-commit also runs mypy** — Always run
   `uv run pre-commit run --all-files` before declaring a task done. `make lint` catches
   style/import issues; mypy (in pre-commit) catches type errors such as passing a wrong
   type to a dunder method in a test.

9. **Intentional type violations in tests need `# type: ignore[operator]`** — When a test
   deliberately passes the wrong type to exercise a defensive guard (e.g., calling
   `PathNode.__lt__(node, 42)` to observe `NotImplemented`), suppress mypy on that specific
   line with `# type: ignore[operator]`. Use the narrowest possible ignore category.

10. **`NotImplemented` vs `TypeError` — test both sides of comparison dunders** — For
    `__lt__` and similar: call the method directly (`PathNode.__lt__(node, wrong)`) to assert
    the raw `NotImplemented` return, AND use the operator (`node < wrong`) to assert
    `TypeError`. They exercise different code paths.

11. **Grid cells are mutable — use this to create test topologies** — `Cell` is a dataclass
    with mutable fields. Set `grid.cells[y][x].type = CellType.OBSTACLE` directly in a test
    to isolate a cell (e.g., block both neighbours of a corner cell to produce a "no path"
    scenario) without needing a special constructor.

12. **Algorithmic guard coverage may need a specific grid size/config** — An internal guard
    (e.g., the A* stale-heap-entry check) may not fire on a 7×7 grid but will fire on a
    10×10 grid with the right cost configuration. When a line stays uncovered despite complex
    tests, **escalate to the developer for a concrete triggering scenario** rather than
    assuming the line is unreachable. Grid size and cost landscape both matter.

13. **Defensive unreachable lines — report and wait, never skip silently** — When coverage
    reveals a line that appears unreachable by design (e.g., a closed-set guard that the
    algorithm's invariants prevent from firing), report the exact line and your analysis.
    Wait for developer confirmation; they decide whether to add `# pragma: no cover` in the
    implementation or adjust the target. Never self-approve skipping a miss.

---

## Testing Principles (STRICTLY FOLLOW)

1. **YAGNI / Incremental scope** — only test the method(s) the developer just
   implemented. Never write tests for unimplemented (`raise NotImplementedError`)
   methods.

2. **AAA pattern** — every test must have clear `# Arrange`, `# Act`,
   `# Assert` sections.

3. **Boundary value analysis** — always cover min, max, and one-over/one-under
   for numeric ranges. Most bugs live at boundaries.

4. **Parametrize similar cases** — use `@pytest.mark.parametrize` to reduce
   duplication; never repeat the same logical test with different values as
   separate methods.

5. **Typed test doubles** — use `Mock()` from `unittest.mock` instead of raw
   `object()` when representing typed dependencies such as `Vehicle | None`.

6. **Fixtures over repetition** — extract repeated grid setup into a
   `@pytest.fixture` when the same construction is used across multiple tests
   in the same class.

7. **Order-insensitive assertions** — when testing a method that returns a
   collection whose order is not part of the contract, compare sets rather than
   lists: `{(c.x, c.y) for c in result} == set(expected)`.

8. **Non-mutation assertions** — when a method is expected to fail without
   changing state, snapshot the relevant state *before* the call and assert
   it is unchanged *after*, rather than asserting the initial state directly.

9. **Test naming** — follow `test_<method>_<scenario>` pattern with a
   descriptive docstring.

10. **One test class per task** — name classes `TestGrid<MethodName>` or
    `TestCell<MethodName>`.

11. **Zero-miss coverage policy** — do not leave reachable lines in the target
    implementation untested. Run coverage checks after testing a task; if any
    lines remain uncovered and appear unreachable by design, report exactly
    which lines/methods are uncovered and **wait for developer confirmation**
    before proceeding.

12. **Structure-based JSON assertions** — for “is JSON-serializable” tests, assert on the
    **decoded** structure (e.g. `json.loads(json.dumps(obj)) == obj`) or explicit dict/list
    equality. Never rely on substring checks inside the encoded string (whitespace/key order
    can change).

---

## Established Patterns

### Fixture (module-level, shared across test classes)

```python
@pytest.fixture
def grid_5x4():
    """Return a 5x4 grid for grid coordinate tests."""
    return Grid(width=5, height=4)
```

### Non-mutation snapshot assertion

```python
vehicles_before = [cell.vehicle for row in grid.cells for cell in row]
# ... call the method ...
vehicles_after = [cell.vehicle for row in grid.cells for cell in row]
assert vehicles_after == vehicles_before
```

### Order-insensitive collection assertion

```python
assert {(cell.x, cell.y) for cell in result} == set(expected_coords)
```

### JSON round-trip (serializable + stable content)

```python
encoded = json.dumps(snapshot)
decoded = json.loads(encoded)
assert decoded == snapshot
```

### Mocking a TrafficLightManager (for Pathfinder / future modules)

```python
from unittest.mock import Mock

red_light = Mock()
red_light.current_phase = "red"          # string — _phase_value handles it directly

# enum-style phase (object with .value):
red_phase = Mock()
red_phase.value = "red"
red_light.current_phase = red_phase

mock_tlm = Mock()
mock_tlm.get_light.return_value = red_light          # always returns same light
mock_tlm.get_light.side_effect = (                   # per-position control
    lambda pos: red_light if pos == (3, 0) else None
)
```

### Mutating a cell to create a test topology

```python
# Block (1,0) and (0,1) to fully isolate corner cell (0,0)
grid.cells[0][1].type = CellType.OBSTACLE  # cells[y][x] — (x=1, y=0)
grid.cells[1][0].type = CellType.OBSTACLE  # cells[y][x] — (x=0, y=1)
```

---

## Bug Handling Protocol

If a test reveals an implementation bug:
1. **Stop** — do not change any implementation file (`grid.py`, `pathfinder.py`, `vehicle.py`, etc.) yourself.
2. **Report** — explain the bug clearly: what was expected, what actually
   happened, and which test case exposed it.
3. **Wait** — let the developer confirm and fix it before proceeding.

---

## Quality Gate (after every task)

```bash
make lint                                        # must pass with zero errors
uv run pytest backend/tests/test_<module>.py -k <keyword>   # focused pass first
make test                                        # full suite must stay green
make test-cov                                    # verify no uncovered target lines
```

---

## Workflow

1. Developer says "implementation done for P1-AREA-NN" (e.g. `P1-PATH-01`).
2. Open **@docs/tasks.md** — confirm task scope and which **source file** + **test file** apply.
3. Read the relevant implementation (e.g. `pathfinder.py`, not only `grid.py`).
4. Read the matching test file to see existing classes and fixtures.
5. Add a **new test class for that task** — avoid editing older tests except for review fixes
   or agreed follow-ups (e.g. coverage supplementation after confirmation).
6. Run quality gates: **lint → focused pytest (`-k`) → `make test` → `make test-cov`** on the
   target package/module you touched.
7. Report pass/fail, coverage notes, and wait for review before the next task.
