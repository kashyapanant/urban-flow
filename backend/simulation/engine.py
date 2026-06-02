"""Core simulation engine that orchestrates the traffic simulation."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal

from ..config import SimulationConfig
from .grid import Grid
from .metrics import Metrics
from .traffic_light import Axis, TrafficLightManager
from .vehicle import Vehicle, VehicleManager


class SimulationState(Enum):
    """Current state of the simulation."""

    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


@dataclass
class SimulationSnapshot:
    """Complete state snapshot for frontend consumption."""

    tick_count: int
    state: str
    config: dict[str, Any]
    grid: dict[str, Any]
    vehicles: list[dict[str, Any]]
    traffic_lights: list[dict[str, Any]]
    metrics: dict[str, Any]


@dataclass(frozen=True)
class ControlResult:
    """Outcome of a user-driven simulation control request."""

    action: Literal["start", "pause", "resume", "stop"]
    applied: bool
    state: SimulationState
    message: str


class SimulationEngine:
    """Core simulation engine that orchestrates all components.

    Manages the tick loop, coordinates all subsystems, and provides
    the main interface for simulation control.
    """

    _PREEMPTION_LOOKAHEAD_CELLS = 3
    _PREEMPTION_YELLOW_DURATION = 2
    _SPAWN_MAX_RETRIES = 10
    _PAUSED_SLEEP_SECONDS = 0.05

    def __init__(
        self,
        config: SimulationConfig | None = None,
        broadcast_callback: (
            Callable[[SimulationSnapshot], Awaitable[None]] | None
        ) = None,
    ):
        """Initialize the simulation engine.

        Args:
            config: Simulation configuration (uses defaults if None)
        """
        self.config = config or SimulationConfig()
        self.grid = Grid(self.config.grid_width, self.config.grid_height)
        self.vehicle_manager = VehicleManager()
        self.traffic_light_manager = TrafficLightManager(
            self.grid.get_intersection_cells(),
            phase_duration=self.config.phase_duration,
        )
        self.metrics = Metrics()
        self.tick_count = 0
        self.state = SimulationState.STOPPED
        self._broadcast_callback = broadcast_callback
        self._run_task: asyncio.Task[None] | None = None

    async def start(self) -> ControlResult:
        """Start the simulation tick loop."""
        if self._run_task is not None and not self._run_task.done():
            if self.state is SimulationState.PAUSED:
                return ControlResult(
                    action="start",
                    applied=False,
                    state=self.state,
                    message="Simulation is paused. Use resume instead of start.",
                )
            return ControlResult(
                action="start",
                applied=False,
                state=SimulationState.RUNNING,
                message="Simulation is already running.",
            )
        if self.state is SimulationState.RUNNING:
            return ControlResult(
                action="start",
                applied=False,
                state=self.state,
                message="Simulation is already running.",
            )
        if self.state is SimulationState.PAUSED:
            return ControlResult(
                action="start",
                applied=False,
                state=self.state,
                message="Simulation is paused. Use resume instead of start.",
            )

        self.state = SimulationState.RUNNING
        self._run_task = asyncio.create_task(self._run_tick_loop())
        self._run_task.add_done_callback(self._finalize_run_task)
        return ControlResult(
            action="start",
            applied=True,
            state=self.state,
            message="Simulation started.",
        )

    async def stop(self) -> ControlResult:
        """Stop the simulation and clean up."""
        if self.state is SimulationState.STOPPED:
            return ControlResult(
                action="stop",
                applied=False,
                state=self.state,
                message="Simulation is already stopped.",
            )

        self.state = SimulationState.STOPPED
        return ControlResult(
            action="stop",
            applied=True,
            state=SimulationState.STOPPED,
            message="Simulation stopped.",
        )

    async def _run_tick_loop(self) -> None:
        """Execute the simulation tick loop until stopped."""
        while self.state is not SimulationState.STOPPED:
            if self.state is SimulationState.PAUSED:
                await asyncio.sleep(self._PAUSED_SLEEP_SECONDS)
                continue

            await self.tick()
            if self.state is SimulationState.STOPPED:
                break
            await asyncio.sleep(1.0 / self.config.tick_speed)

    def _finalize_run_task(self, task: asyncio.Task[None]) -> None:
        """Clear the managed run task when the background loop exits."""
        if task.cancelled():
            self.state = SimulationState.STOPPED
        else:
            exception = task.exception()
            if exception is not None:
                self.state = SimulationState.STOPPED
        if self._run_task is task:
            self._run_task = None

    def pause(self) -> ControlResult:
        """Pause the simulation (can be resumed)."""
        if self.state is SimulationState.STOPPED:
            return ControlResult(
                action="pause",
                applied=False,
                state=self.state,
                message="Cannot pause a stopped simulation. Start it first.",
            )
        if self.state is SimulationState.PAUSED:
            return ControlResult(
                action="pause",
                applied=False,
                state=self.state,
                message="Simulation is already paused.",
            )
        if self.state is SimulationState.RUNNING:
            self.state = SimulationState.PAUSED
            return ControlResult(
                action="pause",
                applied=True,
                state=self.state,
                message="Simulation paused.",
            )
        raise RuntimeError(f"Unhandled simulation state: {self.state!r}")

    def resume(self) -> ControlResult:
        """Resume a paused simulation."""
        if self.state is SimulationState.STOPPED:
            return ControlResult(
                action="resume",
                applied=False,
                state=self.state,
                message="Cannot resume a stopped simulation. Start it first.",
            )
        if self.state is SimulationState.RUNNING:
            return ControlResult(
                action="resume",
                applied=False,
                state=self.state,
                message="Simulation is already running.",
            )
        if self.state is SimulationState.PAUSED:
            self.state = SimulationState.RUNNING
            return ControlResult(
                action="resume",
                applied=True,
                state=self.state,
                message="Simulation resumed.",
            )
        raise RuntimeError(f"Unhandled simulation state: {self.state!r}")

    def set_tick_speed(self, speed: int) -> None:
        """Set simulation tick speed (takes effect next tick).

        Args:
            speed: Ticks per second (1-10)
        """
        self.config = self._validated_config_copy(tick_speed=speed)

    def set_spawn_rate(self, rate: float) -> None:
        """Set vehicle spawn rate (takes effect next tick).

        Args:
            rate: Probability per edge cell per tick (0.0-1.0)
        """
        self.config = self._validated_config_copy(spawn_rate=rate)

    def set_phase_duration(self, duration: int) -> None:
        """Set traffic light phase duration (takes effect next tick).

        Args:
            duration: Ticks per phase (1-20)
        """
        self.config = self._validated_config_copy(phase_duration=duration)
        self.traffic_light_manager.set_phase_duration(duration)

    def snapshot(self) -> SimulationSnapshot:
        """Create a complete state snapshot for frontend consumption.

        Returns:
            Complete simulation state snapshot
        """
        return SimulationSnapshot(
            tick_count=self.tick_count,
            state=self.state.value,
            config=self.config.model_dump(),
            grid=self.grid.snapshot(),
            vehicles=self.vehicle_manager.snapshot(),
            traffic_lights=self.traffic_light_manager.snapshot(),
            metrics=self.metrics.to_dict(),
        )

    def get_metrics(self) -> Metrics:
        """Get current simulation metrics.

        Returns:
            Current metrics object
        """
        return self.metrics

    async def tick(self) -> SimulationSnapshot:
        """Execute one complete deterministic simulation tick."""
        self._scan_preemptions()
        self._update_traffic_lights()
        self._move_vehicles()
        self._spawn_vehicles()
        self._cleanup_and_record_metrics()
        self.tick_count += 1
        await self._broadcast_state()
        return self.snapshot()

    def _validated_config_copy(self, **updates: Any) -> SimulationConfig:
        """Return a fully validated config instance with merged updates."""
        merged = self.config.model_dump()
        merged.update(updates)
        return SimulationConfig.model_validate(merged)

    def _update_traffic_lights(self) -> None:
        """Advance all traffic lights by one tick."""
        self.traffic_light_manager.tick()

    def _move_vehicles(self) -> None:
        """Move active vehicles one step according to priority and signals."""
        self.vehicle_manager.move_vehicles(self.grid, self.traffic_light_manager)

    def _spawn_vehicles(self) -> None:
        """Spawn new vehicles from eligible edge cells for this tick."""
        self.vehicle_manager.spawn_vehicles(
            self.grid,
            self.config.spawn_rate,
            self.config.emergency_probability,
            self._SPAWN_MAX_RETRIES,
            self.traffic_light_manager,
        )

    def _cleanup_and_record_metrics(self) -> None:
        """Collect arrivals, update metrics, and clear stale preemptions."""
        arrived = self.vehicle_manager.collect_arrived()
        if arrived:
            self.metrics.record_multiple_arrivals(arrived)

        active_vehicles = self.vehicle_manager.get_all()
        active_vehicle_ids = {vehicle.id for vehicle in active_vehicles}
        upcoming_positions_by_vehicle_id: dict[str, set[tuple[int, int]]] = {}
        for light in self.traffic_light_manager.get_all():
            holder = light.preempted_by
            if holder is None:
                continue
            if holder.id not in active_vehicle_ids:
                light.release_preemption()
                continue

            upcoming_positions = upcoming_positions_by_vehicle_id.get(holder.id)
            if upcoming_positions is None:
                upcoming_positions = self._upcoming_intersection_positions(holder)
                upcoming_positions_by_vehicle_id[holder.id] = upcoming_positions

            if light.position not in upcoming_positions:
                light.release_preemption()

    def _scan_preemptions(self) -> None:
        """Request preemption for intersections ahead of active emergency vehicles."""
        preemption_yellow_duration = self._preemption_yellow_duration()
        for vehicle in self.vehicle_manager.get_emergency_vehicles():
            for position, axis in self._upcoming_intersections(vehicle):
                self.traffic_light_manager.request_preemption(
                    position,
                    vehicle,
                    axis,
                    preemption_yellow_duration,
                )

    def _preemption_yellow_duration(self) -> int:
        """Return a preemption yellow duration valid for current phase timing."""
        return min(self._PREEMPTION_YELLOW_DURATION, self.config.phase_duration)

    def _upcoming_intersections(
        self, vehicle: Vehicle
    ) -> list[tuple[tuple[int, int], Axis]]:
        """Return upcoming intersections within the preemption lookahead window."""
        intersections: list[tuple[tuple[int, int], Axis]] = []
        max_index = min(
            len(vehicle.path) - 1,
            vehicle.path_index + self._PREEMPTION_LOOKAHEAD_CELLS,
        )
        for path_index in range(vehicle.path_index + 1, max_index + 1):
            position = vehicle.path[path_index]
            cell = self.grid.get_cell(*position)
            if cell is None or cell.traffic_light is None:
                continue

            previous_position = vehicle.path[path_index - 1]
            intersections.append(
                (position, self._axis_for_step(previous_position, position))
            )
        return intersections

    def _upcoming_intersection_positions(
        self, vehicle: Vehicle
    ) -> set[tuple[int, int]]:
        """Return upcoming intersection positions for stale-preemption cleanup."""
        return {position for position, _axis in self._upcoming_intersections(vehicle)}

    @staticmethod
    def _axis_for_step(
        current_position: tuple[int, int], next_position: tuple[int, int]
    ) -> Axis:
        """Map a one-cell path step onto its traffic-light axis."""
        dx = next_position[0] - current_position[0]
        dy = next_position[1] - current_position[1]
        if dx != 0 and dy == 0:
            return Axis.EW
        if dy != 0 and dx == 0:
            return Axis.NS
        raise ValueError(
            "Vehicle path steps must be one-cell cardinal moves; "
            f"got {current_position} -> {next_position}."
        )

    async def _broadcast_state(self) -> None:
        """Emit the latest snapshot through the optional broadcast hook."""
        if self._broadcast_callback is None:
            return
        await self._broadcast_callback(self.snapshot())
