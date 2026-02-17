"""Metrics collector -- subscribes to simulation events and accumulates data."""

from __future__ import annotations

from dataclasses import dataclass, field

from urban_flow.engine.events import (
    EventBus,
    SimulationEvent,
    VehicleArrived,
    VehicleSpawned,
    VehicleWaiting,
    PreemptionStarted,
    PreemptionEnded,
)


@dataclass
class MetricsSummary:
    """Aggregated simulation metrics."""

    total_vehicles_spawned: int = 0
    total_vehicles_arrived: int = 0
    total_emergency_vehicles: int = 0
    total_wait_ticks: int = 0
    total_travel_ticks: int = 0
    total_preemptions: int = 0

    @property
    def average_travel_ticks(self) -> float:
        if self.total_vehicles_arrived == 0:
            return 0.0
        return self.total_travel_ticks / self.total_vehicles_arrived

    @property
    def average_wait_ticks(self) -> float:
        if self.total_vehicles_arrived == 0:
            return 0.0
        return self.total_wait_ticks / self.total_vehicles_arrived


class MetricsCollector:
    """Subscribes to events and builds a running MetricsSummary."""

    def __init__(self, event_bus: EventBus) -> None:
        self._summary = MetricsSummary()

        event_bus.subscribe(VehicleSpawned, self._on_event)
        event_bus.subscribe(VehicleArrived, self._on_event)
        event_bus.subscribe(VehicleWaiting, self._on_event)
        event_bus.subscribe(PreemptionStarted, self._on_event)
        event_bus.subscribe(PreemptionEnded, self._on_event)

    @property
    def summary(self) -> MetricsSummary:
        return self._summary

    def _on_event(self, event: SimulationEvent) -> None:
        if isinstance(event, VehicleSpawned):
            self._summary.total_vehicles_spawned += 1
            if event.is_emergency:
                self._summary.total_emergency_vehicles += 1
        elif isinstance(event, VehicleArrived):
            self._summary.total_vehicles_arrived += 1
            self._summary.total_travel_ticks += event.total_ticks
        elif isinstance(event, VehicleWaiting):
            self._summary.total_wait_ticks += 1
        elif isinstance(event, PreemptionStarted):
            self._summary.total_preemptions += 1
