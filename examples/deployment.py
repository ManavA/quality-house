from dataclasses import replace
from pathlib import Path

from quality_house import Correlation, Response, compare, load, render

source = Path(__file__).with_name("reusable-case.json")
first = load(source)
second = first.deploy(
    [
        Response("spring", "Latch spring"),
        Response("gasket", "Gasket"),
        Response("tray", "Insert tray"),
    ],
    [[9, 3, 0], [1, 9, 0], [0, 1, 9]],
    correlations=[Correlation("spring", "gasket", -1)],
    title="Reusable field case: measures to parts",
)
revised = first.responses[:2] + (Response("liner", "Tool-free liner removal"),)
draft = replace(first, responses=revised)
print("Revised response IDs:", compare(first, draft).changed_responses)
print("Component priorities:", second.scores)
render(second, bars=True).savefig("case-components.pdf")
