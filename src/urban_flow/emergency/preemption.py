"""Preemption manager -- coordinates signal preemption for emergency vehicles.

Listens for EmergencyDetected events and sends preemption requests to the
appropriate signal controllers.  Releases preemption after the vehicle passes.

This module will be implemented in Phase 3.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from urban_flow.core.types import Direction, IntersectionId, VehicleId
from urban_flow.engine.events import (
    EmergencyDetected,
    EventBus,
    PreemptionEnded,
    PreemptionStarted,
    SimulationEvent,
)
from urban_flow.signals.controller import SignalController


@dataclass
class ActivePreemption:
    """Tracks an active preemption at one intersection."""

    vehicle_id: VehicleId
    intersection_id: IntersectionId
    direction: Direction


class PreemptionManager:
    """Coordinates signal preemption across multiple intersections.

    Subscribes to EmergencyDetected events from the EventBus and
    sends preemption requests to signal controllers.
    """

    def __init__(
        self,
        event_bus: EventBus,
        controllers: dict[IntersectionId, SignalController],
    ) -> None:
        self._event_bus = event_bus
        self._controllers = controllers
        self._active: dict[IntersectionId, ActivePreemption] = {}

        self._event_bus.subscribe(EmergencyDetected, self._on_emergency_detected)

    def _on_emergency_detected(self, event: SimulationEvent) -> None:
        """Handle an EmergencyDetected event."""
        assert isinstance(event, EmergencyDetected)
        iid = event.intersection_id

        if iid in self._active:
            return  # already preempted

        controller = self._controllers.get(iid)
        if controller is None:
            return

        controller.request_preemption(event.approach_direction)
        self._active[iid] = ActivePreemption(
            vehicle_id=event.vehicle_id,
            intersection_id=iid,
            direction=event.approach_direction,
        )
        self._event_bus.publish(
            PreemptionStarted(
                tick=event.tick,
                vehicle_id=event.vehicle_id,
                intersection_id=iid,
                direction=event.approach_direction,
            )
        )

    def release(self, intersection_id: IntersectionId, tick: int) -> None:
        """Release preemption at an intersection after the vehicle passes."""
        preemption = self._active.pop(intersection_id, None)
        if preemption is None:
            return

        controller = self._controllers.get(intersection_id)
        if controller:
            controller.release_preemption()

        self._event_bus.publish(
            PreemptionEnded(
                tick=tick,
                vehicle_id=preemption.vehicle_id,
                intersection_id=intersection_id,
            )
        )
