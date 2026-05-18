"""Tests for the metrics module - P1-MET-01."""

from typing import cast

import pytest

from backend.simulation.metrics import Metrics
from backend.simulation.vehicle import Vehicle, VehicleType


def _vehicle(
    *,
    vehicle_id: str,
    vehicle_type: VehicleType,
    ticks_elapsed: int,
) -> Vehicle:
    """Build a minimal vehicle for metrics recording tests."""
    return Vehicle(
        id=vehicle_id,
        type=vehicle_type,
        position=(0, 0),
        origin=(0, 0),
        destination=(0, 0),
        path=[(0, 0)],
        ticks_elapsed=ticks_elapsed,
    )


class TestMetrics:
    """Tests for Metrics aggregate calculations and serialization."""

    def test_fresh_metrics_exposes_zero_values_and_expected_dict_shape(self) -> None:
        """A fresh accumulator reports zeroed derived metrics and payload shape."""
        metrics = Metrics()

        assert metrics.normal_avg_ticks == 0.0
        assert metrics.emergency_avg_ticks == 0.0
        assert metrics.improvement == 0.0
        assert metrics.total_completed == 0
        assert metrics.to_dict() == {
            "normal_avg_ticks": 0.0,
            "emergency_avg_ticks": 0.0,
            "improvement": 0.0,
            "total_completed": 0,
        }

    def test_record_arrival_updates_normal_accumulators(self) -> None:
        """Recording a normal arrival updates only normal totals and counts."""
        metrics = Metrics()
        vehicle = _vehicle(
            vehicle_id="normal-1",
            vehicle_type=VehicleType.NORMAL,
            ticks_elapsed=12,
        )

        metrics.record_arrival(vehicle)

        assert metrics.normal_total_ticks == 12
        assert metrics.normal_vehicle_count == 1
        assert metrics.emergency_total_ticks == 0
        assert metrics.emergency_vehicle_count == 0
        assert metrics.total_completed == 1
        assert metrics.normal_avg_ticks == 12.0
        assert metrics.emergency_avg_ticks == 0.0
        assert metrics.improvement == 0.0

    def test_record_arrival_updates_emergency_accumulators(self) -> None:
        """Recording an emergency arrival updates only emergency totals and counts."""
        metrics = Metrics()
        vehicle = _vehicle(
            vehicle_id="emergency-1",
            vehicle_type=VehicleType.EMERGENCY,
            ticks_elapsed=7,
        )

        metrics.record_arrival(vehicle)

        assert metrics.normal_total_ticks == 0
        assert metrics.normal_vehicle_count == 0
        assert metrics.emergency_total_ticks == 7
        assert metrics.emergency_vehicle_count == 1
        assert metrics.total_completed == 1
        assert metrics.normal_avg_ticks == 0.0
        assert metrics.emergency_avg_ticks == 7.0
        assert metrics.improvement == 0.0

    def test_record_multiple_arrivals_updates_running_averages(self) -> None:
        """Batch recording updates both categories and computes averages."""
        metrics = Metrics()
        vehicles = [
            _vehicle(
                vehicle_id="normal-1",
                vehicle_type=VehicleType.NORMAL,
                ticks_elapsed=10,
            ),
            _vehicle(
                vehicle_id="normal-2",
                vehicle_type=VehicleType.NORMAL,
                ticks_elapsed=14,
            ),
            _vehicle(
                vehicle_id="emergency-1",
                vehicle_type=VehicleType.EMERGENCY,
                ticks_elapsed=6,
            ),
            _vehicle(
                vehicle_id="emergency-2",
                vehicle_type=VehicleType.EMERGENCY,
                ticks_elapsed=8,
            ),
        ]

        metrics.record_multiple_arrivals(vehicles)

        assert metrics.normal_avg_ticks == 12.0
        assert metrics.emergency_avg_ticks == 7.0
        assert metrics.improvement == pytest.approx(41.6666666667)
        assert metrics.total_completed == 4

    def test_improvement_can_be_negative_when_emergency_vehicles_are_slower(
        self,
    ) -> None:
        """Improvement stays negative instead of clamping when emergency is worse."""
        metrics = Metrics()
        metrics.record_arrival(
            _vehicle(
                vehicle_id="normal-1",
                vehicle_type=VehicleType.NORMAL,
                ticks_elapsed=5,
            )
        )
        metrics.record_arrival(
            _vehicle(
                vehicle_id="emergency-1",
                vehicle_type=VehicleType.EMERGENCY,
                ticks_elapsed=8,
            )
        )

        assert metrics.improvement == pytest.approx(-60.0)

    def test_record_multiple_arrivals_matches_repeated_single_recording(self) -> None:
        """Batch recording delegates consistently to single-arrival logic."""
        vehicles = [
            _vehicle(
                vehicle_id="normal-1",
                vehicle_type=VehicleType.NORMAL,
                ticks_elapsed=9,
            ),
            _vehicle(
                vehicle_id="emergency-1",
                vehicle_type=VehicleType.EMERGENCY,
                ticks_elapsed=4,
            ),
            _vehicle(
                vehicle_id="normal-2",
                vehicle_type=VehicleType.NORMAL,
                ticks_elapsed=15,
            ),
        ]
        batch_metrics = Metrics()
        single_metrics = Metrics()

        batch_metrics.record_multiple_arrivals(vehicles)
        for vehicle in vehicles:
            single_metrics.record_arrival(vehicle)

        assert batch_metrics == single_metrics

    def test_reset_clears_totals_counts_and_serialized_output(self) -> None:
        """Reset restores all counters and derived values to the initial state."""
        metrics = Metrics()
        metrics.record_multiple_arrivals(
            [
                _vehicle(
                    vehicle_id="normal-1",
                    vehicle_type=VehicleType.NORMAL,
                    ticks_elapsed=11,
                ),
                _vehicle(
                    vehicle_id="emergency-1",
                    vehicle_type=VehicleType.EMERGENCY,
                    ticks_elapsed=7,
                ),
            ]
        )

        metrics.reset()

        assert metrics == Metrics()
        assert metrics.to_dict() == {
            "normal_avg_ticks": 0.0,
            "emergency_avg_ticks": 0.0,
            "improvement": 0.0,
            "total_completed": 0,
        }

    def test_record_arrival_raises_for_unsupported_vehicle_type(self) -> None:
        """Unknown vehicle types are rejected explicitly."""
        metrics = Metrics()
        invalid_vehicle = _vehicle(
            vehicle_id="invalid-1",
            vehicle_type=VehicleType.NORMAL,
            ticks_elapsed=9,
        )
        invalid_vehicle.type = cast(VehicleType, "bus")

        with pytest.raises(ValueError, match="Unsupported vehicle type"):
            metrics.record_arrival(invalid_vehicle)
