"""modules.report_composite_simple."""

from __future__ import annotations

from modules.report_composite_simple import compute_composite


def test_compute_composite_compare_mode():
    papers = [
        {"number": "1", "vitatyp": "J", "year": "2020", "authors": "McCarl, B.A.", "bookjour": "J1"},
    ]
    faculty = [{"name": "McCarl, B.A.", "positions": ["Professor"], "year": 2020, "citations": 100}]
    headers, rows, missing = compute_composite(
        papers, faculty, 2018, 2022, "compare_output", {}
    )
    assert headers[0] == "Faculty"
    assert isinstance(missing, str)
    assert len(rows) >= 1


def test_compute_composite_empty_faculty():
    headers, rows, missing = compute_composite([], [], 2018, 2022, "compare_output", {})
    assert rows == []
    assert missing == ""
