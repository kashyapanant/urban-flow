"""Grid world model for the traffic simulation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .traffic_light import TrafficLight
    from .vehicle import Vehicle


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
        """Check if vehicles can move through this cell."""
        raise NotImplementedError("Cell.is_traversable() not yet implemented")

    def is_occupied(self) -> bool:
        """Check if this cell is currently occupied by a vehicle."""
        raise NotImplementedError("Cell.is_occupied() not yet implemented")

    def to_dict(self) -> dict[str, Any]:
        """Convert cell to dictionary for serialization."""
        raise NotImplementedError("Cell.to_dict() serialization not yet implemented")


class Grid:
    """The simulation world as a 2D grid of cells.

    Implements the "city blocks" pattern with streets at specific
    rows/columns and intersections where they cross.
    """

    def __init__(self, width: int = 10, height: int = 10):
        """Initialize the grid with the city blocks layout.
        
        Args:
            width: Number of columns (default 10)
            height: Number of rows (default 10)
        """
        raise NotImplementedError("Grid.__init__() city blocks layout generation not yet implemented")

    def get_cell(self, x: int, y: int) -> Cell | None:
        """Get the cell at the specified coordinates.
        
        Args:
            x: Column coordinate
            y: Row coordinate
            
        Returns:
            The cell at (x, y) or None if coordinates are invalid
        """
        raise NotImplementedError("Grid.get_cell() coordinate lookup not yet implemented")

    def get_neighbors(self, x: int, y: int) -> list[Cell]:
        """Get traversable neighboring cells (up, down, left, right).
        
        Args:
            x: Column coordinate
            y: Row coordinate
            
        Returns:
            List of neighboring cells that vehicles can move to
        """
        raise NotImplementedError("Grid.get_neighbors() neighbor lookup not yet implemented")

    def is_traversable(self, x: int, y: int) -> bool:
        """Check if the cell at (x, y) can be traversed by vehicles.
        
        Args:
            x: Column coordinate
            y: Row coordinate
            
        Returns:
            True if vehicles can move through this cell
        """
        raise NotImplementedError("Grid.is_traversable() traversability check not yet implemented")

    def is_occupied(self, x: int, y: int) -> bool:
        """Check if the cell at (x, y) is occupied by a vehicle.
        
        Args:
            x: Column coordinate
            y: Row coordinate
            
        Returns:
            True if a vehicle is currently in this cell
        """
        raise NotImplementedError("Grid.is_occupied() occupancy check not yet implemented")

    def place_vehicle(self, vehicle: Vehicle, x: int, y: int) -> bool:
        """Place a vehicle in the specified cell.
        
        Args:
            vehicle: The vehicle to place
            x: Column coordinate
            y: Row coordinate
            
        Returns:
            True if placement was successful, False otherwise
        """
        raise NotImplementedError("Grid.place_vehicle() vehicle placement logic not yet implemented")

    def remove_vehicle(self, x: int, y: int) -> Vehicle | None:
        """Remove and return the vehicle from the specified cell.
        
        Args:
            x: Column coordinate
            y: Row coordinate
            
        Returns:
            The removed vehicle or None if no vehicle was present
        """
        raise NotImplementedError("Grid.remove_vehicle() vehicle removal logic not yet implemented")

    def get_edge_cells(self) -> list[Cell]:
        """Get all traversable cells on the grid edges for vehicle spawning.
        
        Returns:
            List of cells on the perimeter that vehicles can spawn in
        """
        raise NotImplementedError("Grid.get_edge_cells() edge cell identification not yet implemented")

    def get_intersection_cells(self) -> list[Cell]:
        """Get all intersection cells for traffic light placement.
        
        Returns:
            List of all intersection cells in the grid
        """
        raise NotImplementedError("Grid.get_intersection_cells() intersection identification not yet implemented")

    def snapshot(self) -> dict[str, Any]:
        """Create a serializable snapshot of the grid state.
        
        Returns:
            Dictionary representation of the grid for frontend
        """
        raise NotImplementedError("Grid.snapshot() state serialization not yet implemented")
