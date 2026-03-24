"""Tests for the pathfinder module."""

import heapq
from unittest.mock import Mock

import pytest

from backend.simulation.grid import CellType, Grid
from backend.simulation.pathfinder import Pathfinder, PathNode
from backend.simulation.vehicle import VehicleType

# ---------------------------------------------------------------------------
# Shared fixture for P1-PATH-03 tests
# ---------------------------------------------------------------------------


@pytest.fixture
def grid_7x7() -> Grid:
    """7×7 grid with STREET_SPACING=3.

    Avenues (traversable columns): {0, 3, 6}
    Streets (traversable rows):    {0, 3, 6}

    Notable cells:
      Intersections : (0,0), (3,0), (6,0), (0,3), (3,3), (6,3), (0,6), (3,6), (6,6)
      Road cells    : (1,0), (2,0), (0,1), (0,2), (3,1), (3,2), …
      Obstacles     : (1,1), (2,2), (4,4), …
    """
    return Grid(width=7, height=7)


# ---------------------------------------------------------------------------
# P1-PATH-01 — PathNode.f_cost
# ---------------------------------------------------------------------------


class TestPathNodeFCost:
    """Tests for PathNode.f_cost — A* total cost property."""

    @pytest.mark.parametrize(
        "g_cost, h_cost, expected",
        [
            (0.0, 0.0, 0.0),  # both zero
            (0.0, 5.0, 5.0),  # zero g, positive h
            (5.0, 0.0, 5.0),  # positive g, zero h
            (3.0, 4.0, 7.0),  # typical integer-valued costs
            (1.5, 2.5, 4.0),  # float costs
            (10.0, 0.5, 10.5),  # asymmetric floats
            (100.0, 200.0, 300.0),  # large values
        ],
    )
    def test_f_cost_equals_g_plus_h(
        self, g_cost: float, h_cost: float, expected: float
    ) -> None:
        """f_cost must equal g_cost + h_cost for all valid cost combinations."""
        # Arrange
        node = PathNode(position=(0, 0), g_cost=g_cost, h_cost=h_cost)

        # Act
        result = node.f_cost

        # Assert
        assert result == pytest.approx(expected)

    def test_f_cost_independent_of_position(self) -> None:
        """f_cost must not depend on the node's grid position."""
        # Arrange
        node_origin = PathNode(position=(0, 0), g_cost=3.0, h_cost=4.0)
        node_far = PathNode(position=(10, 15), g_cost=3.0, h_cost=4.0)

        # Act
        cost_origin = node_origin.f_cost
        cost_far = node_far.f_cost

        # Assert
        assert cost_origin == cost_far

    def test_f_cost_independent_of_parent(self) -> None:
        """f_cost must not depend on whether the node has a parent reference."""
        # Arrange
        parent = PathNode(position=(0, 0), g_cost=1.0, h_cost=1.0)
        node_with_parent = PathNode(
            position=(1, 0), g_cost=3.0, h_cost=4.0, parent=parent
        )
        node_without_parent = PathNode(
            position=(1, 0), g_cost=3.0, h_cost=4.0, parent=None
        )

        # Act
        cost_with = node_with_parent.f_cost
        cost_without = node_without_parent.f_cost

        # Assert
        assert cost_with == pytest.approx(7.0)
        assert cost_without == pytest.approx(7.0)


# ---------------------------------------------------------------------------
# P1-PATH-02 — PathNode.__lt__
# ---------------------------------------------------------------------------


class TestPathNodeLt:
    """Tests for PathNode.__lt__ — priority queue comparison."""

    @pytest.mark.parametrize(
        "g_self, h_self, g_other, h_other",
        [
            (1.0, 1.0, 3.0, 3.0),  # f=2 < f=6
            (0.0, 0.0, 0.0, 1.0),  # f=0 < f=1  (boundary: zero vs one)
            (1.5, 0.5, 2.0, 1.0),  # f=2.0 < f=3.0 (floats)
            (1.0, 4.0, 3.0, 4.0),  # f=5 < f=7  (same h, different g)
        ],
    )
    def test_lt_returns_true_when_f_cost_lower(
        self, g_self: float, h_self: float, g_other: float, h_other: float
    ) -> None:
        """__lt__ must return True when self.f_cost is strictly less than other."""
        # Arrange
        node_self = PathNode(position=(0, 0), g_cost=g_self, h_cost=h_self)
        node_other = PathNode(position=(1, 1), g_cost=g_other, h_cost=h_other)

        # Act
        result = node_self < node_other

        # Assert
        assert result is True

    @pytest.mark.parametrize(
        "g_self, h_self, g_other, h_other",
        [
            (5.0, 5.0, 2.0, 2.0),  # f=10 > f=4  (strictly higher)
            (3.0, 4.0, 3.0, 4.0),  # f=7 == f=7  (equal, boundary)
            (5.0, 2.0, 3.0, 4.0),  # f=7 == f=7  (equal total, different g/h split)
            (1.0, 0.0, 0.0, 0.0),  # f=1 > f=0   (boundary: one vs zero)
        ],
    )
    def test_lt_returns_false_when_f_cost_not_lower(
        self, g_self: float, h_self: float, g_other: float, h_other: float
    ) -> None:
        """__lt__ must return False when self.f_cost >= other.f_cost."""
        # Arrange
        node_self = PathNode(position=(0, 0), g_cost=g_self, h_cost=h_self)
        node_other = PathNode(position=(1, 1), g_cost=g_other, h_cost=h_other)

        # Act
        result = node_self < node_other

        # Assert
        assert result is False

    def test_lt_non_pathnode_returns_not_implemented(self) -> None:
        """__lt__ must return NotImplemented when other is not a PathNode."""
        # Arrange
        node = PathNode(position=(0, 0), g_cost=3.0, h_cost=4.0)

        # Act
        result = PathNode.__lt__(node, 42)  # type: ignore[operator]

        # Assert
        assert result is NotImplemented

    def test_lt_non_pathnode_raises_type_error(self) -> None:
        """Using the < operator against a non-PathNode must raise TypeError."""
        # Arrange
        node = PathNode(position=(0, 0), g_cost=3.0, h_cost=4.0)

        # Act / Assert
        with pytest.raises(TypeError):
            _ = node < 42  # type: ignore[operator]

    def test_lt_priority_queue_ordering(self) -> None:
        """Nodes pushed into a heapq must be popped in ascending f_cost order."""
        # Arrange
        node_high = PathNode(position=(2, 2), g_cost=10.0, h_cost=10.0)  # f=20
        node_low = PathNode(position=(0, 0), g_cost=1.0, h_cost=1.0)  # f=2
        node_mid = PathNode(position=(1, 1), g_cost=5.0, h_cost=5.0)  # f=10

        heap: list[PathNode] = []
        for node in [node_high, node_low, node_mid]:
            heapq.heappush(heap, node)

        # Act
        first = heapq.heappop(heap)
        second = heapq.heappop(heap)
        third = heapq.heappop(heap)

        # Assert
        assert first.f_cost == pytest.approx(2.0)
        assert second.f_cost == pytest.approx(10.0)
        assert third.f_cost == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# P1-PATH-03 — Pathfinder.find_path
# ---------------------------------------------------------------------------


class TestPathfinderFindPath:
    """Tests for Pathfinder.find_path — A* pathfinding algorithm."""

    # --- Guard conditions ---

    @pytest.mark.parametrize(
        "start",
        [(-1, 0), (7, 0), (0, -1)],
    )
    def test_returns_none_for_out_of_bounds_start(
        self, grid_7x7: Grid, start: tuple[int, int]
    ) -> None:
        """find_path must return None when start lies outside the grid."""
        # Arrange / Act
        result = Pathfinder.find_path(grid_7x7, start, (3, 0), VehicleType.NORMAL)

        # Assert
        assert result is None

    @pytest.mark.parametrize(
        "goal",
        [(-1, 0), (7, 3), (0, 7)],
    )
    def test_returns_none_for_out_of_bounds_goal(
        self, grid_7x7: Grid, goal: tuple[int, int]
    ) -> None:
        """find_path must return None when goal lies outside the grid."""
        # Arrange / Act
        result = Pathfinder.find_path(grid_7x7, (0, 0), goal, VehicleType.NORMAL)

        # Assert
        assert result is None

    @pytest.mark.parametrize("start", [(1, 1), (2, 2), (4, 4)])
    def test_returns_none_for_non_traversable_start(
        self, grid_7x7: Grid, start: tuple[int, int]
    ) -> None:
        """find_path must return None when start is an obstacle cell."""
        # Arrange / Act
        result = Pathfinder.find_path(grid_7x7, start, (0, 0), VehicleType.NORMAL)

        # Assert
        assert result is None

    @pytest.mark.parametrize("goal", [(1, 1), (2, 2), (4, 4)])
    def test_returns_none_for_non_traversable_goal(
        self, grid_7x7: Grid, goal: tuple[int, int]
    ) -> None:
        """find_path must return None when goal is an obstacle cell."""
        # Arrange / Act
        result = Pathfinder.find_path(grid_7x7, (0, 0), goal, VehicleType.NORMAL)

        # Assert
        assert result is None

    # --- Trivial case ---

    def test_returns_start_list_when_start_equals_goal(self, grid_7x7: Grid) -> None:
        """find_path must return [start] when start and goal are the same cell."""
        # Arrange
        pos = (3, 0)

        # Act
        result = Pathfinder.find_path(grid_7x7, pos, pos, VehicleType.NORMAL)

        # Assert
        assert result == [pos]

    # --- Normal vehicle pathfinding ---

    def test_normal_vehicle_returns_exact_shortest_direct_path(
        self, grid_7x7: Grid
    ) -> None:
        """Path along a clear street row must be the unique optimal sequence."""
        # Arrange
        start, goal = (0, 0), (3, 0)

        # Act
        result = Pathfinder.find_path(grid_7x7, start, goal, VehicleType.NORMAL)

        # Assert — unique minimum-cost path along street row y=0
        assert result == [(0, 0), (1, 0), (2, 0), (3, 0)]

    def test_path_starts_at_start_and_ends_at_goal(self, grid_7x7: Grid) -> None:
        """First element of path must equal start; last must equal goal."""
        # Arrange
        start, goal = (0, 0), (6, 6)

        # Act
        result = Pathfinder.find_path(grid_7x7, start, goal, VehicleType.NORMAL)

        # Assert
        assert result is not None
        assert result[0] == start
        assert result[-1] == goal

    def test_all_path_positions_are_traversable(self, grid_7x7: Grid) -> None:
        """Every position in the returned path must be traversable on the grid."""
        # Arrange
        start, goal = (0, 0), (6, 6)

        # Act
        result = Pathfinder.find_path(grid_7x7, start, goal, VehicleType.NORMAL)

        # Assert
        assert result is not None
        for pos in result:
            assert grid_7x7.is_traversable(*pos), f"Position {pos} is not traversable"

    def test_consecutive_path_positions_are_cardinally_adjacent(
        self, grid_7x7: Grid
    ) -> None:
        """Each consecutive pair must differ by exactly one cardinal step."""
        # Arrange
        start, goal = (0, 0), (6, 6)

        # Act
        result = Pathfinder.find_path(grid_7x7, start, goal, VehicleType.NORMAL)

        # Assert
        assert result is not None
        for (x1, y1), (x2, y2) in zip(result, result[1:], strict=False):
            assert abs(x2 - x1) + abs(y2 - y1) == 1, (
                f"Non-adjacent step: {(x1, y1)} → {(x2, y2)}"
            )

    # --- No path available ---

    def test_returns_none_when_start_is_fully_isolated(self, grid_7x7: Grid) -> None:
        """find_path must return None when start has no traversable neighbours."""
        # Arrange — (0,0) has exactly two traversable neighbours: (1,0) and (0,1).
        # Blocking both isolates (0,0) completely.
        grid_7x7.cells[0][1].type = CellType.OBSTACLE  # (x=1, y=0)
        grid_7x7.cells[1][0].type = CellType.OBSTACLE  # (x=0, y=1)

        # Act
        result = Pathfinder.find_path(grid_7x7, (0, 0), (3, 0), VehicleType.NORMAL)

        # Assert
        assert result is None

    # --- Emergency vehicle ---

    def test_emergency_without_tlm_returns_valid_path(self, grid_7x7: Grid) -> None:
        """Emergency vehicle with no TLM must find a valid path (base cost only)."""
        # Arrange
        start, goal = (0, 0), (3, 0)

        # Act
        result = Pathfinder.find_path(
            grid_7x7, start, goal, VehicleType.EMERGENCY, traffic_light_manager=None
        )

        # Assert
        assert result == [(0, 0), (1, 0), (2, 0), (3, 0)]

    def test_emergency_avoids_red_light_intersection_when_bypass_exists(
        self, grid_7x7: Grid
    ) -> None:
        """Emergency vehicle must take the cheaper bypass around a red intersection.

        Route A via (3,0) [red, +2]: cost = 1+1+(1+2)+1+1+1 = 8
        Route B via (0,3) [no light]: cost = 1+1+1+1+1+1   = 6  ← expected
        """
        # Arrange
        red_light = Mock()
        red_light.current_phase = "red"

        mock_tlm = Mock()
        mock_tlm.get_light.side_effect = lambda pos: (
            red_light if pos == (3, 0) else None
        )

        # Act
        result = Pathfinder.find_path(
            grid_7x7,
            (0, 0),
            (3, 3),
            VehicleType.EMERGENCY,
            traffic_light_manager=mock_tlm,
        )

        # Assert — cheaper route (B) taken; red-light intersection avoided
        assert result is not None
        assert result[0] == (0, 0)
        assert result[-1] == (3, 3)
        assert (3, 0) not in result

    def test_emergency_enum_phase_red_light_avoids_intersection(
        self, grid_7x7: Grid
    ) -> None:
        """Emergency vehicle handles enum-style current_phase (object with .value)."""
        # Arrange — simulate a traffic-light phase enum: getattr(phase, "value", phase)
        red_phase = Mock()
        red_phase.value = "red"

        red_light = Mock()
        red_light.current_phase = red_phase

        mock_tlm = Mock()
        mock_tlm.get_light.side_effect = lambda pos: (
            red_light if pos == (3, 0) else None
        )

        # Act
        result = Pathfinder.find_path(
            grid_7x7,
            (0, 0),
            (3, 3),
            VehicleType.EMERGENCY,
            traffic_light_manager=mock_tlm,
        )

        # Assert
        assert result is not None
        assert (3, 0) not in result

    def test_emergency_phase_value_none_applies_no_penalty(
        self, grid_7x7: Grid
    ) -> None:
        """When phase.value is None, _phase_value returns None — no penalty applied."""
        # Arrange
        none_phase = Mock()
        none_phase.value = None

        light = Mock()
        light.current_phase = none_phase

        mock_tlm = Mock()
        mock_tlm.get_light.return_value = light

        # Act — all intersections have this light; no penalty → same as normal vehicle
        result = Pathfinder.find_path(
            grid_7x7,
            (0, 0),
            (3, 0),
            VehicleType.EMERGENCY,
            traffic_light_manager=mock_tlm,
        )

        # Assert
        assert result == [(0, 0), (1, 0), (2, 0), (3, 0)]

    def test_emergency_get_light_raises_not_implemented_falls_back_to_cell_light(
        self, grid_7x7: Grid
    ) -> None:
        """When get_light raises NotImplementedError, fall back to cell light."""
        # Arrange — get_light always raises; cell.traffic_light is None → no penalty
        mock_tlm = Mock()
        mock_tlm.get_light.side_effect = NotImplementedError

        # Act
        result = Pathfinder.find_path(
            grid_7x7,
            (0, 0),
            (3, 0),
            VehicleType.EMERGENCY,
            traffic_light_manager=mock_tlm,
        )

        # Assert — no penalty applied, same path as normal vehicle
        assert result == [(0, 0), (1, 0), (2, 0), (3, 0)]

    def test_emergency_yellow_light_still_uses_direct_path_when_no_cheaper_bypass(
        self, grid_7x7: Grid
    ) -> None:
        """Emergency vehicle takes the direct path despite yellow-light penalty.

        Direct cost via (3,0) yellow: 1+1+(1+1)=4. Nearest bypass ≥10.
        """
        # Arrange
        yellow_light = Mock()
        yellow_light.current_phase = "yellow"

        mock_tlm = Mock()
        mock_tlm.get_light.side_effect = lambda pos: (
            yellow_light if pos == (3, 0) else None
        )

        # Act
        result = Pathfinder.find_path(
            grid_7x7,
            (0, 0),
            (3, 0),
            VehicleType.EMERGENCY,
            traffic_light_manager=mock_tlm,
        )

        # Assert — direct path is still cheapest despite yellow penalty
        assert result == [(0, 0), (1, 0), (2, 0), (3, 0)]

    def test_stale_heap_entry_guard_is_exercised(self) -> None:
        """Stale-heap-entry guard fires when a node is re-discovered via a cheaper path.

        Verified concrete scenario (developer-confirmed):
          Grid: 10×10, all intersections red, VehicleType.EMERGENCY
          Start: (1, 0)  Goal: (9, 6)

        Node (1, 6) is first discovered with g=16, then improved to g=14.
        When the stale (g=16) entry is later popped, current.g_cost (16) >
        best_g_cost[(1,6)] (14) and the guard on line 126 fires.
        """
        # Arrange — 10×10 grid (avenues: {0,3,6,9}, streets: {0,3,6,9})
        grid = Grid(width=10, height=10)

        red_light = Mock()
        red_light.current_phase = "red"

        mock_tlm = Mock()
        mock_tlm.get_light.return_value = red_light

        # Act
        result = Pathfinder.find_path(
            grid,
            (1, 0),
            (9, 6),
            VehicleType.EMERGENCY,
            traffic_light_manager=mock_tlm,
        )

        # Assert — valid path found and stale-guard was exercised (line 126)
        assert result is not None
        assert result[0] == (1, 0)
        assert result[-1] == (9, 6)
