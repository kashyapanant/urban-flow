# Urban Flow - Developer Handoff

**Last Updated:** 2026-04-16  
**Version:** 2.0

This file is intentionally short. It should help the next implementation agent start fast without repeating large amounts of project history.

## Single Source Of Truth

- **Task status and next work:** `@docs/tasks.md`
- **Product scope:** `@docs/requirements.md`
- **System behavior and contracts:** `@docs/architecture.md`
- **Trade-offs already made:** `@docs/design-decisions.md`

Do **not** duplicate task status in this file. Read `tasks.md` first.

## Your Role

- Implement the current **review-sized** task from `@docs/tasks.md`
- Work on **one task at a time**
- Keep changes scoped to that task unless a tightly related fix is required
- Do **not** write tests unless the human explicitly asks for it

If a human assigns a specific task ID, that overrides the "first unchecked task" rule.

## How To Pick The Next Task

1. Open `@docs/tasks.md`
2. Use the **Phase 1 Review-Sized Task Queue**
3. Pick the first `⬜` task unless the human gave you a specific ID
4. Read the queue row, dependency column, and any relevant watch notes

Ignore older micro-task references if they appear elsewhere. Use the review-sized queue and the legacy mapping in `tasks.md`.

## Read Before Coding

1. `@docs/tasks.md`
2. `@docs/requirements.md`
3. `@docs/architecture.md`
4. Relevant sections of `@docs/design-decisions.md`
5. The target implementation file
6. `@Makefile`

## Phase 1 Invariants

- Phase 1 is a **deterministic**, **single-lane**, **grid-based** MVP
- Coordinates are `(x, y)` and grid storage is row-major: `cells[y][x]`
- Phase 1 emergency vehicles use a **fixed precomputed path**; no rerouting yet
- Tick order is:
  1. preemption scan
  2. traffic light update
  3. vehicle movement
  4. spawning
  5. cleanup and metrics
  6. broadcast
- A vehicle may enter an intersection only when the required axis matches the active axis and the phase permits entry

If you think the current task requires changing one of these assumptions, stop and call it out explicitly.

## Working Rules

- Implement the **whole task slice**, not just one small method inside it
- Avoid speculative future work
- Avoid drive-by refactors in completed modules
- Keep public APIs typed and documented
- Prefer simple control flow and explicit validation
- If a bounded parameter is invalid, reject it clearly rather than silently clamping it unless the contract explicitly says otherwise

## Verification

Minimum after every implementation task:

```bash
make lint
```

Also run the most relevant focused tests if they exist for the touched area. If there are no meaningful focused tests yet, say that clearly in handoff notes.

## When To Update Docs

- Update `@docs/tasks.md` when the task is done
- Add to `@docs/design-decisions.md` only for a real design trade-off
- Do not dump long implementation notes into the prompt files

## Handoff Format

Keep handoff short. Use 4-6 bullets max:

- task ID completed
- files changed
- commands run
- any doc or design-decision updates
- blockers, follow-ups, or risks for the next agent

Do **not** restate the whole project or copy large chunks of context into the handoff.

## Stop Conditions

Stop and report instead of expanding scope when:

- the task is larger than the queue row implied
- a completed module needs a non-trivial redesign
- requirements, architecture, and code disagree in a material way
- you find a bug that should be reviewed separately from the assigned task
