"""Tests for the vehicle module — P1-VEH-01, P1-VEH-02."""

import json
from unittest.mock import Mock, patch

import pytest

from backend.simulation.grid import Grid
from backend.simulation.vehicle import (
    Vehicle,
    VehicleManager,
    VehicleStatus,
    VehicleType,
)

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

    def test_to_dict_normalizes_terminal_status_for_single_cell_path(
        self, vehicle_single_cell: Vehicle
    ) -> None:
        """Terminal path shape serializes ARRIVED even if in-memory status is MOVING."""
        # Arrange
        assert vehicle_single_cell.status is VehicleStatus.MOVING

        # Act
        payload = vehicle_single_cell.to_dict()

        # Assert
        assert payload["next_position"] is None
        assert payload["remaining_distance"] == 0
        assert payload["status"] == VehicleStatus.ARRIVED.value
        assert payload["status"] != VehicleStatus.MOVING.value

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


# ---------------------------------------------------------------------------
# P1-VEH-02 — shared fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def vehicle_manager() -> VehicleManager:
    """Return a fresh VehicleManager with no active vehicles."""
    return VehicleManager()


def _make_arrived_vehicle(vid: str) -> Vehicle:
    """Create a Vehicle at its destination with ARRIVED status."""
    return Vehicle(
        id=vid,
        type=VehicleType.NORMAL,
        position=(1, 0),
        origin=(0, 0),
        destination=(1, 0),
        path=[(0, 0), (1, 0)],
        path_index=1,
        status=VehicleStatus.ARRIVED,
    )


def _make_moving_vehicle(vid: str) -> Vehicle:
    """Create a Vehicle in transit with MOVING status."""
    return Vehicle(
        id=vid,
        type=VehicleType.NORMAL,
        position=(0, 0),
        origin=(0, 0),
        destination=(1, 0),
        path=[(0, 0), (1, 0)],
        path_index=0,
        status=VehicleStatus.MOVING,
    )


def _make_two_cell_mock_grid(
    *,
    origin_occupied: bool = False,
    place_vehicle_result: bool = True,
) -> Mock:
    """Return a Mock grid with two edge cells: origin (0,0) and dest (9,0).

    The origin cell's ``is_occupied`` return value and ``place_vehicle``
    result are configurable so individual tests can exercise different paths
    without repeating boilerplate.
    """
    origin_cell = Mock()
    origin_cell.x = 0
    origin_cell.y = 0
    origin_cell.is_occupied.return_value = origin_occupied

    dest_cell = Mock()
    dest_cell.x = 9
    dest_cell.y = 0
    dest_cell.is_occupied.return_value = False

    mock_grid = Mock()
    mock_grid.get_edge_cells.return_value = [origin_cell, dest_cell]
    mock_grid.place_vehicle.return_value = place_vehicle_result
    return mock_grid


# ---------------------------------------------------------------------------
# P1-VEH-02 — VehicleManager.__init__
# ---------------------------------------------------------------------------


class TestVehicleManagerInit:
    """Tests for VehicleManager.__init__ — initial manager state."""

    def test_init_vehicles_list_is_empty(self) -> None:
        """Freshly constructed manager has an empty vehicle list."""
        # Act
        manager = VehicleManager()

        # Assert
        assert manager._vehicles == []

    def test_init_vehicles_attribute_is_list_type(self) -> None:
        """_vehicles is a list, not another sequence type."""
        # Act
        manager = VehicleManager()

        # Assert
        assert isinstance(manager._vehicles, list)

    def test_init_two_instances_have_independent_lists(self) -> None:
        """Each VehicleManager owns its own _vehicles list; mutation is isolated."""
        # Arrange
        manager_a = VehicleManager()
        manager_b = VehicleManager()

        # Act — mutate one instance's list
        manager_a._vehicles.append(Mock(spec=Vehicle))

        # Assert — sibling instance is unaffected
        assert manager_b._vehicles == []


# ---------------------------------------------------------------------------
# P1-VEH-02 — VehicleManager.spawn_vehicles
# ---------------------------------------------------------------------------


class TestVehicleManagerSpawnVehicles:
    """Tests for VehicleManager.spawn_vehicles — edge-cell vehicle creation."""

    # --- Input validation ---

    @pytest.mark.parametrize("spawn_rate", [-0.01, 1.01, -1.0, 2.0])
    def test_spawn_vehicles_raises_on_invalid_spawn_rate(
        self, vehicle_manager: VehicleManager, spawn_rate: float
    ) -> None:
        """spawn_rate outside [0.0, 1.0] raises ValueError."""
        # Arrange
        mock_grid = Mock()

        # Act / Assert
        with pytest.raises(ValueError, match="spawn_rate"):
            vehicle_manager.spawn_vehicles(mock_grid, spawn_rate, 0.1, 1)

    @pytest.mark.parametrize("emergency_prob", [-0.01, 1.01])
    def test_spawn_vehicles_raises_on_invalid_emergency_probability(
        self, vehicle_manager: VehicleManager, emergency_prob: float
    ) -> None:
        """emergency_probability outside [0.0, 1.0] raises ValueError."""
        # Arrange
        mock_grid = Mock()

        # Act / Assert
        with pytest.raises(ValueError, match="emergency_probability"):
            vehicle_manager.spawn_vehicles(mock_grid, 0.5, emergency_prob, 1)

    @pytest.mark.parametrize("max_retries", [0, -1, -100])
    def test_spawn_vehicles_raises_on_invalid_max_retries(
        self, vehicle_manager: VehicleManager, max_retries: int
    ) -> None:
        """max_retries less than 1 raises ValueError."""
        # Arrange
        mock_grid = Mock()

        # Act / Assert
        with pytest.raises(ValueError, match="max_retries"):
            vehicle_manager.spawn_vehicles(mock_grid, 0.5, 0.1, max_retries)

    # --- Boundary: valid edge inputs must not raise ---

    def test_spawn_vehicles_spawn_rate_zero_never_spawns(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """spawn_rate=0.0 is accepted and produces no vehicles.

        random.random() always returns a value in [0, 1), so
        ``random.random() >= 0.0`` is always True, meaning every edge cell is
        skipped before any work is done.
        """
        # Arrange
        sole_cell = Mock()
        sole_cell.x = 0
        sole_cell.y = 0
        sole_cell.is_occupied.return_value = False
        mock_grid = Mock()
        mock_grid.get_edge_cells.return_value = [sole_cell]

        # Act
        result = vehicle_manager.spawn_vehicles(mock_grid, 0.0, 0.1, 1)

        # Assert
        assert result == []
        assert vehicle_manager._vehicles == []

    def test_spawn_vehicles_max_retries_one_is_accepted(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """max_retries=1 (boundary) raises no ValueError."""
        # Arrange
        mock_grid = Mock()
        mock_grid.get_edge_cells.return_value = []

        # Act / Assert — must not raise
        result = vehicle_manager.spawn_vehicles(mock_grid, 0.5, 0.1, 1)
        assert result == []

    # --- No edge cells ---

    def test_spawn_vehicles_returns_empty_when_no_edge_cells(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Grid with no edge cells immediately returns []."""
        # Arrange
        mock_grid = Mock()
        mock_grid.get_edge_cells.return_value = []

        # Act
        result = vehicle_manager.spawn_vehicles(mock_grid, 0.5, 0.1, 1)

        # Assert
        assert result == []
        assert vehicle_manager._vehicles == []

    # --- Occupied origin cell ---

    def test_spawn_vehicles_skips_occupied_origin_cell(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Occupied edge cell is never used as a spawn origin."""
        # Arrange — sole edge cell is occupied
        occupied_cell = Mock()
        occupied_cell.x = 0
        occupied_cell.y = 0
        occupied_cell.is_occupied.return_value = True
        mock_grid = Mock()
        mock_grid.get_edge_cells.return_value = [occupied_cell]

        # Act — spawn_rate=1.0 guarantees a spawn attempt if cell were free
        result = vehicle_manager.spawn_vehicles(mock_grid, 1.0, 0.0, 1)

        # Assert — occupied cell skipped; nothing spawned
        assert result == []
        assert vehicle_manager._vehicles == []

    # --- Single edge cell: no valid destination ---

    def test_spawn_vehicles_skips_when_no_destination_candidates(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """With exactly one edge cell no destination exists; nothing is spawned."""
        # Arrange — sole traversable edge cell; destination_candidates will be []
        sole_cell = Mock()
        sole_cell.x = 0
        sole_cell.y = 0
        sole_cell.is_occupied.return_value = False
        mock_grid = Mock()
        mock_grid.get_edge_cells.return_value = [sole_cell]

        with patch("random.random", return_value=0.0):  # passes spawn roll
            result = vehicle_manager.spawn_vehicles(mock_grid, 1.0, 0.0, 1)

        # Assert
        assert result == []
        assert vehicle_manager._vehicles == []

    # --- Pathfinding failures ---

    def test_spawn_vehicles_skips_when_all_pathfinding_retries_fail(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Vehicle is not spawned when Pathfinder returns None for every retry."""
        # Arrange
        mock_grid = _make_two_cell_mock_grid()
        fake_path = None

        with (
            patch("random.random", return_value=0.0),
            patch(
                "backend.simulation.pathfinder.Pathfinder.find_path",
                return_value=fake_path,
            ),
        ):
            result = vehicle_manager.spawn_vehicles(mock_grid, 1.0, 0.0, 1)

        # Assert
        assert result == []
        assert vehicle_manager._vehicles == []

    def test_spawn_vehicles_skips_when_pathfinder_returns_empty_path(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Vehicle is not spawned when Pathfinder returns an empty list."""
        # Arrange
        mock_grid = _make_two_cell_mock_grid()

        with (
            patch("random.random", return_value=0.0),
            patch(
                "backend.simulation.pathfinder.Pathfinder.find_path",
                return_value=[],
            ),
        ):
            result = vehicle_manager.spawn_vehicles(mock_grid, 1.0, 0.0, 1)

        # Assert
        assert result == []
        assert vehicle_manager._vehicles == []

    def test_spawn_vehicles_skips_when_path_start_does_not_match_origin(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Vehicle skipped when returned path[0] differs from the spawn origin."""
        # Arrange
        mock_grid = _make_two_cell_mock_grid()
        # Path starts at (1,1) instead of origin (0,0) — first guard fires
        bad_path = [(1, 1), (9, 0)]

        with (
            patch("random.random", return_value=0.0),
            patch(
                "backend.simulation.pathfinder.Pathfinder.find_path",
                return_value=bad_path,
            ),
        ):
            result = vehicle_manager.spawn_vehicles(mock_grid, 1.0, 0.0, 1)

        # Assert
        assert result == []

    def test_spawn_vehicles_skips_when_path_end_does_not_match_destination(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Vehicle skipped when returned path[-1] differs from the chosen destination.

        Mirrors the origin-mismatch test: path[0] matches origin so the first
        half of the endpoint guard passes, but path[-1] != candidate_destination
        triggers the second half and causes the retry to be skipped.
        """
        # Arrange
        mock_grid = _make_two_cell_mock_grid()
        # Path starts at origin (0,0) ✓ but ends at (5,5) instead of (9,0)
        bad_path = [(0, 0), (5, 5)]

        with (
            patch("random.random", return_value=0.0),
            patch(
                "backend.simulation.pathfinder.Pathfinder.find_path",
                return_value=bad_path,
            ),
        ):
            result = vehicle_manager.spawn_vehicles(mock_grid, 1.0, 0.0, 1)

        # Assert
        assert result == []

    # --- grid.place_vehicle failure ---

    def test_spawn_vehicles_skips_when_place_vehicle_fails(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Vehicle not added when grid.place_vehicle returns False."""
        # Arrange — place_vehicle always refuses
        mock_grid = _make_two_cell_mock_grid(place_vehicle_result=False)
        fake_path = [(0, 0), (9, 0)]

        with (
            patch("random.random", return_value=0.0),
            patch(
                "backend.simulation.pathfinder.Pathfinder.find_path",
                return_value=fake_path,
            ),
        ):
            result = vehicle_manager.spawn_vehicles(mock_grid, 1.0, 0.0, 1)

        # Assert
        assert result == []
        assert vehicle_manager._vehicles == []

    # --- Successful spawn ---

    def test_spawn_vehicles_returns_spawned_vehicle_on_success(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Successful spawn: returned list and _vehicles both contain the vehicle."""
        # Arrange
        mock_grid = _make_two_cell_mock_grid()
        fake_path = [(0, 0), (9, 0)]

        with (
            patch("random.random", return_value=0.0),
            patch(
                "backend.simulation.pathfinder.Pathfinder.find_path",
                return_value=fake_path,
            ),
        ):
            result = vehicle_manager.spawn_vehicles(mock_grid, 1.0, 0.0, 1)

        # Assert
        assert len(result) >= 1
        assert len(vehicle_manager._vehicles) >= 1
        for v in result:
            assert v in vehicle_manager._vehicles

    def test_spawn_vehicles_spawned_vehicle_has_correct_route_fields(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Spawned vehicle's origin, destination, path, and position are correct."""
        # Arrange
        mock_grid = _make_two_cell_mock_grid()
        fake_path = [(0, 0), (9, 0)]

        with (
            patch("random.random", return_value=0.0),
            patch(
                "backend.simulation.pathfinder.Pathfinder.find_path",
                return_value=fake_path,
            ),
        ):
            result = vehicle_manager.spawn_vehicles(mock_grid, 1.0, 0.0, 1)

        # Assert
        assert len(result) >= 1
        spawned = result[0]
        assert spawned.origin == (0, 0)
        assert spawned.destination == (9, 0)
        assert spawned.path == [(0, 0), (9, 0)]
        assert spawned.position == (0, 0)
        assert spawned.path_index == 0

    def test_spawn_vehicles_spawned_vehicle_id_is_full_uuid_hex(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Spawned vehicle ID is a 32-character hexadecimal string (uuid4().hex)."""
        # Arrange
        mock_grid = _make_two_cell_mock_grid()
        fake_path = [(0, 0), (9, 0)]

        with (
            patch("random.random", return_value=0.0),
            patch(
                "backend.simulation.pathfinder.Pathfinder.find_path",
                return_value=fake_path,
            ),
        ):
            result = vehicle_manager.spawn_vehicles(mock_grid, 1.0, 0.0, 1)

        assert len(result) >= 1
        assert len(result[0].id) == 32
        assert all(c in "0123456789abcdef" for c in result[0].id)

    def test_spawn_vehicles_spawns_emergency_vehicle_when_probability_is_one(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """emergency_probability=1.0 always produces EMERGENCY type vehicles."""
        # Arrange
        mock_grid = _make_two_cell_mock_grid()
        fake_path = [(0, 0), (9, 0)]

        with (
            patch("random.random", return_value=0.0),
            patch(
                "backend.simulation.pathfinder.Pathfinder.find_path",
                return_value=fake_path,
            ),
        ):
            # random.random()=0.0 < 1.0 → EMERGENCY
            result = vehicle_manager.spawn_vehicles(mock_grid, 1.0, 1.0, 1)

        assert len(result) >= 1
        assert result[0].type is VehicleType.EMERGENCY

    def test_spawn_vehicles_spawns_normal_vehicle_when_probability_is_zero(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """emergency_probability=0.0 always produces NORMAL type vehicles."""
        # Arrange
        mock_grid = _make_two_cell_mock_grid()
        fake_path = [(0, 0), (9, 0)]

        with (
            patch("random.random", return_value=0.0),
            patch(
                "backend.simulation.pathfinder.Pathfinder.find_path",
                return_value=fake_path,
            ),
        ):
            # random.random()=0.0 < 0.0 is False → NORMAL
            result = vehicle_manager.spawn_vehicles(mock_grid, 1.0, 0.0, 1)

        assert len(result) >= 1
        assert result[0].type is VehicleType.NORMAL

    def test_spawn_vehicles_calls_place_vehicle_with_spawned_vehicle_and_origin(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """grid.place_vehicle is called with the new vehicle at the origin coords."""
        # Arrange
        mock_grid = _make_two_cell_mock_grid()
        fake_path = [(0, 0), (9, 0)]

        with (
            patch("random.random", return_value=0.0),
            patch(
                "backend.simulation.pathfinder.Pathfinder.find_path",
                return_value=fake_path,
            ),
        ):
            result = vehicle_manager.spawn_vehicles(mock_grid, 1.0, 0.0, 1)

        # Assert — place_vehicle called once with the spawned vehicle and origin (0,0)
        assert len(result) >= 1
        mock_grid.place_vehicle.assert_called_once_with(result[0], 0, 0)

    def test_spawn_vehicles_accumulates_vehicles_across_successive_calls(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """_vehicles persists between spawn calls; second call grows the list."""
        # Arrange
        fake_path = [(0, 0), (9, 0)]

        for _ in range(2):
            mock_grid = _make_two_cell_mock_grid()
            with (
                patch("random.random", return_value=0.0),
                patch("random.choice", side_effect=lambda lst: lst[0]),
                patch(
                    "backend.simulation.pathfinder.Pathfinder.find_path",
                    return_value=fake_path,
                ),
            ):
                vehicle_manager.spawn_vehicles(mock_grid, 1.0, 0.0, 1)

        # Assert — _vehicles grew over two calls
        assert len(vehicle_manager._vehicles) >= 2


# ---------------------------------------------------------------------------
# P1-VEH-02 — VehicleManager.collect_arrived
# ---------------------------------------------------------------------------


class TestVehicleManagerCollectArrived:
    """Tests for VehicleManager.collect_arrived — removes and returns arrived."""

    def test_collect_arrived_returns_empty_when_no_vehicles(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Manager with no active vehicles returns []."""
        # Act
        result = vehicle_manager.collect_arrived()

        # Assert
        assert result == []

    def test_collect_arrived_returns_empty_when_no_arrived_vehicles(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """All-MOVING vehicle list returns [] and leaves _vehicles unchanged."""
        # Arrange
        v1 = _make_moving_vehicle("v1")
        v2 = _make_moving_vehicle("v2")
        vehicle_manager._vehicles = [v1, v2]

        # Act
        result = vehicle_manager.collect_arrived()

        # Assert
        assert result == []
        assert vehicle_manager._vehicles == [v1, v2]

    def test_collect_arrived_returns_all_when_all_vehicles_arrived(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """All-ARRIVED vehicle list: all returned, _vehicles cleared."""
        # Arrange
        v1 = _make_arrived_vehicle("v1")
        v2 = _make_arrived_vehicle("v2")
        vehicle_manager._vehicles = [v1, v2]

        # Act
        result = vehicle_manager.collect_arrived()

        # Assert
        assert result == [v1, v2]
        assert vehicle_manager._vehicles == []

    def test_collect_arrived_returns_only_arrived_vehicles_in_mixed_list(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Mixed list: only ARRIVED vehicles returned; MOVING ones remain."""
        # Arrange
        v_moving = _make_moving_vehicle("v-move")
        v_arrived = _make_arrived_vehicle("v-arr")
        vehicle_manager._vehicles = [v_moving, v_arrived]

        # Act
        result = vehicle_manager.collect_arrived()

        # Assert
        assert result == [v_arrived]
        assert vehicle_manager._vehicles == [v_moving]

    def test_collect_arrived_preserves_insertion_order_of_arrived_vehicles(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Arrived vehicles are returned in their original insertion order."""
        # Arrange
        v1 = _make_arrived_vehicle("v1")
        v2 = _make_arrived_vehicle("v2")
        v3 = _make_arrived_vehicle("v3")
        vehicle_manager._vehicles = [v1, v2, v3]

        # Act
        result = vehicle_manager.collect_arrived()

        # Assert — order preserved
        assert result == [v1, v2, v3]

    def test_collect_arrived_preserves_relative_order_of_remaining_vehicles(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Non-arrived vehicles remain in _vehicles in their original relative order."""
        # Arrange
        v1 = _make_moving_vehicle("v1")
        v2 = _make_arrived_vehicle("v2")
        v3 = _make_moving_vehicle("v3")
        vehicle_manager._vehicles = [v1, v2, v3]

        # Act
        vehicle_manager.collect_arrived()

        # Assert — v1 and v3 remain; v2 removed; relative order kept
        assert vehicle_manager._vehicles == [v1, v3]

    def test_collect_arrived_does_not_mutate_returned_vehicles(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Vehicles returned by collect_arrived still carry ARRIVED status."""
        # Arrange
        v_arrived = _make_arrived_vehicle("v-arr")
        vehicle_manager._vehicles = [v_arrived]

        # Act
        result = vehicle_manager.collect_arrived()

        # Assert — vehicle state untouched
        assert result[0].status is VehicleStatus.ARRIVED

    def test_collect_arrived_second_call_returns_empty_after_first_collection(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Second collect_arrived call returns [] — vehicles already removed."""
        # Arrange
        v_arrived = _make_arrived_vehicle("v-arr")
        vehicle_manager._vehicles = [v_arrived]
        vehicle_manager.collect_arrived()  # first collection removes the vehicle

        # Act
        result = vehicle_manager.collect_arrived()

        # Assert
        assert result == []

    def test_collect_arrived_ignores_waiting_status_vehicles(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """WAITING vehicles are not collected; only ARRIVED status triggers removal."""
        # Arrange
        v_waiting = Vehicle(
            id="v-wait",
            type=VehicleType.NORMAL,
            position=(0, 0),
            origin=(0, 0),
            destination=(1, 0),
            path=[(0, 0), (1, 0)],
            path_index=0,
            status=VehicleStatus.WAITING,
        )
        vehicle_manager._vehicles = [v_waiting]

        # Act
        result = vehicle_manager.collect_arrived()

        # Assert — WAITING is not ARRIVED; vehicle stays in _vehicles
        assert result == []
        assert vehicle_manager._vehicles == [v_waiting]


# ---------------------------------------------------------------------------
# P1-VEH-03 — shared helpers
# ---------------------------------------------------------------------------


def _vehicle_at(
    vid: str,
    path: list[tuple[int, int]],
    path_index: int = 0,
    vtype: VehicleType = VehicleType.NORMAL,
    status: VehicleStatus = VehicleStatus.MOVING,
) -> Vehicle:
    """Create a Vehicle with consistent path state for move_vehicles tests."""
    return Vehicle(
        id=vid,
        type=vtype,
        position=path[path_index],
        origin=path[0],
        destination=path[-1],
        path=path,
        path_index=path_index,
        status=status,
    )


def _road_cell_mock(occupied: bool = False) -> Mock:
    """Mock of a traversable road cell (no traffic light)."""
    cell = Mock()
    cell.is_occupied.return_value = occupied
    cell.traffic_light = None
    return cell


def _intersection_cell_mock(occupied: bool = False) -> Mock:
    """Mock of a traversable intersection cell (has a traffic light object)."""
    cell = Mock()
    cell.is_occupied.return_value = occupied
    cell.traffic_light = Mock()
    return cell


# ---------------------------------------------------------------------------
# P1-VEH-03 — VehicleManager.move_vehicles
# ---------------------------------------------------------------------------


class TestVehicleManagerMoveVehicles:
    """Tests for VehicleManager.move_vehicles — priority-based tick movement."""

    # --- Empty list and arrived-filter cases ---

    def test_move_vehicles_no_op_with_empty_vehicle_list(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """With no active vehicles the method completes without touching grid or TLM."""
        # Arrange
        mock_grid = Mock()
        mock_tlm = Mock()

        # Act
        vehicle_manager.move_vehicles(mock_grid, mock_tlm)

        # Assert — grid and TLM never consulted
        mock_grid.get_cell.assert_not_called()
        mock_tlm.can_vehicle_enter.assert_not_called()

    def test_move_vehicles_skips_already_arrived_vehicles(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """ARRIVED vehicles are filtered before movement; grid and ticks untouched."""
        # Arrange
        arrived = _vehicle_at(
            "v1", [(0, 0), (1, 0)], path_index=1, status=VehicleStatus.ARRIVED
        )
        vehicle_manager._vehicles = [arrived]
        mock_grid = Mock()
        mock_tlm = Mock()

        # Act
        vehicle_manager.move_vehicles(mock_grid, mock_tlm)

        # Assert
        mock_grid.get_cell.assert_not_called()
        mock_grid.remove_vehicle.assert_not_called()
        assert arrived.ticks_elapsed == 0

    # --- At-destination cleanup (get_next_position returns None) ---

    def test_move_vehicles_at_destination_releases_cell_and_marks_arrived(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Vehicle at final path cell is cleaned up: cell released, status ARRIVED."""
        # Arrange — vehicle at last cell with MOVING status (not yet synced)
        vehicle = _vehicle_at("v1", [(0, 0), (1, 0)], path_index=1)
        vehicle_manager._vehicles = [vehicle]
        mock_grid = Mock()
        mock_tlm = Mock()

        # Act
        vehicle_manager.move_vehicles(mock_grid, mock_tlm)

        # Assert
        assert vehicle.status is VehicleStatus.ARRIVED
        mock_grid.remove_vehicle.assert_called_once_with(1, 0)
        mock_grid.get_cell.assert_not_called()

    def test_move_vehicles_at_destination_does_not_increment_ticks_elapsed(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Destination cleanup is not counted as an elapsed tick."""
        # Arrange
        vehicle = _vehicle_at("v1", [(0, 0), (1, 0)], path_index=1)
        vehicle.ticks_elapsed = 5
        vehicle_manager._vehicles = [vehicle]
        mock_grid = Mock()
        mock_tlm = Mock()

        # Act
        vehicle_manager.move_vehicles(mock_grid, mock_tlm)

        # Assert — ticks_elapsed unchanged
        assert vehicle.ticks_elapsed == 5

    # --- Waiting cases ---

    def test_move_vehicles_occupied_next_cell_sets_waiting_and_increments_ticks(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Vehicle whose next cell is occupied is set to WAITING and ticks_elapsed++."""
        # Arrange
        vehicle = _vehicle_at("v1", [(0, 0), (1, 0)])
        vehicle_manager._vehicles = [vehicle]
        mock_grid = Mock()
        mock_grid.get_cell.return_value = _road_cell_mock(occupied=True)
        mock_tlm = Mock()

        # Act
        vehicle_manager.move_vehicles(mock_grid, mock_tlm)

        # Assert
        assert vehicle.status is VehicleStatus.WAITING
        assert vehicle.ticks_elapsed == 1
        assert vehicle.position == (0, 0)

    def test_move_vehicles_none_next_cell_sets_waiting_and_increments_ticks(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Vehicle whose next cell is outside the grid bounds is set to WAITING."""
        # Arrange
        vehicle = _vehicle_at("v1", [(0, 0), (1, 0)])
        vehicle_manager._vehicles = [vehicle]
        mock_grid = Mock()
        mock_grid.get_cell.return_value = None  # out-of-bounds path cell
        mock_tlm = Mock()

        # Act
        vehicle_manager.move_vehicles(mock_grid, mock_tlm)

        # Assert
        assert vehicle.status is VehicleStatus.WAITING
        assert vehicle.ticks_elapsed == 1
        assert vehicle.position == (0, 0)

    def test_move_vehicles_traffic_light_denied_sets_waiting_and_increments_ticks(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Intersection with red light sets status WAITING and increments ticks."""
        # Arrange
        vehicle = _vehicle_at("v1", [(0, 0), (1, 0)])
        vehicle_manager._vehicles = [vehicle]
        mock_grid = Mock()
        mock_grid.get_cell.return_value = _intersection_cell_mock(occupied=False)
        mock_tlm = Mock()
        mock_tlm.can_vehicle_enter.return_value = False

        # Act
        vehicle_manager.move_vehicles(mock_grid, mock_tlm)

        # Assert
        assert vehicle.status is VehicleStatus.WAITING
        assert vehicle.ticks_elapsed == 1
        assert vehicle.position == (0, 0)

    # --- Successful move cases ---

    def test_move_vehicles_road_cell_moves_without_consulting_traffic_light(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Movement into a road cell (traffic_light is None) never consults the TLM."""
        # Arrange
        vehicle = _vehicle_at("v1", [(0, 0), (1, 0)])
        vehicle_manager._vehicles = [vehicle]
        mock_grid = Mock()
        mock_grid.get_cell.return_value = _road_cell_mock()
        mock_tlm = Mock()

        # Act
        vehicle_manager.move_vehicles(mock_grid, mock_tlm)

        # Assert — TLM not consulted at all; vehicle moved
        mock_tlm.can_vehicle_enter.assert_not_called()
        assert vehicle.position == (1, 0)

    def test_move_vehicles_traffic_light_permitted_moves_vehicle(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Intersection with green light results in successful movement."""
        # Arrange
        vehicle = _vehicle_at("v1", [(0, 0), (1, 0)])
        vehicle_manager._vehicles = [vehicle]
        mock_grid = Mock()
        mock_grid.get_cell.return_value = _intersection_cell_mock()
        mock_tlm = Mock()
        mock_tlm.can_vehicle_enter.return_value = True

        # Act
        vehicle_manager.move_vehicles(mock_grid, mock_tlm)

        # Assert
        assert vehicle.position == (1, 0)
        assert vehicle.status is VehicleStatus.ARRIVED  # 2-cell path ends here
        assert vehicle.ticks_elapsed == 1

    def test_move_vehicles_move_updates_position_path_index_and_ticks(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Successful move advances position, path_index, and ticks_elapsed by one."""
        # Arrange — 3-cell path so vehicle remains MOVING after one step
        vehicle = _vehicle_at("v1", [(0, 0), (1, 0), (2, 0)])
        vehicle_manager._vehicles = [vehicle]
        mock_grid = Mock()
        mock_grid.get_cell.return_value = _road_cell_mock()
        mock_tlm = Mock()

        # Act
        vehicle_manager.move_vehicles(mock_grid, mock_tlm)

        # Assert
        assert vehicle.position == (1, 0)
        assert vehicle.path_index == 1
        assert vehicle.status is VehicleStatus.MOVING
        assert vehicle.ticks_elapsed == 1

    def test_move_vehicles_move_releases_old_cell_and_claims_new_cell(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Move calls remove_vehicle on old position and place_vehicle on new one."""
        # Arrange
        vehicle = _vehicle_at("v1", [(0, 0), (1, 0), (2, 0)])
        vehicle_manager._vehicles = [vehicle]
        mock_grid = Mock()
        mock_grid.get_cell.return_value = _road_cell_mock()
        mock_tlm = Mock()

        # Act
        vehicle_manager.move_vehicles(mock_grid, mock_tlm)

        # Assert
        mock_grid.remove_vehicle.assert_called_once_with(0, 0)
        mock_grid.place_vehicle.assert_called_once_with(vehicle, 1, 0)

    # --- Direction mapping ---

    @pytest.mark.parametrize(
        "current_pos, next_pos, expected_direction",
        [
            ((0, 0), (1, 0), "east"),
            ((1, 0), (0, 0), "west"),
            ((0, 0), (0, 1), "south"),
            ((0, 1), (0, 0), "north"),
        ],
    )
    def test_move_vehicles_direction_passed_to_can_vehicle_enter(
        self,
        vehicle_manager: VehicleManager,
        current_pos: tuple[int, int],
        next_pos: tuple[int, int],
        expected_direction: str,
    ) -> None:
        """Correct direction string is derived from position delta and sent to TLM."""
        # Arrange
        vehicle = _vehicle_at("v1", [current_pos, next_pos])
        vehicle_manager._vehicles = [vehicle]
        mock_grid = Mock()
        mock_grid.get_cell.return_value = _intersection_cell_mock()
        mock_tlm = Mock()
        mock_tlm.can_vehicle_enter.return_value = True

        # Act
        vehicle_manager.move_vehicles(mock_grid, mock_tlm)

        # Assert
        mock_tlm.can_vehicle_enter.assert_called_once_with(next_pos, expected_direction)

    # --- Priority ordering (real Grid for accurate occupancy tracking) ---

    def test_move_vehicles_emergency_processed_before_normal_on_contested_cell(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """EMERGENCY vehicle claims a contested road cell before a NORMAL vehicle can.

        Both vehicles target (2, 0). Despite normal being listed first in
        _vehicles, emergency's lower priority-key tier ensures it moves first
        and occupies the cell, leaving normal WAITING.
        """
        # Arrange — (1,0), (2,0), (4,0) are road cells on y=0 in a 7×7 grid
        grid = Grid(width=7, height=7)
        emergency = _vehicle_at("e1", [(1, 0), (2, 0)], vtype=VehicleType.EMERGENCY)
        normal = _vehicle_at("n1", [(4, 0), (2, 0)], vtype=VehicleType.NORMAL)
        grid.place_vehicle(emergency, 1, 0)
        grid.place_vehicle(normal, 4, 0)

        # List normal first to confirm ordering is not insertion-order dependent
        vehicle_manager._vehicles = [normal, emergency]
        mock_tlm = Mock()

        # Act
        vehicle_manager.move_vehicles(grid, mock_tlm)

        # Assert
        assert emergency.position == (2, 0)
        assert normal.position == (4, 0)
        assert normal.status is VehicleStatus.WAITING

    def test_move_vehicles_shorter_remaining_distance_first_among_same_type(
        self, vehicle_manager: VehicleManager
    ) -> None:
        """Among NORMAL vehicles the one with fewer steps remaining is processed first.

        v_close (remaining=1) and v_far (remaining=2) both target (2, 0).
        v_close wins the cell; v_far is left WAITING.
        """
        # Arrange
        grid = Grid(width=7, height=7)
        v_close = _vehicle_at("vc", [(1, 0), (2, 0)])  # remaining = 1
        v_far = _vehicle_at("vf", [(4, 0), (2, 0), (1, 0)])  # remaining = 2
        grid.place_vehicle(v_close, 1, 0)
        grid.place_vehicle(v_far, 4, 0)

        # List v_far first to confirm ordering is not insertion-order dependent
        vehicle_manager._vehicles = [v_far, v_close]
        mock_tlm = Mock()

        # Act
        vehicle_manager.move_vehicles(grid, mock_tlm)

        # Assert
        assert v_close.position == (2, 0)
        assert v_far.position == (4, 0)
        assert v_far.status is VehicleStatus.WAITING
