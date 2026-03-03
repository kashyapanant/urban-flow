"""A* pathfinding algorithm for vehicle navigation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .grid import Grid
from .vehicle import VehicleType

if TYPE_CHECKING:
    from .traffic_light import TrafficLightManager


@dataclass
class PathNode:
    """A node in the A* search algorithm.

    Represents a position with costs and parent reference for path reconstruction.
    """

    position: tuple[int, int]
    g_cost: float  # Cost from start
    h_cost: float  # Heuristic cost to goal
    parent: PathNode | None = None

    @property
    def f_cost(self) -> float:
        """Total cost (g + h) for A* priority."""
        raise NotImplementedError("PathNode.f_cost calculation")

    def __lt__(self, other: PathNode) -> bool:
        """Comparison for priority queue (lower f_cost = higher priority)."""
        raise NotImplementedError("PathNode.__lt__ comparison")


class Pathfinder:
    """A* pathfinding implementation for vehicle navigation.

    Supports both shortest path (normal vehicles) and fastest path
    (emergency vehicles considering traffic light states).
    """

    @staticmethod
    def find_path(
        grid: Grid,
        start: tuple[int, int],
        goal: tuple[int, int],
        vehicle_type: VehicleType,
        traffic_light_manager: TrafficLightManager | None = None,
    ) -> list[tuple[int, int]] | None:
        """Find optimal path from start to goal using A*.

        Args:
            grid: The simulation grid
            start: Starting position (x, y)
            goal: Goal position (x, y)
            vehicle_type: Type of vehicle for cost calculation
            traffic_light_manager: For emergency vehicle traffic light costs

        Returns:
            List of positions forming the path, or None if no path exists
        """
        raise NotImplementedError("Pathfinder.find_path() A* algorithm")
