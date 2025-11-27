"""Draw a House of Quality as a standalone Matplotlib figure."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from textwrap import fill

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Polygon, Rectangle
from matplotlib.textpath import TextToPath

from .model import House, _indices
from .revision import Revision

_INK = "#203b4f"
_GRID = "#a7b7bf"
_ROOF_HALF_HEIGHT = 0.205
_STRENGTHS = {0: "#ffffff", 1: "#f2f5f6", 3: "#e2edf2", 9: "#c9e0ec"}
_RELATIONSHIPS = {0: "0", 1: "△ 1", 3: "○ 3", 9: "◎ 9"}
_DIRECTIONS = {"increase": "↑", "decrease": "↓", "target": "◎", "": ""}


def render(
    house: House,
    *,
    bars: bool = False,
    show_roof: bool | None = None,
    revision: Revision | None = None,
    show_rank: bool = False,
    response_rows: Mapping[str, Sequence[str]] | None = None,
    criterion_column: tuple[str, Sequence[str]] | None = None,
) -> Figure:
    """Render scores, an optional correlation roof, and any benchmark profiles.

    Bars are proportional to the largest score in this house. Pass a revision
    from compare() to outline changed cells and newly added rows and columns.
    Response rows annotate the columns below the matrix. A criterion column
    adds text alongside the criterion rows, such as observations from a baseline.
    Explicit annotation arguments override the corresponding house annotations.
    """
    roof = bool(house.correlations) if show_roof is None else show_roof
    cols = len(house.responses)
    if criterion_column is None:
        criterion_column = house.criterion_column
    if response_rows is None:
        response_rows = dict(house.response_rows)
    left, pitch = 2.96, 0.96
    context_width = 1.75 if criterion_column is not None else 0
    header_font = FontProperties(size=8, weight="semibold")
    body_font = FontProperties(size=8)
    detail_font = FontProperties(size=7)
    text_path = TextToPath()

    def fit_text(value, chars, inches, font):
        for limit in range(chars, 0, -1):
            wrapped = fill(value, width=limit)
            if all(
                text_path.get_text_width_height_descent(line, font, ismath=False)[0]
                <= inches * 72
                for line in wrapped.splitlines()
            ):
                return wrapped
        return wrapped

    row_labels = [fill(item.label, width=28) for item in house.criteria]
    context_labels = [""] * len(row_labels)
    context_heading = ""
    if criterion_column is not None:
        context_heading, values = criterion_column
        if len(values) != len(row_labels):
            raise ValueError("criterion column needs one value per criterion")
        context_heading = fit_text(
            context_heading, 24, context_width - 0.16, header_font
        )
        context_labels = [
            fit_text(value, 25, context_width - 0.16, body_font) for value in values
        ]
    details = []
    for heading, values in response_rows.items():
        if len(values) != cols:
            raise ValueError(f"response row {heading!r} needs one value per response")
        heading = fit_text(heading, 28, left - 0.32, header_font)
        wrapped = [fit_text(value, 13, pitch - 0.10, detail_font) for value in values]
        lines = max(len(value.splitlines()) for value in wrapped)
        row_height = max(0.30, 0.135 * lines, 0.15 * len(heading.splitlines())) + 0.04
        details.append((heading, wrapped, row_height))
    headers = [" ".join(item.label.split()) for item in house.responses]
    targets = [
        fit_text(item.target, 14, pitch - 0.10, body_font) for item in house.responses
    ]
    benchmark_labels = [fill(item.label, width=13) for item in house.benchmarks]
    heights = [
        max(0.30, 0.16 * max(len(row.splitlines()), len(context.splitlines())) + 0.11)
        for row, context in zip(row_labels, context_labels)
    ]
    roof_height = cols * _ROOF_HALF_HEIGHT + 0.12 if roof and cols > 1 else 0
    header_text_height = (
        max(
            text_path.get_text_width_height_descent(header, header_font, ismath=False)[
                0
            ]
            for header in headers
        )
        / 72
    )
    benchmark_lines = max(
        (len(item.splitlines()) for item in benchmark_labels), default=0
    )
    direction_height = 0.25 if any(item.direction for item in house.responses) else 0
    extra_header_lines = max(benchmark_lines, len(context_heading.splitlines()))
    header_height = max(header_text_height, 0.17 * extra_header_lines) + 0.30
    target_height = (
        0.17 * max(len(item.splitlines()) for item in targets) + 0.15
        if any(targets)
        else 0
    )
    bench_start = left + cols * pitch
    context_start = bench_start + len(benchmark_labels) * pitch
    width = context_start + context_width + 0.20
    title_size = 14 if len(house.title) <= 45 else 11
    title = fill(house.title, width=max(19, int(width * 10)))
    title_space = 0.68 + 0.17 * (len(title.splitlines()) - 1)
    table_y = title_space + roof_height + direction_height + header_height
    has_roof = roof and cols > 1
    height = table_y + sum(heights) + target_height + (0.97 if bars else 0.82)
    height += sum(item[2] for item in details) + (0.23 if show_rank else 0)
    if details:
        height += 0.07
    legend_rows = int(has_roof) + int(bool(direction_height))
    height += legend_rows * 0.16
    figure = Figure(figsize=(width, height), facecolor="white")
    axis = figure.add_axes((0, 0, 1, 1))
    axis.set(xlim=(0, width), ylim=(height, 0))
    axis.axis("off")

    def label(
        x, y, value, *, size=8, weight="normal", align="left", color=_INK, rotation=0
    ):
        axis.text(
            x,
            y,
            value,
            fontsize=size,
            fontweight=weight,
            color=color,
            ha=align,
            va="center",
            rotation=rotation,
            usetex=False,
            parse_math=False,
        )

    def box(x, y, w, h, fill_color, edge=_GRID, line=0.55):
        axis.add_patch(
            Rectangle(
                (x, y), w, h, facecolor=fill_color, edgecolor=edge, linewidth=line
            )
        )

    label(0.2, title_space / 2, title, size=title_size, weight="semibold")
    header_y = table_y - header_height
    direction_y = header_y - direction_height
    if has_roof:
        _draw_roof(axis, house, left, pitch, direction_y, label)
    if direction_height:
        label(
            0.22,
            direction_y + direction_height / 2,
            "Direction of improvement",
            weight="semibold",
        )
    for j, response in enumerate(house.responses):
        x = left + j * pitch
        marked = revision is not None and response.id in revision.added_responses
        if direction_height:
            box(x, direction_y, pitch, direction_height, "#f4f8fa")
            label(
                x + pitch / 2,
                direction_y + direction_height / 2,
                _DIRECTIONS[response.direction],
                align="center",
                size=10,
            )
        box(x, header_y, pitch, header_height, "#e5f2eb" if marked else "#e3edf3")
        label(
            x + pitch / 2,
            header_y + header_height / 2,
            headers[j],
            weight="semibold",
            align="center",
            rotation=90,
        )
    for j, header in enumerate(benchmark_labels):
        x = bench_start + j * pitch
        box(x, header_y, pitch, header_height, "#ebeff2")
        label(
            x + pitch / 2,
            header_y + header_height / 2,
            header,
            weight="semibold",
            align="center",
        )
    label(0.22, header_y + header_height / 2, "Criterion", weight="semibold")
    label(
        left - 0.32,
        header_y + header_height / 2,
        "Weight",
        weight="semibold",
        align="center",
    )
    if criterion_column is not None:
        box(context_start, header_y, context_width, header_height, "#ebeff2")
        label(
            context_start + 0.08,
            header_y + header_height / 2,
            context_heading,
            weight="semibold",
        )

    altered = (
        {(c.criterion_id, c.response_id) for c in revision.relationships}
        if revision
        else set()
    )
    y = table_y
    for i, (criterion, row, row_height) in enumerate(
        zip(house.criteria, house.matrix, heights)
    ):
        mark = revision is not None and criterion.id in revision.added_criteria
        if mark:
            box(0.12, y, left - 0.12, row_height, "#e5f2eb", edge="none")
        label(0.22, y + row_height / 2, row_labels[i])
        label(left - 0.32, y + row_height / 2, f"{criterion.weight:g}", align="center")
        for j, (response, value) in enumerate(zip(house.responses, row)):
            x = left + j * pitch
            changed = (criterion.id, response.id) in altered
            box(
                x,
                y,
                pitch,
                row_height,
                _STRENGTHS[value],
                "#96632d" if changed else _GRID,
                1.6 if changed else 0.55,
            )
            label(
                x + pitch / 2, y + row_height / 2, _RELATIONSHIPS[value], align="center"
            )
        for j, benchmark in enumerate(house.benchmarks):
            x = bench_start + j * pitch
            box(x, y, pitch, row_height, "#f8fafb")
            score = benchmark.ratings[i]
            label(
                x + pitch / 2,
                y + row_height / 2,
                "—" if score is None else f"{score:g}",
                align="center",
            )
        if criterion_column is not None:
            box(context_start, y, context_width, row_height, "#f8fafb")
            label(context_start + 0.08, y + row_height / 2, context_labels[i])
        y += row_height

    if target_height:
        label(0.22, y + target_height / 2, "Target", weight="semibold")
        for j, target in enumerate(targets):
            label(
                left + (j + 0.5) * pitch, y + target_height / 2, target, align="center"
            )
        y += target_height
    label(0.22, y + 0.19, "Weighted score", weight="semibold")
    label(0.22, y + 0.42, "Share of score")
    scores = house.scores
    maximum = max(scores)
    rank_height = 0.23 if show_rank else 0
    if show_rank:
        label(0.22, y + 0.65, "Rank")
    for j, (score, share) in enumerate(zip(scores, house.shares)):
        x = left + j * pitch
        label(
            x + pitch / 2, y + 0.19, f"{score:,.6g}", weight="semibold", align="center"
        )
        label(x + pitch / 2, y + 0.42, f"{share:.2%}", align="center")
        if show_rank:
            rank = 1 + sum(other > score for other in scores)
            label(x + pitch / 2, y + 0.65, str(rank), align="center")
        if bars and maximum:
            bar_y = y + 0.58 + rank_height
            box(x + 0.15, bar_y, pitch - 0.30, 0.06, "#e0e9ee", edge="none")
            box(
                x + 0.15,
                bar_y,
                (pitch - 0.30) * score / maximum,
                0.06,
                "#366c85",
                edge="none",
            )
    detail_y = y + (0.74 if bars else 0.60) + rank_height
    for heading, values, row_height in details:
        label(0.22, detail_y + row_height / 2, heading, weight="semibold")
        for j, value in enumerate(values):
            x = left + j * pitch
            box(x, detail_y, pitch, row_height, "#f4f8fa")
            label(
                x + pitch / 2, detail_y + row_height / 2, value, size=7, align="center"
            )
        detail_y += row_height
    legends = ["Relationships: ◎ 9 strong    ○ 3 moderate    △ 1 weak    0 none"]
    if direction_height:
        legends.append(
            "Direction: ↑ increase    ↓ decrease    ◎ meet a specified target"
        )
    if has_roof:
        legends.append("Roof: + / ++ reinforces    − / −− conflicts")
    for i, legend in enumerate(reversed(legends)):
        label(0.22, height - 0.15 - i * 0.16, legend, size=7)
    return figure


def _draw_roof(
    axis: Axes, house: House, left: float, pitch: float, header_y: float, label
) -> None:
    ids = _indices(house.responses)
    correlations = {
        tuple(
            sorted((ids[correlation.first], ids[correlation.second]))
        ): correlation.strength
        for correlation in house.correlations
    }
    half_height = _ROOF_HALF_HEIGHT
    for column, response in enumerate(house.responses):
        x = left + column * pitch
        axis.add_patch(
            Polygon(
                [
                    (x, header_y),
                    (x + pitch / 2, header_y - half_height),
                    (x + pitch, header_y),
                ],
                facecolor="#f0f5f8",
                edgecolor=_GRID,
                linewidth=0.55,
            )
        )
        if len(response.id) <= 4 and response.id.isprintable():
            label(
                x + pitch / 2,
                header_y - 0.065,
                response.id,
                align="center",
                size=6.5,
                weight="semibold",
            )

    for i in range(len(house.responses)):
        for j in range(i + 1, len(house.responses)):
            x = left + (i + j + 1) * pitch / 2
            y = header_y - (j - i) * half_height
            strength = correlations.get((i, j), 0)
            fill_color = (
                "#dceee7" if strength > 0 else "#f4e5de" if strength < 0 else "#ffffff"
            )
            axis.add_patch(
                Polygon(
                    [
                        (x - pitch / 2, y),
                        (x, y - half_height),
                        (x + pitch / 2, y),
                        (x, y + half_height),
                    ],
                    closed=True,
                    facecolor=fill_color,
                    edgecolor=_GRID,
                    linewidth=0.5,
                )
            )
            if strength:
                sign = "+" if strength > 0 else "−"
                label(
                    x,
                    y,
                    sign * abs(strength),
                    align="center",
                    weight="semibold",
                    color="#135b45" if strength > 0 else "#93402d",
                )
