# Urban Flow - Development Tasks

This document tracks development tasks, issues, and improvements for the Urban Flow project.

## Task Status Legend
- 🔴 **Critical** - Blocks core functionality or security issue
- 🟡 **High** - Important for robustness/user experience  
- 🟢 **Medium** - Nice to have, improves code quality
- 🔵 **Low** - Future enhancement, not urgent

---

## Phase 1: Core Simulation Engine - Pending Tasks

*No pending tasks currently*

---

## Future Task Categories

### Implementation Tasks
*Tasks for implementing the skeleton methods with actual logic*

### Testing Tasks  
*Tasks for writing comprehensive tests*

### Performance Tasks
*Tasks for optimization and performance improvements*

### Documentation Tasks
*Tasks for improving documentation and examples*

### Frontend Tasks
*Tasks for the web frontend (Phase 1 scope)*

---

## Completed Tasks

### ✅ API-001: Add Input Validation to ConfigUpdateRequest

**Status:** Completed  
**Priority:** High  
**Component:** API Layer (`backend/api/routes.py`)  
**Reported:** 2026-02-28  
**Completed:** 2026-03-05  

**Description:**
The `ConfigUpdateRequest` model lacked validation constraints, allowing invalid values to pass through the API boundary. This created a security/robustness gap where invalid data could reach the simulation engine.

**Solution Implemented:**
```python
class ConfigUpdateRequest(BaseModel):
    """Request model for updating simulation configuration."""

    tick_speed: int | None = Field(None, ge=1, le=10, description="Ticks per second")
    spawn_rate: float | None = Field(None, ge=0.0, le=1.0, description="Probability per edge cell per tick")
    phase_duration: int | None = Field(None, ge=1, le=20, description="Ticks per traffic light phase")
```

**Changes Made:**
- ✅ Added Pydantic Field validation to all ConfigUpdateRequest fields
- ✅ Ensured validation constraints match SimulationConfig exactly
- ✅ Added descriptive field messages for better API documentation
- ✅ Logged implementation decision in docs/design-decisions.md

**Result:** API now properly validates configuration updates and returns 422 errors for invalid values, preventing invalid data from reaching the simulation engine.

---

## Notes

- Tasks should be atomic and well-defined
- Include acceptance criteria for each task
- Reference specific files/components affected
- Estimate effort where possible
- Link to relevant architecture decisions or requirements
