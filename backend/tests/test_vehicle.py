"""Tests for the vehicle module — P1-VEH-01."""

import json

import pytest

from backend.simulation.vehicle import Vehicle, VehicleStatus, VehicleType

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def vehicle_on_path() -> Vehicle:
    """Vehicle at start of a 4-cell path: (0,0)→(1,0)→(2,0)→(3,0)."""
    return Vehicle(
        id="v-001",
        type=VehicleType.NORMAL,
        position=(0, 0),
        origin=(0, 0),
        destination=(3, 0),
        path=[(0, 0), (1, 0), (2, 0), (3, 0)],
        path_index=0,
    )


@pytest.fixture
def vehicle_at_destination() -> Vehicle:
    """Vehicle already at the final path cell (destination)."""
    return Vehicle(
        id="v-002",
        type=VehicleType.NORMAL,
        position=(3, 0),
        origin=(0, 0),
        destination=(3, 0),
        path=[(0, 0), (1, 0), (2, 0), (3, 0)],
        path_index=3,
        status=VehicleStatus.ARRIVED,
    )


@pytest.fixture
def vehicle_single_cell() -> Vehicle:
    """Vehicle on a trivial single-cell path (origin == destination)."""
    return Vehicle(
        id="v-003",
        type=VehicleType.NORMAL,
        position=(0, 0),
        origin=(0, 0),
        destination=(0, 0),
        path=[(0, 0)],
        path_index=0,
    )


# ---------------------------------------------------------------------------
# P1-VEH-01 — Vehicle.get_next_position
# ---------------------------------------------------------------------------


class TestVehicleGetNextPosition:
    """Tests for Vehicle.get_next_position — next cell on path."""

    def test_get_next_position_returns_next_cell_at_start(
        self, vehicle_on_path: Vehicle
    ) -> None:
        """At the start of a multi-cell path, returns path[1]."""
        # Act
        result = vehicle_on_path.get_next_position()

        # Assert
        assert result == (1, 0)

    @pytest.mark.parametrize(
        "path_index, position, expected_next",
        [
            (1, (1, 0), (2, 0)),
            (2, (2, 0), (3, 0)),
        ],
    )
    def test_get_next_position_returns_correct_cell_at_mid_path(
        self,
        vehicle_on_path: Vehicle,
        path_index: int,
        position: tuple[int, int],
        expected_next: tuple[int, int],
    ) -> None:
        """At mid-path positions, returns the correct next cell."""
        # Arrange
        vehicle_on_path.path_index = path_index
        vehicle_on_path.position = position

        # Act
        result = vehicle_on_path.get_next_position()

        # Assert
        assert result == expected_next

    def test_get_next_position_returns_none_at_end_of_path(
        self, vehicle_at_destination: Vehicle
    ) -> None:
        """At the final path cell (destination), returns None."""
        # Act
        result = vehicle_at_destination.get_next_position()

        # Assert
        assert result is None

    def test_get_next_position_returns_none_for_single_cell_path(
        self, vehicle_single_cell: Vehicle
    ) -> None:
        """Single-cell path (origin == destination) returns None."""
        # Act
        result = vehicle_single_cell.get_next_position()

        # Assert
        assert result is None

    def test_get_next_position_two_cell_path_returns_destination(self) -> None:
        """Minimal non-trivial path: returns the second (final) cell."""
        # Arrange
        vehicle = Vehicle(
            id="v-2cell",
            type=VehicleType.NORMAL,
            position=(0, 0),
            origin=(0, 0),
            destination=(1, 0),
            path=[(0, 0), (1, 0)],
            path_index=0,
        )

        # Act
        result = vehicle.get_next_position()

        # Assert
        assert result == (1, 0)

    # --- Validation guard tests (exercised via get_next_position) ---

    def test_get_next_position_raises_on_empty_path(self) -> None:
        """Empty path triggers ValueError."""
        # Arrange
        vehicle = Vehicle(
            id="v-bad",
            type=VehicleType.NORMAL,
            position=(0, 0),
            origin=(0, 0),
            destination=(3, 0),
            path=[],
            path_index=0,
        )

        # Act / Assert
        with pytest.raises(ValueError, match="empty path"):
            vehicle.get_next_position()

    @pytest.mark.parametrize("path_index", [-1, 4, 100])
    def test_get_next_position_raises_on_out_of_range_path_index(
        self, vehicle_on_path: Vehicle, path_index: int
    ) -> None:
        """Out-of-range path_index triggers ValueError."""
        # Arrange
        vehicle_on_path.path_index = path_index

        # Act / Assert
        with pytest.raises(ValueError, match="invalid path_index"):
            vehicle_on_path.get_next_position()

    def test_get_next_position_raises_on_path_origin_mismatch(self) -> None:
        """path[0] != origin triggers ValueError."""
        # Arrange
        vehicle = Vehicle(
            id="v-bad",
            type=VehicleType.NORMAL,
            position=(5, 5),
            origin=(5, 5),
            destination=(3, 0),
            path=[(0, 0), (1, 0), (2, 0), (3, 0)],
            path_index=0,
        )

        # Act / Assert
        with pytest.raises(ValueError, match="path must start at origin"):
            vehicle.get_next_position()

    def test_get_next_position_raises_on_path_destination_mismatch(self) -> None:
        """path[-1] != destination triggers ValueError."""
        # Arrange
        vehicle = Vehicle(
            id="v-bad",
            type=VehicleType.NORMAL,
            position=(0, 0),
            origin=(0, 0),
            destination=(9, 9),
            path=[(0, 0), (1, 0), (2, 0), (3, 0)],
            path_index=0,
        )

        # Act / Assert
        with pytest.raises(ValueError, match="path must end at destination"):
            vehicle.get_next_position()

    def test_get_next_position_raises_on_position_path_mismatch(self) -> None:
        """position != path[path_index] triggers ValueError."""
        # Arrange
        vehicle = Vehicle(
            id="v-bad",
            type=VehicleType.NORMAL,
            position=(9, 9),
            origin=(0, 0),
            destination=(3, 0),
            path=[(0, 0), (1, 0), (2, 0), (3, 0)],
            path_index=0,
        )

        # Act / Assert
        with pytest.raises(ValueError, match="position/path mismatch"):
            vehicle.get_next_position()


# ---------------------------------------------------------------------------
# P1-VEH-01 — Vehicle.advance_path
# ---------------------------------------------------------------------------


class TestVehicleAdvancePath:
    """Tests for Vehicle.advance_path — one-step path progression."""

    def test_advance_path_updates_position_and_index(
        self, vehicle_on_path: Vehicle
    ) -> None:
        """Advancing updates position to next cell and increments path_index."""
        # Act
        vehicle_on_path.advance_path()

        # Assert
        assert vehicle_on_path.position == (1, 0)
        assert vehicle_on_path.path_index == 1

    def test_advance_path_sets_status_moving_when_not_at_end(
        self, vehicle_on_path: Vehicle
    ) -> None:
        """Status is MOVING after advance when not at destination."""
        # Act
        vehicle_on_path.advance_path()

        # Assert
        assert vehicle_on_path.status is VehicleStatus.MOVING

    def test_advance_path_sets_status_arrived_at_destination(self) -> None:
        """Status becomes ARRIVED when vehicle reaches the final path cell."""
        # Arrange — vehicle one step before destination
        vehicle = Vehicle(
            id="v-penult",
            type=VehicleType.NORMAL,
            position=(2, 0),
            origin=(0, 0),
            destination=(3, 0),
            path=[(0, 0), (1, 0), (2, 0), (3, 0)],
            path_index=2,
        )

        # Act
        vehicle.advance_path()

        # Assert
        assert vehicle.position == (3, 0)
        assert vehicle.path_index == 3
        assert vehicle.status is VehicleStatus.ARRIVED

    def test_advance_path_noop_position_at_destination(
        self, vehicle_at_destination: Vehicle
    ) -> None:
        """At destination, advance_path does not change position or path_index."""
        # Arrange
        pos_before = vehicle_at_destination.position
        idx_before = vehicle_at_destination.path_index

        # Act
        vehicle_at_destination.advance_path()

        # Assert
        assert vehicle_at_destination.position == pos_before
        assert vehicle_at_destination.path_index == idx_before

    def test_advance_path_status_remains_arrived_at_destination(
        self, vehicle_at_destination: Vehicle
    ) -> None:
        """Calling advance_path at destination keeps status ARRIVED."""
        # Act
        vehicle_at_destination.advance_path()

        # Assert
        assert vehicle_at_destination.status is VehicleStatus.ARRIVED

    def test_advance_path_synchronizes_status_from_waiting_to_moving(self) -> None:
        """advance_path status sync: WAITING becomes MOVING when not at end."""
        # Arrange
        vehicle = Vehicle(
            id="v-wait",
            type=VehicleType.NORMAL,
            position=(0, 0),
            origin=(0, 0),
            destination=(3, 0),
            path=[(0, 0), (1, 0), (2, 0), (3, 0)],
            path_index=0,
            status=VehicleStatus.WAITING,
        )

        # Act
        vehicle.advance_path()

        # Assert
        assert vehicle.status is VehicleStatus.MOVING

    def test_advance_path_synchronizes_status_from_moving_to_arrived_at_end(
        self,
    ) -> None:
        """Vehicle at final cell with MOVING status is synced to ARRIVED."""
        # Arrange
        vehicle = Vehicle(
            id="v-sync",
            type=VehicleType.NORMAL,
            position=(3, 0),
            origin=(0, 0),
            destination=(3, 0),
            path=[(0, 0), (1, 0), (2, 0), (3, 0)],
            path_index=3,
            status=VehicleStatus.MOVING,
        )

        # Act
        vehicle.advance_path()

        # Assert
        assert vehicle.status is VehicleStatus.ARRIVED

    def test_advance_path_full_traversal(self, vehicle_on_path: Vehicle) -> None:
        """Walking the entire 4-cell path reaches destination with ARRIVED."""
        # Arrange
        expected_positions = [(1, 0), (2, 0), (3, 0)]

        # Act
        visited: list[tuple[int, int]] = []
        for _ in range(len(expected_positions)):
            vehicle_on_path.advance_path()
            visited.append(vehicle_on_path.position)

        # Assert
        assert visited == expected_positions
        assert vehicle_on_path.path_index == 3
        assert vehicle_on_path.status is VehicleStatus.ARRIVED

    def test_advance_path_single_cell_path_sets_arrived(
        self, vehicle_single_cell: Vehicle
    ) -> None:
        """On a single-cell path, advance_path sets ARRIVED immediately."""
        # Act
        vehicle_single_cell.advance_path()

        # Assert
        assert vehicle_single_cell.position == (0, 0)
        assert vehicle_single_cell.path_index == 0
        assert vehicle_single_cell.status is VehicleStatus.ARRIVED

    def test_advance_path_raises_on_empty_path(self) -> None:
        """advance_path propagates validation error for empty path."""
        # Arrange
        vehicle = Vehicle(
            id="v-bad",
            type=VehicleType.NORMAL,
            position=(0, 0),
            origin=(0, 0),
            destination=(3, 0),
            path=[],
            path_index=0,
        )

        # Act / Assert
        with pytest.raises(ValueError, match="empty path"):
            vehicle.advance_path()


# ---------------------------------------------------------------------------
# P1-VEH-01 — Vehicle.get_remaining_distance
# ---------------------------------------------------------------------------


class TestVehicleGetRemainingDistance:
    """Tests for Vehicle.get_remaining_distance — steps to destination."""

    @pytest.mark.parametrize(
        "path_index, position, expected_distance",
        [
            (0, (0, 0), 3),
            (1, (1, 0), 2),
            (2, (2, 0), 1),
            (3, (3, 0), 0),
        ],
    )
    def test_get_remaining_distance_at_various_path_positions(
        self,
        path_index: int,
        position: tuple[int, int],
        expected_distance: int,
    ) -> None:
        """Remaining distance decrements correctly at each path position."""
        # Arrange
        vehicle = Vehicle(
            id="v-dist",
            type=VehicleType.NORMAL,
            position=position,
            origin=(0, 0),
            destination=(3, 0),
            path=[(0, 0), (1, 0), (2, 0), (3, 0)],
            path_index=path_index,
        )

        # Act
        result = vehicle.get_remaining_distance()

        # Assert
        assert result == expected_distance

    def test_get_remaining_distance_single_cell_path_is_zero(
        self, vehicle_single_cell: Vehicle
    ) -> None:
        """Single-cell path (origin == destination) returns 0."""
        # Act
        result = vehicle_single_cell.get_remaining_distance()

        # Assert
        assert result == 0

    def test_get_remaining_distance_raises_on_empty_path(self) -> None:
        """get_remaining_distance propagates validation error for empty path."""
        # Arrange
        vehicle = Vehicle(
            id="v-bad",
            type=VehicleType.NORMAL,
            position=(0, 0),
            origin=(0, 0),
            destination=(3, 0),
            path=[],
            path_index=0,
        )

        # Act / Assert
        with pytest.raises(ValueError, match="empty path"):
            vehicle.get_remaining_distance()


# ---------------------------------------------------------------------------
# P1-VEH-01 — Vehicle.to_dict
# ---------------------------------------------------------------------------


class TestVehicleToDict:
    """Tests for Vehicle.to_dict — JSON-serializable vehicle snapshot."""

    def test_to_dict_contains_all_required_keys(self, vehicle_on_path: Vehicle) -> None:
        """Payload includes exactly the 11 documented keys."""
        # Act
        payload = vehicle_on_path.to_dict()

        # Assert
        expected_keys = {
            "id",
            "type",
            "position",
            "origin",
            "destination",
            "path",
            "path_index",
            "status",
            "ticks_elapsed",
            "next_position",
            "remaining_distance",
        }
        assert set(payload.keys()) == expected_keys

    def test_to_dict_values_at_start_of_path(self, vehicle_on_path: Vehicle) -> None:
        """Full snapshot at start of a 4-cell path."""
        # Act
        payload = vehicle_on_path.to_dict()

        # Assert
        assert payload["id"] == "v-001"
        assert payload["type"] == "normal"
        assert payload["position"] == (0, 0)
        assert payload["origin"] == (0, 0)
        assert payload["destination"] == (3, 0)
        assert payload["path"] == [(0, 0), (1, 0), (2, 0), (3, 0)]
        assert payload["path_index"] == 0
        assert payload["status"] == "moving"
        assert payload["ticks_elapsed"] == 0
        assert payload["next_position"] == (1, 0)
        assert payload["remaining_distance"] == 3

    def test_to_dict_at_destination_has_none_next_and_zero_remaining(
        self, vehicle_at_destination: Vehicle
    ) -> None:
        """At destination: next_position is None and remaining_distance is 0."""
        # Act
        payload = vehicle_at_destination.to_dict()

        # Assert
        assert payload["next_position"] is None
        assert payload["remaining_distance"] == 0
        assert payload["status"] == "arrived"

    def test_to_dict_emergency_vehicle_type_string(self) -> None:
        """Emergency vehicle serializes type as 'emergency'."""
        # Arrange
        vehicle = Vehicle(
            id="e-001",
            type=VehicleType.EMERGENCY,
            position=(0, 0),
            origin=(0, 0),
            destination=(1, 0),
            path=[(0, 0), (1, 0)],
            path_index=0,
        )

        # Act
        payload = vehicle.to_dict()

        # Assert
        assert payload["type"] == "emergency"

    def test_to_dict_ticks_elapsed_reflects_field_value(self) -> None:
        """ticks_elapsed in payload matches the vehicle field."""
        # Arrange
        vehicle = Vehicle(
            id="v-ticks",
            type=VehicleType.NORMAL,
            position=(1, 0),
            origin=(0, 0),
            destination=(3, 0),
            path=[(0, 0), (1, 0), (2, 0), (3, 0)],
            path_index=1,
            ticks_elapsed=42,
        )

        # Act
        payload = vehicle.to_dict()

        # Assert
        assert payload["ticks_elapsed"] == 42

    def test_to_dict_path_is_shallow_copy(self, vehicle_on_path: Vehicle) -> None:
        """Returned path list is a copy; mutating it does not affect vehicle."""
        # Arrange
        original_path = list(vehicle_on_path.path)

        # Act
        payload = vehicle_on_path.to_dict()
        payload["path"].append((99, 99))

        # Assert
        assert vehicle_on_path.path == original_path

    def test_to_dict_is_json_serializable(self, vehicle_on_path: Vehicle) -> None:
        """Payload round-trips through JSON; tuples become arrays per contract."""
        # Act
        payload = vehicle_on_path.to_dict()
        encoded = json.dumps(payload)
        decoded = json.loads(encoded)

        # Assert — coordinates become JSON arrays after round-trip
        assert decoded["id"] == "v-001"
        assert decoded["type"] == "normal"
        assert decoded["position"] == [0, 0]
        assert decoded["origin"] == [0, 0]
        assert decoded["destination"] == [3, 0]
        assert decoded["path"] == [[0, 0], [1, 0], [2, 0], [3, 0]]
        assert decoded["path_index"] == 0
        assert decoded["status"] == "moving"
        assert decoded["ticks_elapsed"] == 0
        assert decoded["next_position"] == [1, 0]
        assert decoded["remaining_distance"] == 3

    def test_to_dict_at_destination_json_null_next_position(
        self, vehicle_at_destination: Vehicle
    ) -> None:
        """At destination, next_position serializes as JSON null."""
        # Act
        payload = vehicle_at_destination.to_dict()
        decoded = json.loads(json.dumps(payload))

        # Assert
        assert decoded["next_position"] is None

    def test_to_dict_does_not_mutate_vehicle_state(
        self, vehicle_on_path: Vehicle
    ) -> None:
        """Calling to_dict does not alter any vehicle field."""
        # Arrange
        state_before = (
            vehicle_on_path.id,
            vehicle_on_path.type,
            vehicle_on_path.position,
            vehicle_on_path.origin,
            vehicle_on_path.destination,
            list(vehicle_on_path.path),
            vehicle_on_path.path_index,
            vehicle_on_path.status,
            vehicle_on_path.ticks_elapsed,
        )

        # Act
        _ = vehicle_on_path.to_dict()

        # Assert
        state_after = (
            vehicle_on_path.id,
            vehicle_on_path.type,
            vehicle_on_path.position,
            vehicle_on_path.origin,
            vehicle_on_path.destination,
            list(vehicle_on_path.path),
            vehicle_on_path.path_index,
            vehicle_on_path.status,
            vehicle_on_path.ticks_elapsed,
        )
        assert state_after == state_before

    def test_to_dict_raises_on_empty_path(self) -> None:
        """to_dict propagates validation error for empty path."""
        # Arrange
        vehicle = Vehicle(
            id="v-bad",
            type=VehicleType.NORMAL,
            position=(0, 0),
            origin=(0, 0),
            destination=(3, 0),
            path=[],
            path_index=0,
        )

        # Act / Assert
        with pytest.raises(ValueError, match="empty path"):
            vehicle.to_dict()
