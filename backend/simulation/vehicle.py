"""Vehicle entities and management for the traffic simulation."""

from __future__ import annotations

import random
import uuid
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

    def _validate_path_state(self) -> None:
        """Validate internal path/index state before route operations.

        Raises:
            ValueError: If the path is empty, path_index is out of range,
                path endpoints do not match origin/destination, or the current
                position does not match ``path[path_index]``.
        """
        if not self.path:
            raise ValueError(f"Vehicle {self.id} has an empty path.")
        if not (0 <= self.path_index < len(self.path)):
            raise ValueError(
                f"Vehicle {self.id} has invalid path_index {self.path_index}; "
                f"expected 0 <= path_index < {len(self.path)}."
            )
        if self.path[0] != self.origin:
            raise ValueError(
                f"Vehicle {self.id} path must start at origin {self.origin}; "
                f"got {self.path[0]}."
            )
        if self.path[-1] != self.destination:
            raise ValueError(
                f"Vehicle {self.id} path must end at destination "
                f"{self.destination}; got {self.path[-1]}."
            )
        if self.path[self.path_index] != self.position:
            raise ValueError(
                f"Vehicle {self.id} position/path mismatch: "
                f"position={self.position}, path[{self.path_index}]="
                f"{self.path[self.path_index]}."
            )

    def get_next_position(self) -> tuple[int, int] | None:
        """Get the next position on the vehicle's path.

        The path is an ordered list from origin to destination and includes the
        current position at ``path[path_index]``. This method returns the next
        cell after the current index, or ``None`` when the vehicle is already at
        the final path cell (destination).

        Returns:
            Next (x, y) coordinates, or ``None`` if no further path cell exists.

        Raises:
            ValueError: If ``path``/``path_index``/``position`` are inconsistent.
        """
        self._validate_path_state()

        next_index = self.path_index + 1
        if next_index >= len(self.path):
            return None
        return self.path[next_index]

    def advance_path(self) -> None:
        """Advance one step along the precomputed path.

        If a next path cell exists, the vehicle moves to that cell and
        ``path_index`` increments by one. If the vehicle is already at the end
        of the path, this is a no-op for position/index.

        ``status`` is synchronized after the operation:
        - ``ARRIVED`` when the vehicle is at the destination (end of path)
        - ``MOVING`` otherwise

        Raises:
            ValueError: If ``path``/``path_index``/``position`` are inconsistent.
        """
        next_position = self.get_next_position()
        if next_position is not None:
            self.path_index += 1
            self.position = next_position

        self.status = (
            VehicleStatus.ARRIVED
            if self.path_index == len(self.path) - 1
            else VehicleStatus.MOVING
        )

    def get_remaining_distance(self) -> int:
        """Get the number of cells remaining to destination.

        Remaining distance counts *steps* from the current path index to the
        final path index (destination), so a vehicle already at destination
        returns ``0``.

        Returns:
            Number of path steps remaining to destination.

        Raises:
            ValueError: If ``path``/``path_index``/``position`` are inconsistent.
        """
        self._validate_path_state()
        return len(self.path) - self.path_index - 1

    def to_dict(self) -> dict[str, Any]:
        """Convert vehicle to dictionary for serialization.

        The returned mapping always includes these keys (in this order):
        ``id``, ``type``, ``position``, ``origin``, ``destination``, ``path``,
        ``path_index``, ``status``, ``ticks_elapsed``, ``next_position``,
        ``remaining_distance``.

        ``type`` and ``status`` are enum value strings. Coordinates remain
        ``(x, y)`` tuples in Python and become JSON arrays when encoded.
        ``next_position`` is ``None`` when the vehicle is already at the final
        path cell (destination). For payload consistency, terminal path state
        (``next_position`` is ``None`` and ``remaining_distance`` is ``0``)
        serializes status as ``arrived`` even if the in-memory status has not
        yet been synchronized. ``path`` is returned as a shallow copy so
        serialization does not expose the internal mutable route list.

        Returns:
            JSON-serializable vehicle payload for snapshots/API responses.

        Raises:
            ValueError: If ``path``/``path_index``/``position`` are inconsistent.
        """
        next_position = self.get_next_position()
        remaining_distance = self.get_remaining_distance()
        serialized_status = self.status.value
        if remaining_distance == 0 and next_position is None:
            serialized_status = VehicleStatus.ARRIVED.value

        return {
            "id": self.id,
            "type": self.type.value,
            "position": self.position,
            "origin": self.origin,
            "destination": self.destination,
            "path": list(self.path),
            "path_index": self.path_index,
            "status": serialized_status,
            "ticks_elapsed": self.ticks_elapsed,
            "next_position": next_position,
            "remaining_distance": remaining_distance,
        }


class VehicleManager:
    """Manages the collection of active vehicles in the simulation.

    Handles vehicle spawning, movement, priority ordering, and cleanup.
    """

    def __init__(self):
        """Initialize manager state for active vehicle lifecycle.

        The manager keeps a single source-of-truth list for all vehicles that
        are currently active in the simulation. Vehicles are added when
        successfully spawned and removed once collected after arrival.

        Attributes initialized:
            _vehicles: Active vehicles in insertion order.
        """
        self._vehicles: list[Vehicle] = []

    def spawn_vehicles(
        self,
        grid: Grid,
        spawn_rate: float,
        emergency_probability: float,
        max_retries: int,
        traffic_light_manager: TrafficLightManager | None = None,
    ) -> list[Vehicle]:
        """Spawn new vehicles at grid edges.

        For each traversable edge cell, this method performs a spawn roll using
        ``spawn_rate``. On success, it chooses a destination on a different edge
        cell and attempts pathfinding (up to ``max_retries``). Vehicles are
        placed on the grid and added to the active manager list only when a
        valid path is found and placement succeeds.

        Args:
            grid: The simulation grid
            spawn_rate: Probability of spawning per edge cell per tick
            emergency_probability: Probability that spawned vehicle is emergency
            max_retries: Maximum attempts to find valid origin/destination pair
            traffic_light_manager: For emergency vehicle pathfinding

        Returns:
            List of newly spawned vehicles

        Raises:
            ValueError: If ``spawn_rate`` or ``emergency_probability`` is
                outside ``[0.0, 1.0]``, or if ``max_retries`` is less than 1.
        """
        if not 0.0 <= spawn_rate <= 1.0:
            raise ValueError(f"spawn_rate must be in [0.0, 1.0], got {spawn_rate}.")
        if not 0.0 <= emergency_probability <= 1.0:
            raise ValueError(
                "emergency_probability must be in [0.0, 1.0], "
                f"got {emergency_probability}."
            )
        if max_retries < 1:
            raise ValueError(f"max_retries must be >= 1, got {max_retries}.")

        # Local import avoids module import cycle: pathfinder imports VehicleType.
        from .pathfinder import Pathfinder

        edge_cells = grid.get_edge_cells()
        if not edge_cells:
            return []

        edge_positions = [(cell.x, cell.y) for cell in edge_cells]
        spawned: list[Vehicle] = []

        for origin_cell in edge_cells:
            if origin_cell.is_occupied():
                continue
            if random.random() >= spawn_rate:
                continue

            origin = (origin_cell.x, origin_cell.y)
            destination_candidates = [pos for pos in edge_positions if pos != origin]
            if not destination_candidates:
                continue

            vehicle_type = (
                VehicleType.EMERGENCY
                if random.random() < emergency_probability
                else VehicleType.NORMAL
            )

            destination: tuple[int, int] | None = None
            path: list[tuple[int, int]] | None = None
            retry_destinations = random.sample(
                destination_candidates,
                k=min(max_retries, len(destination_candidates)),
            )
            for candidate_destination in retry_destinations:
                candidate_path = Pathfinder.find_path(
                    grid=grid,
                    start=origin,
                    goal=candidate_destination,
                    vehicle_type=vehicle_type,
                    traffic_light_manager=traffic_light_manager,
                )
                if candidate_path is None:
                    continue
                if not candidate_path:
                    continue
                if (
                    candidate_path[0] != origin
                    or candidate_path[-1] != candidate_destination
                ):
                    continue

                destination = candidate_destination
                path = candidate_path
                break

            if destination is None or path is None:
                continue

            vehicle = Vehicle(
                id=uuid.uuid4().hex,
                type=vehicle_type,
                position=origin,
                origin=origin,
                destination=destination,
                path=path,
            )
            if not grid.place_vehicle(vehicle, *origin):
                continue

            self._vehicles.append(vehicle)
            spawned.append(vehicle)

        return spawned

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
        raise NotImplementedError("VehicleManager.move_vehicles(")

    def collect_arrived(self) -> list[Vehicle]:
        """Remove and return vehicles that have reached their destination.

        Vehicles are collected in their current active-list order. Vehicles that
        are not yet arrived remain active in the same relative order.

        Returns:
            List of vehicles that completed their journey
        """
        arrived: list[Vehicle] = []
        remaining: list[Vehicle] = []
        for vehicle in self._vehicles:
            if vehicle.status is VehicleStatus.ARRIVED:
                arrived.append(vehicle)
            else:
                remaining.append(vehicle)

        if not arrived:
            return []

        self._vehicles = remaining
        return arrived

    def get_all(self) -> list[Vehicle]:
        """Get all active vehicles.

        Returns:
            List of all vehicles currently in the simulation
        """
        raise NotImplementedError("VehicleManager.get_all(")

    def get_emergency_vehicles(self) -> list[Vehicle]:
        """Get all active emergency vehicles.

        Returns:
            List of emergency vehicles currently in the simulation
        """
        raise NotImplementedError("VehicleManager.get_emergency_vehicles(")

    def snapshot(self) -> list[dict[str, Any]]:
        """Create a serializable snapshot of all vehicles.

        Returns:
            List of vehicle dictionaries for frontend
        """
        raise NotImplementedError("VehicleManager.snapshot(")
