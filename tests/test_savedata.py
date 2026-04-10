"""modules.savedata — build_record_block, split, append/overwrite (no Tk)."""

from __future__ import annotations

import pytest

from modules.readdata import CNTReader
from modules.savedata import (
    append_records_to_cnt,
    build_record_block,
    overwrite_all_records_in_cnt,
    overwrite_record_in_cnt,
    split_header_and_records,
)
from tests.conftest import sample_record


def test_build_record_block_includes_core_and_separator():
    data = sample_record("1", "A", "T")
    block = build_record_block(data)
    assert "number||1" in block
    assert "authors||A" in block
    assert "title||T" in block
    assert "*********$$$$$$$$$$$$" in block
    assert block.endswith("\n")


def test_build_record_block_funding_optional():
    d = sample_record("2", "A", "T")
    d["funding_year"] = "2024"
    d["total_amount"] = "100"
    d["usable_amount"] = "50"
    d["decision"] = "Yes"
    b = build_record_block(d)
    assert "funding_year||2024" in b
    assert "total_amount||100" in b
    assert "usable_amount||50" in b
    assert "decision||Yes" in b


def test_split_header_and_records_roundtrip(tmp_path):
    path = tmp_path / "x.cnt"
    header = "Version\n5\n\n"
    r1 = build_record_block(sample_record("1", "A", "One")).strip()
    r2 = build_record_block(sample_record("2", "B", "Two")).strip()
    path.write_text(header + "\n".join([r1, r2]) + "\n", encoding="utf-8")
    h, recs = split_header_and_records(str(path))
    assert any("Version" in x for x in h)
    assert len(recs) == 2


def test_append_and_overwrite(tmp_path):
    path = tmp_path / "db.cnt"
    from modules.utilities_web import write_cnt_new_file

    write_cnt_new_file(str(path), [sample_record("1", "A", "T")], None)
    append_records_to_cnt(
        str(path),
        [sample_record("2", "B", "U")],
        gui_messages=False,
    )
    _, recs = split_header_and_records(str(path))
    assert len(recs) == 2

    r = CNTReader(str(path))
    r.read_file()
    all_rows = r.get_data()
    assert len(all_rows) == 2

    all_rows[0]["title"] = "Changed"
    overwrite_all_records_in_cnt(str(path), all_rows, gui_messages=False)
    r2 = CNTReader(str(path))
    r2.read_file()
    assert r2.get_data()[0]["title"] == "Changed"


def test_overwrite_record_in_cnt_by_number(tmp_path):
    path = tmp_path / "db.cnt"
    from modules.utilities_web import write_cnt_new_file

    write_cnt_new_file(
        str(path),
        [
            sample_record("10", "A", "One"),
            sample_record("20", "B", "Two"),
        ],
        None,
    )
    overwrite_record_in_cnt(
        str(path),
        {**sample_record("20", "B", "Two"), "title": "Updated"},
        gui_messages=False,
    )
    r = CNTReader(str(path))
    r.read_file()
    nums = {x["number"]: x["title"] for x in r.get_data()}
    assert nums["20"] == "Updated"
    assert nums["10"] == "One"


def test_overwrite_missing_number_raises(tmp_path):
    path = tmp_path / "db.cnt"
    from modules.utilities_web import write_cnt_new_file

    write_cnt_new_file(str(path), [sample_record("1", "A", "T")], None)
    with pytest.raises(FileNotFoundError):
        overwrite_record_in_cnt(
            str(path),
            {**sample_record("99", "Z", "Z"), "title": "Nope"},
            gui_messages=False,
        )
