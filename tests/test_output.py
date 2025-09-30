import json

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
