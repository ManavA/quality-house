"""Command-line interface for scoring, rendering, and comparing houses."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .csvio import load_csv
from .drawing import render
from .jsonio import load
from .model import House
from .revision import compare


def _load_input(path: Path, roof: Path | None) -> House:
    if path.suffix.lower() == ".csv":
        return load_csv(path, roof=roof)
    if roof is not None:
        raise ValueError("a separate roof requires a CSV matrix")
    return load(path)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Score and draw a House of Quality.")
    commands = parser.add_subparsers(dest="command", required=True)
    score = commands.add_parser("score", help="print weighted scores and shares")
    draw = commands.add_parser("render", help="write a diagram to PDF, SVG, or PNG")
    revision = commands.add_parser("diff", help="compare two houses by ID")
    for command in (score, draw, revision):
        command.add_argument("input", type=Path)
    for command in (score, draw):
        command.add_argument("--roof", type=Path, help="roof CSV for the input matrix")
    draw.add_argument("output", type=Path)
    draw.add_argument("--bars", action="store_true", help="show weighted score bars")
    draw.add_argument("--rank", action="store_true", help="show weighted score ranks")
    draw.add_argument("--no-roof", action="store_true")
    draw.add_argument(
        "--compare-with", type=Path, help="outline changes from an earlier house"
    )
    draw.add_argument("--compare-roof", type=Path, help="roof CSV for --compare-with")
    revision.add_argument("after", type=Path)
    revision.add_argument("--old-roof", type=Path, help="roof CSV for the input matrix")
    revision.add_argument("--new-roof", type=Path, help="roof CSV for the after matrix")

    args = parser.parse_args(argv)
    try:
        roof = args.old_roof if args.command == "diff" else args.roof
        house = _load_input(args.input, roof)
        if args.command == "score":
            result = [
                {
                    "id": response.id,
                    "label": response.label,
                    "score": score,
                    "share": share,
                }
                for response, score, share in zip(
                    house.responses, house.scores, house.shares
                )
            ]
            print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        elif args.command == "diff":
            print(
                json.dumps(
                    asdict(compare(house, _load_input(args.after, args.new_roof))),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            if args.output.suffix.lower() not in {".pdf", ".svg", ".png"}:
                raise ValueError("output filename must end in .pdf, .svg, or .png")
            if args.compare_roof and not args.compare_with:
                raise ValueError("--compare-roof requires --compare-with")
            change = None
            if args.compare_with:
                change = compare(_load_input(args.compare_with, args.compare_roof), house)
            render(
                house,
                bars=args.bars,
                show_rank=args.rank,
                show_roof=False if args.no_roof else None,
                revision=change,
            ).savefig(args.output, dpi=180)
    except (OSError, ValueError, OverflowError) as exc:
        parser.error(str(exc))
