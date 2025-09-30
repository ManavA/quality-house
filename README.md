# Quality House

Build a House of Quality from Python or JSON. Score engineering responses against weighted criteria, draw the matrix and correlation roof, and carry scores into the next design stage.

## Run an example

Install the package from the project root with \`python -m pip install .\`, then run the example from the same directory.

    quality-house score examples/reusable-case.json
    quality-house render examples/reusable-case.json case.pdf --bars
    python examples/deployment.py

Use a PDF, SVG, or PNG output filename. Add `--no-roof` to hide the roof. Cell strengths are 0 (none), 1 (weak), 3 (moderate), and 9 (strong). Bar lengths scale to the highest score. The share under each score is its fraction of the total.

## Create and deploy a house

\`\`\`python
from quality_house import Correlation, Criterion, House, Response, render

house = House(
    criteria=[Criterion("open", "Easy to open", 5), Criterion("clean", "Easy to clean", 3)],
    responses=[Response("latch", "Latch force"), Response("seal", "Seal compression")],
    matrix=[[9, 1], [1, 9]],
    correlations=[Correlation("latch", "seal", -1, "More compression raises opening force.")],
)
assert house.scores == (48, 32)

parts = house.deploy([Response("spring", "Latch spring")], [[1], [3]])
assert parts.scores == (144,)
render(house, bars=True).savefig("case.pdf")
\`\`\`

The score of a column is the sum of each relationship strength multiplied by its row weight. A deployment uses the exact previous scores in response order. To build a second study from the same original needs, pass \`house.criteria\` to its constructor.

## Inputs and revisions

- Use \`House.from_relationships(criteria, responses, relations)\` for sparse entries. Each entry contains a criterion ID, a response ID, and a strength. Omitted entries are zero.
- Give each criterion and response an ID that stays stable when its label or position changes. \`compare(before, after)\` reports additions, removals, definition changes, and changed relationships and correlations.
- Supply a revision to \`render(after, revision=compare(before, after))\` or use \`quality-house render after.json after.pdf --compare-with before.json\` to outline changed cells.
- Add \`Benchmark(label, ratings)\` for an external reference with one rating per criterion. Use \`None\` when a rating is unavailable. Benchmark ratings and roof signs stay separate from weighted scoring.
- Load a JSON file with \`load(path)\` and save a definition with \`save(house, path)\`. Use \`quality-house diff before.json after.json\` to inspect the model changes as JSON.

The package includes Python and JSON examples. The [example JSON](examples/reusable-case.json) shows targets, directions, correlations and benchmarks together.
