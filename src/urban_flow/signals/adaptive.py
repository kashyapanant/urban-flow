"""Adaptive signal controller — adjusts phase timing based on traffic.

This is a placeholder for Phase 2+.  The adaptive controller will observe
queue lengths on each approach and extend/shorten green phases accordingly.
"""

from __future__ import annotations

from urban_flow.core.intersection import Intersection
from urban_flow.core.signal import SignalPhase
from urban_flow.core.types import Direction, Tick


class AdaptiveController:
    """Queue-length-aware signal controller (stub for future implementation)."""

    def update(self, intersection: Intersection, tick: Tick) -> SignalPhase:
        raise NotImplementedError("AdaptiveController will be implemented in Phase 2")

    def request_preemption(self, direction: Direction) -> None:
        raise NotImplementedError

    def release_preemption(self) -> None:
        raise NotImplementedError
