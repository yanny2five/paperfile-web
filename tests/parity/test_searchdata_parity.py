"""
Parity test: ``modules.searchdata.SearchData``.

These files are byte-identical between desktop and web (`test_byte_identical_modules`
covers that), but we still execute every public method against the same fixtures
to catch any future drift in semantics, hidden state, or import-time side-effects.
"""

from __future__ import annotations

import pytest


def _records(fixture_records):
    return list(fixture_records)


def test_search_by_number_exact(parity, fixture_records):
    desktop, web = parity(
        "searchdata.call",
        {
            "records": _records(fixture_records),
            "method": "search_by_number",
            "args": [11],
            "kwargs": {"exact": True},
        },
    )
    assert desktop == web
    assert len(desktop["records"]) == 1
    assert desktop["records"][0]["number"] == "11"


def test_search_by_number_partial(parity, fixture_records):
    desktop, web = parity(
        "searchdata.call",
        {
            "records": _records(fixture_records),
            "method": "search_by_number",
            "args": [3],
            "kwargs": {"exact": False},
        },
    )
    assert desktop == web
    nums = sorted(r["number"] for r in desktop["records"])
    # 30, 31, 32 contain '3'
    assert nums == ["30", "31", "32"]


def test_search_by_number_range(parity, fixture_records):
    desktop, web = parity(
        "searchdata.call",
        {
            "records": _records(fixture_records),
            "method": "search_by_number_range",
            "args": [10, 31],
        },
    )
    assert desktop == web
    nums = sorted(int(r["number"]) for r in desktop["records"])
    assert nums == [10, 11, 20, 30, 31]


def test_search_by_year_range_skips_non_numeric_years(parity, fixture_records):
    """Record 41 has year 'September/October 2016' — both must drop it."""
    desktop, web = parity(
        "searchdata.call",
        {
            "records": _records(fixture_records),
            "method": "search_by_year_range",
            "args": [2015, 2025],
        },
    )
    assert desktop == web
    years = sorted(int(r["year"]) for r in desktop["records"])
    assert years == [2018, 2019, 2020, 2021, 2022, 2024]


def test_fuzzy_search_by_author_title_AND(parity, fixture_records):
    desktop, web = parity(
        "searchdata.call",
        {
            "records": _records(fixture_records),
            "method": "fuzzy_search_by_author_title",
            "args": ["mccarl", "duplicate"],
        },
    )
    assert desktop == web
    assert {r["number"] for r in desktop["records"]} == {"31"}


def test_fuzzy_search_by_author_title_optional_filters(parity, fixture_records):
    desktop, web = parity(
        "searchdata.call",
        {
            "records": _records(fixture_records),
            "method": "fuzzy_search_by_author_title",
            "args": ["mccarl"],
            "kwargs": {
                "title_text": "policy",
                "optional_author_text": None,
                "optional_title_text": None,
            },
        },
    )
    assert desktop == web
    assert [r["number"] for r in desktop["records"]] == ["11"]


def test_fuzzy_search_by_keyword(parity, fixture_records):
    desktop, web = parity(
        "searchdata.call",
        {
            "records": _records(fixture_records),
            "method": "fuzzy_search_by_keyword",
            "args": ["water"],
        },
    )
    assert desktop == web
    assert [r["number"] for r in desktop["records"]] == ["11"]


def test_fuzzy_search_by_book_journal(parity, fixture_records):
    desktop, web = parity(
        "searchdata.call",
        {
            "records": _records(fixture_records),
            "method": "fuzzy_search_by_book_journal",
            "args": ["american"],
        },
    )
    assert desktop == web
    assert sorted(r["number"] for r in desktop["records"]) == ["31", "32"]


def test_fuzzy_search_by_any_field(parity, fixture_records):
    desktop, web = parity(
        "searchdata.call",
        {
            "records": _records(fixture_records),
            "method": "fuzzy_search_by_any_field",
            "args": ["princeton"],
        },
    )
    assert desktop == web
    assert [r["number"] for r in desktop["records"]] == ["40"]


def test_filter_by_vita_type_empty_list_returns_all(parity, fixture_records):
    """SearchData.filter_by_vita_type with empty list returns all input data."""
    desktop, web = parity(
        "searchdata.call",
        {
            "records": _records(fixture_records),
            "method": "filter_by_vita_type",
            "data": _records(fixture_records),
            "vita_types": [],
        },
    )
    assert desktop == web
    assert len(desktop["records"]) == len(fixture_records)


def test_filter_by_vita_type_subset(parity, fixture_records):
    desktop, web = parity(
        "searchdata.call",
        {
            "records": _records(fixture_records),
            "method": "filter_by_vita_type",
            "data": _records(fixture_records),
            "vita_types": ["J"],
        },
    )
    assert desktop == web
    assert all(r["vitatyp"] == "J" for r in desktop["records"])
