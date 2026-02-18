"""RoadNetwork — the graph holding all intersections and roads.

The network is represented as an adjacency list.  Intersections are nodes
and roads are directed edges.  Helper methods create regular grid layouts
and compute shortest paths.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from urban_flow.core.intersection import Intersection
from urban_flow.core.road import Road
from urban_flow.core.types import Direction, IntersectionId, Position, RoadId


@dataclass
class RoadNetwork:
    """Graph of intersections connected by directed roads.

    Supports arbitrary topologies, but provides a convenience factory
    ``create_grid`` for regular rectangular grids.
    """

    intersections: dict[IntersectionId, Intersection] = field(default_factory=dict)
    roads: dict[RoadId, Road] = field(default_factory=dict)

    # Adjacency: intersection_id → list of (neighbor_id, road_id)
    _adjacency: dict[IntersectionId, list[tuple[IntersectionId, RoadId]]] = field(
        default_factory=dict, repr=False
    )

    # --- Mutation ----------------------------------------------------------

    def add_intersection(self, intersection: Intersection) -> None:
        self.intersections[intersection.intersection_id] = intersection
        self._adjacency.setdefault(intersection.intersection_id, [])

    def add_road(self, road: Road) -> None:
        self.roads[road.road_id] = road
        self._adjacency.setdefault(road.from_intersection, []).append(
            (road.to_intersection, road.road_id)
        )

    # --- Queries -----------------------------------------------------------

    def neighbors(self, intersection_id: IntersectionId) -> list[IntersectionId]:
        """Return IDs of intersections reachable in one hop."""
        return [nid for nid, _ in self._adjacency.get(intersection_id, [])]

    def road_between(
        self, from_id: IntersectionId, to_id: IntersectionId
    ) -> Road | None:
        """Return the road connecting two adjacent intersections, or None."""
        for nid, rid in self._adjacency.get(from_id, []):
            if nid == to_id:
                return self.roads[rid]
        return None

    def shortest_path(
        self, from_id: IntersectionId, to_id: IntersectionId
    ) -> list[IntersectionId]:
        """BFS shortest path (unweighted) returning list of intersection IDs.

        Returns an empty list if no path exists.
        """
        if from_id == to_id:
            return [from_id]

        visited: set[IntersectionId] = {from_id}
        queue: deque[list[IntersectionId]] = deque([[from_id]])

        while queue:
            path = queue.popleft()
            current = path[-1]
            for neighbor_id in self.neighbors(current):
                if neighbor_id in visited:
                    continue
                new_path = [*path, neighbor_id]
                if neighbor_id == to_id:
                    return new_path
                visited.add(neighbor_id)
                queue.append(new_path)

        return []

    # --- Factory -----------------------------------------------------------

    @classmethod
    def create_grid(
        cls,
        rows: int,
        cols: int,
        road_length: int = 10,
    ) -> RoadNetwork:
        """Create a regular rectangular grid of intersections.

        Intersections are named ``"I-{row}-{col}"``.
        Roads connect adjacent intersections in both directions.
        """
        network = cls()

        # Create intersections
        for r in range(rows):
            for c in range(cols):
                iid = f"I-{r}-{c}"
                network.add_intersection(
                    Intersection(intersection_id=iid, position=Position(r, c))
                )

        # Create bidirectional roads between adjacent intersections
        for r in range(rows):
            for c in range(cols):
                current = f"I-{r}-{c}"

                # Road going SOUTH (current → row+1)
                if r + 1 < rows:
                    south_id = f"I-{r + 1}-{c}"
                    south_road = Road(
                        road_id=f"R-{current}-S",
                        from_intersection=current,
                        to_intersection=south_id,
                        num_cells=road_length,
                    )
                    network.add_road(south_road)
                    network.intersections[current].outgoing_roads[Direction.SOUTH] = (
                        south_road.road_id
                    )
                    network.intersections[south_id].incoming_roads[Direction.NORTH] = (
                        south_road.road_id
                    )

                    # Road going NORTH (row+1 → current)
                    north_road = Road(
                        road_id=f"R-{south_id}-N",
                        from_intersection=south_id,
                        to_intersection=current,
                        num_cells=road_length,
                    )
                    network.add_road(north_road)
                    network.intersections[south_id].outgoing_roads[Direction.NORTH] = (
                        north_road.road_id
                    )
                    network.intersections[current].incoming_roads[Direction.SOUTH] = (
                        north_road.road_id
                    )

                # Road going EAST (current → col+1)
                if c + 1 < cols:
                    east_id = f"I-{r}-{c + 1}"
                    east_road = Road(
                        road_id=f"R-{current}-E",
                        from_intersection=current,
                        to_intersection=east_id,
                        num_cells=road_length,
                    )
                    network.add_road(east_road)
                    network.intersections[current].outgoing_roads[Direction.EAST] = (
                        east_road.road_id
                    )
                    network.intersections[east_id].incoming_roads[Direction.WEST] = (
                        east_road.road_id
                    )

                    # Road going WEST (col+1 → current)
                    west_road = Road(
                        road_id=f"R-{east_id}-W",
                        from_intersection=east_id,
                        to_intersection=current,
                        num_cells=road_length,
                    )
                    network.add_road(west_road)
                    network.intersections[east_id].outgoing_roads[Direction.WEST] = (
                        west_road.road_id
                    )
                    network.intersections[current].incoming_roads[Direction.EAST] = (
                        west_road.road_id
                    )

        return network
