"""
Parity test: ``modules.savedata`` write helpers.

The two sides have small signature differences (``show_message`` vs
``gui_messages``) and lazy/eager Tk imports, but the actual file content
written to disk must be byte-identical.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest


def _record(num, **overrides):
    base = {
        "number": str(num),
        "authors": "McCarl, B.A.",
        "title": f"Paper {num}",
        "bookjour": "Test Journal",
        "location": "",
        "volume": "1",
        "pages": "1-2",
        "year": "2020",
        "vitatyp": "J",
        "subject1": "",
        "subject2": "",
        "duplicateoknumber": "0",
        "pdfpresent": "0",
        "pdfpath": "",
        "dateentered": "01/01/2024 12:00:00 PM",
    }
    base.update(overrides)
    return base


def test_build_record_block_text_identical(parity):
    """Same input → identical block text on both sides."""
    data = _record(7, dateentered="03/15/2024 02:34:56 PM")
    desktop, web = parity("savedata.build_record_block", {"data": data})
    assert desktop["text"] == web["text"]
    assert "number||7" in desktop["text"]
    assert desktop["text"].endswith("\n")
    assert "*********$$$$$$$$$$$$" in desktop["text"]


def test_build_record_block_funding_fields_only_when_present(parity):
    """funding_year / total_amount / usable_amount / decision must be omitted when blank."""
    no_funding = _record(8)
    with_funding = _record(
        9,
        vitatyp="PR",
        funding_year="2024",
        total_amount="100000",
        usable_amount="90000",
        decision="Pending",
    )
    d1, w1 = parity("savedata.build_record_block", {"data": no_funding})
    d2, w2 = parity("savedata.build_record_block", {"data": with_funding})
    assert d1 == w1 and d2 == w2
    for blob in (d1["text"], w1["text"]):
        assert "funding_year" not in blob
        assert "total_amount" not in blob
    for blob in (d2["text"], w2["text"]):
        assert "funding_year||2024" in blob
        assert "total_amount||100000" in blob
        assert "usable_amount||90000" in blob
        assert "decision||Pending" in blob


def test_save_to_cnt_appends_byte_for_byte(temp_cnt_pair):
    """save_to_cnt must produce byte-identical output on both sides."""
    from tests.parity.conftest import _run_side, DESKTOP_ROOT, WEB_ROOT

    desktop_path, web_path = temp_cnt_pair
    seed = "MASTER\n01/01/2024\nnumber||1\nauthors||Existing\ntitle||Existing\n*********$$$$$$$$$$$$\n"
    desktop_path.write_text(seed, encoding="utf-8")
    web_path.write_text(seed, encoding="utf-8")

    data = _record(2, dateentered="06/15/2024 10:30:00 AM")
    d_result = _run_side(DESKTOP_ROOT, "savedata.save_to_cnt", {"path": str(desktop_path), "data": data})
    w_result = _run_side(WEB_ROOT, "savedata.save_to_cnt", {"path": str(web_path), "data": data})
    assert d_result["file_b64"] == w_result["file_b64"]


def test_overwrite_record_in_cnt_byte_for_byte(temp_cnt_pair):
    """overwrite_record_in_cnt must produce byte-identical output on both sides."""
    from tests.parity.conftest import _run_side, DESKTOP_ROOT, WEB_ROOT

    desktop_path, web_path = temp_cnt_pair
    seed = (
        "HEADER LINE 1\n"
        "HEADER LINE 2\n"
        "number||1\nauthors||A\ntitle||T1\nbookjour||\nlocation||\nvolume||\npages||\nyear||2020\nvitatyp||J\n"
        "subject1||\nsubject2||\nduplicateoknumber||0\npdfpresent||0\npdfpath||\n"
        "dateentered||01/01/2024 12:00:00 PM\n*********$$$$$$$$$$$$\n"
        "number||2\nauthors||B\ntitle||T2\nbookjour||\nlocation||\nvolume||\npages||\nyear||2021\nvitatyp||J\n"
        "subject1||\nsubject2||\nduplicateoknumber||0\npdfpresent||0\npdfpath||\n"
        "dateentered||02/01/2024 12:00:00 PM\n*********$$$$$$$$$$$$\n"
    )
    desktop_path.write_text(seed, encoding="utf-8")
    web_path.write_text(seed, encoding="utf-8")

    data = _record(2, title="Replaced Title", dateentered="12/01/2024 09:00:00 AM")

    d = _run_side(DESKTOP_ROOT, "savedata.overwrite_record_in_cnt", {"path": str(desktop_path), "data": data})
    w = _run_side(WEB_ROOT, "savedata.overwrite_record_in_cnt", {"path": str(web_path), "data": data})
    assert d["file_b64"] == w["file_b64"]


def test_overwrite_all_records_byte_for_byte(temp_cnt_pair):
    from tests.parity.conftest import _run_side, DESKTOP_ROOT, WEB_ROOT

    desktop_path, web_path = temp_cnt_pair
    seed = "HEADER\n"
    desktop_path.write_text(seed, encoding="utf-8")
    web_path.write_text(seed, encoding="utf-8")

    records = [_record(1), _record(2), _record(3)]
    d = _run_side(DESKTOP_ROOT, "savedata.overwrite_all_records_in_cnt", {"path": str(desktop_path), "records": records})
    w = _run_side(WEB_ROOT, "savedata.overwrite_all_records_in_cnt", {"path": str(web_path), "records": records})
    assert d["file_b64"] == w["file_b64"]


def test_append_records_byte_for_byte(temp_cnt_pair):
    from tests.parity.conftest import _run_side, DESKTOP_ROOT, WEB_ROOT

    desktop_path, web_path = temp_cnt_pair
    seed = "HEADER\nnumber||1\nauthors||X\ntitle||Y\n*********$$$$$$$$$$$$\n"
    desktop_path.write_text(seed, encoding="utf-8")
    web_path.write_text(seed, encoding="utf-8")

    records = [_record(2), _record(3)]
    d = _run_side(DESKTOP_ROOT, "savedata.append_records_to_cnt", {"path": str(desktop_path), "records": records})
    w = _run_side(WEB_ROOT, "savedata.append_records_to_cnt", {"path": str(web_path), "records": records})
    assert d["file_b64"] == w["file_b64"]
