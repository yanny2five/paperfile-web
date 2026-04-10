"""modules.report_funding."""

from __future__ import annotations

from modules.report_funding import (
    author_matches,
    build_funding_rows,
    filter_funding_rows,
)


def test_build_funding_rows_only_pr():
    data = [
        {"vitatyp": "PR", "number": "1", "title": "T", "authors": "A", "funding_year": "2024"},
        {"vitatyp": "J", "number": "2"},
    ]
    rows = build_funding_rows(data)
    assert len(rows) == 1
    assert rows[0][0] == "1"


def test_filter_funding_by_status():
    rows = [
        ("1", "t", "a", "2024", "1", "1", "Accept"),
        ("2", "t", "a", "2024", "1", "1", "Reject"),
    ]
    acc = filter_funding_rows(rows, None, None, None, "accept")
    assert len(acc) == 1


def test_author_matches_last_comma_first():
    assert author_matches("McCarl, B.A. and Other, X.", "McCarl, B.A.") is True
