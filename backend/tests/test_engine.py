"""Tests for the simulation engine."""

from __future__ import annotations

import asyncio
from typing import cast
from unittest.mock import Mock

import pytest

from backend.config import SimulationConfig
from backend.simulation.engine import SimulationEngine, SimulationState
from backend.simulation.traffic_light import Axis
from backend.simulation.vehicle import Vehicle, VehicleStatus, VehicleType


def _vehicle(
    vehicle_id: str,
    vehicle_type: VehicleType,
    path: list[tuple[int, int]],
    *,
    path_index: int = 0,
    status: VehicleStatus = VehicleStatus.MOVING,
    ticks_elapsed: int = 0,
) -> Vehicle:
    """Build a vehicle with path/position aligned for engine tests."""
    return Vehicle(
        id=vehicle_id,
        type=vehicle_type,
        position=path[path_index],
        origin=path[0],
        destination=path[-1],
        path=path,
        path_index=path_index,
        status=status,
        ticks_elapsed=ticks_elapsed,
    )


class TestSimulationEngine:
    """Test cases for the SimulationEngine class."""

    def test_engine_initialization(self) -> None:
        """Engine initializes all core subsystems from config."""
        engine = SimulationEngine()

        assert engine.config.model_dump() == SimulationConfig().model_dump()
        assert engine.grid.width == engine.config.grid_width
        assert engine.grid.height == engine.config.grid_height
        assert engine.tick_count == 0
        assert engine.state is SimulationState.STOPPED
        assert engine.vehicle_manager.get_all() == []
        assert engine.metrics.total_completed == 0
        assert len(engine.traffic_light_manager.get_all()) == len(
            engine.grid.get_intersection_cells()
        )

    def test_configuration_updates(self) -> None:
        """Runtime config setters update engine config and light timing."""
        engine = SimulationEngine()

        engine.set_tick_speed(5)
        engine.set_spawn_rate(0.4)
        engine.set_phase_duration(7)

        assert engine.config.tick_speed == 5
        assert engine.config.spawn_rate == 0.4
        assert engine.config.phase_duration == 7
        phase_durations = {
            light.phase_duration for light in engine.traffic_light_manager.get_all()
        }
        assert phase_durations == {7}

    def test_reset_config_restores_defaults_without_rebuilding_runtime_state(
        self,
    ) -> None:
        """reset_config() restores settings while preserving the current world."""
        engine = SimulationEngine(
            SimulationConfig(grid_width=12, grid_height=8, tick_speed=2)
        )
        original_grid = engine.grid
        original_vehicle_manager = engine.vehicle_manager
        original_light_manager = engine.traffic_light_manager
        original_metrics = engine.metrics

        engine.tick_count = 9
        engine.set_tick_speed(6)
        engine.set_spawn_rate(0.35)
        engine.set_phase_duration(5)
        engine.set_emergency_probability(0.4)

        engine.reset_config()

        assert engine.config.model_dump() == {
            "grid_width": 12,
            "grid_height": 8,
            "tick_speed": 1,
            "spawn_rate": 0.1,
            "emergency_probability": 0.1,
            "phase_duration": 3,
        }
        assert engine.grid is original_grid
        assert engine.vehicle_manager is original_vehicle_manager
        assert engine.traffic_light_manager is original_light_manager
        assert engine.metrics is original_metrics
        assert engine.tick_count == 9
        phase_durations = {
            light.phase_duration for light in engine.traffic_light_manager.get_all()
        }
        assert phase_durations == {SimulationConfig().phase_duration}

    @pytest.mark.asyncio
    async def test_reset_config_preserves_running_state(self) -> None:
        """reset_config() updates settings only and does not stop a live run."""
        engine = SimulationEngine()
        start_result = await engine.start()

        assert start_result.applied is True
        run_task = engine._run_task

        engine.set_tick_speed(7)
        engine.reset_config()

        assert engine.state is SimulationState.RUNNING
        assert engine._run_task is run_task
        assert run_task is not None
        assert run_task.done() is False

        await engine.stop()

    def test_pause_resume_simulation(self) -> None:
        """Pause/resume only transition between running and paused."""
        engine = SimulationEngine()

        engine.state = SimulationState.RUNNING
        pause_result = engine.pause()
        assert engine.state is SimulationState.PAUSED
        assert pause_result.action == "pause"
        assert pause_result.applied is True
        assert pause_result.state is SimulationState.PAUSED
        assert pause_result.message == "Simulation paused."

        resume_result = engine.resume()
        assert engine.state is SimulationState.RUNNING
        assert resume_result.action == "resume"
        assert resume_result.applied is True
        assert resume_result.state is SimulationState.RUNNING
        assert resume_result.message == "Simulation resumed."

    def test_pause_rejects_when_stopped(self) -> None:
        """Paused and stopped are distinct lifecycle states."""
        engine = SimulationEngine()

        result = engine.pause()

        assert result.action == "pause"
        assert result.applied is False
        assert result.state is SimulationState.STOPPED
        assert result.message == "Cannot pause a stopped simulation. Start it first."
        assert engine.state is SimulationState.STOPPED

    def test_resume_rejects_when_stopped(self) -> None:
        """Stopped simulations must be started, not resumed."""
        engine = SimulationEngine()

        result = engine.resume()

        assert result.action == "resume"
        assert result.applied is False
        assert result.state is SimulationState.STOPPED
        assert result.message == "Cannot resume a stopped simulation. Start it first."
        assert engine.state is SimulationState.STOPPED

    @pytest.mark.asyncio
    async def test_reset_rebuilds_clean_state_while_stopped(self) -> None:
        """reset() rebuilds world state and leaves the engine ready to start."""
        engine = SimulationEngine()
        original_grid = engine.grid
        original_vehicle_manager = engine.vehicle_manager
        original_light_manager = engine.traffic_light_manager
        original_metrics = engine.metrics

        engine.tick_count = 12
        engine.set_tick_speed(7)
        engine.set_spawn_rate(0.4)
        engine.set_phase_duration(5)
        engine.set_emergency_probability(0.25)
        engine.metrics.record_arrival(
            _vehicle(
                "completed-1",
                VehicleType.NORMAL,
                [(0, 0)],
                ticks_elapsed=9,
            )
        )

        result = await engine.reset()

        assert result.action == "reset"
        assert result.applied is True
        assert result.state is SimulationState.STOPPED
        assert result.message == "Simulation reset."
        assert engine.state is SimulationState.STOPPED
        assert engine.tick_count == 0
        assert engine.grid is not original_grid
        assert engine.vehicle_manager is not original_vehicle_manager
        assert engine.traffic_light_manager is not original_light_manager
        assert engine.metrics is not original_metrics
        assert engine.vehicle_manager.get_all() == []
        assert engine.metrics.total_completed == 0
        assert engine.config.tick_speed == 7
        assert engine.config.spawn_rate == 0.4
        assert engine.config.phase_duration == 5
        assert engine.config.emergency_probability == 0.25

    @pytest.mark.asyncio
    async def test_reset_stops_live_loop_before_rebuilding(self) -> None:
        """reset() stops the current run loop before rebuilding state."""
        engine = SimulationEngine()
        start_result = await engine.start()

        assert start_result.applied is True
        original_run_task = engine._run_task
        assert original_run_task is not None

        result = await engine.reset()

        assert result.action == "reset"
        assert result.applied is True
        assert result.state is SimulationState.STOPPED
        assert engine.state is SimulationState.STOPPED
        assert engine._run_task is None
        assert original_run_task.done() is True
        assert original_run_task.cancelled() is True
        assert engine.tick_count == 0

    @pytest.mark.asyncio
    async def test_reset_stops_live_task_even_if_state_drifted_to_stopped(self) -> None:
        """reset() uses live task state, not only the lifecycle enum, to shut down."""
        engine = SimulationEngine()
        release_task = asyncio.Event()

        async def wait_forever() -> None:
            await release_task.wait()

        live_task = asyncio.create_task(wait_forever())
        engine.state = SimulationState.STOPPED
        engine._run_task = live_task

        try:
            result = await engine.reset()
        finally:
            if not live_task.done():
                release_task.set()
                await live_task

        assert result.action == "reset"
        assert result.applied is True
        assert result.state is SimulationState.STOPPED
        assert engine.state is SimulationState.STOPPED
        assert engine._run_task is None
        assert live_task.done() is True
        assert live_task.cancelled() is True

    @pytest.mark.asyncio
    async def test_reset_from_paused_state_rebuilds_clean_world(self) -> None:
        """reset() treats paused loops like running ones and ends stopped."""
        engine = SimulationEngine()
        await engine.start()
        pause_result = engine.pause()

        assert pause_result.applied is True
        assert engine.state is SimulationState.PAUSED

        result = await engine.reset()

        assert result.action == "reset"
        assert result.applied is True
        assert result.state is SimulationState.STOPPED
        assert engine.state is SimulationState.STOPPED
        assert engine._run_task is None

    @pytest.mark.asyncio
    async def test_start_rejects_when_live_task_is_running(self) -> None:
        """start() does not create a second loop when one is already active."""
        engine = SimulationEngine()
        engine.state = SimulationState.RUNNING
        release_task = asyncio.Event()

        async def wait_forever() -> None:
            await release_task.wait()

        live_task = asyncio.create_task(wait_forever())
        engine._run_task = live_task

        try:
            result = await engine.start()
        finally:
            release_task.set()
            await live_task

        assert result.action == "start"
        assert result.applied is False
        assert result.state is SimulationState.RUNNING
        assert result.message == "Simulation is already running."

    @pytest.mark.asyncio
    async def test_start_rejects_when_live_task_is_paused(self) -> None:
        """start() requires resume when a paused run loop is still alive."""
        engine = SimulationEngine()
        engine.state = SimulationState.PAUSED
        release_task = asyncio.Event()

        async def wait_forever() -> None:
            await release_task.wait()

        live_task = asyncio.create_task(wait_forever())
        engine._run_task = live_task

        try:
            result = await engine.start()
        finally:
            release_task.set()
            await live_task

        assert result.action == "start"
        assert result.applied is False
        assert result.state is SimulationState.PAUSED
        assert result.message == "Simulation is paused. Use resume instead of start."

    def test_pause_and_resume_are_idempotent_in_same_state(self) -> None:
        """Same-state control calls are harmless."""
        engine = SimulationEngine()
        engine.state = SimulationState.RUNNING

        first_pause = engine.pause()
        assert engine.state is SimulationState.PAUSED
        assert first_pause.applied is True

        second_pause = engine.pause()
        assert engine.state is SimulationState.PAUSED
        assert second_pause.action == "pause"
        assert second_pause.applied is False
        assert second_pause.state is SimulationState.PAUSED
        assert second_pause.message == "Simulation is already paused."

        first_resume = engine.resume()
        assert engine.state is SimulationState.RUNNING
        assert first_resume.applied is True

        second_resume = engine.resume()
        assert engine.state is SimulationState.RUNNING
        assert second_resume.action == "resume"
        assert second_resume.applied is False
        assert second_resume.state is SimulationState.RUNNING
        assert second_resume.message == "Simulation is already running."

    def test_stop_is_idempotent_when_already_stopped(self) -> None:
        """stop() returns an informational result when already stopped."""
        engine = SimulationEngine()

        result = asyncio.run(engine.stop())

        assert result.action == "stop"
        assert result.applied is False
        assert result.state is SimulationState.STOPPED
        assert result.message == "Simulation is already stopped."

    def test_pause_raises_on_unhandled_state(self) -> None:
        """pause() raises only for unexpected internal state corruption."""
        engine = SimulationEngine()
        engine.state = cast(SimulationState, "invalid")

        with pytest.raises(RuntimeError, match="Unhandled simulation state"):
            engine.pause()

    def test_resume_raises_on_unhandled_state(self) -> None:
        """resume() raises only for unexpected internal state corruption."""
        engine = SimulationEngine()
        engine.state = cast(SimulationState, "invalid")

        with pytest.raises(RuntimeError, match="Unhandled simulation state"):
            engine.resume()

    def test_tick_execution_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """One engine tick runs the deterministic six-phase order."""
        engine = SimulationEngine()
        call_order: list[str] = []

        monkeypatch.setattr(
            engine,
            "_scan_preemptions",
            lambda: call_order.append("preemption_scan"),
        )
        monkeypatch.setattr(
            engine,
            "_update_traffic_lights",
            lambda: call_order.append("traffic_light_update"),
        )
        monkeypatch.setattr(
            engine,
            "_move_vehicles",
            lambda: call_order.append("vehicle_movement"),
        )
        monkeypatch.setattr(
            engine,
            "_spawn_vehicles",
            lambda: call_order.append("vehicle_spawning"),
        )
        monkeypatch.setattr(
            engine,
            "_cleanup_and_record_metrics",
            lambda: call_order.append("cleanup_metrics"),
        )

        async def fake_broadcast() -> None:
            call_order.append("broadcast")

        monkeypatch.setattr(engine, "_broadcast_state", fake_broadcast)

        asyncio.run(engine.tick())

        assert call_order == [
            "preemption_scan",
            "traffic_light_update",
            "vehicle_movement",
            "vehicle_spawning",
            "cleanup_metrics",
            "broadcast",
        ]
        assert engine.tick_count == 1

    def test_preemption_handling(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Only emergency vehicles request preemption on upcoming intersections."""
        engine = SimulationEngine()
        normal = _vehicle("n-1", VehicleType.NORMAL, [(0, 0), (1, 0), (2, 0), (3, 0)])
        emergency = _vehicle(
            "e-1",
            VehicleType.EMERGENCY,
            [(0, 0), (1, 0), (2, 0), (3, 0), (3, 1), (3, 2), (3, 3)],
        )
        engine.vehicle_manager._vehicles = [normal, emergency]
        request_preemption = Mock()
        monkeypatch.setattr(
            engine.traffic_light_manager,
            "request_preemption",
            request_preemption,
        )

        engine._scan_preemptions()

        request_preemption.assert_called_once_with((3, 0), emergency, Axis.EW, 2)

    def test_preemption_handling_uses_ns_axis_for_vertical_approach(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Emergency vehicles request NS preemption for vertical approach steps."""
        engine = SimulationEngine()
        emergency = _vehicle(
            "e-1",
            VehicleType.EMERGENCY,
            [(0, 0), (0, 1), (0, 2), (0, 3)],
        )
        engine.vehicle_manager._vehicles = [emergency]
        request_preemption = Mock()
        monkeypatch.setattr(
            engine.traffic_light_manager,
            "request_preemption",
            request_preemption,
        )

        engine._scan_preemptions()

        request_preemption.assert_called_once_with((0, 3), emergency, Axis.NS, 2)

    def test_preemption_yellow_duration_is_bounded_by_phase_duration(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Preemption yellow duration is capped by phase duration."""
        engine = SimulationEngine(SimulationConfig(phase_duration=1))
        emergency = _vehicle(
            "e-1",
            VehicleType.EMERGENCY,
            [(0, 0), (1, 0), (2, 0), (3, 0)],
        )
        engine.vehicle_manager._vehicles = [emergency]
        request_preemption = Mock()
        monkeypatch.setattr(
            engine.traffic_light_manager,
            "request_preemption",
            request_preemption,
        )

        engine._scan_preemptions()

        request_preemption.assert_called_once_with((3, 0), emergency, Axis.EW, 1)

    def test_metrics_collection(self) -> None:
        """Arrivals are recorded into metrics and removed from active vehicles."""
        engine = SimulationEngine()
        arrived_normal = _vehicle(
            "n-1",
            VehicleType.NORMAL,
            [(0, 0)],
            status=VehicleStatus.ARRIVED,
            ticks_elapsed=12,
        )
        arrived_emergency = _vehicle(
            "e-1",
            VehicleType.EMERGENCY,
            [(3, 3)],
            status=VehicleStatus.ARRIVED,
            ticks_elapsed=6,
        )
        active = _vehicle("n-2", VehicleType.NORMAL, [(0, 3), (1, 3)])
        engine.vehicle_manager._vehicles = [arrived_normal, arrived_emergency, active]

        engine._cleanup_and_record_metrics()

        assert engine.metrics.total_completed == 2
        assert engine.metrics.normal_vehicle_count == 1
        assert engine.metrics.emergency_vehicle_count == 1
        assert engine.metrics.normal_avg_ticks == 12.0
        assert engine.metrics.emergency_avg_ticks == 6.0
        assert engine.vehicle_manager.get_all() == [active]

    def test_cleanup_releases_stale_preemptions(self) -> None:
        """Cleanup releases preemption held by vehicles no longer approaching."""
        engine = SimulationEngine()
        emergency = _vehicle(
            "e-1",
            VehicleType.EMERGENCY,
            [(0, 0), (1, 0), (2, 0), (3, 0)],
            path_index=1,
        )
        engine.vehicle_manager._vehicles = [emergency]
        light = engine.traffic_light_manager.get_light((0, 0))
        assert light is not None
        light.preempted_by = emergency

        engine._cleanup_and_record_metrics()

        assert light.preempted_by is None

    def test_cleanup_releases_preemption_for_vehicle_no_longer_active(self) -> None:
        """Cleanup clears holders that are no longer in the active vehicle list."""
        engine = SimulationEngine()
        emergency = _vehicle(
            "e-1",
            VehicleType.EMERGENCY,
            [(0, 0), (1, 0), (2, 0), (3, 0)],
        )
        light = engine.traffic_light_manager.get_light((3, 0))
        assert light is not None
        light.preempted_by = emergency

        engine._cleanup_and_record_metrics()

        assert light.preempted_by is None

    def test_cleanup_reuses_upcoming_intersections_for_shared_holder(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cleanup computes upcoming intersections once per shared holder."""
        engine = SimulationEngine()
        emergency = _vehicle(
            "e-1",
            VehicleType.EMERGENCY,
            [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0)],
            path_index=2,
        )
        engine.vehicle_manager._vehicles = [emergency]

        first_light = engine.traffic_light_manager.get_light((3, 0))
        second_light = engine.traffic_light_manager.get_light((6, 0))
        assert first_light is not None
        assert second_light is not None
        first_light.preempted_by = emergency
        second_light.preempted_by = emergency

        calls: list[str] = []

        def fake_upcoming_positions(vehicle: Vehicle) -> set[tuple[int, int]]:
            calls.append(vehicle.id)
            return {(3, 0)}

        monkeypatch.setattr(
            engine,
            "_upcoming_intersection_positions",
            fake_upcoming_positions,
        )

        engine._cleanup_and_record_metrics()

        assert calls == ["e-1"]
        assert first_light.preempted_by is emergency
        assert second_light.preempted_by is None

    def test_state_snapshot(self) -> None:
        """Snapshot contains the complete frontend-facing simulation state."""
        engine = SimulationEngine()
        engine.state = SimulationState.RUNNING
        snapshot = engine.snapshot()

        assert snapshot.tick_count == 0
        assert snapshot.state == "running"
        assert snapshot.config == engine.config.model_dump()
        assert snapshot.grid["width"] == engine.grid.width
        assert isinstance(snapshot.vehicles, list)
        assert isinstance(snapshot.traffic_lights, list)
        assert snapshot.metrics == engine.metrics.to_dict()

    def test_get_metrics_returns_live_metrics_instance(self) -> None:
        """get_metrics returns the engine-owned metrics object."""
        engine = SimulationEngine()

        assert engine.get_metrics() is engine.metrics

    @pytest.mark.asyncio
    async def test_start_returns_immediately_when_already_running(self) -> None:
        """Calling start while already running exits without an extra tick loop."""
        engine = SimulationEngine()
        engine.state = SimulationState.RUNNING

        result = await engine.start()

        assert engine.state is SimulationState.RUNNING
        assert engine.tick_count == 0
        assert result.action == "start"
        assert result.applied is False
        assert result.state is SimulationState.RUNNING
        assert result.message == "Simulation is already running."

    @pytest.mark.asyncio
    async def test_start_rejects_when_paused(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A paused simulation must be resumed, not started again."""
        engine = SimulationEngine()
        engine.state = SimulationState.PAUSED

        async def fake_tick():
            pytest.fail("start() should reject a paused state before ticking")

        monkeypatch.setattr(engine, "tick", fake_tick)

        result = await engine.start()

        assert result.action == "start"
        assert result.applied is False
        assert result.state is SimulationState.PAUSED
        assert result.message == "Simulation is paused. Use resume instead of start."
        assert engine.state is SimulationState.PAUSED
        assert engine._run_task is None

    @pytest.mark.asyncio
    async def test_start_returns_immediately_and_tracks_background_task(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """start() schedules the run loop and returns before the loop exits."""
        engine = SimulationEngine()
        run_started = asyncio.Event()
        release_loop = asyncio.Event()

        async def fake_run_tick_loop() -> None:
            run_started.set()
            await release_loop.wait()

        monkeypatch.setattr(engine, "_run_tick_loop", fake_run_tick_loop)

        result = await engine.start()

        assert result.action == "start"
        assert result.applied is True
        assert result.state is SimulationState.RUNNING
        assert result.message == "Simulation started."
        assert engine.state is SimulationState.RUNNING
        assert engine._run_task is not None

        await run_started.wait()
        assert not engine._run_task.done()

        release_loop.set()
        await engine._run_task
        assert engine._run_task is None

    @pytest.mark.asyncio
    async def test_start_stop_simulation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Start loop ticks while running, idles while paused, and exits cleanly."""
        broadcasts: list[int] = []
        sleeps: list[float] = []

        async def broadcast_callback(snapshot) -> None:
            broadcasts.append(snapshot.tick_count)

        engine = SimulationEngine(broadcast_callback=broadcast_callback)

        async def fake_sleep(delay: float) -> None:
            sleeps.append(delay)
            if len(broadcasts) == 1 and engine.state is SimulationState.RUNNING:
                engine.pause()
            elif engine.state is SimulationState.PAUSED:
                engine.resume()
            elif len(broadcasts) >= 2:
                await engine.stop()

        monkeypatch.setattr("backend.simulation.engine.asyncio.sleep", fake_sleep)

        result = await engine.start()
        assert result.action == "start"
        assert result.applied is True
        assert result.state is SimulationState.RUNNING
        assert result.message == "Simulation started."

        assert engine._run_task is not None
        await engine._run_task

        assert broadcasts == [1, 2]
        assert 0.05 in sleeps
        assert 1.0 / engine.config.tick_speed in sleeps
        assert engine.state is SimulationState.STOPPED
        assert engine._run_task is None

    @pytest.mark.asyncio
    async def test_stop_cancels_and_awaits_background_task(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """stop() cancels the managed run task and waits for cleanup."""
        engine = SimulationEngine()
        tick_cancelled = asyncio.Event()

        async def fake_tick():
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                tick_cancelled.set()
                raise
            return engine.snapshot()

        monkeypatch.setattr(engine, "tick", fake_tick)

        start_result = await engine.start()
        assert start_result.applied is True
        assert engine._run_task is not None

        await asyncio.sleep(0)
        run_task = engine._run_task

        stop_result = await engine.stop()

        assert stop_result.action == "stop"
        assert stop_result.applied is True
        assert stop_result.state is SimulationState.STOPPED
        assert stop_result.message == "Simulation stopped."
        assert engine.state is SimulationState.STOPPED
        assert await asyncio.wait_for(tick_cancelled.wait(), timeout=1.0) is True
        assert run_task is not None
        assert run_task.cancelled()
        assert engine._run_task is None

    @pytest.mark.asyncio
    async def test_stop_clears_task_handle_when_callback_has_not_run(self) -> None:
        """stop() clears the task handle if callback-based cleanup has not happened."""
        engine = SimulationEngine()
        engine.state = SimulationState.RUNNING

        class PendingFinalizeTask:
            def __init__(self) -> None:
                self.cancel_called = False

            def done(self) -> bool:
                return False

            def cancel(self) -> None:
                self.cancel_called = True

            def __await__(self):
                async def _cancelled() -> None:
                    raise asyncio.CancelledError

                return _cancelled().__await__()

        run_task = PendingFinalizeTask()
        engine._run_task = cast(asyncio.Task[None], run_task)

        stop_result = await engine.stop()

        assert stop_result.action == "stop"
        assert stop_result.applied is True
        assert stop_result.state is SimulationState.STOPPED
        assert run_task.cancel_called is True
        assert engine._run_task is None

    @pytest.mark.asyncio
    async def test_run_loop_breaks_after_tick_stops_engine(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The run loop exits immediately when a tick stops the engine."""
        engine = SimulationEngine()
        sleeps: list[float] = []

        async def fake_tick():
            await engine.stop()
            return engine.snapshot()

        async def fake_sleep(delay: float) -> None:
            sleeps.append(delay)

        monkeypatch.setattr(engine, "tick", fake_tick)
        monkeypatch.setattr("backend.simulation.engine.asyncio.sleep", fake_sleep)

        start_result = await engine.start()
        assert start_result.applied is True
        assert engine._run_task is not None

        await engine._run_task

        assert sleeps == []
        assert engine.state is SimulationState.STOPPED
        assert engine._run_task is None

    @pytest.mark.asyncio
    async def test_finalize_run_task_handles_cancelled_task(self) -> None:
        """Cancelled run tasks reset engine state and clear the task handle."""
        engine = SimulationEngine()
        engine.state = SimulationState.RUNNING
        release_task = asyncio.Event()

        async def wait_forever() -> None:
            await release_task.wait()

        task = asyncio.create_task(wait_forever())
        engine._run_task = task
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        engine._finalize_run_task(task)

        assert engine.state is SimulationState.STOPPED
        assert engine._run_task is None

    @pytest.mark.asyncio
    async def test_finalize_run_task_handles_failed_task(self) -> None:
        """Failed run tasks reset engine state and clear the task handle."""
        engine = SimulationEngine()
        engine.state = SimulationState.RUNNING

        async def fail() -> None:
            raise RuntimeError("boom")

        task = asyncio.create_task(fail())
        engine._run_task = task

        with pytest.raises(RuntimeError, match="boom"):
            await task

        engine._finalize_run_task(task)

        assert engine.state is SimulationState.STOPPED
        assert engine._run_task is None

    @pytest.mark.asyncio
    async def test_broadcast_state_noops_without_callback(self) -> None:
        """Broadcast helper returns cleanly when no callback is configured."""
        engine = SimulationEngine()

        await engine._broadcast_state()

        assert engine.tick_count == 0

    def test_axis_for_step_raises_on_non_cardinal_move(self) -> None:
        """Axis resolution rejects diagonal or zero-length path steps."""
        with pytest.raises(ValueError, match="one-cell cardinal moves"):
            SimulationEngine._axis_for_step((0, 0), (1, 1))
        with pytest.raises(ValueError, match="one-cell cardinal moves"):
            SimulationEngine._axis_for_step((0, 0), (2, 0))
        with pytest.raises(ValueError, match="one-cell cardinal moves"):
            SimulationEngine._axis_for_step((0, 0), (0, 0))
