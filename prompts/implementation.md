# Implementation Prompt

## Prompt

You are a Senior Python Developer on the Urban Flow traffic simulation project.

### Context

Read the architecture, current code, and design decisions along with requirements:

- `@docs/requirements.md`
- `@docs/architecture.md`
- `@docs/decisions.md`
- `@docs/design-decisions.md`

In this phase we will start with actual implementation.

### Current state

The skeleton structure is present; please go through the codebase once.

### Your task

Implement class methods **ONE AT A TIME**. After each method, wait for my review before proceeding.

### Rules

1. Implement only the method I specify.
2. Use type hints from `types.py`.
3. Add comprehensive docstrings (Args, Returns, Raises).
4. Handle edge cases and validate inputs.
5. Raise descriptive errors (`ValueError`, `IndexError`, etc.).
6. **Do NOT write tests** (Tester handles that).
7. If you make implementation choices not in the architecture, log them in `docs/design-decisions.md` (see `@prompts/senior_developer_backend.md` lines 39–47 for format).

### Before starting

Let’s discuss the following:

1. Did you get the project structure?
2. Based on your understanding, which class should we start with?
3. Show me **ONLY** the class and method name to start with.

---

## Response

**Class:** Grid  
**Method:** `Cell.is_traversable()`

**Rationale:**

- **Foundation first:** Grid is the base data structure that Vehicle, TrafficLight, and Pathfinder all depend on.
- **Simple start:** `Cell.is_traversable()` is a straightforward method with clear logic.
- **Building block:** This method is used by pathfinding, vehicle movement, and spawning.
- **No dependencies:** It only depends on the cell’s type, making it self-contained.

---

## Follow-up prompt

Thanks — what about `__init__` in the Grid class? Shouldn’t that be the first one?

---

## Response

You’re absolutely right. The `__init__` method should be implemented first, since it’s the constructor that sets up the fundamental state of the Grid class. All other methods depend on the grid being properly initialized.

**Class:** Grid  
**Method:** `Grid.__init__()`

**Rationale:**

- **Constructor first:** `__init__` establishes the basic grid structure and data.
- **Foundation:** All other Grid methods depend on the initialized state (cells array, dimensions, layout).
- **City blocks pattern:** This method needs to implement the specific layout described in the architecture.
- **Traffic light setup:** It needs to identify intersection positions for traffic light placement.

---

### Task handoff

# Moving to sonnet 4.6 or gpt-5.3 codex as they are better suited for coding and other related task

# Urban Flow - Development Context Handoff

## Project & Role
You are a Senior Python Developer on the Urban Flow traffic simulation project - a tick-based emergency vehicle preemption system with Python backend + browser frontend.

## Current Status
**Phase**: Implementation (skeleton complete, implementing methods one-by-one)
**Next Task**: P1-GRID-01 (`Grid.__init__()`) - pending clarification questions

## Key Resources (READ THESE)
- **@docs/tasks.md** - Complete development plan, task order, and progress tracking
- **@docs/requirements.md** - MVP scope and user stories  
- **@docs/architecture.md** - Complete system design
- **@docs/design-decisions.md** - All implementation decisions (link new ones to task IDs)

## Implementation Rules
1. Implement only the method specified, wait for review before next
2. Use existing type hints and add comprehensive docstrings
3. Handle edge cases, validate inputs, raise descriptive errors
4. **CRITICAL**: Run `make lint` after each implementation, use `make format` to fix issues
5. Log implementation choices in docs/design-decisions.md with task ID reference:
   ```markdown
   ## Decision: [Title] (Task: P1-GRID-01)
   **Date:** 2026-XX-XX
   **Context:** [What needed deciding]
   **Decision:** [What you chose] 
   **Rationale:** [Why this choice]
   ```

## Recent Completed Work
- ✅ API-001: Added ConfigUpdateRequest validation + `extra="forbid"`
- ✅ Development plan created in docs/tasks.md with task IDs

## Pending Questions for P1-GRID-01
**ANSWER THESE BEFORE IMPLEMENTING:**
1. Grid layout: Exact "city blocks" pattern or configurable?
2. Traffic lights: Create objects in `Grid.__init__()` or just identify positions?
3. Error handling: ValueError for invalid dimensions or use SimulationConfig validation?
4. Implementation depth: Full working method or incremental approach?

## Next Steps
1. Review @docs/tasks.md for complete context
2. Answer the 4 questions above
3. Implement P1-GRID-01 with proper task ID logging
4. Run `make lint` and wait for review
