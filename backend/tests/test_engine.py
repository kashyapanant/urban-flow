"""Tests for the simulation engine."""

from __future__ import annotations

import asyncio
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

        assert engine.config == SimulationConfig()
        assert engine.grid.width == 10
        assert engine.grid.height == 10
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

    @pytest.mark.asyncio
    async def test_start_breaks_before_sleep_when_tick_stops_engine(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The loop breaks without the tick-speed sleep when tick stops the engine."""
        engine = SimulationEngine()
        sleep_calls: list[float] = []

        async def fake_tick():
            engine.tick_count += 1
            await engine.stop()
            return engine.snapshot()

        async def fake_sleep(delay: float) -> None:
            sleep_calls.append(delay)

        monkeypatch.setattr(engine, "tick", fake_tick)
        monkeypatch.setattr("backend.simulation.engine.asyncio.sleep", fake_sleep)

        result = await engine.start()

        assert engine.tick_count == 1
        assert sleep_calls == []
        assert engine.state is SimulationState.STOPPED
        assert result.action == "start"
        assert result.applied is True
        assert result.state is SimulationState.RUNNING
        assert result.message == "Simulation started."

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

        assert broadcasts == [1, 2]
        assert 0.05 in sleeps
        assert 1.0 / engine.config.tick_speed in sleeps
        assert engine.state is SimulationState.STOPPED
        assert result.action == "start"
        assert result.applied is True
        assert result.state is SimulationState.RUNNING
        assert result.message == "Simulation started."

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
