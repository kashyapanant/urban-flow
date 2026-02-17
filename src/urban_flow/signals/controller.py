"""Abstract signal controller protocol.

All signal controllers implement this protocol so they can be used
interchangeably -- per intersection if desired.
"""

from __future__ import annotations

from typing import Protocol

from urban_flow.core.intersection import Intersection
from urban_flow.core.signal import SignalPhase
from urban_flow.core.types import Direction, Tick


class SignalController(Protocol):
    """Protocol that every signal control strategy must satisfy."""

    def update(self, intersection: Intersection, tick: Tick) -> SignalPhase:
        """Determine and apply the signal phase for this tick.

        The controller should mutate intersection.signal_states and
        return the active phase.
        """
        ...

    def request_preemption(self, direction: Direction) -> None:
        """Request an emergency green override for the given direction.

        While preemption is active, the controller should hold green
        for the requested direction regardless of normal cycling.
        """
        ...

    def release_preemption(self) -> None:
        """Cancel the active preemption and resume normal operation."""
        ...
