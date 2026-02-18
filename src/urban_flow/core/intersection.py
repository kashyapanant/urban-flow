"""Intersection — a node in the road network.

Each intersection has a position on the grid, connects to incoming and
outgoing roads, and holds the current signal state for each direction.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from urban_flow.core.types import (
    Direction,
    IntersectionId,
    Position,
    SignalState,
)


@dataclass
class Intersection:
    """A single intersection in the road network.

    Parameters
    ----------
    intersection_id:
        Unique identifier (e.g. ``"I-0-0"`` for row 0, col 0).
    position:
        Grid coordinates of this intersection.
    """

    intersection_id: IntersectionId
    position: Position

    # Roads keyed by the direction they *arrive from*
    incoming_roads: dict[Direction, str] = field(default_factory=dict)
    # Roads keyed by the direction they *depart towards*
    outgoing_roads: dict[Direction, str] = field(default_factory=dict)

    # Current signal state per direction (default RED for all)
    signal_states: dict[Direction, SignalState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.signal_states:
            self.signal_states = {d: SignalState.RED for d in Direction}

    def is_green(self, direction: Direction) -> bool:
        """Check whether the signal is green for traffic arriving from *direction*."""
        return self.signal_states.get(direction) == SignalState.GREEN

    def set_signal(self, direction: Direction, state: SignalState) -> None:
        self.signal_states[direction] = state

    def set_all_red(self) -> None:
        for d in Direction:
            self.signal_states[d] = SignalState.RED
