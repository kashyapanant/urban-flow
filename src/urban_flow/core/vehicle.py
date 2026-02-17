"""Vehicle entities that move through the road network."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from urban_flow.core.types import (
    IntersectionId,
    Tick,
    VehicleId,
    VehicleType,
)

if TYPE_CHECKING:
    pass


@dataclass
class Vehicle:
    """A regular vehicle navigating from origin to destination.

    Parameters
    ----------
    vehicle_id:
        Unique identifier.
    origin:
        Intersection where the vehicle enters the network.
    destination:
        Intersection where the vehicle exits the network.
    vehicle_type:
        Classification (CAR by default).
    """

    vehicle_id: VehicleId
    origin: IntersectionId
    destination: IntersectionId
    vehicle_type: VehicleType = VehicleType.CAR

    # Runtime state (set by the simulation engine)
    current_road: str | None = field(default=None, repr=False)
    current_cell: int = field(default=0, repr=False)
    spawn_tick: Tick = field(default=0, repr=False)
    arrived: bool = field(default=False, repr=False)
    wait_ticks: int = field(default=0, repr=False)

    @property
    def is_emergency(self) -> bool:
        return self.vehicle_type == VehicleType.EMERGENCY


@dataclass
class EmergencyVehicle(Vehicle):
    """An emergency vehicle with preemption privileges.

    Inherits all vehicle behaviour and adds route and priority metadata.
    """

    vehicle_type: VehicleType = field(default=VehicleType.EMERGENCY)

    # Pre-computed route: ordered list of intersection IDs from origin to destination
    route: list[IntersectionId] = field(default_factory=list)

    # How many intersections ahead to request preemption
    preemption_lookahead: int = 2

    # Index into ``route`` indicating the next intersection to reach
    route_index: int = field(default=0, repr=False)

    @property
    def next_intersection(self) -> IntersectionId | None:
        if self.route_index < len(self.route):
            return self.route[self.route_index]
        return None

    def advance_route(self) -> None:
        """Mark the current intersection as passed."""
        self.route_index += 1
