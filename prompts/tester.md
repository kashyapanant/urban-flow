# Tester Prompt

## Initial prompt

You are an Expert QA Engineer specializing in Python testing.

### Context

- `@docs/requirements.md`
- `@docs/architecture.md`
- `@docs/decisions.md`
- `@docs/design-decisions.md`

### Requirements

1. Use pytest fixtures for common setup.
2. Use `@pytest.mark.parametrize` for multiple test cases.
3. Follow AAA pattern (Arrange, Act, Assert).
4. Test both happy paths and edge cases.
5. Use descriptive test names (`test_<method>_<scenario>`).
6. Group tests by method using classes.

**For `__init__`, test:**

- Valid initialization with various dimensions
- Invalid inputs (negative, zero, non-integers, floats, strings)
- Edge case: 1×1 grid
- Large grids (e.g. 100×100)

### Your task

Write comprehensive pytest tests for the files or methods I provide.

Do not write any test cases yet; just confirm whether the task is clear. If you have questions, feel free to ask.

---

## Response

Understood the task clearly: write comprehensive pytest tests as an Expert QA Engineer with the specified framework, patterns, and coverage (including `__init__` cases). Referenced the documentation for context. Asked clarifying questions: which files/methods to start with, test file organization, mock preferences, and coverage expectations.

---

## Next prompt

1. I will provide that in a bit; please wait for now.
2. The repo already has a test folder under `backend/` and many test files are present there.
3. I’ll leave the mock part to you; please decide based on your best judgment.
4. I think the focus should be on critical business logic and edge cases.

---

## Response

Confirmed understanding:

- **Testing requirements:** pytest fixtures, `@pytest.mark.parametrize`, AAA, happy path + edge cases, descriptive names, group by method with classes.
- **`__init__` testing:** valid dimensions, invalid inputs, 1×1 grid, large grids (100×100).
- **Additional context:** Existing test structure under `backend/`, mocking left to the tester, focus on critical business logic and edge cases; specific files/methods to be provided later.

Asked: Should I examine the existing test structure first? When you provide files/methods, create new or add to existing? Any specific test file naming? Should I read the context docs first?

---

## Response (your answers)

**Should I examine the existing test structure first?**  
Yes, please.

**When you provide files/methods: create new test files or add to existing? Naming?**  
If a test file for that module/method exists, use it. If you need to add tests, add to that file or create a new one. Use descriptive test names: `test_<method>_<scenario>`.

**Should I read the context documents first?**  
Yes, please.

---

## Response (summary)

**Understanding summary**

- **Business domain:** Urban traffic simulation with emergency vehicle signal preemption; 10×10 grid, roads, intersections, obstacles; normal and emergency vehicles; 4-phase traffic lights with preemption; goal to measure emergency vehicle travel time improvements.
- **Current test structure:** Tests by module (`test_<module>.py`), classes per tested class (e.g. `TestGrid`, `TestVehicle`), methods `test_<method>_<scenario>` with docstrings; placeholder methods currently; pytest + pytest-asyncio; Black + Ruff; Python 3.12+.
- **Key testing requirements:** Fixtures, parametrize, AAA, happy path + edge cases, descriptive names, group by method; for `__init__`: valid dimensions, invalid inputs, 1×1 grid, large grids.

**Confirmation**

- Examine existing patterns ✅
- Follow naming: `test_<method>_<scenario>` ✅
- Add to existing files or create new as needed ✅
- Focus on critical business logic and edge cases ✅
- Handle mocking per architecture ✅

Ready to write tests when specific files or methods are provided.
