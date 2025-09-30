"""Validated inputs and weighted priorities for a House of Quality."""

from __future__ import annotations

from dataclasses import dataclass
from math import fsum, isfinite
from numbers import Integral, Real
from typing import Iterable, Sequence


def _name(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")


def _number(value: Real, field: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not isfinite(value)
        or value < 0
    ):
        raise ValueError(f"{field} must be a finite, nonnegative number")


@dataclass(frozen=True, slots=True)
class Criterion:
    id: str
    label: str
    weight: float

    def __post_init__(self) -> None:
        _name(self.id, "criterion ID")
        _name(self.label, "criterion label")
        _number(self.weight, "weight")
        object.__setattr__(self, "weight", float(self.weight))


@dataclass(frozen=True, slots=True)
class Response:
    id: str
    label: str
    target: str = ""
    direction: str = ""

    def __post_init__(self) -> None:
        _name(self.id, "response ID")
        _name(self.label, "response label")
        if not isinstance(self.target, str):
            raise ValueError("target must be a string")
        if self.direction not in ("", "increase", "decrease", "target"):
            raise ValueError("direction must be increase, decrease, target, or empty")


@dataclass(frozen=True, slots=True)
class Correlation:
    first: str
    second: str
    strength: int
    note: str = ""

    def __post_init__(self) -> None:
        _name(self.first, "first response ID")
        _name(self.second, "second response ID")
        if self.first == self.second:
            raise ValueError("a response cannot have a correlation with itself")
        if (
            isinstance(self.strength, bool)
            or not isinstance(self.strength, Integral)
            or self.strength not in (-2, -1, 1, 2)
        ):
            raise ValueError("correlation strength must be -2, -1, 1, or 2")
        if not isinstance(self.note, str):
            raise ValueError("correlation note must be a string")
        object.__setattr__(self, "strength", int(self.strength))


@dataclass(frozen=True, slots=True)
class Benchmark:
    """Ratings for an external reference on the house's criterion rows."""

    label: str
    ratings: tuple[float | None, ...]

    def __post_init__(self) -> None:
        _name(self.label, "benchmark label")
        ratings = tuple(self.ratings)
        for rating in ratings:
            if rating is not None:
                _number(rating, "benchmark rating")
        object.__setattr__(
            self, "ratings", tuple(float(r) if r is not None else None for r in ratings)
        )


@dataclass(frozen=True, slots=True)
class House:
    """The criteria, response columns, and assessed relationships for one stage.

    Relationships use 0, 1, 3, and 9. Correlations are unordered pairs of
    response IDs and are separate from weighted scoring.
    """

    criteria: tuple[Criterion, ...]
    responses: tuple[Response, ...]
    matrix: tuple[tuple[int, ...], ...]
    correlations: tuple[Correlation, ...] = ()
    benchmarks: tuple[Benchmark, ...] = ()
    title: str = "House of Quality"

    def __post_init__(self) -> None:
        _name(self.title, "title")
        for field in ("criteria", "responses", "correlations", "benchmarks"):
            object.__setattr__(self, field, tuple(getattr(self, field)))
        matrix = tuple(tuple(row) for row in self.matrix)
        if not self.criteria or not self.responses:
            raise ValueError("a house needs at least one criterion and one response")
        _indices(self.criteria)
        responses = _indices(self.responses)
        if len(matrix) != len(self.criteria) or any(
            len(row) != len(responses) for row in matrix
        ):
            raise ValueError("matrix dimensions must match criteria and responses")
        for row in matrix:
            for score in row:
                if (
                    isinstance(score, bool)
                    or not isinstance(score, Integral)
                    or score not in (0, 1, 3, 9)
                ):
                    raise ValueError("relationship strength must be 0, 1, 3, or 9")
        object.__setattr__(
            self, "matrix", tuple(tuple(map(int, row)) for row in matrix)
        )
        pairs: set[frozenset[str]] = set()
        for correlation in self.correlations:
            pair = frozenset((correlation.first, correlation.second))
            if pair - responses.keys():
                raise ValueError(
                    "correlations must refer to response IDs in this house"
                )
            if pair in pairs:
                raise ValueError("duplicate correlation pair")
            pairs.add(pair)
        labels: set[str] = set()
        for benchmark in self.benchmarks:
            if len(benchmark.ratings) != len(self.criteria):
                raise ValueError("each benchmark needs one rating per criterion")
            if benchmark.label in labels:
                raise ValueError("duplicate benchmark label")
            labels.add(benchmark.label)

    @classmethod
    def from_relationships(
        cls,
        criteria: Sequence[Criterion],
        responses: Sequence[Response],
        relationships: Iterable[tuple[str, str, int]],
        **options,
    ) -> House:
        """Build from (criterion ID, response ID, strength) entries. Omitted cells are zero."""
        rows, columns = _indices(criteria), _indices(responses)
        matrix = [[0] * len(columns) for _ in rows]
        seen: set[tuple[int, int]] = set()
        for criterion_id, response_id, strength in relationships:
            try:
                i, j = rows[criterion_id], columns[response_id]
            except KeyError as exc:
                raise ValueError(f"unknown relationship ID: {exc.args[0]}") from exc
            if (i, j) in seen:
                raise ValueError(
                    f"duplicate relationship: {criterion_id}/{response_id}"
                )
            seen.add((i, j))
            matrix[i][j] = strength
        return cls(criteria, responses, matrix, **options)

    @property
    def scores(self) -> tuple[float, ...]:
        try:
            scores = tuple(
                fsum(
                    criterion.weight * value
                    for criterion, value in zip(self.criteria, column)
                )
                for column in zip(*self.matrix)
            )
        except OverflowError as exc:
            raise ValueError("weighted scores must be finite") from exc
        if not all(map(isfinite, scores)):
            raise ValueError("weighted scores must be finite")
        return scores

    @property
    def shares(self) -> tuple[float, ...]:
        """Column fractions of total score. All-zero scores yield zero shares."""
        scores = self.scores
        maximum = max(scores)
        if maximum == 0:
            return scores
        scaled = tuple(score / maximum for score in scores)
        total = fsum(scaled)
        return tuple(score / total for score in scaled)

    def deploy(
        self, responses: Sequence[Response], matrix: Sequence[Sequence[int]], **options
    ) -> House:
        """Use this house's responses and unrounded scores as the next stage's criteria."""
        criteria = tuple(
            Criterion(response.id, response.label, score)
            for response, score in zip(self.responses, self.scores)
        )
        return House(criteria, responses, matrix, **options)


def _indices(items: Sequence[Criterion | Response]) -> dict[str, int]:
    result: dict[str, int] = {}
    for index, item in enumerate(items):
        if item.id in result:
            raise ValueError(f"duplicate ID: {item.id}")
        result[item.id] = index
    return result
