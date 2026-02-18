"""Shared enums, type aliases, and lightweight value objects."""

from __future__ import annotations

from enum import Enum, auto
from typing import NamedTuple


class Direction(Enum):
    """Cardinal direction a vehicle can travel or a signal can face."""

    NORTH = auto()
    SOUTH = auto()
    EAST = auto()
    WEST = auto()

    @property
    def opposite(self) -> Direction:
        _opposites = {
            Direction.NORTH: Direction.SOUTH,
            Direction.SOUTH: Direction.NORTH,
            Direction.EAST: Direction.WEST,
            Direction.WEST: Direction.EAST,
        }
        return _opposites[self]

    @property
    def axis(self) -> str:
        """Return 'NS' for north/south, 'EW' for east/west."""
        if self in (Direction.NORTH, Direction.SOUTH):
            return "NS"
        return "EW"


class SignalState(Enum):
    """Possible states of a traffic signal."""

    RED = auto()
    YELLOW = auto()
    GREEN = auto()


class VehicleType(Enum):
    """Classification of vehicles in the simulation."""

    CAR = auto()
    EMERGENCY = auto()


class Position(NamedTuple):
    """Grid coordinate of an intersection (row, col)."""

    row: int
    col: int


# Type aliases
IntersectionId = str
RoadId = str
VehicleId = str
Tick = int
