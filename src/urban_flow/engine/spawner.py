"""Vehicle spawner — generates vehicles at network entry points."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from urban_flow.core.grid import RoadNetwork
from urban_flow.core.types import IntersectionId, Tick
from urban_flow.core.vehicle import EmergencyVehicle, Vehicle


@dataclass
class SpawnerConfig:
    """Configuration for vehicle generation.

    Parameters
    ----------
    spawn_probability:
        Probability of spawning a vehicle each tick at each entry point.
    emergency_probability:
        Probability that a spawned vehicle is an emergency vehicle.
    seed:
        Random seed for reproducibility. ``None`` means non-deterministic.
    """

    spawn_probability: float = 0.3
    emergency_probability: float = 0.02
    seed: int | None = None


class VehicleSpawner:
    """Generates vehicles and places them at network entry points.

    Entry points are intersections on the grid boundary (edges of the grid).
    """

    def __init__(self, config: SpawnerConfig, network: RoadNetwork) -> None:
        self._config = config
        self._network = network
        self._rng = random.Random(config.seed)
        self._counter = 0
        self._entry_points: list[IntersectionId] = self._find_entry_points()

    def _find_entry_points(self) -> list[IntersectionId]:
        """Identify intersections on the grid boundary."""
        if not self._network.intersections:
            return []

        all_positions = {
            iid: ix.position
            for iid, ix in self._network.intersections.items()
        }
        if not all_positions:
            return []

        min_row = min(p.row for p in all_positions.values())
        max_row = max(p.row for p in all_positions.values())
        min_col = min(p.col for p in all_positions.values())
        max_col = max(p.col for p in all_positions.values())

        entries = []
        for iid, pos in all_positions.items():
            if pos.row in (min_row, max_row) or pos.col in (min_col, max_col):
                entries.append(iid)
        return entries

    def spawn(self, tick: Tick) -> list[Vehicle]:
        """Attempt to spawn vehicles this tick. Returns newly created vehicles."""
        spawned: list[Vehicle] = []

        for entry in self._entry_points:
            if self._rng.random() > self._config.spawn_probability:
                continue

            # Pick a random destination different from origin
            possible_dests = [e for e in self._entry_points if e != entry]
            if not possible_dests:
                continue
            destination = self._rng.choice(possible_dests)

            self._counter += 1
            is_emergency = (
                self._rng.random() < self._config.emergency_probability
            )

            if is_emergency:
                route = self._network.shortest_path(entry, destination)
                vehicle = EmergencyVehicle(
                    vehicle_id=f"EV-{self._counter}",
                    origin=entry,
                    destination=destination,
                    route=route,
                    spawn_tick=tick,
                )
            else:
                vehicle = Vehicle(
                    vehicle_id=f"V-{self._counter}",
                    origin=entry,
                    destination=destination,
                    spawn_tick=tick,
                )

            spawned.append(vehicle)

        return spawned
