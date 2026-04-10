"""modules.edit_fix_service — duplicates and title keys."""

from __future__ import annotations

from modules.edit_fix_service import (
    correct_elements_filter,
    get_exact_duplicate_groups,
    get_exact_title_duplicate_groups,
    normalize_title_key,
)


def test_get_exact_duplicate_groups():
    a = {"number": "1", "authors": "X", "title": "T", "year": "2020", "vitatyp": "J"}
    b = {"number": "2", "authors": "X", "title": "T", "year": "2020", "vitatyp": "J"}
    c = {"number": "3", "authors": "Y", "title": "Other", "year": "2020", "vitatyp": "J"}
    groups = get_exact_duplicate_groups([a, b, c])
    assert len(groups) == 1
    _sig, recs = groups[0]
    assert {r["number"] for r in recs} == {"1", "2"}


def test_normalize_title_key():
    assert "hello" in normalize_title_key("  Hello, World!  ").lower()


def test_title_duplicate_groups():
    a = {"number": "1", "title": "Same Title Here"}
    b = {"number": "2", "title": "same title here"}
    groups = get_exact_title_duplicate_groups([a, b])
    assert len(groups) >= 1


def test_correct_elements_filter():
    recs = [
        {"number": "1", "title": "Apple study", "authors": "A"},
        {"number": "2", "title": "Banana report", "authors": "B"},
    ]
    m = correct_elements_filter(recs, "title", "apple")
    assert len(m) == 1
    assert m[0][0] == "1"
    assert len(correct_elements_filter(recs, "title", "")) == 2
