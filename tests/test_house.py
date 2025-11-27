import pytest

from quality_house import Criterion, House, Response, compare


def example():
    return House(
        criteria=[
            Criterion("easy", "Easy to open", 5),
            Criterion("clean", "Easy to clean", 3),
        ],
        responses=[Response("latch", "Latch"), Response("seal", "Seal")],
        matrix=[[9, 1], [1, 9]],
    )


def test_scores_feed_next_stage_in_response_order():
    first = example()
    assert first.scores == (48, 32)
    assert first.shares == pytest.approx((0.60, 0.40))
    second = first.deploy([Response("spring", "Spring")], [[1], [3]])
    assert [criterion.id for criterion in second.criteria] == ["latch", "seal"]
    assert second.scores == (144,)


def test_sparse_relationships_and_revision_follow_ids():
    before = example()
    after = House.from_relationships(
        list(reversed(before.criteria)),
        [Response("seal", "Removable seal"), Response("shell", "Shell")],
        [("easy", "seal", 3), ("clean", "seal", 9)],
    )
    change = compare(before, after)
    assert change.removed_responses == ("latch",)
    assert change.added_responses == ("shell",)
    assert change.changed_responses == ("seal",)
    assert [
        (e.criterion_id, e.response_id, e.before, e.after) for e in change.relationships
    ] == [("easy", "seal", 1, 3)]


@pytest.mark.parametrize(
    "matrix",
    [
        [[9], [1]],
        [[9, 2], [1, 3]],
        [[9, True], [1, 3]],
    ],
)
def test_invalid_matrix_is_rejected_at_construction(matrix):
    first = example()
    with pytest.raises(ValueError):
        House(first.criteria, first.responses, matrix)


def test_large_finite_column_totals_can_have_finite_shares():
    large = House(
        [Criterion("load", "Load", 1e308)],
        [Response("a", "A"), Response("b", "B")],
        [[1, 1]],
    )
    assert large.shares == (0.5, 0.5)
    with pytest.raises(ValueError, match="finite"):
        House(large.criteria, large.responses, [[9, 1]]).scores
