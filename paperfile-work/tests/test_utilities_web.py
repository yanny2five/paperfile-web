"""modules.utilities_web — numbering helpers, write_cnt_new_file."""

from __future__ import annotations

from pathlib import Path

from modules.readdata import CNTReader, abs_from_config
from modules.utilities_web import assign_sequential_numbers, max_record_number, write_cnt_new_file
from tests.conftest import sample_record


def test_max_record_number():
    papers = [{"number": "3"}, {"number": "100"}, {"number": "bad"}, {"number": ""}]
    assert max_record_number(papers) == 100


def test_assign_sequential_numbers():
    rows = [{"number": "x", "title": "a"}, {"title": "b"}]
    out = assign_sequential_numbers(rows, 5)
    assert out[0]["number"] == "5"
    assert out[1]["number"] == "6"


def test_abs_from_config_relative(tmp_path: Path):
    cfg = tmp_path / "config.json"
    cfg.touch()
    rel = "data/db.cnt"
    ap = abs_from_config(str(cfg), rel)
    assert ap == str((tmp_path / "data" / "db.cnt").resolve())


def test_write_cnt_new_file_reads_back(tmp_path: Path):
    dest = tmp_path / "out.cnt"
    recs = [sample_record("1", "A", "T")]
    write_cnt_new_file(str(dest), recs, None)
    r = CNTReader(str(dest))
    r.read_file()
    assert len(r.get_data()) == 1
    assert r.get_data()[0]["authors"] == "A"
