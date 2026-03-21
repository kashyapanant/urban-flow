"""Grid world model for the traffic simulation."""

from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from backend.config import MAX_GRID_SIZE, MIN_GRID_SIZE, STREET_SPACING

if TYPE_CHECKING:
    from .traffic_light import TrafficLight
    from .vehicle import Vehicle

logger = logging.getLogger(__name__)


def _component_id(component: Any | None) -> str | None:
    """Resolve a JSON-safe id string from an object that exposes ``id``.

    Returns ``None`` when ``component`` is ``None`` or ``id`` is missing.
    Otherwise returns ``str(id)`` so values are always JSON-serializable.
    """
    if component is None:
        return None
    ident = getattr(component, "id", None)
    if ident is None:
        return None
    return str(ident)


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
        """Serialize this cell for API/WebSocket payloads.

        The mapping always includes the same keys so consumers can read a
        uniform shape: ``x``, ``y``, ``type``, ``vehicle_id``, and
        ``traffic_light_id``. ``type`` is the string :attr:`CellType.value`.
        Occupant fields use ``None`` when there is no vehicle or traffic light
        in the cell.

        References are not embedded as nested objects: only ``vehicle_id`` and
        ``traffic_light_id`` are set (via :func:`_component_id`), matching how
        the simulation engine exposes full vehicle and light records in
        separate top-level snapshot lists.

        Returns:
            A JSON-serializable dict describing this cell.
        """
        return {
            "x": self.x,
            "y": self.y,
            "type": self.type.value,
            "vehicle_id": _component_id(self.vehicle),
            "traffic_light_id": _component_id(self.traffic_light),
        }


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

        Only the four cardinal directions are considered — no diagonals.
        A neighbour is included only if it exists within the grid bounds
        and its cell type is not OBSTACLE (i.e. ``Cell.is_traversable()``
        returns True).

        Args:
            x: Column coordinate of the source cell.
            y: Row coordinate of the source cell.

        Returns:
            List of traversable neighbouring cells. Empty if the source
            coordinates are out of bounds or all neighbours are obstacles.
        """
        # Validate source coordinates first — return empty list immediately if
        # (x, y) is outside the grid, matching the documented contract.
        if self.get_cell(x, y) is None:
            return []

        neighbors: list[Cell] = []
        # Each (dx, dy) is a cardinal direction offset:
        #   (0, -1) up  |  (0, +1) down  |  (-1, 0) left  |  (+1, 0) right
        # get_cell() returns None for out-of-bounds coordinates, so no
        # separate bounds check is needed for the neighbours themselves.
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            cell = self.get_cell(x + dx, y + dy)
            if cell is not None and cell.is_traversable():
                neighbors.append(cell)
        return neighbors

    def is_traversable(self, x: int, y: int) -> bool:
        """Check if the cell at (x, y) can be traversed by vehicles.

        Convenience wrapper around ``Cell.is_traversable()``. Returns False
        for out-of-bounds coordinates.

        Args:
            x: Column coordinate
            y: Row coordinate

        Returns:
            True if vehicles can move through this cell
        """
        cell = self.get_cell(x, y)
        return cell is not None and cell.is_traversable()

    def is_occupied(self, x: int, y: int) -> bool:
        """Check if the cell at (x, y) is occupied by a vehicle.

        Convenience wrapper around ``Cell.is_occupied()``. Returns False
        for out-of-bounds coordinates.

        Args:
            x: Column coordinate
            y: Row coordinate

        Returns:
            True if a vehicle is currently in this cell
        """
        cell = self.get_cell(x, y)
        return cell is not None and cell.is_occupied()

    def place_vehicle(self, vehicle: Vehicle, x: int, y: int) -> bool:
        """Place a vehicle in the specified cell.

        Placement fails (returns False) if any of these conditions hold:
        - ``vehicle`` is None.
        - (x, y) is outside the grid bounds.
        - The cell is not traversable (OBSTACLE).
        - The cell is already occupied by another vehicle.

        Args:
            vehicle: The vehicle to place. Must not be None.
            x: Column coordinate of the target cell.
            y: Row coordinate of the target cell.

        Returns:
            True if the vehicle was placed successfully, False otherwise.
        """
        if vehicle is None:
            return False
        cell = self.get_cell(x, y)
        if cell is None or not cell.is_traversable() or cell.is_occupied():
            return False
        cell.vehicle = vehicle
        return True

    def remove_vehicle(self, x: int, y: int) -> Vehicle | None:
        """Remove and return the vehicle from the specified cell.

        If the coordinates are out of bounds or the cell contains no vehicle,
        the grid is left unchanged and None is returned.

        Args:
            x: Column coordinate.
            y: Row coordinate.

        Returns:
            The vehicle that was occupying the cell, or None if the cell was
            empty, did not exist, or was out of bounds.
        """
        cell = self.get_cell(x, y)
        if cell is None or cell.vehicle is None:
            return None
        vehicle = cell.vehicle
        cell.vehicle = None
        return vehicle

    def get_edge_cells(self) -> list[Cell]:
        """Get all traversable cells on the grid edges for vehicle spawning.

        Collects every cell on the four perimeter edges (top row, bottom row,
        left column, right column), deduplicates corner cells, and filters to
        only those that are traversable (ROAD or INTERSECTION).  The returned
        list is ordered top-row → bottom-row → left-column → right-column,
        with corners belonging to the row passes only.

        Returns:
            List of traversable perimeter cells, in reading order around the
            border.  Empty if no perimeter cell is traversable (e.g. a 1×1
            grid whose single OBSTACLE cell sits on every edge).
        """
        edges = [
            [self.cells[0][x] for x in range(self.width)],
            [self.cells[self.height - 1][x] for x in range(self.width)],
            [self.cells[y][0] for y in range(self.height)],
            [self.cells[y][self.width - 1] for y in range(self.height)],
        ]

        seen: set[tuple[int, int]] = set()
        edge_cells: list[Cell] = []
        for cell in itertools.chain.from_iterable(edges):
            if (cell.x, cell.y) not in seen:
                seen.add((cell.x, cell.y))
                if cell.is_traversable():
                    edge_cells.append(cell)

        return edge_cells

    def get_intersection_cells(self) -> list[Cell]:
        """Get all intersection cells for traffic light placement.

        Iterates the grid in row-major order and collects every cell whose
        type is INTERSECTION (i.e. cells that lie on both an avenue column
        and a street row).

        Returns:
            List of all INTERSECTION cells in row-major order (top-left to
            bottom-right).  Empty if the grid contains no intersections.
        """
        return [
            self.cells[y][x]
            for y in range(self.height)
            for x in range(self.width)
            if self.cells[y][x].type is CellType.INTERSECTION
        ]

    def snapshot(self) -> dict[str, Any]:
        """Create a serializable snapshot of the entire grid.

        The returned dict has three keys:

        - ``width`` / ``height``: grid dimensions (same as :attr:`width` /
          :attr:`height`).
        - ``cells``: nested list in **row-major** order — outer index is row
          ``y``, inner index is column ``x``. ``cells[y][x]`` is the dict from
          :meth:`Cell.to_dict` for :attr:`cells` ``[y][x]``, aligned with
          internal storage.

        Returns:
            A JSON-serializable dict suitable for WebSocket/API ``grid`` payloads.
        """
        return {
            "width": self.width,
            "height": self.height,
            "cells": [[cell.to_dict() for cell in row] for row in self.cells],
        }
