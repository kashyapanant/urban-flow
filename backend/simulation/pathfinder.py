"""A* pathfinding algorithm for vehicle navigation."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from math import inf
from typing import TYPE_CHECKING, Any

from .grid import Cell, CellType, Grid
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
        return self.g_cost + self.h_cost

    def __lt__(self, other: PathNode) -> bool:
        """Comparison for priority queue (lower f_cost = higher priority)."""
        if not isinstance(other, PathNode):
            return NotImplemented
        return self.f_cost < other.f_cost


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
        start_cell = grid.get_cell(*start)
        goal_cell = grid.get_cell(*goal)

        if start_cell is None or goal_cell is None:
            return None
        if not start_cell.is_traversable() or not goal_cell.is_traversable():
            return None
        if start == goal:
            return [start]

        def heuristic(position: tuple[int, int]) -> float:
            """Compute Manhattan distance from position to the goal."""
            return float(abs(position[0] - goal[0]) + abs(position[1] - goal[1]))

        def _phase_value(phase: Any) -> str | None:
            """Normalize traffic phase enums/strings to a lowercase string."""
            if phase is None:
                return None
            value = getattr(phase, "value", phase)
            if value is None:
                return None
            return str(value).lower()

        is_emergency = vehicle_type is VehicleType.EMERGENCY
        get_light_fn = None
        if traffic_light_manager is not None:
            maybe_get_light = getattr(traffic_light_manager, "get_light", None)
            if callable(maybe_get_light):
                get_light_fn = maybe_get_light

        def movement_cost(cell: Cell) -> float:
            """Return movement cost for entering a neighbour cell."""
            base_cost = 1.0
            if not is_emergency:
                return base_cost
            if cell.type is not CellType.INTERSECTION:
                return base_cost

            light = None
            if get_light_fn is not None:
                try:
                    light = get_light_fn((cell.x, cell.y))
                except NotImplementedError:
                    light = None
            if light is None:
                light = cell.traffic_light

            phase = _phase_value(getattr(light, "current_phase", None))
            if phase == "red":
                return base_cost + 2.0
            if phase == "yellow":
                return base_cost + 1.0
            return base_cost

        open_heap: list[PathNode] = [
            PathNode(position=start, g_cost=0.0, h_cost=heuristic(start), parent=None)
        ]
        best_g_cost: dict[tuple[int, int], float] = {start: 0.0}
        closed: set[tuple[int, int]] = set()

        while open_heap:
            current = heapq.heappop(open_heap)

            if current.g_cost > best_g_cost.get(current.position, inf):
                continue

            if current.position == goal:
                path: list[tuple[int, int]] = []
                node: PathNode | None = current
                while node is not None:
                    path.append(node.position)
                    node = node.parent
                path.reverse()
                return path

            if current.position in closed:  # pragma: no cover
                continue
            closed.add(current.position)

            for neighbor in grid.get_neighbors(*current.position):
                neighbor_pos = (neighbor.x, neighbor.y)
                if neighbor_pos in closed:
                    continue

                tentative_g = current.g_cost + movement_cost(neighbor)
                if tentative_g >= best_g_cost.get(neighbor_pos, inf):
                    continue

                best_g_cost[neighbor_pos] = tentative_g
                heapq.heappush(
                    open_heap,
                    PathNode(
                        position=neighbor_pos,
                        g_cost=tentative_g,
                        h_cost=heuristic(neighbor_pos),
                        parent=current,
                    ),
                )

        return None
