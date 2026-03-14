"""Tests for P1-GRID-01 (`Grid.__init__()`) behavior."""

from collections import Counter

import pytest

from backend.config import MAX_GRID_SIZE, MIN_GRID_SIZE, STREET_SPACING
from backend.simulation.grid import Cell, CellType, Grid


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
        occupied_road_cell = Cell(x=0, y=0, type=CellType.ROAD, vehicle=object())
        occupied_intersection_cell = Cell(
            x=1,
            y=1,
            type=CellType.INTERSECTION,
            vehicle=object(),
        )

        # Act
        road_result = occupied_road_cell.is_traversable()
        intersection_result = occupied_intersection_cell.is_traversable()

        # Assert
        assert road_result is True
        assert intersection_result is True


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
