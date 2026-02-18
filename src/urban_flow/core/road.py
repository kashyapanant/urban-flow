"""Road — a directed edge between two intersections.

A road is divided into discrete *cells*.  Each cell can hold at most one
vehicle, implementing a simplified cellular-automaton traffic model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from urban_flow.core.types import IntersectionId, RoadId

if TYPE_CHECKING:
    from urban_flow.core.vehicle import Vehicle


@dataclass
class Cell:
    """A single cell on a road.  Either empty or occupied by one vehicle."""

    index: int
    vehicle: Vehicle | None = None

    @property
    def is_empty(self) -> bool:
        return self.vehicle is None


@dataclass
class Road:
    """Directed road segment connecting two intersections.

    Parameters
    ----------
    road_id:
        Unique identifier for this road.
    from_intersection:
        ID of the source intersection.
    to_intersection:
        ID of the destination intersection.
    num_cells:
        Number of discrete cells (determines road length).
    speed_limit:
        Maximum cells a vehicle can advance per tick (default 1).
    """

    road_id: RoadId
    from_intersection: IntersectionId
    to_intersection: IntersectionId
    num_cells: int
    speed_limit: int = 1
    cells: list[Cell] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if not self.cells:
            self.cells = [Cell(index=i) for i in range(self.num_cells)]

    @property
    def vehicles(self) -> list[Vehicle]:
        """Return all vehicles currently on this road, front to back."""
        return [c.vehicle for c in self.cells if c.vehicle is not None]

    @property
    def occupancy(self) -> float:
        """Fraction of cells occupied (0.0 – 1.0)."""
        if self.num_cells == 0:
            return 0.0
        return sum(1 for c in self.cells if not c.is_empty) / self.num_cells

    @property
    def is_full(self) -> bool:
        return all(not c.is_empty for c in self.cells)

    def cell_at(self, index: int) -> Cell:
        return self.cells[index]

    def clear(self) -> None:
        """Remove all vehicles from the road."""
        for cell in self.cells:
            cell.vehicle = None
