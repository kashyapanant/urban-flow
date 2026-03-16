"""Tests for implemented Grid/Cell task behavior."""

from collections import Counter
from unittest.mock import Mock

import pytest

from backend.config import MAX_GRID_SIZE, MIN_GRID_SIZE, STREET_SPACING
from backend.simulation.grid import Cell, CellType, Grid


@pytest.fixture
def grid_5x4():
    """Return a 5x4 grid for grid coordinate tests."""
    return Grid(width=5, height=4)


class TestCellIsTraversable:
    """Test cases for P1-GRID-02 `Cell.is_traversable()`."""

    @pytest.mark.parametrize(
        ("cell_type", "expected"),
        [
            (CellType.ROAD, True),
            (CellType.INTERSECTION, True),
            (CellType.OBSTACLE, False),
        ],
    )
    def test_is_traversable_returns_expected_by_cell_type(self, cell_type, expected):
        """Cell traversability is determined by its type."""
        # Arrange
        cell = Cell(x=1, y=2, type=cell_type)

        # Act
        actual = cell.is_traversable()

        # Assert
        assert actual is expected

    def test_is_traversable_ignores_vehicle_occupancy(self):
        """A road/intersection remains traversable even when occupied."""
        # Arrange
        occupied_road_cell = Cell(x=0, y=0, type=CellType.ROAD, vehicle=Mock())
        occupied_intersection_cell = Cell(
            x=1,
            y=1,
            type=CellType.INTERSECTION,
            vehicle=Mock(),
        )

        # Act
        road_result = occupied_road_cell.is_traversable()
        intersection_result = occupied_intersection_cell.is_traversable()

        # Assert
        assert road_result is True
        assert intersection_result is True


class TestCellIsOccupied:
    """Test cases for P1-GRID-03 `Cell.is_occupied()`."""

    @pytest.mark.parametrize(
        ("vehicle_ref", "expected"),
        [
            (None, False),
            (Mock(), True),
        ],
    )
    def test_is_occupied_returns_expected_for_vehicle_presence(
        self, vehicle_ref, expected
    ):
        """Occupancy depends only on whether vehicle reference exists."""
        # Arrange
        cell = Cell(x=2, y=3, type=CellType.ROAD, vehicle=vehicle_ref)

        # Act
        actual = cell.is_occupied()

        # Assert
        assert actual is expected

    @pytest.mark.parametrize(
        "cell_type",
        [CellType.ROAD, CellType.INTERSECTION, CellType.OBSTACLE],
    )
    def test_is_occupied_is_consistent_across_cell_types(self, cell_type):
        """Cell type does not change occupancy semantics."""
        # Arrange
        empty_cell = Cell(x=0, y=0, type=cell_type, vehicle=None)
        occupied_cell = Cell(x=0, y=0, type=cell_type, vehicle=Mock())

        # Act
        empty_result = empty_cell.is_occupied()
        occupied_result = occupied_cell.is_occupied()

        # Assert
        assert empty_result is False
        assert occupied_result is True


class TestGridInit:
    """Test cases for Grid constructor behavior."""

    @pytest.mark.parametrize(
        ("width", "height"),
        [
            (MIN_GRID_SIZE, MIN_GRID_SIZE),
            (10, 10),
            (7, 13),
            (MAX_GRID_SIZE, MAX_GRID_SIZE),
        ],
    )
    def test_init_accepts_dimension_boundaries_and_valid_sizes(self, width, height):
        """Grid accepts min/max boundaries and representative valid sizes."""
        # Arrange / Act
        grid = Grid(width=width, height=height)

        # Assert
        assert grid.width == width
        assert grid.height == height
        assert len(grid.cells) == height
        assert all(len(row) == width for row in grid.cells)

    @pytest.mark.parametrize(
        ("width", "height", "expected_fragment"),
        [
            (MIN_GRID_SIZE - 1, 10, "Grid width must be between"),
            (-1, 10, "Grid width must be between"),
            (MAX_GRID_SIZE + 1, 10, "Grid width must be between"),
            (10, MIN_GRID_SIZE - 1, "Grid height must be between"),
            (10, -1, "Grid height must be between"),
            (10, MAX_GRID_SIZE + 1, "Grid height must be between"),
        ],
    )
    def test_init_rejects_dimensions_outside_allowed_range(
        self, width, height, expected_fragment
    ):
        """Grid rejects invalid width/height with descriptive ValueError."""
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match=expected_fragment):
            Grid(width=width, height=height)

    @pytest.mark.parametrize(("width", "height"), [(10, 10), (8, 5), (1, 1), (11, 4)])
    def test_init_computes_street_and_avenue_sets_from_fixed_spacing(
        self, width, height
    ):
        """Street/avenue index sets follow fixed STREET_SPACING from index 0."""
        # Arrange / Act
        grid = Grid(width=width, height=height)

        # Assert
        assert grid.avenue_cols == frozenset(range(0, width, STREET_SPACING))
        assert grid.street_rows == frozenset(range(0, height, STREET_SPACING))

    def test_init_builds_row_major_cells_with_expected_coordinates(self):
        """Grid stores cells row-major as cells[y][x]."""
        # Arrange
        width, height = 4, 3

        # Act
        grid = Grid(width=width, height=height)

        # Assert
        assert len(grid.cells) == height
        assert len(grid.cells[0]) == width
        assert grid.cells[0][0].x == 0 and grid.cells[0][0].y == 0
        assert grid.cells[2][1].x == 1 and grid.cells[2][1].y == 2
        assert grid.cells[1][3].x == 3 and grid.cells[1][3].y == 1

    @pytest.mark.parametrize(
        ("x", "y", "expected_type"),
        [
            (0, 0, CellType.INTERSECTION),
            (3, 6, CellType.INTERSECTION),
            (1, 0, CellType.ROAD),
            (0, 2, CellType.ROAD),
            (2, 2, CellType.OBSTACLE),
            (5, 8, CellType.OBSTACLE),
        ],
    )
    def test_init_assigns_cell_type_from_street_avenue_membership(
        self, x, y, expected_type
    ):
        """Cell type is determined by avenue/street membership rules."""
        # Arrange
        grid = Grid(width=10, height=10)

        # Act
        cell = grid.cells[y][x]

        # Assert
        assert cell.type is expected_type

    def test_init_default_10x10_matches_expected_cell_type_distribution(self):
        """Default 10x10 grid has 16 intersections, 48 roads, 36 obstacles."""
        # Arrange
        grid = Grid(width=10, height=10)

        # Act
        counts = Counter(cell.type for row in grid.cells for cell in row)

        # Assert
        assert counts[CellType.INTERSECTION] == 16
        assert counts[CellType.ROAD] == 48
        assert counts[CellType.OBSTACLE] == 36


class TestGridGetCell:
    """Test cases for P1-GRID-04 `Grid.get_cell()`."""

    @pytest.mark.parametrize(
        ("x", "y"),
        [
            (0, 0),
            (3, 2),
            (4, 3),
        ],
    )
    def test_get_cell_returns_cell_for_in_bounds_coordinates(self, grid_5x4, x, y):
        """Valid coordinates return the corresponding cell instance."""
        # Act
        cell = grid_5x4.get_cell(x, y)

        # Assert
        assert cell is not None
        assert cell is grid_5x4.cells[y][x]
        assert cell.x == x
        assert cell.y == y

    @pytest.mark.parametrize(
        ("x", "y"),
        [
            (-1, 0),
            (0, -1),
            (5, 0),
            (0, 4),
            (5, 4),
            (-1, -1),
        ],
    )
    def test_get_cell_returns_none_for_out_of_bounds_coordinates(self, grid_5x4, x, y):
        """Coordinates outside grid boundaries return None."""
        # Act
        cell = grid_5x4.get_cell(x, y)

        # Assert
        assert cell is None


class TestGridGetNeighbors:
    """Test cases for P1-GRID-05 `Grid.get_neighbors()`."""

    @pytest.mark.parametrize(
        ("x", "y", "expected_coords"),
        [
            (0, 0, [(0, 1), (1, 0)]),
            (0, 1, [(0, 0), (0, 2)]),
            (3, 1, [(3, 0), (3, 2)]),
            (1, 1, [(1, 0), (0, 1)]),
        ],
    )
    def test_get_neighbors_returns_only_traversable_cardinal_neighbors(
        self, grid_5x4, x, y, expected_coords
    ):
        """Neighbors include only in-bounds traversable cardinal cells."""
        # Act
        neighbors = grid_5x4.get_neighbors(x, y)

        # Assert
        assert {(cell.x, cell.y) for cell in neighbors} == set(expected_coords)

    @pytest.mark.parametrize(
        ("x", "y"),
        [
            (-1, 0),
            (0, -1),
            (5, 0),
            (0, 4),
            (5, 4),
            (-1, -1),
        ],
    )
    def test_get_neighbors_returns_empty_list_for_out_of_bounds_coordinates(
        self, grid_5x4, x, y
    ):
        """Out-of-bounds source coordinates produce no neighbors."""
        # Act
        neighbors = grid_5x4.get_neighbors(x, y)

        # Assert
        assert neighbors == []


class TestGridPlaceVehicle:
    """Test cases for P1-GRID-06 `Grid.place_vehicle()`."""

    def test_place_vehicle_returns_true_and_stores_vehicle_on_traversable_cell(
        self, grid_5x4
    ):
        """Placing a vehicle on an empty traversable cell succeeds."""
        # Arrange
        vehicle = Mock()

        # Act
        result = grid_5x4.place_vehicle(vehicle, 1, 0)

        # Assert
        assert result is True
        assert grid_5x4.cells[0][1].vehicle is vehicle

    @pytest.mark.parametrize(
        ("x", "y"),
        [
            (-1, 0),
            (0, -1),
            (5, 0),
            (0, 4),
        ],
    )
    def test_place_vehicle_returns_false_for_out_of_bounds_coordinates(
        self, grid_5x4, x, y
    ):
        """Out-of-bounds placement attempts fail without mutating the grid."""
        # Arrange
        vehicle = Mock()

        # Act
        result = grid_5x4.place_vehicle(vehicle, x, y)

        # Assert
        assert result is False
        assert all(cell.vehicle is None for row in grid_5x4.cells for cell in row)

    def test_place_vehicle_returns_false_for_obstacle_cell(self, grid_5x4):
        """Placement on an obstacle cell fails and leaves the cell empty."""
        # Arrange
        vehicle = Mock()

        # Act
        result = grid_5x4.place_vehicle(vehicle, 1, 1)

        # Assert
        assert result is False
        assert grid_5x4.cells[1][1].type is CellType.OBSTACLE
        assert grid_5x4.cells[1][1].vehicle is None

    def test_place_vehicle_returns_false_when_cell_is_already_occupied(self, grid_5x4):
        """Placement fails when the target traversable cell already has a vehicle."""
        # Arrange
        existing_vehicle = Mock()
        new_vehicle = Mock()
        grid_5x4.cells[0][1].vehicle = existing_vehicle

        # Act
        result = grid_5x4.place_vehicle(new_vehicle, 1, 0)

        # Assert
        assert result is False
        assert grid_5x4.cells[0][1].vehicle is existing_vehicle
