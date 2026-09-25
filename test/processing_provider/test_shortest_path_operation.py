import pytest

from qaequilibrae.modules.processing_provider.paths_procedures.shortest_path import (
    PathSegment,
    ShortestPathError,
    ShortestPathResult,
    parse_excluded_link_ids,
)


def test_parse_excluded_link_ids():
    """Excluded link IDs use the compact form accepted by the Processing adapter."""
    assert parse_excluded_link_ids(" 4, 14,  20 ") == (4, 14, 20)
    assert parse_excluded_link_ids(" ") == ()


def test_parse_excluded_link_ids_rejects_non_integers():
    with pytest.raises(ShortestPathError, match="integers"):
        parse_excluded_link_ids("4, not-a-link")


def test_shortest_path_result_preserves_path_order_and_cost():
    result = ShortestPathResult(
        (
            PathSegment(link_id=14, a_node=1, b_node=2, direction=1, cost=2.5),
            PathSegment(link_id=4, a_node=2, b_node=6, direction=-1, cost=3.0),
        )
    )

    assert result.link_ids == (14, 4)
    assert result.total_cost == 5.5
