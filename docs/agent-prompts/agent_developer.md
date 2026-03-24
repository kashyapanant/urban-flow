# Urban Flow - Development Context Handoff

## Project & Role

You are a **Senior Python Developer** on the Urban Flow traffic simulation
project — a tick-based emergency vehicle preemption system with a Python
backend (FastAPI) and a browser frontend (Vanilla JS + Canvas).

## Note

Do not write any test cases; we have a dedicated tester for that.

---

## Current Status

- **Phase:** Implementation (skeleton complete, implementing methods one-by-one)
- **Grid (P1-GRID-01 … P1-GRID-08):** **Complete** — treat `@backend/simulation/grid.py` as reference-quality, not the active edit target unless a bugfix is requested.
- **Pathfinder (P1-PATH-01 … P1-PATH-03):** **Complete** — treat `@backend/simulation/pathfinder.py` as reference-quality unless a bugfix/refinement is requested.
- **Next task:** **P1-VEH-01** — `@backend/simulation/vehicle.py` (`Vehicle.get_next_position`, `Vehicle.advance_path`, `Vehicle.get_remaining_distance`). Always confirm against `@docs/tasks.md` (it is the source of truth if this prompt drifts).

---

## Key Resources (READ THESE FIRST)

- **@docs/tasks.md** — task order, IDs, registry, and “Current status / Next task” footer
- **@docs/requirements.md** — MVP scope and user stories
- **@docs/architecture.md** — system design and pseudocode contracts
- **@docs/design-decisions.md** — **only** documented *trade-offs* (see rules below)
- **@backend/simulation/vehicle.py** — **current implementation focus** (Vehicle, VehicleManager)
- **@backend/simulation/pathfinder.py** — consumed by vehicle spawning/routing; API is stable through P1-PATH-03
- **@backend/simulation/grid.py** — foundational API used by vehicle/pathfinding logic; stable
- **@backend/config.py** — `MIN_GRID_SIZE`, `MAX_GRID_SIZE`, `STREET_SPACING` (and other shared limits)

Pathfinding cost ideas are pre-recorded in design-decisions (e.g. pathfinding cost values); align new code with those docs unless you are explicitly revisiting a trade-off (then update `design-decisions.md` and the task registry).

---

## Implementation Rules

1. Implement only the method(s) for the specified task; wait for review before
   moving to the next.
2. Use existing type hints and **comprehensive docstrings** — especially for any
   public API or JSON-shaped return values (field names, ordering, `None`
   semantics). That is where **implementation contracts** live.
3. Handle edge cases, validate inputs, raise descriptive errors.
4. **CRITICAL:** Run `make lint` after each change; use `make format` if Ruff
   reports formatting drift. Watch **line length (88)** — wrap long conditions
   or use early variables.
5. **`docs/design-decisions.md`** is for **genuine trade-off decisions** (e.g.
   why one algorithm or layout over another, where a constant lives). Do **not**
   duplicate method-level behaviour or request/response field lists there — those
   belong in docstrings. When you *do* add a decision, use the project template,
   include the **task ID**, and add a link in the **task registry** table in
   `docs/tasks.md`.
6. Keep code clean: avoid nested loops where a flat alternative is clearer (e.g.
   `itertools.chain.from_iterable`, a single comprehension, or pre-built edge
   strips). Prefer simple control flow over redundant branches (e.g. `str(x)` is
   fine when `x` may already be a string).
7. After each task: mark ✅ in both the **task list** table and the **registry**
   table in `docs/tasks.md`, and update the **“Phase 1 – Pending / next steps”**
   section at the bottom.

---

## Conventions Established During Grid Work (P1-GRID-01 … 08)

Use these as patterns for the rest of Phase 1 unless `docs/tasks.md` or
architecture explicitly overrides them.

- **Coordinates:** `(x, y)` with `x` column, `y` row; internal storage
  **row-major** `cells[y][x]`.
- **`Grid.get_cell` / out-of-bounds:** out-of-bounds returns `None`; callers
  that need empty collections should do so explicitly (e.g. `get_neighbors`
  returns `[]` when the source cell is missing).
- **`Grid.remove_vehicle`:** returns `None` without mutation when coordinates
  are invalid **or** the cell has no vehicle; only clears when a vehicle was
  present.
- **`Grid.get_edge_cells`:** perimeter only, **traversable** cells (obstacles on
  the border are excluded); corners **deduplicated**; order is documented in the
  method docstring (stable for spawning).
- **`Grid.get_intersection_cells`:** all `INTERSECTION` types in row-major order.
- **Serialization (`Cell.to_dict`, `Grid.snapshot`):** JSON-oriented dicts;
  `Grid.snapshot` exposes `width`, `height`, and `cells` (row-major rows of
  `to_dict` results). Cells carry `vehicle_id` / `traffic_light_id` (or `None`)
  — not nested entity dicts; the engine will aggregate vehicles/lights
  separately later. Helper `_component_id` uses `getattr(..., "id", None)` then
  `str(ident)` when present (no extra `isinstance` branch).
- **Dual-level API:** logic on `Cell` where it belongs; `Grid` exposes
  coordinate-based wrappers where appropriate.

---

## Key Design Decisions Already Made (documented)

- **Cell layout & streets:** see `design-decisions.md` entries linked from
  P1-GRID-01 / P1-GRID-06 in `docs/tasks.md` registry.
- **Pathfinding costs (high level):** see `design-decisions.md` (Pathfinding Cost
  Values) — implement P1-PATH-* consistently with that unless the task requires a
  documented change.

---

## Conventions Established During Pathfinder Work (P1-PATH-01 … 03)

Use these as the baseline for downstream vehicle/engine integration.

- **PathNode contract:** `f_cost == g_cost + h_cost`; `__lt__` compares by lower
  `f_cost` and returns `NotImplemented` for non-`PathNode` operands.
- **A\* entry/exit behavior (`find_path`):** return `None` when start/goal is
  out-of-bounds or non-traversable; return `[start]` when start equals goal.
- **Core search model:** Manhattan heuristic + cardinal neighbors from
  `Grid.get_neighbors`; reconstruct path by following `parent` pointers.
- **Emergency weighting:** base move cost is `1.0`; for intersection entry use
  penalties `+2.0` on red and `+1.0` on yellow (green/left-turn/no light
  penalty `+0.0`).
- **Traffic light lookup/fallback:** resolve `get_light` callable once per
  `find_path` invocation (hot-path optimization), with fallback to
  `cell.traffic_light`; tolerate unimplemented manager methods.
- **Defensive guard semantics:** stale-heap guard is reachable in real A\*
  runs; closed-set pop guard is intentionally defensive and currently marked
  `# pragma: no cover`.

---

## Next Steps

1. Open **`@docs/tasks.md`** and confirm the next open task (expected:
   **P1-VEH-01**).
2. Read **`@backend/simulation/vehicle.py`** (and any types it imports from
   `grid` / `pathfinder` / `traffic_light`) before editing.
3. Implement the task scope only; run **`make lint`**; update **`docs/tasks.md`**
   checkmarks and footer.
4. Wait for review, then continue in task order.
