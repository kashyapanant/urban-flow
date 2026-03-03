"""Traffic light system for intersection control and emergency preemption."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .vehicle import Vehicle


class Axis(Enum):
    """Traffic light axes for intersection control."""

    NS = "north_south"  # North-South axis
    EW = "east_west"  # East-West axis


class Phase(Enum):
    """Traffic light phases within an axis cycle."""

    GREEN = "green"
    LEFT_TURN = "leftTurn"
    YELLOW = "yellow"
    RED = "red"


@dataclass
class TrafficLight:
    """A traffic light at an intersection.

    Each intersection has a dual-axis traffic light that cycles through
    four phases per axis. Only one axis is active at a time.
    """

    id: str
    position: tuple[int, int]
    active_axis: Axis
    current_phase: Phase
    phase_duration: int
    ticks_in_phase: int = 0
    preempted_by: Vehicle | None = None

    def tick(self) -> None:
        """Advance the traffic light by one tick.

        Handles normal phase progression and preemption transitions.
        """
        raise NotImplementedError("TrafficLight.tick(")

    def can_enter(self, direction: str) -> bool:
        """Check if a vehicle can enter from the given direction.

        Args:
            direction: Movement direction ("north", "south", "east", "west")

        Returns:
            True if vehicle can proceed through intersection
        """
        raise NotImplementedError("TrafficLight.can_enter(")

    def request_preemption(
        self, vehicle: Vehicle, preemption_yellow_duration: int
    ) -> bool:
        """Request emergency preemption for a vehicle.

        Args:
            vehicle: Emergency vehicle requesting preemption
            preemption_yellow_duration: Ticks for yellow transition

        Returns:
            True if preemption was granted
        """
        raise NotImplementedError("TrafficLight.request_preemption(")

    def release_preemption(self) -> None:
        """Release emergency preemption and return to normal cycling."""
        raise NotImplementedError("TrafficLight.release_preemption(")

    def to_dict(self) -> dict[str, Any]:
        """Convert traffic light to dictionary for serialization.

        Returns:
            Dictionary representation for frontend
        """
        raise NotImplementedError("TrafficLight.to_dict(")


class TrafficLightManager:
    """Manages all traffic lights in the simulation.

    Handles traffic light updates, preemption requests, and movement permissions.
    """

    def __init__(self, intersections: list[tuple[int, int]], phase_duration: int = 3):
        """Initialize traffic lights at all intersections.

        Args:
            intersections: List of (x, y) coordinates for intersections
            phase_duration: Default ticks per phase
        """
        raise NotImplementedError("TrafficLightManager.__init__()")

    def tick(self) -> None:
        """Advance all traffic lights by one tick."""
        raise NotImplementedError("TrafficLightManager.tick(")

    def request_preemption(
        self,
        position: tuple[int, int],
        vehicle: Vehicle,
        preemption_yellow_duration: int,
    ) -> bool:
        """Request emergency preemption at an intersection.

        Args:
            position: Intersection coordinates
            vehicle: Emergency vehicle requesting preemption
            preemption_yellow_duration: Ticks for yellow transition

        Returns:
            True if preemption was granted
        """
        raise NotImplementedError("TrafficLightManager.request_preemption(")

    def release_preemption(self, position: tuple[int, int]) -> None:
        """Release emergency preemption at an intersection.

        Args:
            position: Intersection coordinates
        """
        raise NotImplementedError("TrafficLightManager.release_preemption(")

    def can_vehicle_enter(self, position: tuple[int, int], direction: str) -> bool:
        """Check if a vehicle can enter an intersection.

        Args:
            position: Intersection coordinates
            direction: Vehicle movement direction

        Returns:
            True if vehicle can proceed
        """
        raise NotImplementedError("TrafficLightManager.can_vehicle_enter(")

    def get_light(self, position: tuple[int, int]) -> TrafficLight | None:
        """Get the traffic light at a specific position.

        Args:
            position: Intersection coordinates

        Returns:
            TrafficLight or None if no light exists
        """
        raise NotImplementedError("TrafficLightManager.get_light(")

    def get_all(self) -> list[TrafficLight]:
        """Get all traffic lights.

        Returns:
            List of all traffic lights in the simulation
        """
        raise NotImplementedError("TrafficLightManager.get_all(")

    def set_phase_duration(self, duration: int) -> None:
        """Update phase duration for all traffic lights.

        Args:
            duration: New phase duration in ticks
        """
        raise NotImplementedError("TrafficLightManager.set_phase_duration(")

    def snapshot(self) -> list[dict[str, Any]]:
        """Create a serializable snapshot of all traffic lights.

        Returns:
            List of traffic light dictionaries for frontend
        """
        raise NotImplementedError("TrafficLightManager.snapshot(")
