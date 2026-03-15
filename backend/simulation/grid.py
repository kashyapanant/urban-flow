"""Grid world model for the traffic simulation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from backend.config import MAX_GRID_SIZE, MIN_GRID_SIZE, STREET_SPACING

if TYPE_CHECKING:
    from .traffic_light import TrafficLight
    from .vehicle import Vehicle

logger = logging.getLogger(__name__)


class CellType(Enum):
    """Types of cells in the simulation grid."""

    ROAD = "road"
    INTERSECTION = "intersection"
    OBSTACLE = "obstacle"


@dataclass
class Cell:
    """A single cell in the simulation grid.

    Each cell has coordinates, a type, and can optionally contain
    a vehicle and/or traffic light.
    """

    x: int
    y: int
    type: CellType
    vehicle: Vehicle | None = None  # Forward reference
    traffic_light: TrafficLight | None = None  # Forward reference

    def is_traversable(self) -> bool:
        """Check if vehicles can move through this cell.

        A cell is traversable if its type is ROAD or INTERSECTION.
        OBSTACLE cells (building interiors) block all movement.

        Returns:
            True if vehicles can enter and move through this cell.
        """
        return self.type is not CellType.OBSTACLE

    def is_occupied(self) -> bool:
        """Check if this cell is currently occupied by a vehicle.

        Returns:
            True if a vehicle reference is present in this cell.
        """
        return self.vehicle is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert cell to dictionary for serialization."""
        raise NotImplementedError("Cell.to_dict(")


class Grid:
    """The simulation world as a 2D grid of cells.

    Implements the "city blocks" pattern with streets at specific
    rows/columns and intersections where they cross.
    """

    def __init__(self, width: int = 10, height: int = 10):
        """Initialize the grid with the city blocks layout.

        Builds a 2D cell array (row-major: ``cells[y][x]``) where each cell
        is classified as INTERSECTION, ROAD, or OBSTACLE based on whether it
        sits at the crossing of an avenue column and a street row, on exactly
        one of those axes, or on neither.

        Streets run East–West at every row index that is a multiple of
        ``STREET_SPACING`` (e.g. rows 0, 3, 6, 9 for a 10-row grid).
        Avenues run North–South at every column index that is a multiple of
        ``STREET_SPACING``.

        Args:
            width: Number of columns. Must be between MIN_GRID_SIZE and
                MAX_GRID_SIZE (inclusive).
            height: Number of rows. Must be between MIN_GRID_SIZE and
                MAX_GRID_SIZE (inclusive).

        Raises:
            ValueError: If ``width`` or ``height`` is outside the allowed
                range [MIN_GRID_SIZE, MAX_GRID_SIZE].
        """
        if not (MIN_GRID_SIZE <= width <= MAX_GRID_SIZE):
            raise ValueError(
                f"Grid width must be between {MIN_GRID_SIZE} and {MAX_GRID_SIZE}, "
                f"got {width}."
            )
        if not (MIN_GRID_SIZE <= height <= MAX_GRID_SIZE):
            raise ValueError(
                f"Grid height must be between {MIN_GRID_SIZE} and {MAX_GRID_SIZE}, "
                f"got {height}."
            )

        self.width: int = width
        self.height: int = height

        # Avenue columns and street rows — every STREET_SPACING-th index from 0.
        self.avenue_cols: frozenset[int] = frozenset(range(0, width, STREET_SPACING))
        self.street_rows: frozenset[int] = frozenset(range(0, height, STREET_SPACING))

        # Build the 2D cell array row-major: cells[y][x].
        self.cells: list[list[Cell]] = [
            [self._make_cell(x, y) for x in range(width)] for y in range(height)
        ]

        logger.debug(
            "Grid initialised: %dx%d, %d avenues, %d streets, "
            "%d intersections, %d roads, %d obstacles.",
            width,
            height,
            len(self.avenue_cols),
            len(self.street_rows),
            sum(
                1
                for y in range(height)
                for x in range(width)
                if self.cells[y][x].type is CellType.INTERSECTION
            ),
            sum(
                1
                for y in range(height)
                for x in range(width)
                if self.cells[y][x].type is CellType.ROAD
            ),
            sum(
                1
                for y in range(height)
                for x in range(width)
                if self.cells[y][x].type is CellType.OBSTACLE
            ),
        )

    def _make_cell(self, x: int, y: int) -> Cell:
        """Classify and construct a single cell at (x, y).

        Args:
            x: Column coordinate.
            y: Row coordinate.

        Returns:
            A new Cell with the appropriate CellType.
        """
        on_avenue = x in self.avenue_cols
        on_street = y in self.street_rows

        if on_avenue and on_street:
            cell_type = CellType.INTERSECTION
        elif on_avenue or on_street:
            cell_type = CellType.ROAD
        else:
            cell_type = CellType.OBSTACLE

        return Cell(x=x, y=y, type=cell_type)

    def get_cell(self, x: int, y: int) -> Cell | None:
        """Get the cell at the specified coordinates.

        Args:
            x: Column coordinate (0-indexed, left to right).
            y: Row coordinate (0-indexed, top to bottom).

        Returns:
            The cell at (x, y), or None if the coordinates fall outside
            the grid bounds.
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.cells[y][x]
        return None

    def get_neighbors(self, x: int, y: int) -> list[Cell]:
        """Get traversable neighboring cells (up, down, left, right).

        Args:
            x: Column coordinate
            y: Row coordinate

        Returns:
            List of neighboring cells that vehicles can move to
        """
        raise NotImplementedError("Grid.get_neighbors(")

    def is_traversable(self, x: int, y: int) -> bool:
        """Check if the cell at (x, y) can be traversed by vehicles.

        Args:
            x: Column coordinate
            y: Row coordinate

        Returns:
            True if vehicles can move through this cell
        """
        raise NotImplementedError("Grid.is_traversable(")

    def is_occupied(self, x: int, y: int) -> bool:
        """Check if the cell at (x, y) is occupied by a vehicle.

        Args:
            x: Column coordinate
            y: Row coordinate

        Returns:
            True if a vehicle is currently in this cell
        """
        raise NotImplementedError("Grid.is_occupied(")

    def place_vehicle(self, vehicle: Vehicle, x: int, y: int) -> bool:
        """Place a vehicle in the specified cell.

        Args:
            vehicle: The vehicle to place
            x: Column coordinate
            y: Row coordinate

        Returns:
            True if placement was successful, False otherwise
        """
        raise NotImplementedError("Grid.place_vehicle(")

    def remove_vehicle(self, x: int, y: int) -> Vehicle | None:
        """Remove and return the vehicle from the specified cell.

        Args:
            x: Column coordinate
            y: Row coordinate

        Returns:
            The removed vehicle or None if no vehicle was present
        """
        raise NotImplementedError("Grid.remove_vehicle(")

    def get_edge_cells(self) -> list[Cell]:
        """Get all traversable cells on the grid edges for vehicle spawning.

        Returns:
            List of cells on the perimeter that vehicles can spawn in
        """
        raise NotImplementedError("Grid.get_edge_cells(")

    def get_intersection_cells(self) -> list[Cell]:
        """Get all intersection cells for traffic light placement.

        Returns:
            List of all intersection cells in the grid
        """
        raise NotImplementedError("Grid.get_intersection_cells(")

    def snapshot(self) -> dict[str, Any]:
        """Create a serializable snapshot of the grid state.

        Returns:
            Dictionary representation of the grid for frontend
        """
        raise NotImplementedError("Grid.snapshot(")
