"""Metrics reporter -- exports collected metrics in various formats."""

from __future__ import annotations

import json
from typing import Any

from urban_flow.metrics.collector import MetricsCollector, MetricsSummary


class MetricsReporter:
    """Formats and exports simulation metrics."""

    def __init__(self, collector: MetricsCollector) -> None:
        self._collector = collector

    @property
    def summary(self) -> MetricsSummary:
        return self._collector.summary

    def to_dict(self) -> dict[str, Any]:
        """Return metrics as a plain dictionary."""
        s = self.summary
        return {
            "total_vehicles_spawned": s.total_vehicles_spawned,
            "total_vehicles_arrived": s.total_vehicles_arrived,
            "total_emergency_vehicles": s.total_emergency_vehicles,
            "average_travel_ticks": s.average_travel_ticks,
            "average_wait_ticks": s.average_wait_ticks,
            "total_preemptions": s.total_preemptions,
        }

    def to_json(self, indent: int = 2) -> str:
        """Return metrics as a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def print_summary(self) -> None:
        """Print a human-readable summary to stdout."""
        s = self.summary
        print("=== Simulation Metrics ===")
        print(f"  Vehicles spawned:    {s.total_vehicles_spawned}")
        print(f"  Vehicles arrived:    {s.total_vehicles_arrived}")
        print(f"  Emergency vehicles:  {s.total_emergency_vehicles}")
        print(f"  Avg travel (ticks):  {s.average_travel_ticks:.1f}")
        print(f"  Avg wait (ticks):    {s.average_wait_ticks:.1f}")
        print(f"  Signal preemptions:  {s.total_preemptions}")
