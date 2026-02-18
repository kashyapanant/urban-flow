"""Simulation clock — manages discrete time progression."""

from __future__ import annotations

from dataclasses import dataclass

from urban_flow.core.types import Tick


@dataclass
class SimulationClock:
    """Tracks simulation time as an integer tick counter.

    Parameters
    ----------
    tick_duration_seconds:
        Real-world seconds represented by one simulation tick.
    """

    tick_duration_seconds: float = 1.0
    _current_tick: Tick = 0

    @property
    def current_tick(self) -> Tick:
        return self._current_tick

    @property
    def elapsed_seconds(self) -> float:
        return self._current_tick * self.tick_duration_seconds

    def advance(self) -> Tick:
        """Advance the clock by one tick and return the new tick number."""
        self._current_tick += 1
        return self._current_tick

    def reset(self) -> None:
        self._current_tick = 0
