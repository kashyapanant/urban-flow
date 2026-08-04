# P1-ENG-04 Segment Admission and Congestion Design

**Date:** 2026-07-17  
**Status:** Accepted for implementation planning  
**Tasks:** P1-ENG-04 through P1-ENG-07

## Goal

Reduce Phase 1 congestion under sustained demand without removing, teleporting,
reversing, or rerouting vehicles. Preserve the one-cell grid geometry, prevent
opposing-direction segment deadlocks, make emergency priority safe and
observable, and detect whole-network standstill without claiming universal
liveness.

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
- An intersection may be selected as a spawn origin. Its admission target is the
  first downstream road segment on the vehicle's path; the spawn is admitted
  only when that segment grants the vehicle's first movement direction and its
  first downstream road cell is available. The grant reserves that road cell
  atomically with intersection placement until the spawned vehicle enters it.
- A spawn candidate submits a transient segment request during the spawn phase.
  The request participates in a transactional arbitration with persistent
  requests under the same emergency-precedence and fairness rules. An empty,
  unreserved segment may switch direction immediately when the candidate wins.
  Candidate-only admission state and the request commit atomically with vehicle
  placement; both are discarded if admission or placement fails.

### Road segments

- Add a `RoadSegmentManager` that derives deterministic maximal straight runs
  of road cells between intersections or grid boundaries. Intersections are not
  part of a segment.
- A segment has one active travel direction. Opposing demand closes admission,
  drains current occupants, and then switches direction.
- Requests from vehicles already on the grid persist until fulfilled or
  invalidated. Only the lead normal vehicle at an approach requests access.
- Emergency requests take precedence over all normal requests on an empty
  segment. Emergencies are served first-come-first-served. When only normal
  requests contend, same-tick ties use the direction not served last, with a
  deterministic lower-coordinate-to-higher-coordinate initial tie. Simultaneous
  emergency requests use that same lower-coordinate-to-higher-coordinate
  direction tie-break after first-come-first-served ordering.
- Normal requests begin before the light turns green, but do not alter signal
  timing.
- Non-terminal intersection entry requires a permissive signal, an empty
  intersection, a downstream segment grant, and an available downstream cell.
  A terminal intersection destination requires only the permissive signal and
  empty intersection; it bypasses segment admission and downstream-cell checks
  and completes the vehicle upon entry.
- A selected vehicle's grant becomes committed during arbitration, before it
  enters the intersection. The grant survives arbitration and reconciliation
  until the vehicle reaches the downstream segment's first road cell or its
  request is invalidated.
- A committed grant also reserves that first downstream road cell from spawn
  admission. The reservation releases when the vehicle reaches the cell or the
  grant is invalidated; spawn candidates must choose another eligible origin or
  be rejected for that demand attempt.
- Pathfinding remains fixed and does not inspect live segment locks or occupancy.

### Emergency priority

- An emergency reserves only its next segment within the existing three-cell
  lookahead.
- The first granted emergency reservation is non-preemptible until the vehicle
  clears the segment.
- Reconciliation releases an emergency reservation when its holder clears the
  segment, arrives anywhere within the reserved segment, or otherwise leaves
  the active vehicle set.
- Existing opposing occupants drain forward. Vehicles already ahead of the
  reservation holder may continue through the reserved segment and drain. No
  new normal entry or spawn placement is permitted anywhere in an
  emergency-reserved segment.
- The reservation holder is the only emergency that may preempt the associated
  entry signal. For a terminal intersection destination, an emergency holds a
  signal-only preemption claim instead of a segment reservation; it releases
  when the vehicle enters and arrives. Later emergencies queue in arrival
  order.
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
- Detection is explicit, not destructive. Phase 1 detects whole-network
  standstill, not arbitrary per-cycle blockage; it does not add rerouting,
  reversing, removal, or cycle-rotation movement.
- Directional admission reduces avoidable deadlocks but does not guarantee
  progress from every reachable network configuration.

## Tick Order

```text
refresh segment requests
arbitrate segment direction and reservations
apply emergency signal preemption
advance traffic lights
move vehicles and count successful moves
reconcile segment occupancy and reservations
attempt spawning using movement/capacity admission and transactional arbitration
collect arrivals and update metrics
reconcile segment occupancy and reservations after arrival cleanup
increment tick and broadcast snapshot
```

## Implementation Order

The slices are deliberately ordered around the scheduler dependency:

1. `P1-ENG-04` derives segments, persists normal requests, performs deterministic
   normal arbitration, and represents committed intersection-crossing grants.
2. `P1-ENG-05` adds emergency precedence, reservations, and preemption
   coordination to that scheduler.
3. `P1-ENG-06` changes spawn demand and capacity admission, then uses the
   completed scheduler for transactional spawn arbitration.
4. `P1-ENG-07` integrates the admission-aware tick order and movement gates, then
   completes snapshots, liveness telemetry, reset behavior, and regression
   coverage.

## Snapshot Contract

Snapshots add a top-level `road_segments` collection. Records expose:

```text
id, orientation, start, end, cells
active_direction, pending_direction
is_draining, accepting_entries
emergency_reserved_by, committed_entry_cells, occupant_count
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
  `phase_duration=1`. For this fixed scenario, assert continued completions in
  both halves, no cap violation, and no sustained gridlock flag. This is a
  regression expectation, not a universal liveness proof.
- Construct a whole-network standstill separately and assert detection, spawn
  pause, continued engine operation, and no vehicle removal or rerouting.
- Construct a committed non-terminal intersection crossing and assert that spawn
  admission cannot place a vehicle in its reserved downstream road cell before
  the crossing completes.

## Non-Goals

- Multi-lane or static one-way road geometry.
- Live occupancy-aware rerouting or reversing.
- Vehicle removal or teleportation as deadlock recovery.
- Emergency urgency levels.
- Adaptive signal control for normal traffic.
- An external queue for rejected spawn demand.
- Browser visualization changes; the backend snapshot is frontend-ready.
