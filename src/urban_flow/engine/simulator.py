"""Simulator — the main discrete-time simulation loop.

Orchestrates one tick of the simulation by advancing the clock, spawning
vehicles, updating signals, moving vehicles, and collecting metrics.

This module is a skeleton that will be fleshed out in Phase 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from urban_flow.config.settings import SimulationConfig
from urban_flow.core.grid import RoadNetwork
from urban_flow.core.vehicle import Vehicle
from urban_flow.engine.clock import SimulationClock
from urban_flow.engine.events import EventBus
from urban_flow.engine.spawner import SpawnerConfig, VehicleSpawner


@dataclass
class SimulationState:
    """Snapshot of the simulation at a given tick."""

    tick: int
    num_vehicles: int
    num_arrived: int
    num_waiting: int


@dataclass
class SimulationResult:
    """Summary returned after a complete simulation run."""

    total_ticks: int
    total_vehicles_spawned: int
    total_vehicles_arrived: int
    average_travel_ticks: float


class Simulator:
    """Discrete-time traffic simulation engine.

    Usage::

        config = SimulationConfig()
        network = RoadNetwork.create_grid(rows=4, cols=4)
        sim = Simulator(config=config, network=network)
        result = sim.run(num_ticks=500)
    """

    def __init__(self, config: SimulationConfig, network: RoadNetwork) -> None:
        self._config = config
        self._network = network
        self._clock = SimulationClock(
            tick_duration_seconds=config.tick_duration_seconds
        )
        self._event_bus = EventBus()
        self._spawner = VehicleSpawner(
            config=SpawnerConfig(
                spawn_probability=config.spawn_probability,
                emergency_probability=config.emergency_probability,
                seed=config.seed,
            ),
            network=network,
        )

        # Vehicle registries
        self._active_vehicles: dict[str, Vehicle] = {}
        self._arrived_vehicles: list[Vehicle] = []

    @property
    def clock(self) -> SimulationClock:
        return self._clock

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def network(self) -> RoadNetwork:
        return self._network

    def tick(self) -> SimulationState:
        """Execute one simulation step.

        Order of operations:
            1. Advance clock
            2. Spawn vehicles
            3. (Phase 3) Detect emergency vehicles
            4. (Phase 3) Process preemption requests
            5. (Phase 2) Update signal controllers
            6. Move vehicles
            7. Collect metrics

        Returns a snapshot of the current state.
        """
        current_tick = self._clock.advance()

        # 1. Spawn
        new_vehicles = self._spawner.spawn(current_tick)
        for v in new_vehicles:
            self._active_vehicles[v.vehicle_id] = v

        # 2-6: Movement, signals, emergency — implemented in later phases
        # TODO(phase-1): Implement vehicle movement along roads
        # TODO(phase-2): Integrate signal controllers
        # TODO(phase-3): Add emergency detection and preemption

        return SimulationState(
            tick=current_tick,
            num_vehicles=len(self._active_vehicles),
            num_arrived=len(self._arrived_vehicles),
            num_waiting=0,
        )

    def run(self, num_ticks: int) -> SimulationResult:
        """Run the simulation for *num_ticks* steps and return a summary."""
        for _ in range(num_ticks):
            self.tick()

        total_travel = sum(
            (v.wait_ticks + (self._clock.current_tick - v.spawn_tick))
            for v in self._arrived_vehicles
        )
        avg_travel = (
            total_travel / len(self._arrived_vehicles)
            if self._arrived_vehicles
            else 0.0
        )

        return SimulationResult(
            total_ticks=self._clock.current_tick,
            total_vehicles_spawned=len(self._active_vehicles)
            + len(self._arrived_vehicles),
            total_vehicles_arrived=len(self._arrived_vehicles),
            average_travel_ticks=avg_travel,
        )
