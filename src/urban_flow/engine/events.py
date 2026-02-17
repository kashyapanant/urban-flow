"""Event bus and simulation event definitions.

Components communicate through events to stay loosely coupled.
The ``EventBus`` implements a simple publish-subscribe pattern.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable

from urban_flow.core.types import (
    Direction,
    IntersectionId,
    RoadId,
    SignalState,
    Tick,
    VehicleId,
)


# ---------------------------------------------------------------------------
# Event dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SimulationEvent:
    """Base class for all simulation events."""

    tick: Tick


@dataclass(frozen=True)
class VehicleSpawned(SimulationEvent):
    vehicle_id: VehicleId
    origin: IntersectionId
    destination: IntersectionId
    is_emergency: bool = False


@dataclass(frozen=True)
class VehicleMoved(SimulationEvent):
    vehicle_id: VehicleId
    road_id: RoadId
    cell_index: int


@dataclass(frozen=True)
class VehicleArrived(SimulationEvent):
    vehicle_id: VehicleId
    destination: IntersectionId
    total_ticks: int


@dataclass(frozen=True)
class VehicleWaiting(SimulationEvent):
    vehicle_id: VehicleId
    intersection_id: IntersectionId


@dataclass(frozen=True)
class SignalChanged(SimulationEvent):
    intersection_id: IntersectionId
    direction: Direction
    new_state: SignalState


@dataclass(frozen=True)
class EmergencyDetected(SimulationEvent):
    vehicle_id: VehicleId
    intersection_id: IntersectionId
    approach_direction: Direction
    distance_cells: int


@dataclass(frozen=True)
class PreemptionStarted(SimulationEvent):
    vehicle_id: VehicleId
    intersection_id: IntersectionId
    direction: Direction


@dataclass(frozen=True)
class PreemptionEnded(SimulationEvent):
    vehicle_id: VehicleId
    intersection_id: IntersectionId


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------

EventHandler = Callable[[SimulationEvent], Any]


class EventBus:
    """Simple synchronous publish-subscribe event bus.

    Usage::

        bus = EventBus()
        bus.subscribe(VehicleSpawned, my_handler)
        bus.publish(VehicleSpawned(tick=1, vehicle_id="V-1", ...))
    """

    def __init__(self) -> None:
        self._handlers: dict[type, list[EventHandler]] = defaultdict(list)

    def subscribe(
        self, event_type: type[SimulationEvent], handler: EventHandler
    ) -> None:
        """Register a handler for a specific event type."""
        self._handlers[event_type].append(handler)

    def unsubscribe(
        self, event_type: type[SimulationEvent], handler: EventHandler
    ) -> None:
        """Remove a previously registered handler."""
        self._handlers[event_type].remove(handler)

    def publish(self, event: SimulationEvent) -> None:
        """Dispatch an event to all registered handlers for its type."""
        for handler in self._handlers.get(type(event), []):
            handler(event)

    def clear(self) -> None:
        """Remove all handlers."""
        self._handlers.clear()
