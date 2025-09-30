"""Command-line interface for JSON houses and rendered charts."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .drawing import render
from .jsonio import load
from .revision import compare


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Score and draw a House of Quality.")
    commands = parser.add_subparsers(dest="command", required=True)
    score = commands.add_parser("score", help="print weighted scores and shares")
    draw = commands.add_parser("render", help="write a diagram to PDF, SVG, or PNG")
    revision = commands.add_parser("diff", help="compare two JSON houses by ID")
    for command in (score, draw, revision):
        command.add_argument("input", type=Path)
    draw.add_argument("output", type=Path)
    draw.add_argument("--bars", action="store_true", help="show weighted score bars")
    draw.add_argument("--no-roof", action="store_true")
    draw.add_argument(
        "--compare-with", type=Path, help="outline changes from an earlier house"
    )
    revision.add_argument("after", type=Path)

    args = parser.parse_args(argv)
    try:
        house = load(args.input)
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
                    asdict(compare(house, load(args.after))),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            if args.output.suffix.lower() not in {".pdf", ".svg", ".png"}:
                raise ValueError("output filename must end in .pdf, .svg, or .png")
            change = (
                compare(load(args.compare_with), house) if args.compare_with else None
            )
            render(
                house,
                bars=args.bars,
                show_roof=False if args.no_roof else None,
                revision=change,
            ).savefig(args.output, dpi=180)
    except (OSError, ValueError, OverflowError) as exc:
        parser.error(str(exc))
