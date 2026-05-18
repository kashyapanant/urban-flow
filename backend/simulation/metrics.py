"""Performance metrics tracking for the traffic simulation."""

from dataclasses import dataclass
from typing import Any

from .vehicle import Vehicle, VehicleType


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
        if self.normal_vehicle_count == 0:
            return 0.0
        return self.normal_total_ticks / self.normal_vehicle_count

    @property
    def emergency_avg_ticks(self) -> float:
        """Average travel time for emergency vehicles.

        Returns:
            Average ticks to destination for emergency vehicles
        """
        if self.emergency_vehicle_count == 0:
            return 0.0
        return self.emergency_total_ticks / self.emergency_vehicle_count

    @property
    def improvement(self) -> float:
        """Percentage improvement in travel time for emergency vehicles.

        Returns:
            Percentage fewer ticks for emergency vs normal vehicles
            Positive values indicate emergency vehicles are faster
        """
        normal_avg = self.normal_avg_ticks
        emergency_avg = self.emergency_avg_ticks

        if normal_avg == 0.0 or self.emergency_vehicle_count == 0:
            return 0.0
        return ((normal_avg - emergency_avg) / normal_avg) * 100.0

    def record_arrival(self, vehicle: Vehicle) -> None:
        """Record the arrival of a vehicle for metrics calculation.

        Args:
            vehicle: Vehicle that completed its journey
        """
        if vehicle.type is VehicleType.NORMAL:
            self.normal_total_ticks += vehicle.ticks_elapsed
            self.normal_vehicle_count += 1
        elif vehicle.type is VehicleType.EMERGENCY:
            self.emergency_total_ticks += vehicle.ticks_elapsed
            self.emergency_vehicle_count += 1
        else:
            raise ValueError(f"Unsupported vehicle type: {vehicle.type!r}")

        self.total_completed += 1

    def record_multiple_arrivals(self, vehicles: list[Vehicle]) -> None:
        """Record arrivals for multiple vehicles.

        Args:
            vehicles: List of vehicles that completed their journeys
        """
        for vehicle in vehicles:
            self.record_arrival(vehicle)

    def reset(self) -> None:
        """Reset all metrics to initial state.

        Useful for restarting simulations or clearing data.
        """
        self.normal_total_ticks = 0
        self.normal_vehicle_count = 0
        self.emergency_total_ticks = 0
        self.emergency_vehicle_count = 0
        self.total_completed = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for serialization.

        Returns:
            Dictionary representation for API responses and frontend
        """
        return {
            "normal_avg_ticks": self.normal_avg_ticks,
            "emergency_avg_ticks": self.emergency_avg_ticks,
            "improvement": self.improvement,
            "total_completed": self.total_completed,
        }
