"""Tests for the pathfinder module."""

import heapq

import pytest

from backend.simulation.pathfinder import PathNode

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
