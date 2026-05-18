---
name: urban-flow-executor
description: Use when doing normal day-to-day Urban Flow delivery work and the agent should pick the next valid task, implement it, run validation, and update task status without requiring separate developer and tester prompts.
---

# Urban Flow Executor

Use this as the default implementation workflow in the Urban Flow repository.

## Start Here

Read these files in order:

1. `docs/tasks.md`
2. `docs/requirements.md`
3. `docs/architecture.md`
4. Relevant parts of `docs/design-decisions.md`
5. The target implementation and test files
6. `Makefile`

`docs/tasks.md` is the source of truth for task status and next work.

## Role

- Pick the next valid Phase 1 review-sized task unless the human assigns a specific task ID
- Implement the full task slice
- Add or update the most relevant tests for that slice
- Run the required validation
- Update `docs/tasks.md` when the task is complete

Use `urban-flow-reviewer` separately for PR review or review-comment triage. This skill is for delivery work, not review-first workflows.

## Workflow

1. Open `docs/tasks.md`
2. Use the Phase 1 review-sized queue
3. Pick the first unchecked task unless the human assigned one
4. Read the task row, dependencies, and watch notes
5. Implement the task with tight scope
6. Add or update focused tests for the changed behavior
7. Run validation:

```bash
make lint
uv run pytest <focused test selection>
```

8. Run broader checks when the scope warrants it:

```bash
uv run pytest --cov --cov-report=term-missing
```

9. Mark the task complete in `docs/tasks.md`
10. Return a short handoff with files changed, commands run, and any risks

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
- Intersection entry depends on both axis and phase

If the task appears to require changing one of these assumptions, stop and call it out explicitly.

## Working Rules

- Keep scope to one task slice
- Do not add speculative future work
- Avoid drive-by refactors in completed modules
- Use `uv` as the package manager and run project dependencies and Python commands through `uv`
- Prefer explicit validation and simple control flow
- Reject invalid bounded parameters clearly instead of silently clamping them unless the contract says otherwise
- If testing reveals a real implementation bug outside the assigned scope, stop and report it instead of folding it into the task silently

## When To Stop

Stop and report instead of expanding scope when:

- the queue row is materially larger than expected
- requirements, architecture, and code disagree in a material way
- a completed module needs non-trivial redesign
- a new bug should be reviewed separately

## Handoff

Keep handoff short. Include:

- task ID completed
- files changed
- commands run
- task-doc updates
- blockers, follow-ups, or risks
