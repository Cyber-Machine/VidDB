from dataclasses import dataclass
from typing import TypedDict


@dataclass(frozen=True)
class Interval:
    start_ms: int
    end_ms: int

    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


class TemporalCandidate(TypedDict):
    asset_id: str
    start_ms: int
    end_ms: int
    evidence: list[str]


def intersect(left: Interval, right: Interval) -> Interval | None:
    start_ms = max(left.start_ms, right.start_ms)
    end_ms = min(left.end_ms, right.end_ms)
    if start_ms > end_ms:
        return None
    return Interval(start_ms=start_ms, end_ms=end_ms)


def union(left: Interval, right: Interval) -> Interval:
    return Interval(
        start_ms=min(left.start_ms, right.start_ms),
        end_ms=max(left.end_ms, right.end_ms),
    )


def before(left: Interval, right: Interval) -> bool:
    return left.end_ms <= right.start_ms


def after(left: Interval, right: Interval) -> bool:
    return left.start_ms >= right.end_ms


def within(inner: Interval, outer: Interval) -> bool:
    return outer.start_ms <= inner.start_ms and inner.end_ms <= outer.end_ms


def sequence(intervals: list[Interval]) -> bool:
    return all(
        current.end_ms <= next_interval.start_ms
        for current, next_interval in zip(intervals, intervals[1:])
    )


def duration(interval: Interval) -> int:
    return interval.duration_ms()


def plan_temporal_query(operator: str, intervals: list[Interval]) -> dict[str, object]:
    return {
        "operator": operator,
        "interval_count": len(intervals),
        "steps": [f"apply {operator} to candidate intervals"],
    }


def apply_temporal_operator(
    candidates: list[TemporalCandidate],
    operator: str,
    reference: Interval,
) -> dict[str, object]:
    filtered = []
    for candidate in candidates:
        interval = Interval(
            start_ms=candidate["start_ms"],
            end_ms=candidate["end_ms"],
        )
        if _matches(interval, operator, reference):
            filtered.append(candidate)
    return {
        "query_plan": plan_temporal_query(operator, [reference]),
        "results": filtered,
    }


def boundary_accuracy(expected: Interval, actual: Interval) -> float:
    overlap = intersect(expected, actual)
    if overlap is None:
        return 0.0
    expected_duration = max(expected.duration_ms(), 1)
    return overlap.duration_ms() / expected_duration


def _matches(interval: Interval, operator: str, reference: Interval) -> bool:
    if operator == "INTERSECT":
        return intersect(interval, reference) is not None
    if operator == "BEFORE":
        return before(interval, reference)
    if operator == "AFTER":
        return after(interval, reference)
    if operator == "WITHIN":
        return within(interval, reference)
    raise ValueError("unsupported temporal operator")
