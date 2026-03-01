"""Vehicle entities and management for the traffic simulation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from .grid import Grid

if TYPE_CHECKING:
    from .traffic_light import TrafficLightManager


class VehicleType(Enum):
    """Types of vehicles in the simulation."""

    NORMAL = "normal"
    EMERGENCY = "emergency"


class VehicleStatus(Enum):
    """Current status of a vehicle."""

    MOVING = "moving"
    WAITING = "waiting"
    ARRIVED = "arrived"


@dataclass
class Vehicle:
    """A vehicle entity in the simulation.

    Each vehicle has a unique ID, type, position, path, and status.
    The path is pre-computed at spawn time and not modified during movement.
    """

    id: str
    type: VehicleType
    position: tuple[int, int]
    origin: tuple[int, int]
    destination: tuple[int, int]
    path: list[tuple[int, int]]
    path_index: int = 0
    status: VehicleStatus = VehicleStatus.MOVING
    ticks_elapsed: int = 0

    def get_next_position(self) -> tuple[int, int] | None:
        """Get the next position on the vehicle's path.

        Returns:
            Next (x, y) coordinates or None if at destination
        """
        pass

    def advance_path(self) -> None:
        """Move to the next position in the path."""
        pass

    def get_remaining_distance(self) -> int:
        """Get the number of cells remaining to destination.

        Returns:
            Number of path cells remaining
        """
        pass

    def to_dict(self) -> dict[str, Any]:
        """Convert vehicle to dictionary for serialization.

        Returns:
            Dictionary representation for frontend
        """
        pass


class VehicleManager:
    """Manages the collection of active vehicles in the simulation.

    Handles vehicle spawning, movement, priority ordering, and cleanup.
    """

    def __init__(self):
        """Initialize the vehicle manager."""
        pass

    def spawn_vehicles(
        self,
        grid: Grid,
        spawn_rate: float,
        emergency_probability: float,
        max_retries: int,
        traffic_light_manager: TrafficLightManager | None = None,
    ) -> list[Vehicle]:
        """Spawn new vehicles at grid edges.

        Args:
            grid: The simulation grid
            spawn_rate: Probability of spawning per edge cell per tick
            emergency_probability: Probability that spawned vehicle is emergency
            max_retries: Maximum attempts to find valid origin/destination pair
            traffic_light_manager: For emergency vehicle pathfinding

        Returns:
            List of newly spawned vehicles
        """
        pass

    def move_vehicles(
        self, grid: Grid, traffic_light_manager: TrafficLightManager
    ) -> None:
        """Move all vehicles one step along their paths.

        Vehicles are processed in priority order: emergency first, then by
        remaining distance (shortest first), then random tiebreak.

        Args:
            grid: The simulation grid
            traffic_light_manager: For traffic light permission checks
        """
        pass

    def collect_arrived(self) -> list[Vehicle]:
        """Remove and return vehicles that have reached their destination.

        Returns:
            List of vehicles that completed their journey
        """
        pass

    def get_all(self) -> list[Vehicle]:
        """Get all active vehicles.

        Returns:
            List of all vehicles currently in the simulation
        """
        pass

    def get_emergency_vehicles(self) -> list[Vehicle]:
        """Get all active emergency vehicles.

        Returns:
            List of emergency vehicles currently in the simulation
        """
        pass

    def snapshot(self) -> list[dict[str, Any]]:
        """Create a serializable snapshot of all vehicles.

        Returns:
            List of vehicle dictionaries for frontend
        """
        pass
