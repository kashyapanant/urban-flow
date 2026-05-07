# Urban Flow - Tester Handoff

**Last Updated:** 2026-04-16  
**Version:** 2.0

This file is intentionally short. It should help the next testing agent start quickly without carrying a long duplicated handbook.

## Single Source Of Truth

- **What is implemented:** `@docs/tasks.md`
- **Product behavior:** `@docs/requirements.md`
- **System contracts:** `@docs/architecture.md`
- **Known trade-offs:** `@docs/design-decisions.md`

Do **not** duplicate task status in this file. Read `tasks.md` first.

## Your Role

- Write tests for a **completed review-sized task**
- Work on **one task at a time**
- Do **not** edit implementation code
- If you find an implementation bug, stop and report it clearly

If a human assigns a specific task ID, test that task instead of auto-picking the first eligible one.

## How To Pick The Next Task

1. Open `@docs/tasks.md`
2. Use the **Phase 1 Review-Sized Task Queue**
3. Pick the first `✅` task that still needs coverage, unless the human assigned a task
4. Ignore `⬜` tasks

Use the queue and legacy mapping in `tasks.md` instead of older micro-task references.

## Read Before Testing

1. `@docs/tasks.md`
2. `@docs/requirements.md`
3. `@docs/architecture.md`
4. Relevant sections of `@docs/design-decisions.md`
5. The implementation file under test
6. The existing test file for that area, if present
7. `@Makefile`

## Phase 1 Invariants

- Phase 1 is a **deterministic**, **single-lane**, **grid-based** MVP
- Coordinates are `(x, y)` and grid storage is row-major: `cells[y][x]`
- Emergency vehicles use a **fixed precomputed path** in Phase 1
- Tick order is:
  1. preemption scan
  2. traffic light update
  3. vehicle movement
  4. spawning
  5. cleanup and metrics
  6. broadcast
- Intersection entry depends on both axis and phase, not phase alone

## Testing Rules

- Test the **whole completed task slice**, not random future behavior
- Prefer boundary cases, non-mutation checks, serialization checks, and contract-level assertions
- Use parametrization when it makes tests shorter and clearer
- If order is not part of the contract, do not assert order
- If uncovered lines remain after testing, report the exact misses instead of hand-waving them away
- Use **AAA pattern** 

## Bug Protocol

If a test reveals a bug:

1. stop
2. report expected vs actual behavior
3. name the failing test or reproduction
4. wait for an implementation fix before continuing

## Verification

Run these after adding or updating tests:

```bash
make lint
uv run pytest <focused test selection>
make test
make test-cov
```

Target the implementation file for the assigned task. Aim for zero unexplained coverage misses on the touched module.

## Handoff Format

Keep handoff short. Use 4-6 bullets max:

- task ID tested
- tests added or updated
- commands run
- coverage result or uncovered lines
- any bugs or blockers for the next agent

Do **not** restate the whole project or copy long status tables into the handoff.
