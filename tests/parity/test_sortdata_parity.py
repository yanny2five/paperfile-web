"""
Parity test: ``modules.sortdata.SortData``.

Verifies that the multi-key sort produces identical output for every named
sort flavor used by the desktop UI: number, author, title, book/journal, vita.
"""

from __future__ import annotations

import pytest


# Sort configs taken from desktop pages/left_panel.py get_sort_config().
SORT_CONFIGS = {
    "number": {
        "number": {"priority": 1, "order": "backward"},
        "authors": {"priority": 2, "order": "forwards"},
        "title": {"priority": 3, "order": "forwards"},
        "bookjour": {"priority": 4, "order": "forwards"},
        "year": {"priority": 5, "order": "backward"},
        "vitatyp": {"priority": 6, "order": "vitord"},
    },
    "author": {
        "authors": {"priority": 1, "order": "forwards"},
        "title": {"priority": 2, "order": "forwards"},
        "bookjour": {"priority": 3, "order": "forwards"},
        "vitatyp": {"priority": 4, "order": "vitord"},
        "year": {"priority": 5, "order": "backward"},
        "number": {"priority": 6, "order": "backward"},
    },
    "title": {
        "title": {"priority": 1, "order": "forwards"},
        "authors": {"priority": 2, "order": "forwards"},
        "bookjour": {"priority": 3, "order": "forwards"},
        "year": {"priority": 4, "order": "backward"},
        "vitatyp": {"priority": 5, "order": "vitord"},
        "number": {"priority": 6, "order": "backward"},
    },
    "bookjour": {
        "bookjour": {"priority": 1, "order": "forwards"},
        "vitatyp": {"priority": 2, "order": "vitord"},
        "authors": {"priority": 3, "order": "forwards"},
        "title": {"priority": 4, "order": "forwards"},
        "year": {"priority": 5, "order": "backward"},
        "number": {"priority": 6, "order": "backward"},
    },
    "vitatyp": {
        "vitatyp": {"priority": 1, "order": "vitord"},
        "year": {"priority": 2, "order": "backward"},
        "authors": {"priority": 3, "order": "forwards"},
        "title": {"priority": 4, "order": "forwards"},
        "bookjour": {"priority": 5, "order": "forwards"},
        "number": {"priority": 6, "order": "backward"},
    },
}


def _sortable(records):
    """Historically SortData crashed when ``order=backward`` and a numeric
    field was empty or non-parseable. Both sides now coerce empty / non-int
    values to a typed sentinel that sorts last (PARITY_REPORT.md §3.3 #1, #2).
    This shim used to filter such rows out; we keep the function (callers
    still pass ``_sortable(...)``) but it is now a no-op pass-through, so
    we exercise the messy-year and empty-int rows in the existing flavor
    parity tests too."""
    return list(records)


@pytest.mark.parametrize("flavor", sorted(SORT_CONFIGS))
def test_sort_flavors_match_desktop_and_web(parity, fixture_records, flavor):
    desktop, web = parity(
        "sortdata.sort",
        {
            "records": _sortable(fixture_records),
            "sort_config": SORT_CONFIGS[flavor],
            "vita_order_key": "vitord1",
        },
    )
    assert desktop == web, (
        f"sort flavor {flavor!r} disagrees:\n"
        f"  desktop order: {[r['number'] for r in desktop['records']]}\n"
        f"  web order:     {[r['number'] for r in web['records']]}"
    )


@pytest.mark.parametrize("vita_order_key", ["vitord1", "vitord2", "vitordg"])
def test_sort_vita_order_keys_match(parity, fixture_records, vita_order_key):
    desktop, web = parity(
        "sortdata.sort",
        {
            "records": _sortable(fixture_records),
            "sort_config": SORT_CONFIGS["vitatyp"],
            "vita_order_key": vita_order_key,
        },
    )
    assert desktop == web, f"vita_order_key={vita_order_key} disagrees"


def test_sort_messy_years_no_crash_and_match(parity):
    """Messy / non-integer year strings used to crash both sides under
    ``order=backward``; the fix (PARITY_REPORT.md §3.3 #2) coerces them to a
    typed missing-sentinel that sorts after parseable years. Both sides
    must agree."""
    records = [
        {"number": "1", "year": "September/October 2016", "authors": "X"},
        {"number": "2", "year": "2020", "authors": "Y"},
        {"number": "3", "year": "", "authors": "Z"},
    ]
    config = {
        "year": {"priority": 1, "order": "backward"},
    }
    desktop, web = parity(
        "sortdata.sort",
        {"records": records, "sort_config": config, "vita_order_key": "vitord1"},
    )
    assert desktop == web, (
        "messy-year sort disagrees:\n"
        f"  desktop: {[r['number'] for r in desktop['records']]}\n"
        f"  web:     {[r['number'] for r in web['records']]}"
    )
    # The parseable year (2020) must come first under backward sort, and the
    # missing/non-parseable values must sort last. Order between the two
    # missing rows is stable.
    nums = [r["number"] for r in desktop["records"]]
    assert nums[0] == "2", nums


def test_sort_empty_strings_go_last(parity):
    """Empty fields sort after non-empty regardless of key type
    (typed missing-sentinel; PARITY_REPORT.md §3.3 #1)."""
    records = [
        {"number": "1", "authors": "Beta", "title": "B", "year": "2020", "vitatyp": "J"},
        {"number": "2", "authors": "", "title": "A", "year": "2021", "vitatyp": "J"},
    ]
    config = {
        "authors": {"priority": 1, "order": "forwards"},
    }
    desktop, web = parity(
        "sortdata.sort",
        {"records": records, "sort_config": config, "vita_order_key": "vitord1"},
    )
    assert desktop == web
    # Non-empty author should come first; empty last.
    assert desktop["records"][0]["authors"] == "Beta"
    assert desktop["records"][1]["authors"] == ""


def test_sort_empty_int_field_backward_no_crash(parity):
    """Empty ``year``/``number`` under ``backward`` used to raise TypeError when
    other rows had real ints (mixed str ``"zzzzzzzz"`` vs int). Now both sides
    return a stable order with empties sorted last."""
    records = [
        {"number": "10", "authors": "A", "year": "2020"},
        {"number": "", "authors": "B", "year": "2018"},
        {"number": "5", "authors": "C", "year": ""},
    ]
    config = {
        "number": {"priority": 1, "order": "backward"},
    }
    desktop, web = parity(
        "sortdata.sort",
        {"records": records, "sort_config": config, "vita_order_key": "vitord1"},
    )
    assert desktop == web
    nums = [r["number"] for r in desktop["records"]]
    assert nums[0] == "10" and nums[-1] == "", nums
