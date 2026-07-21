# Traffic Simulation System - Requirements

## Problem Statement

Emergency vehicles in urban environments face delays at traffic signals and congested routes, directly impacting response times. There is no lightweight, iterative way for a developer to simulate and visualize how dynamic traffic-light preemption (turning lights green ahead of emergency vehicles) affects travel time on a simplified grid before scaling to real-world city maps.

This project builds a traffic simulation starting with a minimal 10x10 grid and incrementally evolving toward real city map integration with live traffic and signal data.

## MVP Scope (v1)

### In Scope

- **10x10 grid world** with roads, intersections, and static non-traversable cells (buildings, parks, etc.)
- **Single-lane roads** — each road cell holds at most one vehicle at a time
- **Two vehicle types**: normal car and emergency vehicle
- **Vehicle spawning** at random grid edges with one demand roll per tick and a bounded active-vehicle capacity, each with a randomly assigned destination (point A to B)
- **Vehicle movement** at 1 cell per tick
- **Pathfinding**: A\* shortest-path for normal vehicles; fastest-path (factoring current light states) for emergency vehicles
- **Emergency vehicle path**: fixed pre-computed path, no mid-journey rerouting
- **Traffic lights** at intersections with a full four-phase cycle (green, yellow, red, left-turn arrow), each phase lasting 3 ticks (configurable)
- **Emergency vehicle signal preemption**: an emergency claims an intersection from 3 cells away, triggers a yellow transition for cross-traffic, and coordinates the green phase with its next road-segment reservation
- **Web-based real-time visualization** of the grid, vehicles, and traffic light states
- **Simulation controls**: pause/resume, tick speed adjustment (1–10 ticks/second)
- **Performance metric**: track and display the percentage difference in travel ticks between emergency vehicles and normal vehicles over the same or comparable routes

### Out of Scope (Future Phases)

- Multi-lane roads (planned for graph-based map phase)
- Mid-journey rerouting for emergency vehicles
- Manual obstacle placement or removal at runtime
- Manual emergency vehicle spawning on demand
- Real city map integration and live traffic data
- Pedestrians, buses, trucks, or other vehicle types

## User Stories

| # | As a... | I want to... | So that... |
|---|---------|-------------|------------|
| 1 | Developer | view a 10x10 grid with roads, intersections, and obstacles rendered in a web browser | I can visually verify the simulation world is set up correctly |
| 2 | Developer | see vehicles spawn at grid edges and navigate to their destinations | I can confirm pathfinding and movement logic work |
| 3 | Developer | observe traffic lights cycling through all four phases at intersections | I can verify signal timing and phase transitions |
| 4 | Developer | watch an emergency vehicle turn signals green as it approaches an intersection | I can validate the preemption mechanism works with proper yellow transitions for cross-traffic |
| 5 | Developer | pause and resume the simulation | I can inspect a specific moment in time |
| 6 | Developer | adjust the tick speed between 1 and 10 ticks per second | I can slow down to observe details or speed up to see aggregate behavior |
| 7 | Developer | configure the vehicle spawn rate and traffic light phase duration | I can test different traffic scenarios without changing code |
| 8 | Developer | see a metric comparing emergency vehicle travel time vs. normal vehicle travel time | I can quantify whether signal preemption actually improves emergency response |

## Data Model

### Grid

| Property | Type | Description |
|----------|------|-------------|
| width | integer | Number of columns (10 for MVP) |
| height | integer | Number of rows (10 for MVP) |
| cells | Cell[][] | 2D array of cells |

### Cell

| Property | Type | Description |
|----------|------|-------------|
| x | integer | Column index |
| y | integer | Row index |
| type | enum | `road`, `intersection`, `obstacle` |
| vehicle | Vehicle? | Vehicle currently occupying the cell (null if empty) |
| trafficLight | TrafficLight? | Present only on `intersection` cells |

### Vehicle

| Property | Type | Description |
|----------|------|-------------|
| id | string | Unique identifier |
| type | enum | `normal`, `emergency` |
| position | (x, y) | Current cell coordinates |
| origin | (x, y) | Spawn point (grid edge) |
| destination | (x, y) | Target cell |
| path | (x, y)[] | Pre-computed ordered list of cells to traverse |
| status | enum | `moving`, `waiting`, `arrived` |
| waitReasons | enum[] | All applicable movement blockers for a waiting vehicle |
| ticksElapsed | integer | Number of ticks since spawn (for metric tracking) |

### TrafficLight

| Property | Type | Description |
|----------|------|-------------|
| id | string | Unique identifier |
| intersection | (x, y) | Cell coordinates |
| currentPhase | enum | `green`, `yellow`, `red`, `leftTurn` |
| phaseDuration | integer | Ticks per phase (default: 3, configurable) |
| ticksInCurrentPhase | integer | Counter within current phase |
| preemptedBy | Vehicle? | Emergency vehicle that has claimed this intersection (null if none) |

### RoadSegment

| Property | Type | Description |
|----------|------|-------------|
| id | string | Deterministic segment identifier |
| cells | (x, y)[] | Straight road cells controlled as one admission segment |
| activeDirection | enum? | Current admitted travel direction |
| pendingDirection | enum? | Direction waiting for the segment to drain |
| isDraining | boolean | Whether new entries are closed while occupants clear |
| emergencyReservedBy | string? | Emergency vehicle holding the reservation |

### Simulation

| Property | Type | Description |
|----------|------|-------------|
| tickCount | integer | Current simulation tick |
| tickSpeed | integer | Ticks per second (1–10) |
| state | enum | `running`, `paused` |
| spawnRate | float | One demand probability per tick, with at most one attempt per tick |
| vehicles | Vehicle[] | All active vehicles |
| metrics | Metrics | Aggregated performance data |

### Metrics

| Property | Type | Description |
|----------|------|-------------|
| normalAvgTicks | float | Average ticks-to-destination for normal vehicles |
| emergencyAvgTicks | float | Average ticks-to-destination for emergency vehicles |
| improvement | float | Percentage fewer ticks for emergency vs. normal |
| totalVehiclesCompleted | integer | Count of vehicles that reached their destination |
| activeVehicles | integer | Current active vehicle count |
| waitingVehicles | integer | Current vehicles with one or more blockers |
| movesThisTick | integer | Vehicles that advanced during the current tick |
| consecutiveZeroMoveTicks | integer | Active-vehicle ticks with no movement |
| gridlockSuspected | boolean | Liveness warning after the derived zero-movement threshold |
| spawnAttempts | integer | Cumulative successful demand rolls |
| spawnAdmitted | integer | Cumulative admitted vehicles |
| spawnRejectedCapacity | integer | Cumulative capacity rejections |
| spawnRejectedNetworkStalled | integer | Cumulative zero-movement rejections |
| spawnRejectedNoAdmissibleEntry | integer | Cumulative path or segment admission rejections |
| activeVehicleCap | integer | Read-only derived active capacity |
| emergencyReservedSlots | integer | Read-only capacity reserved for emergencies |
)
## Edge Cases

| # | Scenario | Expected Behavior |
|---|----------|-------------------|
| 1 | Two vehicles try to enter the same cell on the same tick | One vehicle waits; priority goes to the vehicle already closer to its destination (or random tiebreak). Emergency vehicles always win ties against normal vehicles. |
| 2 | Emergency vehicle claims an intersection but another emergency vehicle also approaches | First-come-first-served based on which vehicle reached the 3-cell claim range first. Second emergency vehicle waits for the first to clear. |
| 3 | Vehicle's destination is unreachable (surrounded by obstacles) | Vehicle is not spawned; a new origin/destination pair is selected. |
| 4 | No valid path exists between a random origin and destination | Same as above — re-roll until a valid pair is found, with a max retry limit to avoid infinite loops. |
| 5 | Emergency vehicle claims intersection, but it is already mid-phase for cross-traffic | Cross-traffic phase transitions to yellow immediately, then red, before emergency vehicle's direction goes green. The remaining phase time is not preserved — normal cycling resumes after the emergency vehicle clears. |
| 6 | Active cap reached or the active network made no movement | Spawn demand is rejected for the tick; the engine does not remove existing vehicles. |
| 7 | Multiple intersections claimed simultaneously by the same emergency vehicle | Each intersection within 3 cells ahead on the emergency vehicle's path begins its preemption sequence independently. |
| 8 | Emergency vehicle reaches destination while a light is still preempted ahead | Preempted intersection reverts to normal cycling immediately. |
| 9 | Tick speed changed while simulation is running | Takes effect on the next tick — no partial-tick behavior. |
| 10 | All vehicles have arrived and no new ones are spawning | Simulation continues running (lights still cycle) but nothing moves. User can adjust spawn rate or pause. |

## Success Criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| 1 | Vehicles navigate from origin to destination without passing through obstacles or occupied cells | Visual inspection + automated path validation |
| 2 | Traffic lights cycle correctly through all four phases at the configured duration | Phase counter matches expected tick counts |
| 3 | Emergency vehicles trigger green lights at intersections within 3 cells, with proper yellow transition for cross-traffic | Visual inspection + event log verification |
| 4 | Emergency vehicles reach their destination in measurably fewer ticks than normal vehicles on comparable routes | Metrics dashboard shows a positive improvement percentage |
| 5 | Simulation runs smoothly at all tick speeds (1–10 ticks/second) without UI lag or dropped frames | Manual testing across speed range |
| 6 | Pause/resume works correctly with no state corruption | Simulation state is identical before pause and after resume |
| 7 | Configurable parameters (spawn rate, phase duration, tick speed) take effect without restarting the simulation | Runtime adjustment verified visually |

### P1-ENG-04 Congestion and Admission Requirements

- The public spawn-rate range remains 0.0-1.0, but each tick performs at most one demand attempt.
- The default 10x10 grid admits at most 30 active vehicles and reserves three admission slots for emergency arrivals.
- A road segment admits one travel direction at a time and drains current occupants before switching to an opposing request.
- Normal vehicles may not enter an intersection without a permissive light, segment admission, and downstream space.
- Emergency priority grants the next safe segment access after opposing occupants drain; it does not permit overtaking or pass-through.
- Vehicle snapshots expose all applicable movement blockers through a stable wait-reasons list.
- Metrics expose active and waiting counts, movement progress, spawn rejection causes, capacity, and suspected gridlock.
- A full simulation reset rebuilds segment state and clears requests, reservations, liveness counters, and metrics; a config reset does not rebuild world state.
- Phase 1 detects arbitrary cyclic blockage but does not remove, reverse, reroute, or teleport vehicles.
