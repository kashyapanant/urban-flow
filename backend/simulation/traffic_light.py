"""Traffic light system for intersection control and emergency preemption."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from .vehicle import Vehicle


class Axis(Enum):
    """Traffic light axes for intersection control."""

    NS = "north_south"  # North-South axis
    EW = "east_west"  # East-West axis


class Phase(Enum):
    """Traffic light phases within an axis cycle."""

    GREEN = "green"
    LEFT_TURN = "leftTurn"
    YELLOW = "yellow"
    RED = "red"


@dataclass
class TrafficLight:
    """A traffic light at an intersection.

    Each intersection has a dual-axis traffic light that cycles through
    four phases per axis. Only one axis is active at a time.
    """

    id: str
    position: tuple[int, int]
    active_axis: Axis
    current_phase: Phase
    phase_duration: int
    ticks_in_phase: int = 0
    preempted_by: Vehicle | None = None

    # Ordered phase progression within one axis cycle.
    _PHASE_SEQUENCE: ClassVar[tuple[Phase, ...]] = (
        Phase.GREEN,
        Phase.LEFT_TURN,
        Phase.YELLOW,
        Phase.RED,
    )

    # Directions that belong to each axis.
    _AXIS_FOR_DIRECTION: ClassVar[dict[str, Axis]] = {
        "north": Axis.NS,
        "south": Axis.NS,
        "east": Axis.EW,
        "west": Axis.EW,
    }

    # Phases that allow a vehicle to enter.
    _ENTRY_PHASES: ClassVar[frozenset[Phase]] = frozenset(
        {Phase.GREEN, Phase.LEFT_TURN}
    )

    def tick(self) -> None:
        """Advance the traffic light by one tick.

        Increments ``ticks_in_phase``. When the count reaches
        ``phase_duration``, the light transitions to the next phase in the
        sequence GREEN → LEFT_TURN → YELLOW → RED. When RED completes, the
        active axis flips (NS ↔ EW) and the new axis starts at GREEN.

        Preemption does **not** alter this method's behavior — it operates
        only through the phase/axis state that ``request_preemption`` sets up.
        The normal tick loop therefore drives the forced yellow → red → green
        transition transparently once preemption positions the light correctly.
        """
        self.ticks_in_phase += 1
        if self.ticks_in_phase < self.phase_duration:
            return

        self.ticks_in_phase = 0
        current_index = self._PHASE_SEQUENCE.index(self.current_phase)
        next_index = (current_index + 1) % len(self._PHASE_SEQUENCE)
        self.current_phase = self._PHASE_SEQUENCE[next_index]

        if self.current_phase is Phase.GREEN:
            # RED just completed — flip axis for the new cycle.
            self.active_axis = Axis.EW if self.active_axis is Axis.NS else Axis.NS

    def can_enter(self, direction: str) -> bool:
        """Check whether a vehicle travelling in ``direction`` may enter.

        Entry is permitted when the direction's axis matches ``active_axis``
        **and** the current phase is ``GREEN`` or ``LEFT_TURN``. Yellow means
        do-not-enter; red means stop.

        Args:
            direction: Cardinal movement direction of the approaching vehicle.
                Must be one of ``"north"``, ``"south"``, ``"east"``,
                ``"west"``. An unrecognised direction is treated as belonging
                to no active axis and therefore always returns ``False``.

        Returns:
            ``True`` if the vehicle may proceed through the intersection,
            ``False`` otherwise.
        """
        axis = self._AXIS_FOR_DIRECTION.get(direction)
        if axis is None:
            return False
        return axis is self.active_axis and self.current_phase in self._ENTRY_PHASES

    def request_preemption(
        self,
        vehicle: Vehicle,
        required_axis: Axis,
        preemption_yellow_duration: int,
    ) -> bool:
        """Request emergency preemption for an approaching vehicle.

        Preemption grants the intersection's green phase to ``required_axis``
        as quickly as possible:

        1. If another vehicle already holds preemption, the request is denied
           (first-come-first-served).
        2. If ``active_axis`` already matches ``required_axis`` **and** the
           current phase is ``GREEN`` or ``LEFT_TURN``, the vehicle is
           registered and no phase change is needed — the light already serves
           the right direction.
        3. If ``active_axis`` already matches ``required_axis`` but the phase
           is ``YELLOW`` or ``RED``, the phase is immediately reset to
           ``GREEN`` on the same axis. Going through the normal YELLOW→RED
           path would flip the axis on RED completion, landing on the wrong
           axis.
        4. If ``active_axis`` is the cross-axis, the light is forced into a
           short YELLOW transition by setting ``ticks_in_phase`` so that
           exactly ``preemption_yellow_duration`` ticks remain. The normal
           ``tick()`` loop then advances YELLOW → RED → (axis flip) → GREEN,
           putting ``required_axis`` at green automatically.

        Args:
            vehicle: Emergency vehicle requesting preemption. Stored in
                ``preempted_by`` when granted.
            required_axis: The axis that must be green for the vehicle to
                proceed. Derived by the caller from the vehicle's direction of
                travel (NS for north/south movement, EW for east/west).
            preemption_yellow_duration: Number of ticks the forced YELLOW phase
                should last before the axis flips. Must be >= 1 and <=
                ``phase_duration``. Values larger than ``phase_duration`` are
                rejected with ``ValueError`` because ``tick()`` advances phases
                in units of ``phase_duration`` — honoring a longer yellow would
                require state the tick loop does not carry.

        Returns:
            ``True`` if preemption was granted (this vehicle is now the
            registered preemptor), ``False`` if another vehicle already holds
            preemption on this intersection.

        Raises:
            ValueError: If ``preemption_yellow_duration`` is less than 1 or
                greater than ``phase_duration``. Not raised when the same
                holder re-requests (no-op path skips validation).
        """
        if self.preempted_by is vehicle:
            # Same holder re-requesting — transition already in progress, no-op.
            # Duration argument is irrelevant here; skip validation entirely.
            return True

        if not 1 <= preemption_yellow_duration <= self.phase_duration:
            raise ValueError(
                f"preemption_yellow_duration must be between 1 and "
                f"phase_duration ({self.phase_duration}), "
                f"got {preemption_yellow_duration}."
            )

        if self.preempted_by is not None:
            # A different vehicle holds preemption — deny.
            return False

        self.preempted_by = vehicle

        already_serving = (
            self.active_axis is required_axis
            and self.current_phase in self._ENTRY_PHASES
        )
        if already_serving:
            return True

        if self.active_axis is required_axis:
            # Correct axis but phase is YELLOW or RED — the normal YELLOW→RED
            # path would flip the axis on RED completion, landing on the *wrong*
            # axis. Instead, immediately restart GREEN on the already-correct
            # axis so the vehicle can enter on the next tick.
            self.current_phase = Phase.GREEN
            self.ticks_in_phase = 0
            return True

        # Cross-axis case: force a short YELLOW so the normal tick loop carries
        # the light through YELLOW → RED → (axis flip) → GREEN, putting
        # required_axis at green automatically.
        self.current_phase = Phase.YELLOW
        # Position ticks_in_phase so exactly preemption_yellow_duration ticks
        # remain: tick() increments first, so set the counter to
        # phase_duration - preemption_yellow_duration.
        self.ticks_in_phase = self.phase_duration - preemption_yellow_duration
        return True

    def release_preemption(self) -> None:
        """Release emergency preemption and resume normal cycling.

        Clears ``preempted_by``. The light continues from its current phase
        and axis without any forced transition — the normal ``tick()`` loop
        takes over immediately.
        """
        self.preempted_by = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the traffic light to a dictionary for serialization.

        The returned mapping always includes these keys:
        ``id``, ``position``, ``active_axis``, ``current_phase``,
        ``phase_duration``, ``ticks_in_phase``, ``preempted_by``.

        ``active_axis`` and ``current_phase`` are enum value strings.
        ``preempted_by`` is the vehicle ID string when preemption is active,
        or ``None`` otherwise.

        Returns:
            JSON-serializable traffic-light payload for snapshots/API
            responses.
        """
        preempted_by_id: str | None = None
        if self.preempted_by is not None:
            ident = getattr(self.preempted_by, "id", None)
            preempted_by_id = str(ident) if ident is not None else None

        return {
            "id": self.id,
            "position": self.position,
            "active_axis": self.active_axis.value,
            "current_phase": self.current_phase.value,
            "phase_duration": self.phase_duration,
            "ticks_in_phase": self.ticks_in_phase,
            "preempted_by": preempted_by_id,
        }


class TrafficLightManager:
    """Manages all traffic lights in the simulation.

    Handles traffic light updates, preemption requests, and movement permissions.
    """

    def __init__(self, intersections: list[tuple[int, int]], phase_duration: int = 3):
        """Initialize traffic lights at all intersections.

        Args:
            intersections: List of (x, y) coordinates for intersections
            phase_duration: Default ticks per phase
        """
        raise NotImplementedError("TrafficLightManager.__init__()")

    def tick(self) -> None:
        """Advance all traffic lights by one tick."""
        raise NotImplementedError("TrafficLightManager.tick(")

    def request_preemption(
        self,
        position: tuple[int, int],
        vehicle: Vehicle,
        required_axis: Axis,
        preemption_yellow_duration: int,
    ) -> bool:
        """Request emergency preemption at an intersection.

        Args:
            position: Intersection coordinates
            vehicle: Emergency vehicle requesting preemption
            required_axis: The axis that must be green for the vehicle to
                proceed (NS for north/south movement, EW for east/west).
            preemption_yellow_duration: Ticks for yellow transition

        Returns:
            True if preemption was granted
        """
        raise NotImplementedError("TrafficLightManager.request_preemption(")

    def release_preemption(self, position: tuple[int, int]) -> None:
        """Release emergency preemption at an intersection.

        Args:
            position: Intersection coordinates
        """
        raise NotImplementedError("TrafficLightManager.release_preemption(")

    def can_vehicle_enter(self, position: tuple[int, int], direction: str) -> bool:
        """Check if a vehicle can enter an intersection.

        Args:
            position: Intersection coordinates
            direction: Vehicle movement direction

        Returns:
            True if vehicle can proceed
        """
        raise NotImplementedError("TrafficLightManager.can_vehicle_enter(")

    def get_light(self, position: tuple[int, int]) -> TrafficLight | None:
        """Get the traffic light at a specific position.

        Args:
            position: Intersection coordinates

        Returns:
            TrafficLight or None if no light exists
        """
        raise NotImplementedError("TrafficLightManager.get_light(")

    def get_all(self) -> list[TrafficLight]:
        """Get all traffic lights.

        Returns:
            List of all traffic lights in the simulation
        """
        raise NotImplementedError("TrafficLightManager.get_all(")

    def set_phase_duration(self, duration: int) -> None:
        """Update phase duration for all traffic lights.

        Args:
            duration: New phase duration in ticks
        """
        raise NotImplementedError("TrafficLightManager.set_phase_duration(")

    def snapshot(self) -> list[dict[str, Any]]:
        """Create a serializable snapshot of all traffic lights.

        Returns:
            List of traffic light dictionaries for frontend
        """
        raise NotImplementedError("TrafficLightManager.snapshot(")
