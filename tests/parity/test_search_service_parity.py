"""
Parity test: ``search_service.search_papers`` (web) vs ``SearchData.fuzzy_*``
chain (desktop) for the same query.

The web search_service is a re-implementation, not a port. It does Unicode
normalization + multi-term AND, while the desktop uses raw case-insensitive
substring. We assert AGREEMENT on simple cases that real users hit
("McCarl" + "policy", a journal name, a keyword string) and document the
known intentional divergences as expected differences.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = REPO_ROOT / "paperfile-web"


@pytest.fixture(autouse=True)
def _sys_path():
    if str(WEB_ROOT) not in sys.path:
        sys.path.insert(0, str(WEB_ROOT))
    yield


@pytest.fixture
def common_records():
    return [
        {"number": "10", "authors": "McCarl, B.A. and Other, O.", "title": "Corn Futures and Climate", "bookjour": "Test Journal", "year": "2019", "vitatyp": "J", "subject1": "energy", "subject2": "policy"},
        {"number": "11", "authors": "McCarl, B.A.", "title": "Water Policy Note", "bookjour": "Other Journal", "year": "2020", "vitatyp": "J", "subject1": "water", "subject2": ""},
        {"number": "20", "authors": "Smith, J. and Jones, K.L.", "title": "A Book Chapter on Methods", "bookjour": "Some Press", "year": "2018", "vitatyp": "B", "subject1": "methods", "subject2": ""},
        {"number": "31", "authors": "McCarl, B.A.", "title": "Duplicate Title Case", "bookjour": "American Journal", "year": "2021", "vitatyp": "J", "subject1": "duplicate", "subject2": ""},
    ]


def _desktop_author_title(parity_callable, records, author, title):
    desktop, _ = parity_callable(
        "searchdata.call",
        {
            "records": records,
            "method": "fuzzy_search_by_author_title",
            "args": [author, title],
        },
    )
    return [r["number"] for r in desktop["records"]]


def _desktop_keyword(parity_callable, records, keyword):
    desktop, _ = parity_callable(
        "searchdata.call",
        {
            "records": records,
            "method": "fuzzy_search_by_keyword",
            "args": [keyword],
        },
    )
    return [r["number"] for r in desktop["records"]]


def _desktop_journal(parity_callable, records, journal):
    desktop, _ = parity_callable(
        "searchdata.call",
        {
            "records": records,
            "method": "fuzzy_search_by_book_journal",
            "args": [journal],
        },
    )
    return [r["number"] for r in desktop["records"]]


def test_author_title_simple_query_matches_desktop(parity, common_records):
    """Simple ASCII author+title AND query: web and desktop must agree."""
    from modules.search_service import search_papers

    web_hits = sorted(
        r["number"]
        for r in search_papers(
            common_records,
            query={"author": "mccarl", "title": "policy"},
            search_type="author_title",
        )
    )
    desktop_hits = sorted(_desktop_author_title(parity, common_records, "mccarl", "policy"))
    assert web_hits == desktop_hits == ["11"]


def test_journal_book_simple_query_matches_desktop(parity, common_records):
    from modules.search_service import search_papers

    web_hits = sorted(
        r["number"]
        for r in search_papers(common_records, query="american", search_type="journal_book")
    )
    desktop_hits = sorted(_desktop_journal(parity, common_records, "american"))
    assert web_hits == desktop_hits == ["31"]


def test_keyword_query_matches_desktop_via_subject_fields(parity, common_records):
    """Web's keyword mode searches keywords + subject1 + subject2; desktop
    searches subject1 + subject2 only. For inputs that hit subject fields
    they should agree."""
    from modules.search_service import search_papers

    web_hits = sorted(
        r["number"]
        for r in search_papers(common_records, query="energy", search_type="keyword")
    )
    desktop_hits = sorted(_desktop_keyword(parity, common_records, "energy"))
    assert web_hits == desktop_hits == ["10"]


def test_year_only_filter_matches_desktop_year_range(parity, common_records):
    """Year=='2020' returns the same records as a desktop year range [2020,2020]."""
    from modules.search_service import search_papers

    web_hits = sorted(
        r["number"]
        for r in search_papers(common_records, query="2020", search_type="year")
    )
    desktop_records, _ = parity(
        "searchdata.call",
        {
            "records": common_records,
            "method": "search_by_year_range",
            "args": [2020, 2020],
        },
    )
    desktop_hits = sorted(r["number"] for r in desktop_records["records"])
    assert web_hits == desktop_hits == ["11"]
