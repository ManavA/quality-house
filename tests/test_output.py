import json
import pytest

from matplotlib.backends.backend_agg import FigureCanvasAgg

from quality_house import (
    Benchmark,
    Correlation,
    Criterion,
    House,
    Response,
    load,
    render,
    save,
)


def test_json_round_trip_and_pdf(tmp_path):
    house = House(
        [Criterion("a", "Easy to open", 5), Criterion("b", "Easy to clean", 2)],
        [
            Response("latch", "Spring-loaded latch", "Under 10 N", "decrease"),
            Response("seal", "Seal"),
        ],
        [[9, 1], [3, 9]],
        correlations=[
            Correlation(
                "seal", "latch", -1, "Opening force increases with seal pressure."
            )
        ],
        benchmarks=[Benchmark("Current design", [3, None])],
        title="Reusable case",
    )
    path = tmp_path / "case.json"
    save(house, path)
    assert json.loads(path.read_text())["matrix"] == [[9, 1], [3, 9]]
    assert load(path) == house
    chart = render(house, bars=True)
    FigureCanvasAgg(chart).draw()
    labels = [" ".join(t.get_text().split()) for axis in chart.axes for t in axis.texts]
    assert "51" in labels and "−" in labels and "Current design" in labels
    pdf = tmp_path / "case.pdf"
    chart.savefig(pdf)
    assert pdf.read_bytes().startswith(b"%PDF-")


def test_relationship_symbols_and_response_heading_orientation():
    house = House(
        [Criterion("n1", "Clear directions", 2)],
        [
            Response(
                "R1",
                "A long technical heading for numbered signs",
                direction="increase",
            ),
            Response("R2", "Typeface"),
            Response("R3", "Illumination"),
            Response("R4", "Floor finish"),
        ],
        [[9, 3, 1, 0]],
    )
    chart = render(
        house,
        show_rank=True,
        response_rows={"Unit": ["signs", "points", "lux", "class"]},
        criterion_column=("Baseline", ["Survey pending"]),
    )
    canvas = FigureCanvasAgg(chart)
    canvas.draw()
    axis = chart.axes[0]
    labels = {label.get_text(): label for label in axis.texts}

    assert {"◎ 9", "○ 3", "△ 1", "0", "↑"} <= labels.keys()
    legend = next(text for text in labels if text.startswith("Relationships:"))
    assert all(pair in legend for pair in ("◎ 9", "○ 3", "△ 1", "0 none"))
    assert {
        "Direction of improvement",
        "Rank",
        "Unit",
        "lux",
        "Baseline",
        "Survey pending",
    } <= labels.keys()
    assert (
        labels["↑"].get_position()[1]
        < labels[house.responses[0].label].get_position()[1]
    )
    assert labels["Clear directions"].get_rotation() == 0
    for response in house.responses:
        heading = labels[response.label]
        assert heading.get_rotation() == 90
        heading_box = heading.get_window_extent(canvas.get_renderer())
        assert any(
            all(
                cell.get_window_extent().contains(*point)
                for point in heading_box.get_points()
            )
            for cell in axis.patches
        )


def test_roof_base_and_pair_share_response_column_boundaries():
    from matplotlib.patches import Polygon

    house = House(
        [Criterion("n1", "Read easily", 1)],
        [Response("R1", "Contrast"), Response("R2", "Light"), Response("R3", "Size")],
        [[9, 3, 1]],
        correlations=[Correlation("R1", "R2", 1)],
    )
    axis = render(house).axes[0]
    triangles = [
        patch
        for patch in axis.patches
        if isinstance(patch, Polygon) and len(patch.get_xy()) == 4
    ]
    diamonds = [
        patch
        for patch in axis.patches
        if isinstance(patch, Polygon) and len(patch.get_xy()) == 5
    ]
    anchors = [list(patch.get_xy()) for patch in triangles]

    assert len(anchors) == len(house.responses)
    assert len(diamonds) == 3
    assert anchors[0][2] == pytest.approx(anchors[1][0])
    assert diamonds[0].get_xy()[3] == pytest.approx(anchors[1][0])
    assert diamonds[0].get_xy()[0] == pytest.approx(anchors[0][1])
    assert diamonds[0].get_xy()[2] == pytest.approx(anchors[1][1])


def test_annotations_fit_column_width_with_wide_characters():
    target, detail, context = "W" * 14, "W" * 13, "W" * 25
    house = House(
        [Criterion("C1", "Criterion", 1)],
        [Response("R1", "Response", target=target)],
        [[9]],
        response_rows=(("Test", (detail,)),),
        criterion_column=("Context", (context,)),
    )
    chart = render(house)
    canvas = FigureCanvasAgg(chart)
    canvas.draw()
    axis = chart.axes[0]
    labels = {"".join(t.get_text().splitlines()): t for t in axis.texts}
    response_width = axis.patches[0].get_window_extent().width
    for value in (target, detail):
        assert (
            labels[value].get_window_extent(canvas.get_renderer()).width
            < response_width
        )
    assert (
        labels[context].get_window_extent(canvas.get_renderer()).x1 < chart.bbox.width
    )
