"""Performance metrics tracking for the traffic simulation."""

from dataclasses import dataclass
from typing import Any

from .vehicle import Vehicle


@dataclass
class Metrics:
    """Tracks and calculates performance metrics for the simulation.

    Maintains running averages of travel times for normal and emergency
    vehicles to measure the effectiveness of signal preemption.
    """

    normal_total_ticks: int = 0
    normal_vehicle_count: int = 0
    emergency_total_ticks: int = 0
    emergency_vehicle_count: int = 0
    total_completed: int = 0

    @property
    def normal_avg_ticks(self) -> float:
        """Average travel time for normal vehicles.

        Returns:
            Average ticks to destination for normal vehicles
        """
        raise NotImplementedError("Metrics.normal_avg_ticks calculation")

    @property
    def emergency_avg_ticks(self) -> float:
        """Average travel time for emergency vehicles.

        Returns:
            Average ticks to destination for emergency vehicles
        """
        raise NotImplementedError("Metrics.emergency_avg_ticks calculation")

    @property
    def improvement(self) -> float:
        """Percentage improvement in travel time for emergency vehicles.

        Returns:
            Percentage fewer ticks for emergency vs normal vehicles
            Positive values indicate emergency vehicles are faster
        """
        raise NotImplementedError("Metrics.improvement calculation")

    def record_arrival(self, vehicle: Vehicle) -> None:
        """Record the arrival of a vehicle for metrics calculation.

        Args:
            vehicle: Vehicle that completed its journey
        """
        raise NotImplementedError("Metrics.record_arrival(")

    def record_multiple_arrivals(self, vehicles: list[Vehicle]) -> None:
        """Record arrivals for multiple vehicles.

        Args:
            vehicles: List of vehicles that completed their journeys
        """
        raise NotImplementedError("Metrics.record_multiple_arrivals(")

    def reset(self) -> None:
        """Reset all metrics to initial state.

        Useful for restarting simulations or clearing data.
        """
        raise NotImplementedError("Metrics.reset(")

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for serialization.

        Returns:
            Dictionary representation for API responses and frontend
        """
        raise NotImplementedError("Metrics.to_dict(")
