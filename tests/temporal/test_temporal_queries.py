from apps.temporal import (
    Interval,
    TemporalCandidate,
    after,
    apply_temporal_operator,
    before,
    boundary_accuracy,
    duration,
    intersect,
    plan_temporal_query,
    sequence,
    union,
    within,
)


def test_temporal_interval_operators_are_deterministic() -> None:
    first = Interval(0, 100)
    second = Interval(50, 150)
    third = Interval(200, 300)

    assert intersect(first, second) == Interval(50, 100)
    assert union(first, second) == Interval(0, 150)
    assert before(first, third)
    assert after(third, first)
    assert within(Interval(10, 90), first)
    assert sequence([first, third])
    assert duration(first) == 100


def test_temporal_query_plan_filters_candidates_and_scores_boundaries() -> None:
    candidates: list[TemporalCandidate] = [
        {"asset_id": "a", "start_ms": 0, "end_ms": 100, "evidence": ["goal"]},
        {"asset_id": "a", "start_ms": 200, "end_ms": 300, "evidence": ["replay"]},
    ]

    response = apply_temporal_operator(candidates, "INTERSECT", Interval(50, 120))

    assert response["query_plan"] == plan_temporal_query(
        "INTERSECT",
        [Interval(50, 120)],
    )
    assert response["results"] == [candidates[0]]
    assert boundary_accuracy(Interval(0, 100), Interval(25, 75)) == 0.5
