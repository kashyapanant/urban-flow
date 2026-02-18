"""Signal phase and plan definitions.

A *signal plan* is an ordered sequence of *signal phases*.  Each phase
specifies which directions get green (or yellow) and for how many ticks.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from urban_flow.core.types import Direction, SignalState


@dataclass(frozen=True)
class SignalPhase:
    """One phase in a signal cycle.

    Parameters
    ----------
    green_directions:
        Set of directions that receive GREEN during this phase.
    duration:
        Number of ticks this phase lasts.
    state:
        The signal state applied to the green directions (GREEN or YELLOW).
        All other directions are implicitly RED.
    """

    green_directions: frozenset[Direction]
    duration: int
    state: SignalState = SignalState.GREEN

    def applies_to(self, direction: Direction) -> bool:
        return direction in self.green_directions


@dataclass
class SignalPlan:
    """A full signal cycle: an ordered list of phases.

    The plan loops: after the last phase completes, it wraps to the first.
    """

    phases: list[SignalPhase] = field(default_factory=list)

    @property
    def cycle_length(self) -> int:
        """Total ticks for one complete cycle."""
        return sum(p.duration for p in self.phases)

    def phase_at_tick(self, tick: int) -> SignalPhase:
        """Return the active phase for a given tick within the cycle."""
        if not self.phases:
            raise ValueError("SignalPlan has no phases")
        offset = tick % self.cycle_length
        elapsed = 0
        for phase in self.phases:
            elapsed += phase.duration
            if offset < elapsed:
                return phase
        return self.phases[-1]

    @classmethod
    def default_four_way(
        cls,
        green_duration: int = 30,
        yellow_duration: int = 5,
    ) -> SignalPlan:
        """Create a standard 4-way signal plan (NS green → NS yellow → EW green → EW yellow)."""
        return cls(
            phases=[
                SignalPhase(
                    green_directions=frozenset({Direction.NORTH, Direction.SOUTH}),
                    duration=green_duration,
                    state=SignalState.GREEN,
                ),
                SignalPhase(
                    green_directions=frozenset({Direction.NORTH, Direction.SOUTH}),
                    duration=yellow_duration,
                    state=SignalState.YELLOW,
                ),
                SignalPhase(
                    green_directions=frozenset({Direction.EAST, Direction.WEST}),
                    duration=green_duration,
                    state=SignalState.GREEN,
                ),
                SignalPhase(
                    green_directions=frozenset({Direction.EAST, Direction.WEST}),
                    duration=yellow_duration,
                    state=SignalState.YELLOW,
                ),
            ]
        )
