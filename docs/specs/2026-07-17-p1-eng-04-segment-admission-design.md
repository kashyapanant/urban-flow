# P1-ENG-04 Segment Admission and Congestion Design

**Date:** 2026-07-17  
**Status:** Accepted for implementation planning  
**Tasks:** P1-ENG-04 through P1-ENG-07

## Goal

Keep the Phase 1 10x10 simulation live under sustained demand without removing,
teleporting, reversing, or rerouting vehicles. Preserve the one-cell grid
geometry and make emergency priority safe and observable.

## Root Cause

The current grid is physically single-lane but logically bidirectional. The old
spawn implementation rolled independently for every eligible edge cell, so
inflow could exceed the network's ability to drain. Vehicles have fixed paths
and wait when their next cell is occupied. Opposing traffic can fill a segment
or form a cyclic wait while the engine continues ticking.

## Accepted Decisions

### Spawn demand and capacity

- `spawn_rate` remains in `[0.0, 1.0]` but means one demand roll per tick,
  not a probability per edge cell.
- A successful demand roll creates at most one spawn attempt.
- Rejected demand is discarded; there is no external spawn queue.
- The default 10x10 grid has an active cap of 30 vehicles. For other grids:
  ```text
  active_cap = max(1, floor(traversable_cells * 30 / 64))
  emergency_reserve = min(active_cap - 1, max(1, ceil(active_cap * 0.10)))
  ```
- Normal admission stops at `active_cap - emergency_reserve`. Emergency
  admission may use the reserved slots, but never exceeds `active_cap`.
- If active vehicles exist and no vehicle moved during the movement phase,
  spawning is rejected for that tick. An empty grid may still spawn.

### Road segments

- Add a `RoadSegmentManager` that derives deterministic maximal straight runs
  of road cells between intersections or grid boundaries. Intersections are not
  part of a segment.
- A segment has one active travel direction. Opposing demand closes admission,
  drains current occupants, and then switches direction.
- Requests persist until fulfilled or invalidated. Only the lead normal vehicle
  at an approach requests access. Same-tick ties use the direction not served
  last, with a deterministic lower-coordinate-to-higher-coordinate initial tie.
- Normal requests begin before the light turns green, but do not alter signal
  timing.
- Intersection entry requires a permissive signal, an empty intersection, and a
  segment grant. A non-terminal destination also requires an available downstream
  cell; a terminal intersection destination does not require one and completes the
  vehicle upon entry.
- Pathfinding remains fixed and does not inspect live segment locks or occupancy.

### Emergency priority

- An emergency reserves only its next segment within the existing three-cell
  lookahead.
- The first granted emergency reservation is non-preemptible until the vehicle
  clears the segment.
- Existing opposing occupants drain forward. Same-direction vehicles already
  ahead of the reservation holder may enter or continue through the reserved
  segment and drain. New normal vehicles cannot enter behind the emergency.
- The reservation holder is the only emergency that may preempt the associated
  entry signal. Later emergencies queue in arrival order.
- Emergency vehicles cannot overtake vehicles ahead in the one-cell geometry.
- Urgency levels are a future extension; Phase 1 treats all emergencies equally.

### Liveness and observability

- Movement remains sequential in the existing priority order after admission.
- Vehicles expose an ordered `wait_reasons` list containing every applicable
  blocker in this canonical order: `next_cell_occupied`, `traffic_light`,
  `segment_admission`, and `downstream_cell_occupied`.
- Metrics add spawn outcomes, movement progress, active/waiting counts, capacity
  values, and `gridlock_suspected`.
- `gridlock_suspected` becomes true after
  `max(30, phase_duration * 8)` active-vehicle ticks with zero movement. The
  engine continues running and clears the flag after movement resumes.
- Detection is explicit, not destructive. Arbitrary cyclic arrangements remain
  a documented limitation; Phase 1 does not add rerouting, reversing, removal,
  or cycle-rotation movement.

## Tick Order

```text
refresh segment requests
arbitrate segment direction and reservations
apply emergency signal preemption
advance traffic lights
move vehicles and count successful moves
reconcile segment occupancy and reservations
attempt spawning using movement/capacity admission
collect arrivals and update metrics
increment tick and broadcast snapshot
```

## Snapshot Contract

Snapshots add a top-level `road_segments` collection. Records expose:

```text
id, orientation, start, end, cells
active_direction, pending_direction
is_draining, accepting_entries
emergency_reserved_by, occupant_count
waiting_counts: {direction: {normal, emergency}}
```

Vehicle snapshots add `wait_reasons`. Existing REST and WebSocket fields remain
compatible; the new fields are additive.

## Validation

- Unit-test spawn demand, capacity, emergency reserve, segment admission,
  fairness, intersection gating, emergency reservation, wait reasons, reset,
  and metrics.
- Run a 500-tick seeded regression with `random.seed(0)`,
  `spawn_rate=0.7`, `emergency_probability=0.3`, and
  `phase_duration=1`. Assert continued completions in both halves, no cap
  violation, and no sustained gridlock flag.
- Construct a cyclic blockage separately and assert detection, spawn pause,
  continued engine operation, and no vehicle removal or rerouting.

## Non-Goals

- Multi-lane or static one-way road geometry.
- Live occupancy-aware rerouting or reversing.
- Vehicle removal or teleportation as deadlock recovery.
- Emergency urgency levels.
- Adaptive signal control for normal traffic.
- An external queue for rejected spawn demand.
- Browser visualization changes; the backend snapshot is frontend-ready.
