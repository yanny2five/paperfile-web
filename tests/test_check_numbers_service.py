"""modules.check_numbers_service — parse, stats, renumber."""

from __future__ import annotations

import pytest

from modules.check_numbers_service import compute_number_stats, parse_paper_int, renumber_in_range


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("42", 42),
        (" 99 ", 99),
        ("1,000", 1000),
        ("", None),
        (None, None),
        (7, 7),
        ("abc", None),
    ],
)
def test_parse_paper_int(raw, expected):
    assert parse_paper_int(raw) == expected


def test_compute_number_stats_empty():
    s = compute_number_stats([])
    assert s["lowest"] is None
    assert s["highest"] is None


def test_compute_number_stats_gaps_and_dupes():
    papers = [
        {"number": "1"},
        {"number": "3"},
        {"number": "3"},
        {"number": "5"},
    ]
    s = compute_number_stats(papers)
    assert s["lowest"] == 1
    assert s["highest"] == 5
    assert 2 in s["missing_25"]
    assert 4 in s["missing_25"]
    assert 3 in s["duplicates_25"]
    assert s["suggested_start"] == 6


def test_renumber_in_range():
    data = [{"number": "10", "title": "a"}, {"number": "11", "title": "b"}, {"number": "50", "title": "c"}]
    out, n = renumber_in_range(data, 10, 11)
    assert n == 2
    assert out[0]["number"] == "10"
    assert out[1]["number"] == "11"
    assert out[2]["number"] == "50"
