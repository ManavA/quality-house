"""Compare two house definitions using their stable row and column IDs."""

from __future__ import annotations

from dataclasses import dataclass

from .model import Correlation, House, _indices


@dataclass(frozen=True, slots=True)
class RelationshipChange:
    criterion_id: str
    response_id: str
    before: int
    after: int


@dataclass(frozen=True, slots=True)
class CorrelationChange:
    responses: tuple[str, str]
    before: Correlation | None
    after: Correlation | None


@dataclass(frozen=True, slots=True)
class Revision:
    added_criteria: tuple[str, ...]
    removed_criteria: tuple[str, ...]
    changed_criteria: tuple[str, ...]
    added_responses: tuple[str, ...]
    removed_responses: tuple[str, ...]
    changed_responses: tuple[str, ...]
    relationships: tuple[RelationshipChange, ...]
    correlations: tuple[CorrelationChange, ...]


def compare(before: House, after: House) -> Revision:
    """Find definition and relationship changes by ID."""
    old_rows, new_rows = _indices(before.criteria), _indices(after.criteria)
    old_cols, new_cols = _indices(before.responses), _indices(after.responses)
    relations = []
    for criterion_id, i in old_rows.items():
        if criterion_id not in new_rows:
            continue
        for response_id, j in old_cols.items():
            if response_id not in new_cols:
                continue
            old = before.matrix[i][j]
            new = after.matrix[new_rows[criterion_id]][new_cols[response_id]]
            if old != new:
                relations.append(
                    RelationshipChange(criterion_id, response_id, old, new)
                )
    old_pairs = _pairs(before)
    new_pairs = _pairs(after)
    correlations = tuple(
        CorrelationChange(pair, old_pairs.get(pair), new_pairs.get(pair))
        for pair in sorted(old_pairs.keys() | new_pairs.keys())
        if old_pairs.get(pair) != new_pairs.get(pair)
    )
    return Revision(
        tuple(key for key in new_rows if key not in old_rows),
        tuple(key for key in old_rows if key not in new_rows),
        tuple(
            key
            for key in old_rows
            if key in new_rows
            and before.criteria[old_rows[key]] != after.criteria[new_rows[key]]
        ),
        tuple(key for key in new_cols if key not in old_cols),
        tuple(key for key in old_cols if key not in new_cols),
        tuple(
            key
            for key in old_cols
            if key in new_cols
            and before.responses[old_cols[key]] != after.responses[new_cols[key]]
        ),
        tuple(relations),
        correlations,
    )


def _pairs(house: House) -> dict[tuple[str, str], Correlation]:
    result = {}
    for correlation in house.correlations:
        first, second = sorted((correlation.first, correlation.second))
        result[first, second] = Correlation(
            first, second, correlation.strength, correlation.note
        )
    return result
