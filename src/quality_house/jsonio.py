"""Read and write portable House of Quality data."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .model import Benchmark, Correlation, Criterion, House, Response


def load(path: str | Path) -> House:
    """Read a JSON house with either a dense matrix or sparse relationships."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("house JSON must contain an object")
    if ("matrix" in data) == ("relationships" in data):
        raise ValueError("provide exactly one of matrix or relationships")
    try:
        criteria = tuple(Criterion(**item) for item in data["criteria"])
        responses = tuple(Response(**item) for item in data["responses"])
        correlations = tuple(
            Correlation(**item) for item in data.get("correlations", [])
        )
        benchmarks = tuple(Benchmark(**item) for item in data.get("benchmarks", []))
        options = {"correlations": correlations, "benchmarks": benchmarks}
        for field in ("title", "response_rows", "criterion_column"):
            if field in data:
                options[field] = data[field]
        if "matrix" in data:
            return House(criteria, responses, data["matrix"], **options)
        return House.from_relationships(
            criteria, responses, data["relationships"], **options
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"invalid house JSON: {exc}") from exc


def save(house: House, path: str | Path) -> None:
    """Write the house as UTF-8 JSON with a dense relationship matrix."""
    Path(path).write_text(
        json.dumps(asdict(house), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
