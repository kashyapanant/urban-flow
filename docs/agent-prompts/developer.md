# Urban Flow - Development Context Handoff

## Project & Role
You are a Senior Python Developer on the Urban Flow traffic simulation
project — a tick-based emergency vehicle preemption system with a Python
backend (FastAPI) and a browser frontend (Vanilla JS + Canvas).

## Current Status
**Phase:** Implementation (skeleton complete, implementing methods one-by-one)
**Next Task:** Please pick from @docs/tasks.md

## Key Resources (READ THESE FIRST)
- **@docs/tasks.md** — complete task list, order, and progress tracking
- **@docs/requirements.md** — MVP scope and user stories
- **@docs/architecture.md** — full system design
- **@docs/design-decisions.md** — all implementation decisions (link new
  ones to task IDs)
- **@backend/simulation/grid.py** — the file currently being implemented
- **@backend/config.py** — MIN_GRID_SIZE, MAX_GRID_SIZE, STREET_SPACING
  constants (single source of truth for grid limits)

## Implementation Rules
1. Implement only the method(s) for the specified task, wait for review
   before moving to the next
2. Use existing type hints and add comprehensive docstrings
3. Handle edge cases, validate inputs, raise descriptive errors
4. **CRITICAL:** Run `make lint` after each implementation; use
   `make format` to fix formatting issues
5. Log implementation choices in docs/design-decisions.md with task ID:
   ```markdown
   ## Decision: [Title] (Task: taskid)
   **Date:** 2026-XX-XX
   **Context:** [What needed deciding]
   **Decision:** [What you chose]
   **Rationale:** [Why this choice]
   ```
6. After each task: mark ✅ in both the task list table AND the registry
   table in docs/tasks.md, and update the "Current status" / "Next task"
   lines at the bottom of the file



## Key Design Decisions Already Made
- **Cell layout:** row-major `cells[y][x]`; INTERSECTION if on both axes,
  ROAD if on one, OBSTACLE if neither
- **Street spacing:** fixed at 3 (`range(0, dim, STREET_SPACING)`),
  stored as `frozenset` in `avenue_cols` / `street_rows`
- **Dimension constants:** `MIN_GRID_SIZE=1`, `MAX_GRID_SIZE=100`,
  `STREET_SPACING=3` all in `backend/config.py`
- **Dual-level API:** `Cell` methods for callers with a cell object; `Grid`
  wrappers for coordinate-based callers — logic lives in `Cell` only

## Next Steps
1. Read `@backend/simulation/grid.py` fully before touching anything
2. Implement next task from docs/task.md
3. Run `make lint`, update docs/tasks.md, wait for review
4. Then proceed to next one
