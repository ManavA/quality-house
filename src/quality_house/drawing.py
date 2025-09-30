"""Draw a House of Quality as a standalone Matplotlib figure."""

from __future__ import annotations

from textwrap import fill
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Polygon, Rectangle

from .model import House, _indices
from .revision import Revision

_INK = "#203b4f"
_GRID = "#a7b7bf"
_STRENGTHS = {0: "#ffffff", 1: "#f2f5f6", 3: "#e2edf2", 9: "#c9e0ec"}
_DIRECTIONS = {"increase": "↑", "decrease": "↓", "target": "◎", "": ""}


def render(
    house: House,
    *,
    bars: bool = False,
    show_roof: bool | None = None,
    revision: Revision | None = None,
) -> Figure:
    """Render scores, an optional correlation roof, and any benchmark profiles.

    Bars are proportional to the largest score in this house. Pass a revision
    from compare() to outline changed cells and newly added rows and columns.
    """
    roof = bool(house.correlations) if show_roof is None else show_roof
    cols = len(house.responses)
    row_labels = [fill(item.label, width=28) for item in house.criteria]
    headers = [fill(item.label, width=14) for item in house.responses]
    targets = [fill(item.target, width=14) for item in house.responses]
    benchmark_labels = [fill(item.label, width=13) for item in house.benchmarks]
    heights = [max(0.30, 0.16 * len(label.splitlines()) + 0.11) for label in row_labels]
    roof_height = (cols - 1) * 0.235 + 0.09 if roof and cols > 1 else 0
    header_height = (
        0.17 * (max(len(i.splitlines()) for i in headers + benchmark_labels) + 1) + 0.18
    )
    target_height = (
        0.17 * max(len(item.splitlines()) for item in targets) + 0.15
        if any(targets)
        else 0
    )
    left, pitch = 2.96, 0.96
    bench_start = left + cols * pitch
    width = bench_start + len(benchmark_labels) * pitch + 0.20
    title_size = 14 if len(house.title) <= 45 else 11
    title = fill(house.title, width=max(19, int(width * 10)))
    title_space = 0.68 + 0.17 * (len(title.splitlines()) - 1)
    table_y = title_space + roof_height + header_height
    height = table_y + sum(heights) + target_height + (0.97 if bars else 0.82)
    figure = Figure(figsize=(width, height), facecolor="white")
    axis = figure.add_axes((0, 0, 1, 1))
    axis.set(xlim=(0, width), ylim=(height, 0))
    axis.axis("off")

    def label(x, y, value, *, size=8, weight="normal", align="left", color=_INK):
        axis.text(
            x,
            y,
            value,
            fontsize=size,
            fontweight=weight,
            color=color,
            ha=align,
            va="center",
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
    if roof and cols > 1:
        _draw_roof(axis, house, left, pitch, header_y, label)
    for j, response in enumerate(house.responses):
        x = left + j * pitch
        marked = revision is not None and response.id in revision.added_responses
        box(x, header_y, pitch, header_height, "#e5f2eb" if marked else "#e3edf3")
        label(
            x + pitch / 2,
            header_y + header_height / 2,
            headers[j] + f"\n{_DIRECTIONS[response.direction]}",
            weight="semibold",
            align="center",
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
            label(x + pitch / 2, y + row_height / 2, str(value), align="center")
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
    for j, (score, share) in enumerate(zip(scores, house.shares)):
        x = left + j * pitch
        label(
            x + pitch / 2, y + 0.19, f"{score:,.6g}", weight="semibold", align="center"
        )
        label(x + pitch / 2, y + 0.42, f"{share:.2%}", align="center")
        if bars and maximum:
            box(x + 0.15, y + 0.58, pitch - 0.30, 0.06, "#e0e9ee", edge="none")
            box(
                x + 0.15,
                y + 0.58,
                (pitch - 0.30) * score / maximum,
                0.06,
                "#366c85",
                edge="none",
            )
    legend = "9 strong    3 moderate    1 weak    0 none"
    if roof and cols > 1:
        legend += "    |    Roof: + reinforces    − conflicts"
    label(0.22, height - 0.15, legend, size=7)
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
    for i in range(len(house.responses)):
        for j in range(i + 1, len(house.responses)):
            x = left + (i + j + 1) * pitch / 2
            y = header_y - 0.245 - (j - i - 1) * 0.235
            strength = correlations.get((i, j), 0)
            fill_color = (
                "#dceee7" if strength > 0 else "#f4e5de" if strength < 0 else "#f9fafb"
            )
            axis.add_patch(
                Polygon(
                    [
                        (x - pitch / 2, y),
                        (x, y - 0.235),
                        (x + pitch / 2, y),
                        (x, y + 0.235),
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
