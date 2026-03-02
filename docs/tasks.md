# Urban Flow - Development Tasks

This document tracks development tasks, issues, and improvements for the Urban Flow project.

## Task Status Legend
- 🔴 **Critical** - Blocks core functionality or security issue
- 🟡 **High** - Important for robustness/user experience  
- 🟢 **Medium** - Nice to have, improves code quality
- 🔵 **Low** - Future enhancement, not urgent

---

## Phase 1: Core Simulation Engine - Pending Tasks

### 🟡 API-001: Add Input Validation to ConfigUpdateRequest

**Status:** Open  
**Priority:** High  
**Component:** API Layer (`backend/api/routes.py`)  
**Reported:** 2026-02-28  

**Description:**
The `ConfigUpdateRequest` model lacks validation constraints, allowing invalid values to pass through the API boundary. This creates a security/robustness gap where invalid data could reach the simulation engine.

**Current State:**
```python
class ConfigUpdateRequest(BaseModel):
    tick_speed: int | None = None        # ❌ No validation
    spawn_rate: float | None = None      # ❌ No validation  
    phase_duration: int | None = None    # ❌ No validation
```

**Expected State:**
```python
class ConfigUpdateRequest(BaseModel):
    tick_speed: int | None = Field(None, ge=1, le=10, description="Ticks per second")
    spawn_rate: float | None = Field(None, ge=0.0, le=1.0, description="Probability per edge cell per tick")
    phase_duration: int | None = Field(None, ge=1, le=20, description="Ticks per traffic light phase")
```

**Constraints (from SimulationConfig):**
- `tick_speed`: 1-10 ticks per second
- `spawn_rate`: 0.0-1.0 probability  
- `phase_duration`: 1-20 ticks per phase

**Acceptance Criteria:**
- [ ] Add Pydantic Field validation to all ConfigUpdateRequest fields
- [ ] Ensure validation constraints match SimulationConfig exactly
- [ ] Add appropriate error messages for validation failures
- [ ] Test with invalid values to ensure 422 responses
- [ ] Update API documentation to reflect constraints

**Estimated Effort:** 1-2 hours

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

*Completed tasks will be moved here for reference*

---

## Notes

- Tasks should be atomic and well-defined
- Include acceptance criteria for each task
- Reference specific files/components affected
- Estimate effort where possible
- Link to relevant architecture decisions or requirements
