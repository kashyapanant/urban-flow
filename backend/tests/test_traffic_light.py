"""Tests for the traffic light module — P1-TL-01 (TrafficLight core)."""

import json
from unittest.mock import Mock

import pytest

from backend.simulation.traffic_light import Axis, Phase, TrafficLight
from backend.simulation.vehicle import Vehicle


def _light(
    *,
    active_axis: Axis = Axis.NS,
    current_phase: Phase = Phase.GREEN,
    phase_duration: int = 3,
    ticks_in_phase: int = 0,
    preempted_by: Vehicle | None = None,
) -> TrafficLight:
    """Build a TrafficLight at (1, 1) with configurable phase state."""
    return TrafficLight(
        id="tl-1",
        position=(1, 1),
        active_axis=active_axis,
        current_phase=current_phase,
        phase_duration=phase_duration,
        ticks_in_phase=ticks_in_phase,
        preempted_by=preempted_by,
    )


# ---------------------------------------------------------------------------
# TrafficLight.tick
# ---------------------------------------------------------------------------


class TestTrafficLightTick:
    """Tests for TrafficLight.tick — phase sequence and axis flip."""

    def test_tick_increments_ticks_in_phase_before_duration_elapsed(self) -> None:
        """While below phase_duration, only ticks_in_phase increases."""
        # Arrange
        light = _light(phase_duration=4, ticks_in_phase=0)

        # Act
        light.tick()

        # Assert
        assert light.ticks_in_phase == 1
        assert light.current_phase is Phase.GREEN
        assert light.active_axis is Axis.NS

    def test_tick_advances_to_next_phase_when_duration_elapsed(self) -> None:
        """When ticks reach phase_duration, phase advances and counter resets."""
        # Arrange — one tick away from rollover
        light = _light(phase_duration=2, ticks_in_phase=1)

        # Act
        light.tick()

        # Assert
        assert light.ticks_in_phase == 0
        assert light.current_phase is Phase.LEFT_TURN

    @pytest.mark.parametrize(
        "start_phase,expected_next",
        [
            (Phase.GREEN, Phase.LEFT_TURN),
            (Phase.LEFT_TURN, Phase.YELLOW),
            (Phase.YELLOW, Phase.RED),
        ],
    )
    def test_tick_phase_sequence_before_red_to_green(
        self, start_phase: Phase, expected_next: Phase
    ) -> None:
        """GREEN→LEFT_TURN→YELLOW→RED in order (phase_duration=1 per step)."""
        # Arrange
        light = _light(
            current_phase=start_phase,
            phase_duration=1,
            ticks_in_phase=0,
        )

        # Act
        light.tick()

        # Assert
        assert light.current_phase is expected_next
        assert light.ticks_in_phase == 0

    def test_tick_flips_active_axis_when_transitioning_red_to_green(self) -> None:
        """Completing RED rolls to GREEN and flips NS↔EW."""
        # Arrange — phase_duration=1 so one tick completes RED
        light = _light(
            active_axis=Axis.NS,
            current_phase=Phase.RED,
            phase_duration=1,
            ticks_in_phase=0,
        )

        # Act
        light.tick()

        # Assert
        assert light.current_phase is Phase.GREEN
        assert light.active_axis is Axis.EW

    def test_tick_full_cycle_ns_green_through_red_flips_axis_to_ew_green(
        self,
    ) -> None:
        """Four duration-1 ticks: GREEN→LEFT→YELLOW→RED→GREEN with axis NS→EW."""
        # Arrange
        light = _light(
            active_axis=Axis.NS,
            current_phase=Phase.GREEN,
            phase_duration=1,
            ticks_in_phase=0,
        )
        v = Mock(spec=Vehicle)
        light.preempted_by = v

        # Act
        light.tick()  # LEFT_TURN
        light.tick()  # YELLOW
        light.tick()  # RED
        light.tick()  # GREEN + flip

        # Assert
        assert light.current_phase is Phase.GREEN
        assert light.active_axis is Axis.EW
        assert light.ticks_in_phase == 0
        assert light.preempted_by is v

    def test_tick_second_red_completion_flips_axis_back_to_ns(self) -> None:
        """After EW cycle completes RED, next GREEN is on NS again."""
        # Arrange — already at EW GREEN (one tick past a full NS→EW cycle)
        light = _light(
            active_axis=Axis.EW,
            current_phase=Phase.GREEN,
            phase_duration=1,
            ticks_in_phase=0,
        )

        # Act — run EW through RED
        light.tick()
        light.tick()
        light.tick()
        light.tick()

        # Assert
        assert light.current_phase is Phase.GREEN
        assert light.active_axis is Axis.NS

    def test_tick_high_phase_duration_requires_all_ticks_before_rollover(
        self,
    ) -> None:
        """With phase_duration=100, 99 ticks stay in phase; 100th advances."""
        # Arrange
        light = _light(phase_duration=100, ticks_in_phase=0)

        # Act
        for _ in range(99):
            light.tick()

        # Assert — still GREEN, counter at 99
        assert light.current_phase is Phase.GREEN
        assert light.ticks_in_phase == 99

        # Act — 100th tick rolls
        light.tick()

        # Assert
        assert light.current_phase is Phase.LEFT_TURN
        assert light.ticks_in_phase == 0

    def test_tick_when_ticks_in_phase_already_past_duration_still_advances_phase(
        self,
    ) -> None:
        """If state is inconsistent (counter already ≥ duration), tick still rolls once.

        Defensive: simulates corrupted or restored state without clamping.
        """
        # Arrange — would normally be invalid mid-phase
        light = _light(phase_duration=3, current_phase=Phase.YELLOW, ticks_in_phase=5)

        # Act
        light.tick()

        # Assert — rolled to next phase, counter reset
        assert light.current_phase is Phase.RED
        assert light.ticks_in_phase == 0

    @pytest.mark.parametrize("phase_duration", [0, 1])
    def test_tick_phase_duration_boundary_advances_every_tick_when_zero_or_one(
        self, phase_duration: int
    ) -> None:
        """duration 0: every tick advances phase (degenerate). duration 1: same."""
        # Arrange
        light = _light(
            current_phase=Phase.GREEN,
            phase_duration=phase_duration,
            ticks_in_phase=0,
        )

        # Act
        light.tick()

        # Assert
        assert light.current_phase is Phase.LEFT_TURN
        assert light.ticks_in_phase == 0


# ---------------------------------------------------------------------------
# TrafficLight.can_enter
# ---------------------------------------------------------------------------


class TestTrafficLightCanEnter:
    """Tests for TrafficLight.can_enter — axis and phase gating."""

    @pytest.mark.parametrize("direction", ["north", "south"])
    def test_can_enter_true_when_ns_active_and_green_or_left_turn(
        self, direction: str
    ) -> None:
        """NS directions may enter when axis is NS and phase allows."""
        # Arrange
        for phase in (Phase.GREEN, Phase.LEFT_TURN):
            light = _light(active_axis=Axis.NS, current_phase=phase)

            # Act
            ok = light.can_enter(direction)

            # Assert
            assert ok is True

    @pytest.mark.parametrize("direction", ["east", "west"])
    def test_can_enter_true_when_ew_active_and_green_or_left_turn(
        self, direction: str
    ) -> None:
        """EW directions may enter when axis is EW and phase allows."""
        # Arrange
        for phase in (Phase.GREEN, Phase.LEFT_TURN):
            light = _light(active_axis=Axis.EW, current_phase=phase)

            # Act
            ok = light.can_enter(direction)

            # Assert
            assert ok is True

    @pytest.mark.parametrize(
        "phase",
        [Phase.YELLOW, Phase.RED],
    )
    def test_can_enter_false_when_entry_phase_not_green_or_left(
        self, phase: Phase
    ) -> None:
        """YELLOW and RED deny entry even when axis matches."""
        # Arrange
        light = _light(active_axis=Axis.NS, current_phase=phase)

        # Act
        ok = light.can_enter("north")

        # Assert
        assert ok is False

    def test_can_enter_false_when_axis_mismatch(self) -> None:
        """Correct phase but wrong axis denies entry."""
        # Arrange
        light = _light(active_axis=Axis.EW, current_phase=Phase.GREEN)

        # Act
        ok = light.can_enter("north")

        # Assert
        assert ok is False

    @pytest.mark.parametrize("bad_direction", ["", "northeast", "up"])
    def test_can_enter_false_for_unknown_direction(self, bad_direction: str) -> None:
        """Unrecognised direction string never grants entry."""
        # Arrange
        light = _light(active_axis=Axis.NS, current_phase=Phase.GREEN)

        # Act
        ok = light.can_enter(bad_direction)

        # Assert
        assert ok is False


# ---------------------------------------------------------------------------
# TrafficLight.request_preemption
# ---------------------------------------------------------------------------


class TestTrafficLightRequestPreemption:
    """Tests for TrafficLight.request_preemption — FCFS and yellow forcing."""

    def test_request_preemption_denied_when_other_vehicle_holds(self) -> None:
        """Second vehicle is denied while preempted_by points elsewhere."""
        # Arrange
        holder = Mock(spec=Vehicle)
        holder.id = "h"
        other = Mock(spec=Vehicle)
        other.id = "o"
        light = _light(preempted_by=holder)

        # Act
        result = light.request_preemption(other, 2)

        # Assert
        assert result is False
        assert light.preempted_by is holder

    def test_request_preemption_grants_when_already_in_entry_phase(self) -> None:
        """GREEN: register vehicle without changing phase."""
        # Arrange
        light = _light(current_phase=Phase.GREEN, preempted_by=None)
        v = Mock(spec=Vehicle)
        v.id = "em1"

        # Act
        result = light.request_preemption(v, 5)

        # Assert
        assert result is True
        assert light.preempted_by is v
        assert light.current_phase is Phase.GREEN

    def test_request_preemption_forces_yellow_when_not_in_entry_phase(self) -> None:
        """RED forces YELLOW and sets ticks_in_phase for remaining yellow ticks."""
        # Arrange
        light = _light(
            current_phase=Phase.RED,
            phase_duration=10,
            ticks_in_phase=0,
            preempted_by=None,
        )
        v = Mock(spec=Vehicle)
        v.id = "em1"

        # Act
        result = light.request_preemption(v, 3)

        # Assert
        assert result is True
        assert light.preempted_by is v
        assert light.current_phase is Phase.YELLOW
        assert light.ticks_in_phase == 7

    def test_request_preemption_same_vehicle_can_reenter_when_already_holder(
        self,
    ) -> None:
        """preempted_by is same vehicle — not treated as conflict."""
        # Arrange
        v = Mock(spec=Vehicle)
        v.id = "em1"
        light = _light(current_phase=Phase.GREEN, preempted_by=v)

        # Act
        result = light.request_preemption(v, 2)

        # Assert
        assert result is True
        assert light.preempted_by is v

    def test_request_preemption_ticks_clamped_when_yellow_longer_than_phase_duration(
        self,
    ) -> None:
        """Large preemption_yellow_duration yields ticks_in_phase 0."""
        # Arrange
        light = _light(
            current_phase=Phase.RED,
            phase_duration=5,
            ticks_in_phase=0,
            preempted_by=None,
        )
        v = Mock(spec=Vehicle)

        # Act
        light.request_preemption(v, 99)

        # Assert
        assert light.ticks_in_phase == 0
        assert light.current_phase is Phase.YELLOW


# ---------------------------------------------------------------------------
# TrafficLight.release_preemption
# ---------------------------------------------------------------------------


class TestTrafficLightReleasePreemption:
    """Tests for TrafficLight.release_preemption."""

    def test_release_preemption_clears_holder(self) -> None:
        """preempted_by becomes None; phase unchanged."""
        # Arrange
        v = Mock(spec=Vehicle)
        v.id = "em1"
        light = _light(current_phase=Phase.GREEN, preempted_by=v)

        # Act
        light.release_preemption()

        # Assert
        assert light.preempted_by is None
        assert light.current_phase is Phase.GREEN

    def test_release_preemption_when_already_clear_is_no_op(self) -> None:
        """Calling release with no holder is safe and leaves state unchanged."""
        # Arrange
        light = _light(current_phase=Phase.YELLOW, ticks_in_phase=2)

        # Act
        light.release_preemption()

        # Assert
        assert light.preempted_by is None
        assert light.current_phase is Phase.YELLOW
        assert light.ticks_in_phase == 2

    def test_release_preemption_is_idempotent(self) -> None:
        """Second call after clear does not error and does not mutate phase."""
        # Arrange
        v = Mock(spec=Vehicle)
        light = _light(current_phase=Phase.RED, preempted_by=v)

        # Act
        light.release_preemption()
        light.release_preemption()

        # Assert
        assert light.preempted_by is None
        assert light.current_phase is Phase.RED

    def test_release_preemption_only_clears_holder_preserves_phase_and_ticks(
        self,
    ) -> None:
        """Doc contract: normal cycling continues; only preempted_by is cleared."""
        # Arrange
        v = Mock(spec=Vehicle)
        light = _light(
            active_axis=Axis.EW,
            current_phase=Phase.YELLOW,
            phase_duration=5,
            ticks_in_phase=3,
            preempted_by=v,
        )

        # Act
        light.release_preemption()

        # Assert
        assert light.preempted_by is None
        assert light.active_axis is Axis.EW
        assert light.current_phase is Phase.YELLOW
        assert light.ticks_in_phase == 3


# ---------------------------------------------------------------------------
# TrafficLight.to_dict
# ---------------------------------------------------------------------------


class TestTrafficLightToDict:
    """Tests for TrafficLight.to_dict — snapshot payload."""

    def test_to_dict_includes_expected_keys_and_enum_values(self) -> None:
        """Structure and enum value strings for JSON-friendly output."""
        # Arrange
        light = _light()

        # Act
        d = light.to_dict()

        # Assert
        assert d == {
            "id": "tl-1",
            "position": (1, 1),
            "active_axis": "north_south",
            "current_phase": "green",
            "phase_duration": 3,
            "ticks_in_phase": 0,
            "preempted_by": None,
        }

    def test_to_dict_preempted_by_vehicle_id(self) -> None:
        """preempted_by serializes vehicle id string."""
        # Arrange
        v = Mock(spec=Vehicle)
        v.id = "veh-99"
        light = _light(preempted_by=v)

        # Act
        d = light.to_dict()

        # Assert
        assert d["preempted_by"] == "veh-99"

    def test_to_dict_round_trips_through_json(self) -> None:
        """Payload is JSON-serializable; tuples become lists on decode."""
        # Arrange
        light = _light()

        # Act
        d = light.to_dict()
        decoded = json.loads(json.dumps(d))

        # Assert
        assert decoded["id"] == "tl-1"
        assert decoded["position"] == [1, 1]
        assert decoded["active_axis"] == "north_south"
        assert decoded["preempted_by"] is None
