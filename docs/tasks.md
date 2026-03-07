# Urban Flow - Development Tasks

This document tracks development tasks, issues, and improvements for the Urban Flow project.

## Task Status Legend
- 🔴 **Critical** - Blocks core functionality or security issue
- 🟡 **High** - Important for robustness/user experience  
- 🟢 **Medium** - Nice to have, improves code quality
- 🔵 **Low** - Future enhancement, not urgent

---

## Phase 1: Core Simulation Engine - Development Plan

### Implementation Order (Foundation-First Approach)

#### 1. Grid Class (Foundation)
- [ ] `Grid.__init__()` - Initialize grid with city blocks layout
- [ ] `Cell.is_traversable()` - Check if cell allows vehicle movement
- [ ] `Cell.is_occupied()` - Check if cell contains vehicle
- [ ] `Grid.get_cell()` - Get cell at coordinates
- [ ] `Grid.get_neighbors()` - Get traversable neighboring cells
- [ ] `Grid.place_vehicle()` - Place vehicle in cell
- [ ] `Grid.remove_vehicle()` - Remove vehicle from cell
- [ ] `Grid.get_edge_cells()` - Get spawn-eligible edge cells
- [ ] `Grid.get_intersection_cells()` - Get intersection positions
- [ ] `Grid.snapshot()` - Create serializable state

#### 2. Pathfinder Class (Depends: Grid)
- [ ] `PathNode.f_cost` - A* total cost calculation
- [ ] `PathNode.__lt__()` - Priority queue comparison
- [ ] `Pathfinder.find_path()` - A* pathfinding algorithm

#### 3. Vehicle Classes (Depends: Grid, Pathfinder)
- [ ] `Vehicle.get_next_position()` - Get next path position
- [ ] `Vehicle.advance_path()` - Move to next position
- [ ] `Vehicle.get_remaining_distance()` - Calculate remaining cells
- [ ] `VehicleManager.__init__()` - Initialize manager
- [ ] `VehicleManager.spawn_vehicles()` - Spawn at grid edges
- [ ] `VehicleManager.move_vehicles()` - Priority-based movement
- [ ] `VehicleManager.collect_arrived()` - Remove completed vehicles

#### 4. TrafficLight Classes (Depends: Vehicle)
- [ ] `TrafficLight.tick()` - Advance phase timing
- [ ] `TrafficLight.can_enter()` - Check movement permission
- [ ] `TrafficLight.request_preemption()` - Emergency preemption
- [ ] `TrafficLight.release_preemption()` - Resume normal cycling
- [ ] `TrafficLightManager.__init__()` - Initialize all lights
- [ ] `TrafficLightManager.tick()` - Update all lights

#### 5. Metrics Class (Depends: Vehicle)
- [ ] `Metrics.normal_avg_ticks` - Calculate normal vehicle average
- [ ] `Metrics.emergency_avg_ticks` - Calculate emergency average
- [ ] `Metrics.improvement` - Calculate percentage improvement
- [ ] `Metrics.record_arrival()` - Record vehicle completion

#### 6. SimulationEngine (Orchestrates All)
- [ ] `SimulationEngine.__init__()` - Initialize all components
- [ ] `SimulationEngine.start()` - Begin tick loop
- [ ] `SimulationEngine.tick()` - Execute single simulation step
- [ ] `SimulationEngine.snapshot()` - Create complete state

---

## Active Issues & Bugs

*Space for logging bugs found during implementation*

---

## Phase 1: Core Simulation Engine - Pending Tasks

*No pending tasks currently*

---

## Future Task Categories

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
