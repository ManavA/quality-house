"""Read a relationship matrix and optional roof from spreadsheet CSV exports."""

from __future__ import annotations

import csv
import re
from dataclasses import replace
from pathlib import Path
from typing import Iterator

from .model import Correlation, Criterion, House, Response

_CONTEXT_HEADER = re.compile(r"context(?:\s*\[([^:\[\]]+)\])?", re.IGNORECASE)
_DIRECTIONS = {"↑": "increase", "↓": "decrease", "◎": "target"}
_RESPONSE_FIELDS = {
    "direction": "direction",
    "direction of improvement": "direction",
    "target": "target",
    "proposed target": "target",
}


def _rows(path: str | Path) -> Iterator[tuple[int, list[str]]]:
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source, strict=True)
        try:
            for row in reader:
                cells = [cell.strip() for cell in row]
                if any(cells):
                    yield reader.line_num, cells
        except csv.Error as exc:
            raise ValueError(f"{path}:{reader.line_num}: {exc}") from exc


def _read_roof(path: str | Path) -> list[Correlation]:
    rows = _rows(path)
    _, header = next(rows, (0, []))
    if header != ["left", "right", "relation"]:
        raise ValueError(f"{path}: roof header must be left,right,relation")
    correlations = []
    for line, row in rows:
        if len(row) != len(header):
            raise ValueError(f"{path}:{line}: expected {len(header)} columns")
        try:
            left, right, relation = row
            correlations.append(Correlation(left, right, int(relation)))
        except ValueError as exc:
            raise ValueError(f"{path}:{line}: {exc}") from exc
    return correlations


def load_csv(path: str | Path, *, roof: str | Path | None = None) -> House:
    """Load a CSV matrix, chart annotations, and an optional companion roof."""
    path = Path(path)
    rows = _rows(path)
    line, header = next(rows, (1, []))
    context = _CONTEXT_HEADER.fullmatch(header[-1]) if header else None
    response_headers = header[3:-1] if context else header[3:]
    if header[:3] != ["criterion_id", "criterion", "weight"] or not response_headers:
        raise ValueError(
            f"{path}:{line}: expected criterion_id,criterion,weight and response columns"
        )
    context_heading = (context[1] or "Context").strip() if context else ""
    if context and not context_heading:
        raise ValueError(f"{path}:{line}: expected a context heading inside brackets")
    responses = []
    for column in response_headers:
        response_id, separator, label = column.partition(":")
        if not separator or not response_id.strip() or not label.strip():
            raise ValueError(f"{path}:{line}: expected response header 'ID: Label', got {column!r}")
        responses.append(Response(response_id.strip(), label.strip()))
    criteria = []
    matrix = []
    context_values = []
    annotations = {}
    response_fields = set()
    for line, row in rows:
        if len(row) != len(header):
            raise ValueError(f"{path}:{line}: expected {len(header)} columns")
        try:
            criterion_id, label, weight, *values = row
            note = values.pop() if context else ""
            if not criterion_id and not weight:
                if not label or note:
                    raise ValueError("an annotation row needs a heading and an empty context cell")
                field = _RESPONSE_FIELDS.get(label.casefold())
                if field:
                    if field in response_fields:
                        raise ValueError(f"duplicate {field} row")
                    response_fields.add(field)
                    if field == "direction":
                        values = [_DIRECTIONS.get(value, value.lower()) for value in values]
                    responses = [
                        replace(response, **{field: value})
                        for response, value in zip(responses, values)
                    ]
                else:
                    if label in annotations:
                        raise ValueError(f"duplicate response row heading: {label!r}")
                    annotations[label] = values
                continue
            if response_fields or annotations:
                raise ValueError("criterion rows must come before annotation rows")
            criteria.append(Criterion(criterion_id, label, float(weight)))
            matrix.append([int(value) if value else 0 for value in values])
            if context:
                context_values.append(note)
        except ValueError as exc:
            raise ValueError(f"{path}:{line}: {exc}") from exc
    if roof is None:
        companion = path.with_name(f"{path.stem}-roof.csv")
        if companion.is_file():
            roof = companion
    return House(
        criteria,
        responses,
        matrix,
        correlations=_read_roof(roof) if roof is not None else (),
        response_rows=tuple(annotations.items()),
        criterion_column=(context_heading, context_values) if context else None,
    )
