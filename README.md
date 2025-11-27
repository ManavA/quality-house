# Quality House

Build a House of Quality from Python, JSON, or CSV. Score engineering responses against weighted criteria, draw the matrix and correlation roof, and carry scores into the next design stage.

## Install

With Python 3.10 or later, install from [PyPI](https://pypi.org/project/quality-house/).

```sh
python -m pip install quality-house
```

## Run an example

Clone the repository and run these commands from its root. The checkout includes the CSV commands.

```sh
python -m pip install .
quality-house score examples/reusable-case.json
quality-house render examples/reusable-case.json case.pdf --bars
python examples/deployment.py
```

Use a PDF, SVG, or PNG output filename. Add `--no-roof` to hide the roof or `--rank` to display each response's rank. Cell strengths are 0 (none), 1 (weak), 3 (moderate), and 9 (strong). Bar lengths scale to the highest score. The share under each score is its fraction of the total.

## Use a spreadsheet CSV

Export a UTF-8 CSV with three criterion columns followed by one `ID: Label`
column per engineering response.

```csv
criterion_id,criterion,weight,latch: Latch force,seal: Seal compression,context [As-is comparison]
open,Open with gloved hands,5,9,3,High latch force
protect,Keep out rain,4,3,9,Water enters at corners
,,,,,
,Direction,,decrease,target,
,Target,,Below 10 N,2 mm,
,Current measurement,,14 N,1 mm,
```

Use one row per criterion. Blank relationship cells count as zero, and wholly
blank rows are skipped. The optional rightmost `context` column adds text beside
each criterion. Use `context [Heading]` for a custom heading without colons or
brackets.

Add optional annotation rows below the criteria. Leave `criterion_id`,
`weight`, and the context cell empty, put the heading in `criterion`, and fill
in the response cells. `Direction` (or `Direction of improvement`) accepts
`increase`, `decrease`, `target`, or the symbols `↑`, `↓`, `◎`. Use `Target`
or `Proposed target` for proposed values. Other headings add text rows under
the matrix.

For the optional roof, put a companion CSV named `<matrix-stem>-roof.csv` in
the same directory. Use columns `left,right,relation` and enter two response
IDs and one of `-2`, `-1`, `1`, or `2` per row.

```sh
quality-house score examples/reusable-case.csv
quality-house render examples/reusable-case.csv case.pdf --rank
quality-house diff examples/reusable-case.json examples/reusable-case.csv
```

Use `--roof` (or `load_csv(path, roof=roof_path)` in Python) to choose a
different roof file. For `diff`, use `--old-roof` and `--new-roof`. For
`render --compare-with`, use `--compare-roof` for the earlier CSV. The JSON
format also supports titles, roof notes, and benchmarks.

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

The package includes Python, JSON, and CSV examples. The [example JSON](examples/reusable-case.json) shows targets, directions, correlations and benchmarks together.
