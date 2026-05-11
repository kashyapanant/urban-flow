# Phase 1 Code Review

## Scope Reviewed

Completed Phase 1 surface as of now:

- `backend/simulation/grid.py`
- `backend/simulation/pathfinder.py`
- `backend/simulation/vehicle.py`
- `backend/simulation/traffic_light.py` (`TrafficLight` only)
- `backend/api/routes.py` (`ConfigUpdateRequest` only)
- related tests in `backend/tests/`

Evidence used:

- direct code review
- requirements and architecture docs
- current test suite run: `uv run pytest backend/tests -q`
- placeholder engine test run: `uv run pytest backend/tests/test_engine.py -q`

## Findings

### High

#### 1. Placeholder engine tests pass without testing anything

`backend/tests/test_engine.py` currently contains 8 test methods whose bodies are just `pass`. They all pass in CI, which creates false confidence around the engine even though `backend/simulation/engine.py` is still a stub.

Why this matters:

- the suite reports green for engine behavior that does not exist
- future contributors may assume engine behavior is already locked down
- review signal gets diluted because these tests look real but verify nothing

Recommendation:

- delete the placeholder tests, or
- mark them `@pytest.mark.skip(reason="engine not implemented")`, or
- replace them only when `P1-ENG-01` starts

Affected paths:

- `backend/tests/test_engine.py`
- `backend/simulation/engine.py`

#### 2. Route planning ignores occupied cells, but the requirements say it should not

`Pathfinder.find_path()` plans through any traversable road/intersection cell. Occupancy is enforced later during movement, not during planning. That is internally consistent, but `docs/requirements.md` currently says vehicles should navigate "without passing through obstacles or occupied cells".

Current behavior:

- `Cell.is_traversable()` ignores occupancy
- `Grid.get_neighbors()` uses traversability only
- `Pathfinder.find_path()` expands neighbors without treating occupied cells as blocked
- `VehicleManager.move_vehicles()` handles blockage by waiting at runtime

Why this matters:

- code and requirement wording are currently out of sync
- a reviewer reading only the requirements could conclude the planner is wrong
- future tests could accidentally encode the wrong rule

Recommendation:

Choose one rule and make code + docs match:

1. **Preferred for Phase 1:** clarify that pathfinding uses static traversability and occupancy is enforced during movement.
2. If you want stricter planning semantics, make the planner occupancy-aware and define whether the goal cell is exempt.

Affected paths:

- `backend/simulation/grid.py`
- `backend/simulation/pathfinder.py`
- `backend/simulation/vehicle.py`
- `docs/requirements.md`

### Medium

#### 3. `TrafficLight.request_preemption()` accepts non-emergency vehicles

The `TrafficLight` API will currently grant preemption to any `Vehicle` object if the caller asks for it. The method docstring describes an emergency vehicle, and the product behavior is clearly emergency-only, but enforcement is not in the completed code yet.

This is already partially acknowledged in `docs/tasks.md` as `DESIGN-WATCH-TL-01`, so this is a known issue, not a surprise.

Why this matters:

- the completed `TrafficLight` core is callable in a way the product should reject
- future engine wiring could accidentally rely on caller discipline and forget the guard

Recommendation:

Pick one enforcement point during `P1-ENG-01` and test it explicitly:

- reject inside `TrafficLight.request_preemption()`, or
- enforce in the engine before calling the light

Affected paths:

- `backend/simulation/traffic_light.py`
- `docs/tasks.md`

#### 4. `VehicleManager.move_vehicles()` docstring does not match actual tick accounting

The `move_vehicles()` docstring says `ticks_elapsed` increments for every non-arrived vehicle regardless of whether it moved or waited. The actual code has one exception: if a vehicle is already at destination (`next_pos is None`), the manager removes it from the grid, marks it arrived, and does **not** increment `ticks_elapsed`.

Tests currently match the implementation, not the docstring.

Why this matters:

- the implementation is reasonable
- the docstring is misleading for anyone wiring metrics later

Recommendation:

Fix the docstring to describe the real behavior:

- destination-cleanup path does not increment
- all other active vehicles increment once per tick

Affected paths:

- `backend/simulation/vehicle.py`

#### 5. Architecture text and emergency path cost logic do not quite match

The architecture doc describes emergency pathfinding as penalizing unfavorable current light state, with an example of `+2 for red/yellow in the vehicle's travel axis`. The implementation currently applies:

- `+2` for `red`
- `+1` for `yellow`
- `+0` otherwise

This is not necessarily a code bug, but it is documentation drift.

Why this matters:

- tests currently lock in the implemented behavior
- future routing changes could be argued from the doc and create unnecessary churn

Recommendation:

Align one side:

- update `docs/architecture.md` to match the implemented cost model, or
- change the code and tests if the doc is meant to be authoritative

Affected paths:

- `backend/simulation/pathfinder.py`
- `docs/architecture.md`
- `backend/tests/test_pathfinder.py`

### Low

#### 6. `TrafficLight` degenerate `phase_duration=0` behavior exists in tests but not in public config

`TrafficLight.tick()` currently allows `phase_duration=0`, and tests explicitly cover that degenerate case. But public configuration validation only allows `phase_duration >= 1`.

Why this matters:

- it is test-only behavior, not publicly reachable through current config
- it adds cognitive load when reading the tests
- preemption validation (`1 <= yellow_duration <= phase_duration`) is unusable when duration is `0`

Recommendation:

Pick one:

- keep it as defensive internal behavior but document it as non-public, or
- remove the `phase_duration=0` test case and treat `phase_duration < 1` as invalid everywhere

Affected paths:

- `backend/simulation/traffic_light.py`
- `backend/tests/test_traffic_light.py`
- `backend/config.py`
- `backend/api/routes.py`

## Missing Or High-Value Tests

These are the best next tests to add once the relevant slices are being worked on:

1. Replace `backend/tests/test_engine.py` placeholders with real tests only when `P1-ENG-01` starts.
2. Add one explicit policy test around occupancy:
   - either planning should avoid occupied cells, or
   - planning may ignore occupancy and movement enforces waiting
3. Add an explicit test for emergency-only preemption once the enforcement point is chosen.
4. Add an integration-style test around movement + a minimal real light-permission bridge once `P1-TL-02` exists.

## Things That Look Good

- `Grid` is clean, stable, and well-covered.
- `Pathfinder` core A* flow is solid for the current grid-based MVP.
- `Vehicle` path state validation is strict and catches corruption early.
- `ConfigUpdateRequest` validation is focused and well-tested.
- `TrafficLight` preemption behavior is more carefully tested than most of the rest of the Phase 1 surface.

## Suggested Fix Order

1. Remove or skip placeholder engine tests.
2. Resolve the occupied-cell rule mismatch between code and requirements.
3. Lock down emergency-only preemption when `P1-ENG-01` is implemented.
4. Clean up smaller doc/code drift such as tick accounting wording and yellow-light penalty wording.

---

## Low-Token Agent Handoff Guidance

The biggest token waste usually comes from repeating project history and task status in every prompt. The fix is not "make the file shorter" by itself; it is to make the handoff file point to the right source of truth and only keep the invariants that the next agent truly needs.

### Keep In The Handoff File

Only keep these sections:

1. **Single source of truth**
   - usually `docs/tasks.md`
2. **Role**
   - developer or tester
3. **How to pick next task**
   - 3-4 lines max
4. **Read before work**
   - `tasks.md`, `requirements.md`, `architecture.md`, target file
5. **Phase invariants**
   - only the rules that would cause wrong code if forgotten
6. **Verification**
   - the few commands that must run
7. **Handoff format**
   - 4-6 bullets max
8. **Stop conditions**
   - when to stop instead of expanding scope

### Remove From The Handoff File

Avoid carrying these inside the handoff doc:

- completed-task tables
- long examples
- old changelog/history
- repeated explanations of the whole project
- giant style guides
- method-by-method advice copied from prior tasks
- detailed learnings that already live in `design-decisions.md`

### Practical Rules To Save Tokens

- Keep the handoff file under roughly **80-140 lines**.
- Store status only in `docs/tasks.md`.
- Store design rationale only in `docs/design-decisions.md`.
- Store behavior contracts only in `docs/architecture.md` and code docstrings.
- Use the handoff file only as a **router**, not as an encyclopedia.

### Recommended Developer Handoff Shape

```md
# <Project> - Developer Handoff

Single source of truth: @docs/tasks.md

Role:
- implement the current review-sized task
- do not write tests unless asked

Next task:
1. open @docs/tasks.md
2. pick the first unchecked task
3. read dependencies and watch notes

Read first:
- @docs/tasks.md
- @docs/requirements.md
- @docs/architecture.md
- target file

Phase invariants:
- <3-6 bullets max>

Verification:
- make lint
- <focused test command if relevant>

Handoff back:
- task completed
- files changed
- commands run
- blockers/risks

Stop if:
- scope exceeds the queue row
- docs and code materially disagree
- a completed module needs redesign
```

### Recommended Tester Handoff Shape

```md
# <Project> - Tester Handoff

Single source of truth: @docs/tasks.md

Role:
- test one completed review-sized task
- do not edit implementation

Next task:
1. open @docs/tasks.md
2. pick the first completed task that still needs coverage

Read first:
- @docs/tasks.md
- @docs/requirements.md
- @docs/architecture.md
- target implementation file
- existing test file

Phase invariants:
- <3-6 bullets max>

Verification:
- make lint
- uv run pytest <focused selection>
- make test
- make test-cov

Handoff back:
- task tested
- tests added
- commands run
- coverage result
- bugs/blockers
```

### Best Mental Model

Think of the handoff file as:

- a **launch checklist**

not:

- a compressed copy of the entire repo

If the next agent needs more than that, the missing information probably belongs in `tasks.md`, `architecture.md`, `design-decisions.md`, or the code itself.
