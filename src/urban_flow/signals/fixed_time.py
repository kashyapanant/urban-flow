"""Fixed-time signal controller -- cycles through phases on a fixed schedule."""

from __future__ import annotations

from dataclasses import dataclass, field

from urban_flow.core.intersection import Intersection
from urban_flow.core.signal import SignalPhase, SignalPlan
from urban_flow.core.types import Direction, SignalState, Tick


@dataclass
class FixedTimeController:
    """Cycles through a SignalPlan on a fixed timer.

    Supports emergency preemption: when request_preemption is called,
    the controller holds green for the requested direction until released.
    """

    plan: SignalPlan = field(default_factory=SignalPlan.default_four_way)

    _preemption_active: bool = field(default=False, repr=False)
    _preemption_direction: Direction | None = field(default=None, repr=False)

    def update(self, intersection: Intersection, tick: Tick) -> SignalPhase:
        """Apply the current phase to the intersection."""
        if self._preemption_active and self._preemption_direction is not None:
            return self._apply_preemption(intersection)

        phase = self.plan.phase_at_tick(tick)
        self._apply_phase(intersection, phase)
        return phase

    def request_preemption(self, direction: Direction) -> None:
        self._preemption_active = True
        self._preemption_direction = direction

    def release_preemption(self) -> None:
        self._preemption_active = False
        self._preemption_direction = None

    def _apply_phase(
        self, intersection: Intersection, phase: SignalPhase
    ) -> None:
        """Set intersection signals according to the given phase."""
        intersection.set_all_red()
        for d in phase.green_directions:
            intersection.set_signal(d, phase.state)

    def _apply_preemption(self, intersection: Intersection) -> SignalPhase:
        """Override: green only for the preemption direction."""
        assert self._preemption_direction is not None
        intersection.set_all_red()
        intersection.set_signal(self._preemption_direction, SignalState.GREEN)
        return SignalPhase(
            green_directions=frozenset({self._preemption_direction}),
            duration=0,
            state=SignalState.GREEN,
        )
