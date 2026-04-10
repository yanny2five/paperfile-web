"""modules.journals_people_service — faculty line I/O."""

from __future__ import annotations

from pathlib import Path

from modules.journals_people_service import (
    build_faculty_line,
    faculty_rows_from_post,
    load_faculty_rows,
    save_faculty_cng,
    split_faculty_line,
)


def test_split_and_build_faculty_roundtrip():
    line = "Doe, J.::Prof;;2020;;5;;none;;-1;;-1;;-1;;-1;;"
    row = split_faculty_line(line)
    assert row is not None
    assert row["name"] == "Doe, J."
    out = build_faculty_line(
        {
            "name": row["name"],
            "positions_text": row["positions_text"],
            "year": row["year"],
            "citations": row["citations"],
            "tail": row["tail"],
        }
    )
    assert "Doe, J." in out


def test_load_and_save_faculty_cng(tmp_path: Path):
    p = tmp_path / "f.cng"
    p.write_text("A, B.::X;;1;;2;;none;;-1;;-1;;-1;;-1;;\n", encoding="utf-8")
    rows = load_faculty_rows(str(p))
    assert len(rows) == 1
    save_faculty_cng(str(tmp_path / "out.cng"), rows)
    rows2 = load_faculty_rows(str(tmp_path / "out.cng"))
    assert len(rows2) == 1


def test_faculty_rows_from_post():
    form = {
        "f_name_0": "Smith, J.",
        "f_pos_0": "Prof",
        "f_year_0": "2020",
        "f_cit_0": "10",
        "f_tail_0": "",
    }
    rows = faculty_rows_from_post(form)
    assert len(rows) == 1
    assert rows[0]["name"] == "Smith, J."
