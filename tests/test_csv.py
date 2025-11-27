import json

import pytest

from quality_house import Correlation, load, load_csv, render, save
from quality_house.cli import main


def test_score_csv_with_blank_relationship(tmp_path, capsys):
    matrix = tmp_path / "case.csv"
    matrix.write_text(
        '\ufeffcriterion_id,criterion,weight,R1: Latch force,"R2: Seal, outer"\r\n'
        'C1,Open with gloved hands,5,9,\r\n'
        'C2,Clean after field use,3.5,1,9\r\n',
        encoding="utf-8",
    )

    main(["score", str(matrix)])

    result = json.loads(capsys.readouterr().out)
    assert [(row["id"], row["label"], row["score"]) for row in result] == [
        ("R1", "Latch force", 48.5),
        ("R2", "Seal, outer", 31.5),
    ]


def test_diff_and_render_csv_roof_with_json_baseline(tmp_path, capsys):
    before = tmp_path / "before.json"
    before.write_text(
        json.dumps(
            {
                "criteria": [{"id": "C1", "label": "Open easily", "weight": 5}],
                "responses": [
                    {"id": "R1", "label": "Latch force"},
                    {"id": "R2", "label": "Seal compression"},
                ],
                "matrix": [[9, 0]],
            }
        ),
        encoding="utf-8",
    )
    after = tmp_path / "after.csv"
    after.write_text(
        "criterion_id,criterion,weight,R1: Latch force,R2: Seal compression\n"
        "C1,Open easily,5,9,3\n",
        encoding="utf-8",
    )
    roof = tmp_path / "roof.csv"
    roof.write_text("left,right,relation\nR2,R1,-1\n", encoding="utf-8")
    after.with_name("after-roof.csv").write_text(
        "left,right,relation\nR2,R1,2\n", encoding="utf-8"
    )

    house = load_csv(after, roof=roof)
    assert house.correlations == (Correlation("R2", "R1", -1),)
    assert house.scores == (45, 15)

    main(["diff", str(before), str(after), "--new-roof", str(roof)])
    change = json.loads(capsys.readouterr().out)
    assert change["relationships"] == [
        {"criterion_id": "C1", "response_id": "R2", "before": 0, "after": 3}
    ]
    assert change["correlations"][0]["after"]["strength"] == -1

    output = tmp_path / "case.pdf"
    main([
        "render", str(after), str(output), "--roof", str(roof),
        "--compare-with", str(before),
    ])
    assert output.read_bytes().startswith(b"%PDF-")


def test_csv_requires_a_field_for_each_response(tmp_path):
    matrix = tmp_path / "case.csv"
    matrix.write_text(
        "criterion_id,criterion,weight,R1: Latch force,R2: Seal compression\n"
        "C1,Open easily,5,9\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"case\.csv:2: expected 5 columns"):
        load_csv(matrix)


def test_csv_annotations_render_and_survive_json(tmp_path):
    matrix = tmp_path / "case.csv"
    matrix.write_text(
        "criterion_id,criterion,weight,R1: Latch force,R2: Seal compression,"
        "context [As-is comparison]\n"
        "C1,Open easily,5,9,,Gloves slip\n"
        ",,,,,\n"
        "C2,Keep out rain,3,1,9,Seal leaks\n"
        ",Direction,,↓,target,\n"
        ",Target,,20 N,2 mm,\n"
        ",Current measurement,,30 N,1 mm,\n",
        encoding="utf-8",
    )
    matrix.with_name("case-roof.csv").write_text(
        "left,right,relation\nR2,R1,-1\n", encoding="utf-8"
    )
    house = load_csv(matrix)
    assert house.scores == (48, 27)
    assert house.correlations == (Correlation("R2", "R1", -1),)
    assert [response.direction for response in house.responses] == ["decrease", "target"]
    assert [response.target for response in house.responses] == ["20 N", "2 mm"]

    stored = tmp_path / "case.json"
    save(house, stored)
    restored = load(stored)
    assert restored == house
    labels = {label.get_text() for label in render(restored).axes[0].texts}
    assert {
        "As-is comparison",
        "Gloves slip",
        "Seal leaks",
        "Current measurement",
        "30 N",
        "1 mm",
        "20 N",
        "2 mm",
        "↓",
        "◎",
    } <= labels
    assert "Rank" not in labels

    output = tmp_path / "case.svg"
    main(["render", str(matrix), str(output), "--rank"])
    svg = output.read_text(encoding="utf-8")
    assert "Current measurement" in svg
    assert "Rank" in svg
