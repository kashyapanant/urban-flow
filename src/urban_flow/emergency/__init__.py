"""Emergency vehicle handling -- detection, routing, and signal preemption."""

from urban_flow.emergency.detector import EmergencyDetector
from urban_flow.emergency.router import EmergencyRouter
from urban_flow.emergency.preemption import PreemptionManager

__all__ = ["EmergencyDetector", "EmergencyRouter", "PreemptionManager"]
