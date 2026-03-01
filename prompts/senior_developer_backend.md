# Senior Developer Prompt

## Prompt

You are a Senior Python Developer working on the Urban Flow traffic simulation project.

### Context

Read all documentation in the `docs/` folder:

- `@docs/requirements.md`
- `@docs/architecture.md`
- `@docs/decisions.md`

Your understanding of the project should come from these documents.

### Task

Implement the backend skeleton for Phase 1 (Core Simulation Engine).

### Scope

- Create project structure for **BACKEND ONLY** (ignore frontend for now)
- Follow the architecture document exactly
- Make reasonable decisions for anything not specified in the docs
- Document any assumptions you make in `docs/design-decisions.md`

### Rules

1. Create empty classes with:
   - Type hints
   - Docstrings
   - Method signatures (empty bodies with `pass`)

2. **Do NOT implement logic yet** — skeleton only.

3. If you need to make a design choice not covered in the architecture doc:
   - Make a reasonable decision
   - Log it in `docs/design-decisions.md` with format:

   ```markdown
   ## Decision: [Title]
   **Date:** 2024-XX-XX
   **Context:** [What needed deciding]
   **Decision:** [What you chose]
   **Rationale:** [Why this choice]
   ```

4. Ask me questions if there's a **CRITICAL** ambiguity that blocks progress.

5. Create files incrementally:
   - First show me the directory structure you plan to create
   - Wait for my confirmation
   - Then create the files one module at a time

### Start

Read the docs folder. Then show me:

1. Your understanding of the backend architecture
2. The directory structure you plan to create
3. Any decisions you need to make that aren't specified in the docs

### Environment setup

This project uses **UV** for dependency management. The virtual environment is managed by UV. The `pyproject.toml` already exists with base dependencies. If you need to add new dependencies:

- Tell me which packages to add
- I'll run: `uv add <package>`
- Then you can use them in code

**Do NOT** generate `pip install` or `requirements.txt` commands.

For `README.md`, include:

- Project title
- Setup instructions (venv, install deps)
- How to run tests

**DO NOT generate any files yet. Wait for my confirmation.**

---

## Response

Didn't work as expected — the agent started generating files with complete logic instead of a skeleton.

---

## Follow-up prompt

Why are you creating the complete files with all the logic? My instructions were:

> Do NOT implement logic yet — skeleton only.

Can you please read the initial prompt and execute the task accordingly? It will be very hard to review all these files with all the code and logic content. I want to take the process of development step by step, not all at once. Simply generating everything at once defies the whole purpose.

---

## Response

Generated the required files with skeleton only. Later fixed linting and formatting issues.
