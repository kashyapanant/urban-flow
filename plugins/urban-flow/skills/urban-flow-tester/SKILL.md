---
name: urban-flow-tester
description: Use when adding or updating tests for Urban Flow. Follow the Phase 1 tester workflow: read docs/tasks.md first, test one completed review-sized task at a time, do not edit implementation code, report bugs instead of patching them, and run the required validation and coverage checks.
---

# Urban Flow Tester

Use this skill for test-writing and test-review work in the Urban Flow repository.

## Start Here

Read these files in order before testing:

1. `docs/tasks.md`
2. `docs/requirements.md`
3. `docs/architecture.md`
4. Relevant parts of `docs/design-decisions.md`
5. The implementation file under test
6. The existing test file for that area, if present
7. `Makefile`

`docs/tasks.md` is the source of truth for implemented status. Do not duplicate task state in the skill.

## Role

- Write tests for a completed review-sized task
- Work on one task at a time
- Do not edit implementation code
- If you find an implementation bug, stop and report it clearly

If the human gives a specific task ID, test that task instead of auto-picking the next eligible one.

## Picking Work

1. Open `docs/tasks.md`
2. Use the Phase 1 review-sized task queue
3. Pick the first completed task that still needs coverage, unless the human assigned a task
4. Ignore unchecked tasks

Use the queue and legacy mapping in `docs/tasks.md` instead of older micro-task references.

## Phase 1 Invariants

- Phase 1 is deterministic, single-lane, and grid-based
- Coordinates are `(x, y)` and grid storage is row-major: `cells[y][x]`
- Emergency vehicles use a fixed precomputed path in Phase 1
- Tick order is:
  1. preemption scan
  2. traffic light update
  3. vehicle movement
  4. spawning
  5. cleanup and metrics
  6. broadcast
- Intersection entry depends on both axis and phase, not phase alone

## Testing Rules

- Test the whole completed task slice, not future behavior
- Prefer boundary cases, non-mutation checks, serialization checks, and contract-level assertions
- Use parametrization when it makes tests shorter and clearer
- If order is not part of the contract, do not assert order
- If uncovered lines remain after testing, report the exact misses
- Use the AAA pattern

## Bug Protocol

If a test reveals a bug:

1. stop
2. report expected versus actual behavior
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

Aim for zero unexplained coverage misses on the touched module.

## Handoff

Keep handoff short. Include:

- task ID tested
- tests added or updated
- commands run
- coverage result or uncovered lines
- bugs or blockers for the next agent
