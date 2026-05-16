---
name: urban-flow-developer
description: Use when working on Urban Flow implementation tasks. Follow the Phase 1 developer workflow: read docs/tasks.md first, implement one review-sized task at a time, keep scope tight, respect deterministic simulation invariants, run the required validation, and update task status when done.
---

# Urban Flow Developer

Use this skill for implementation work in the Urban Flow repository.

## Start Here

Read these files in order before coding:

1. `docs/tasks.md`
2. `docs/requirements.md`
3. `docs/architecture.md`
4. Relevant parts of `docs/design-decisions.md`
5. The target implementation file
6. `Makefile`

`docs/tasks.md` is the source of truth for task status and next work. Do not duplicate task status in the skill.

## Role

- Implement the current review-sized task from `docs/tasks.md`
- Work on one task at a time
- Keep changes scoped to that task unless a tightly related fix is required
- Do not add speculative future work

If the human gives a specific task ID, that overrides the default next-task rule.

## Picking Work

1. Open `docs/tasks.md`
2. Use the Phase 1 review-sized task queue
3. Pick the first unchecked task unless the human assigned a specific task
4. Read the queue row, dependencies, and watch notes

Ignore stale micro-task references elsewhere. Use the review-sized queue and the legacy mapping in `docs/tasks.md`.

## Phase 1 Invariants

- Phase 1 is deterministic, single-lane, and grid-based
- Coordinates are `(x, y)` and grid storage is row-major: `cells[y][x]`
- Phase 1 emergency vehicles use a fixed precomputed path
- Tick order is:
  1. preemption scan
  2. traffic light update
  3. vehicle movement
  4. spawning
  5. cleanup and metrics
  6. broadcast
- A vehicle may enter an intersection only when the required axis matches the active axis and the phase permits entry

If the task appears to require changing one of these assumptions, stop and call it out explicitly.

## Working Rules

- Implement the whole task slice, not a partial method-level subset
- Avoid drive-by refactors in completed modules
- Keep public APIs typed and documented
- Prefer simple control flow and explicit validation
- If a bounded parameter is invalid, reject it clearly instead of silently clamping it unless the contract explicitly says otherwise

## Verification

Minimum after each implementation task:

```bash
make lint
```

Also run the most relevant focused tests for the touched area when they exist. If no meaningful focused tests exist yet, say so in handoff notes.

## Docs Updates

- Update `docs/tasks.md` when the task is done
- Add to `docs/design-decisions.md` only for a real design trade-off
- Do not dump long implementation notes into prompt or skill files

## Handoff

Keep handoff short. Include:

- task ID completed
- files changed
- commands run
- doc or design-decision updates
- blockers, follow-ups, or risks

## Stop Conditions

Stop and report instead of expanding scope when:

- the task is larger than the queue row implies
- a completed module needs a non-trivial redesign
- requirements, architecture, and code disagree in a material way
- you find a bug that should be reviewed separately from the assigned task
