"""Core domain models for UrbanFlow.

This package contains pure Python domain entities with zero external
dependencies.  Every other UrbanFlow package may depend on ``core``,
but ``core`` never imports from sibling packages.
"""

from urban_flow.core.types import Direction, Position, SignalState, VehicleType
from urban_flow.core.road import Road, Cell
from urban_flow.core.intersection import Intersection
from urban_flow.core.vehicle import Vehicle, EmergencyVehicle
from urban_flow.core.signal import SignalPhase, SignalPlan
from urban_flow.core.grid import RoadNetwork

__all__ = [
    "Direction",
    "Position",
    "SignalState",
    "VehicleType",
    "Road",
    "Cell",
    "Intersection",
    "Vehicle",
    "EmergencyVehicle",
    "SignalPhase",
    "SignalPlan",
    "RoadNetwork",
]
