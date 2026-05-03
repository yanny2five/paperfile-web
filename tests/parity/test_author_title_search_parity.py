"""Parity tests: web author/title search must equal desktop's
``fuzzy_search_by_author_title`` byte-for-byte when invoked through the
desktop-shape four-input dict.

Background
----------
The desktop UI exposes four parallel inputs feeding
``SearchData.fuzzy_search_by_author_title``:

    author_text, optional_author_text, title_text, optional_title_text

Every nonempty input is ANDed: the authors field must contain every nonempty
``author`` input (substring), and the title field must contain every nonempty
``title`` input (substring). All-empty inputs return all records.

The web Retrieve form was refactored (May 2026) to mirror this exact shape:

    author_query, optional_author_query, title_query, optional_title_query

These tests transcribe ``fuzzy_search_by_author_title`` verbatim as
``_ref_fuzzy_search`` and pin the web's ``search_papers`` to it across a
representative set of multi-input combinations.
"""

from __future__ import annotations

import os
import sys
from typing import List

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if WEB_ROOT not in sys.path:
    sys.path.insert(0, WEB_ROOT)

from modules.search_service import (  # noqa: E402
    get_number,
    passes_search_type,
    search_papers,
)


# -----------------------------------------------------------------------------
# Reference implementation transcribed verbatim from
# paperfile/modules/searchdata.py::SearchData.fuzzy_search_by_author_title
# -----------------------------------------------------------------------------

def _ref_fuzzy_search(
    data: List[dict],
    author_text: str = "",
    title_text: str = "",
    optional_author_text: str = "",
    optional_title_text: str = "",
) -> List[dict]:
    results: List[dict] = []
    for record in data:
        author_ok = True
        title_ok = True

        if "authors" in record:
            author_field = record["authors"].lower()
            if author_text and author_text.lower() not in author_field:
                author_ok = False
            if optional_author_text and optional_author_text.lower() not in author_field:
                author_ok = False
        else:
            if author_text or optional_author_text:
                author_ok = False

        if "title" in record:
            title_field = record["title"].lower()
            if title_text and title_text.lower() not in title_field:
                title_ok = False
            if optional_title_text and optional_title_text.lower() not in title_field:
                title_ok = False
        else:
            if title_text or optional_title_text:
                title_ok = False

        if author_ok and title_ok:
            results.append(record)
    return results


def _dataset() -> List[dict]:
    """Author/title corpus designed to surface AND-vs-OR mistakes."""
    return [
        {"number": "1", "authors": "Adams, R.M. and Mearns, L.O.",
         "title": "Climate change and US agriculture", "year": "2010", "vitatyp": "J"},
        {"number": "2", "authors": "Jones, B. and Smith, K.",
         "title": "Climate adaptation in forestry", "year": "2012", "vitatyp": "J"},
        {"number": "3", "authors": "Adams, R.M.",
         "title": "Risk analysis in dryland farming", "year": "2014", "vitatyp": "J"},
        {"number": "4", "authors": "Doe, A.",
         "title": "Wheat yield variability", "year": "2015", "vitatyp": "J"},
        {"number": "5", "authors": "Adams, R.M. and Lee, P.",
         "title": "Adaptation to climate change in agriculture",
         "year": "2016", "vitatyp": "J"},
    ]


def _nums(records: List[dict]) -> List[str]:
    return sorted(get_number(r) for r in records)


WIDE = {"year_min": "1900", "year_max": "2100"}


# -----------------------------------------------------------------------------
# Parametrized parity matrix: every meaningful 4-input combination
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "author,opt_author,title,opt_title",
    [
        # All empty (filter-only via vita / year).
        ("", "", "", ""),
        # Single inputs.
        ("adams", "", "", ""),
        ("", "", "climate", ""),
        # Pair of primary inputs.
        ("adams", "", "climate", ""),
        # Author + opt_author both filled.
        ("adams", "mearns", "", ""),
        ("adams", "lee", "", ""),
        # Title + opt_title both filled.
        ("", "", "climate", "change"),
        ("", "", "climate", "wheat"),  # wheat veto
        # All four filled.
        ("adams", "lee", "climate", "agriculture"),
        ("adams", "mearns", "climate", "agriculture"),
        # Case sensitivity (both substring searches lowercase the inputs).
        ("Adams", "", "Climate", ""),
        ("ADAMS", "", "CLIMATE", ""),
    ],
)
def test_search_papers_matches_desktop_for_4_input_combinations(
    author, opt_author, title, opt_title,
):
    """Web's author_title path must agree with desktop's
    fuzzy_search_by_author_title for every nonempty-AND combination."""
    papers = _dataset()
    desktop_hits = _ref_fuzzy_search(
        papers,
        author_text=author,
        title_text=title,
        optional_author_text=opt_author,
        optional_title_text=opt_title,
    )
    q = {
        "author": author,
        "optional_author": opt_author,
        "title": title,
        "optional_title": opt_title,
    }
    web_hits = search_papers(papers, query=q, search_type="author_title", **WIDE)
    assert _nums(web_hits) == _nums(desktop_hits)


# -----------------------------------------------------------------------------
# Targeted regression tests (the bugs that motivated the parity refactor)
# -----------------------------------------------------------------------------

def test_substring_phrase_must_be_in_order():
    """Desktop substring semantics: 'change climate' is not the substring
    'climate change' so the search must return zero hits."""
    papers = _dataset()
    desktop_hits = _ref_fuzzy_search(papers, title_text="change climate")
    web_hits = search_papers(
        papers,
        query={"title": "change climate"},
        search_type="author_title",
        **WIDE,
    )
    assert desktop_hits == []
    assert web_hits == []


def test_dual_author_box_AND_does_not_match_when_only_one_side_present():
    """author='adams' alone matches papers 1, 3, 5. Adding optional_author='mearns'
    must filter to the single record that has both."""
    papers = _dataset()
    only_adams = search_papers(
        papers, query={"author": "adams"}, search_type="author_title", **WIDE,
    )
    assert _nums(only_adams) == ["1", "3", "5"]
    both = search_papers(
        papers, query={"author": "adams", "optional_author": "mearns"},
        search_type="author_title", **WIDE,
    )
    assert _nums(both) == ["1"]
    desktop_both = _ref_fuzzy_search(papers, author_text="adams", optional_author_text="mearns")
    assert _nums(both) == _nums(desktop_both)


def test_passes_search_type_dict_uses_all_four_inputs():
    """Unit-level guard: passes_search_type must independently evaluate the
    four constraints."""
    paper = {"authors": "Adams, R.M. and Mearns, L.O.",
             "title": "Climate change and US agriculture"}
    # All filled, all satisfied -> True.
    assert passes_search_type(
        paper,
        {"author": "adams", "optional_author": "mearns",
         "title": "climate", "optional_title": "agriculture"},
        "author_title",
    ) is True
    # optional_author='lee' (not present) -> False.
    assert passes_search_type(
        paper,
        {"author": "adams", "optional_author": "lee",
         "title": "climate", "optional_title": "agriculture"},
        "author_title",
    ) is False
    # optional_title='wheat' (not present) -> False.
    assert passes_search_type(
        paper,
        {"author": "adams", "optional_author": "mearns",
         "title": "climate", "optional_title": "wheat"},
        "author_title",
    ) is False
