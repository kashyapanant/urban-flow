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
