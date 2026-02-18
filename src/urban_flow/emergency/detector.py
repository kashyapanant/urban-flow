"""Emergency vehicle detector -- monitors the network for approaching emergency vehicles.

This module will be implemented in Phase 3.  The detector scans vehicles each
tick and emits EmergencyDetected events when an emergency vehicle is within
a configurable distance of an intersection.
"""

from __future__ import annotations

from urban_flow.core.grid import RoadNetwork
from urban_flow.core.vehicle import EmergencyVehicle
from urban_flow.engine.events import EmergencyDetected, EventBus


class EmergencyDetector:
    """Scans the road network for emergency vehicles approaching intersections.

    When an emergency vehicle is within ``detection_range`` cells of an
    intersection, an ``EmergencyDetected`` event is published.
    """

    def __init__(
        self,
        network: RoadNetwork,
        event_bus: EventBus,
        detection_range: int = 20,
    ) -> None:
        self._network = network
        self._event_bus = event_bus
        self._detection_range = detection_range

    def scan(
        self, tick: int, emergency_vehicles: list[EmergencyVehicle]
    ) -> None:
        """Check all emergency vehicles and emit detection events.

        To be implemented in Phase 3.
        """
        # TODO(phase-3): Iterate emergency vehicles, check distance to next
        # intersection on their route, and emit EmergencyDetected events.
        pass
