---
name: urban-flow-reviewer
description: Use when reviewing Urban Flow changes, triaging PR comments, or preparing a fix plan from a branch or pull request. Follow the Phase 1 review workflow: compare the PR against local files, prioritize correctness and regression risks, map each review comment to a concrete action, and summarize findings before editing.
---

# Urban Flow Reviewer

Use this skill for PR review, review-comment triage, and fix planning in the Urban Flow repository.

## Start Here

Read these in order before reviewing:

1. `docs/tasks.md`
2. `docs/requirements.md`
3. `docs/architecture.md`
4. Relevant parts of `docs/design-decisions.md`
5. The changed implementation files
6. The changed test files
7. `Makefile`

`docs/tasks.md` remains the source of truth for task completion state. Do not rely on stale status copied into prompt files, PR descriptions, or handoff notes.

## Role

- Review the assigned branch, diff, or PR
- Prioritize correctness issues, regression risks, contract mismatches, and missing tests
- Inspect the local files before proposing fixes
- Summarize findings and the concrete fix plan before editing when the human asks for planning first

If the human asks only for review, stay in review mode and do not edit. If the human asks for fixes after review, implement only the agreed scope.

## Review Workflow

1. Identify the branch, PR, or diff to review
2. Fetch the PR diff and comments using the best available integration
3. Compare the PR state with the local files
4. Read the touched code and relevant tests
5. Group comments into:
   - correctness or behavior issues
   - test gaps
   - docs consistency issues
   - refactor or maintainability suggestions
6. Decide which comments are truly actionable versus redundant, already fixed, or non-blocking
7. Produce a fix plan that maps each actionable comment to a concrete code or doc change

## Review Priorities

- Behavioral regressions
- Violations of Phase 1 invariants
- Determinism problems
- API or contract mismatches
- Incomplete task slices
- Missing or weak tests for changed behavior
- Stale docs that conflict with `docs/tasks.md` or actual code

Treat style-only feedback as secondary unless the repo already treats it as a required standard.

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
- Intersection entry rules depend on axis and phase

If a proposed fix would alter one of these assumptions, call it out explicitly before changing code.

## Comment Triage Rules

- Do not treat every comment as equally important
- Collapse duplicate comments into one shared fix when appropriate
- Mark comments as already addressed if the local code already resolves them
- Prefer one coherent internal refactor over several repetitive micro-fixes when behavior is unchanged
- Use `uv` as the package manager and run project dependencies and Python commands through `uv`
- Keep planned fixes concrete: file, function, change

## Planning Output

When asked for a plan before editing, provide:

- the list of actionable comments
- the comments that are already resolved or non-blocking
- the concrete fix mapped to each actionable comment
- expected validation commands

Keep the plan specific enough that implementation can follow directly without re-analysis.

## Verification

After review-driven fixes:

```bash
make lint
uv run pytest <focused test selection>
```

Run broader checks when the scope warrants it.

## Handoff

Keep the handoff short. Include:

- branch or PR reviewed
- findings or comment themes
- files changed, if fixes were applied
- commands run
- remaining risks or follow-ups
