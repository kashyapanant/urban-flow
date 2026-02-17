"""Emergency router -- computes optimal paths for emergency vehicles.

Uses the RoadNetwork's shortest_path (BFS) initially.  Can be extended
to use weighted shortest path (Dijkstra) considering current traffic
congestion in later phases.
"""

from __future__ import annotations

from dataclasses import dataclass

from urban_flow.core.grid import RoadNetwork
from urban_flow.core.types import IntersectionId
from urban_flow.core.vehicle import EmergencyVehicle


@dataclass(frozen=True)
class Route:
    """A computed route for an emergency vehicle."""

    vehicle_id: str
    path: list[IntersectionId]

    @property
    def length(self) -> int:
        """Number of intersections in the route."""
        return len(self.path)


class EmergencyRouter:
    """Computes routes for emergency vehicles through the network."""

    def __init__(self, network: RoadNetwork) -> None:
        self._network = network

    def compute_route(self, vehicle: EmergencyVehicle) -> Route:
        """Compute the shortest route from current position to destination."""
        origin = vehicle.origin
        if vehicle.next_intersection:
            origin = vehicle.next_intersection

        path = self._network.shortest_path(origin, vehicle.destination)
        return Route(vehicle_id=vehicle.vehicle_id, path=path)
