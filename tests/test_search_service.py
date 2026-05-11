"""Unit tests for ``modules.search_service`` under the desktop-strict spec.

The web's search engine is a thin wrapper around the byte-identical desktop
``modules.searchdata.SearchData`` module plus the year-filter / variants
helpers transcribed from ``paperfile/pages/left_panel.py`` &
``paperfile/pages/right_panel.py``. These tests pin the strict behavior:

* All text matching is case-insensitive **substring** (no Unicode
  normalization, no token-AND, no word swapping).
* Year handling: both empty -> empty-only mode; one filled -> invalid;
  non-4-digit -> invalid; out of [1900, 2100] -> invalid.
* Vita filter: strict uppercase code equality on ``record["vitatyp"]``.
* Keyword: searches subject1 + subject2 only (not the ``keywords`` field).
* Author/title dict shape supports the four desktop inputs:
  ``author``, ``optional_author``, ``title``, ``optional_title`` (all ANDed).
"""

from __future__ import annotations

import pytest

from modules.search_service import (
    apply_year_filter,
    author_variants,
    get_authors,
    get_number,
    get_title,
    get_vita_type,
    get_year,
    normalize,
    parse_year_range_inputs,
    passes_search_type,
    passes_vita_type,
    passes_year_range,
    search_papers,
    sort_results,
)


# ---------------------------------------------------------------------------
# Field accessors
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  Hello  ", "hello"),
        ("", ""),
        (None, ""),
    ],
)
def test_normalize(raw, expected):
    assert normalize(raw) == expected


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

def sample_papers():
    return [
        {
            "number": "5",
            "authors": "Smith, J. and Doe, A.",
            "title": "Machine Learning for Corn",
            "bookjour": "JFE",
            "year": "2020",
            "vitatyp": "J",
            "keywords": "agriculture risk",
        },
        {
            "number": "12",
            "authors": "Jones, B.",
            "title": "Water Policy",
            "bookjour": "AJAE",
            "year": "2018",
            "vitatyp": "B",
            "keywords": "water",
        },
        {
            "number": "7",
            "authors": "X., Y.",
            "title": "Other",
            "bookjour": "J",
            "year": "2010",
            "vitatyp": "R",
            "keywords": "",
            "subject1": "carbon sequestration",
            "subject2": "land use",
        },
    ]


def _author_title_dataset():
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


WIDE_YEAR = {"year_min": "1900", "year_max": "2100"}


# ---------------------------------------------------------------------------
# passes_search_type — author_title (substring, AND across all 4 inputs)
# ---------------------------------------------------------------------------

def test_passes_search_type_author_title_dict_two_inputs():
    p = sample_papers()[0]
    assert passes_search_type(p, {"author": "smith", "title": "corn"}, "author_title") is True
    assert passes_search_type(p, {"author": "smith", "title": "wheat"}, "author_title") is False
    assert passes_search_type(p, {"author": "", "title": ""}, "author_title") is True


def test_passes_search_type_author_title_dict_four_inputs_AND():
    """Filling optional_author / optional_title adds extra ANDed substring
    constraints, mirroring desktop's fuzzy_search_by_author_title."""
    paper = {"authors": "Adams, R.M. and Mearns, L.O.",
             "title": "Climate change and US agriculture"}
    # Both author inputs satisfied
    assert passes_search_type(
        paper,
        {"author": "adams", "optional_author": "mearns", "title": "climate"},
        "author_title",
    ) is True
    # optional_author requires "lee" which isn't there -> reject
    assert passes_search_type(
        paper,
        {"author": "adams", "optional_author": "lee", "title": "climate"},
        "author_title",
    ) is False
    # optional_title requires "wheat" which isn't there -> reject
    assert passes_search_type(
        paper,
        {"author": "adams", "title": "climate", "optional_title": "wheat"},
        "author_title",
    ) is False


# ---------------------------------------------------------------------------
# Strict substring (no token swapping; matches desktop)
# ---------------------------------------------------------------------------

def test_substring_phrase_in_order_matches():
    papers = _author_title_dataset()
    r = search_papers(
        papers,
        query={"title": "climate change"},
        search_type="author_title",
        **WIDE_YEAR,
    )
    nums = sorted(get_number(p) for p in r)
    assert nums == ["1", "5"]


def test_substring_phrase_words_swapped_does_not_match():
    """Desktop substring semantics: 'change climate' is not the substring
    'climate change' so neither paper matches."""
    papers = _author_title_dataset()
    r = search_papers(
        papers,
        query={"title": "change climate"},
        search_type="author_title",
        **WIDE_YEAR,
    )
    assert r == []


def test_search_papers_author_dual_box_AND():
    """Filling author + optional_author ANDs both constraints in the author
    field exactly the way desktop does."""
    papers = _author_title_dataset()
    q = {"author": "adams", "optional_author": "mearns"}
    r = search_papers(papers, query=q, search_type="author_title", **WIDE_YEAR)
    nums = sorted(get_number(p) for p in r)
    assert nums == ["1"]


def test_search_papers_title_dual_box_AND():
    papers = _author_title_dataset()
    q = {"title": "climate", "optional_title": "change"}
    r = search_papers(papers, query=q, search_type="author_title", **WIDE_YEAR)
    nums = sorted(get_number(p) for p in r)
    assert nums == ["1", "5"]


def test_search_papers_all_four_boxes_AND():
    papers = _author_title_dataset()
    q = {
        "author": "adams", "optional_author": "lee",
        "title": "climate", "optional_title": "agriculture",
    }
    r = search_papers(papers, query=q, search_type="author_title", **WIDE_YEAR)
    nums = sorted(get_number(p) for p in r)
    assert nums == ["5"]


def test_author_title_dict_all_empty_passes():
    """All-empty dict + wide year range = every record (used for filter-only
    retrieval by vita type or year range)."""
    papers = _author_title_dataset()
    q = {"author": "", "optional_author": "", "title": "", "optional_title": ""}
    r = search_papers(papers, query=q, search_type="author_title", **WIDE_YEAR)
    assert len(r) == len(papers)


# ---------------------------------------------------------------------------
# Author-name variants (desktop _author_variants)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "input_query,expected_variants",
    [
        ("",            [""]),
        ("Adams",       ["Adams"]),               # no initials -> no variants
        ("P. Cal",      ["P. Cal", "Cal, P.", "Cal P."]),
        ("Cal P.",      ["Cal P.", "P. Cal", "Cal, P."]),
        ("Cal, P.",     ["Cal, P.", "P. Cal", "Cal P."]),
    ],
)
def test_author_variants_match_desktop(input_query, expected_variants):
    assert author_variants(input_query) == expected_variants


def test_author_variants_search_finds_records_in_either_storage_form():
    """A user typing 'B.A. McCarl' must match records stored as either
    'McCarl, B.A.' (first author) or 'B.A. McCarl' (subsequent author)."""
    records = [
        {"number": "10", "authors": "McCarl, B.A. and Bryant, K.J.",
         "title": "T1", "year": "2000"},
        {"number": "20", "authors": "Smith, J., B.A. McCarl, and Doe, A.",
         "title": "T2", "year": "2001"},
        {"number": "30", "authors": "Doe, A.", "title": "T3", "year": "2002"},
    ]
    r = search_papers(
        records,
        query={"author": "B.A. McCarl"},
        search_type="author_title",
        **WIDE_YEAR,
    )
    nums = sorted(get_number(p) for p in r)
    assert nums == ["10", "20"]


# ---------------------------------------------------------------------------
# Year handling — strict desktop semantics
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "first,last,expected",
    [
        ("",     "",     {"mode": "empty_only"}),
        ("2010", "2020", {"mode": "range", "first_year": 2010, "last_year": 2020}),
        ("2010", "",     None),
        ("",     "2020", None),
        ("20",   "2020", None),
        ("abc",  "2020", None),
        ("1899", "2020", None),
        ("2010", "2101", None),
    ],
)
def test_parse_year_range_inputs(first, last, expected):
    assert parse_year_range_inputs(first, last) == expected


def test_apply_year_filter_empty_only_mode():
    records = [{"year": "2020"}, {"year": ""}, {"year": "abc"}, {"year": "2010"}]
    r = apply_year_filter(records, {"mode": "empty_only"})
    assert r == [{"year": ""}]


def test_apply_year_filter_range_mode_drops_non_4_digit():
    records = [{"year": "2020"}, {"year": "abc"}, {"year": "20"}, {"year": "2015"}]
    r = apply_year_filter(records, {"mode": "range", "first_year": 2010, "last_year": 2020})
    years = [p["year"] for p in r]
    assert years == ["2020", "2015"]


def test_search_papers_year_both_empty_returns_year_empty_records_only():
    papers = sample_papers() + [{"number": "99", "year": ""}]
    r = search_papers(
        papers, query={"author": "", "title": ""},
        search_type="author_title",
    )
    nums = sorted(get_number(p) for p in r)
    assert nums == ["99"]


def test_search_papers_invalid_year_input_returns_empty():
    """Desktop blocks the search via popup; web returns []."""
    papers = sample_papers()
    r = search_papers(
        papers, query={"author": "", "title": ""},
        search_type="author_title",
        year_min="2010",
        year_max="",
    )
    assert r == []


def test_search_papers_year_range_filter_works():
    papers = sample_papers()
    r = search_papers(
        papers,
        query={"author": "", "title": ""},
        search_type="author_title",
        year_min="2020",
        year_max="2021",
    )
    assert len(r) == 1
    assert get_number(r[0]) == "5"


# ---------------------------------------------------------------------------
# Vita-type filter — strict uppercase code equality
# ---------------------------------------------------------------------------

def test_passes_vita_type_empty_list_passes():
    assert passes_vita_type({"vitatyp": "J"}, []) is True


def test_passes_vita_type_strict_uppercase_match():
    assert passes_vita_type({"vitatyp": "J"}, ["J"]) is True
    assert passes_vita_type({"vitatyp": "B"}, ["J", "B"]) is True
    assert passes_vita_type({"vitatyp": "B"}, ["J"]) is False


def test_passes_vita_type_strict_does_not_match_lowercase():
    """Desktop strict equality: lowercase code does NOT match uppercase."""
    assert passes_vita_type({"vitatyp": "J"}, ["j"]) is False


def test_passes_vita_type_strict_does_not_match_label():
    """Desktop strict equality: label does NOT match code."""
    assert passes_vita_type({"vitatyp": "J"}, ["Journal Articles"]) is False
    assert passes_vita_type({"vitatyp": "Journal Articles"}, ["J"]) is False


def test_search_papers_vita_filter_strict():
    papers = sample_papers()
    r = search_papers(
        papers, query={"author": "", "title": ""},
        search_type="author_title",
        vita_types=["J"],
        **WIDE_YEAR,
    )
    assert len(r) == 1
    assert get_number(r[0]) == "5"


# ---------------------------------------------------------------------------
# Other modes
# ---------------------------------------------------------------------------

def test_search_papers_journal_book_substring():
    papers = sample_papers()
    r = search_papers(papers, query="jfe", search_type="journal_book", **WIDE_YEAR)
    assert [get_number(p) for p in r] == ["5"]


def test_search_papers_journal_book_words_swapped_does_not_match():
    papers = sample_papers() + [
        {"number": "99", "authors": "X.", "title": "T", "bookjour": "American Journal",
         "year": "2020", "vitatyp": "J"}
    ]
    r = search_papers(papers, query="Journal American", search_type="journal_book", **WIDE_YEAR)
    assert r == []


def test_search_papers_keyword_subject1_subject2_only():
    """Keyword mode searches subject1 + subject2; the ``keywords`` field is
    NOT searched (matches desktop ``fuzzy_search_by_keyword``)."""
    papers = sample_papers()
    # Paper #7 has subject1='carbon sequestration', subject2='land use'.
    r = search_papers(papers, query="sequestration", search_type="keyword", **WIDE_YEAR)
    assert [get_number(p) for p in r] == ["7"]
    r2 = search_papers(papers, query="land use", search_type="keyword", **WIDE_YEAR)
    assert [get_number(p) for p in r2] == ["7"]
    # Paper #5 has keywords='agriculture risk' but no subject1/subject2 with
    # those tokens. Strict-desktop keyword mode must NOT find it.
    r3 = search_papers(papers, query="agriculture risk", search_type="keyword", **WIDE_YEAR)
    assert r3 == []


def test_search_papers_year_mode_filters_by_year_range_only():
    """Select-by-Year mirrors desktop: filter full dataset by First/Last year;
    no separate query field (``query`` may be empty)."""
    papers = sample_papers()
    r = search_papers(papers, query="", search_type="year",
                      year_min="2018", year_max="2018")
    assert [get_number(p) for p in r] == ["12"]


def test_search_papers_number_exact_int_match():
    """search_type='number' uses SearchData.search_by_number(int, exact=True)."""
    papers = sample_papers()
    r = search_papers(papers, query="5", search_type="number", **WIDE_YEAR)
    assert [get_number(p) for p in r] == ["5"]


def test_search_papers_multiple_numbers():
    papers = sample_papers()
    r = search_papers(papers, query="5,12", search_type="multiple_numbers", **WIDE_YEAR)
    nums = sorted(get_number(p) for p in r)
    assert nums == ["12", "5"]


def test_search_papers_multiple_numbers_empty_returns_nothing():
    papers = sample_papers()
    assert search_papers(papers, query="", search_type="multiple_numbers", **WIDE_YEAR) == []
    assert search_papers(papers, query="   ,  ,", search_type="multiple_numbers", **WIDE_YEAR) == []


def test_search_papers_any_field_substring_in_any_single_field():
    """Desktop ``fuzzy_search_by_any_field``: the substring must appear in
    at least one single field (no concatenation, no token AND)."""
    papers = sample_papers()
    # 'agriculture' is in paper #5 keywords field (substring across one field).
    # All other papers don't have 'agriculture' anywhere.
    r = search_papers(papers, query="agriculture", search_type="any_field", **WIDE_YEAR)
    assert [get_number(p) for p in r] == ["5"]


def test_search_papers_any_field_cross_field_tokens_do_NOT_match():
    """e.g., 'machine policy' would match if web concatenated all fields and
    tokenized; desktop substring semantics correctly returns nothing."""
    papers = sample_papers()
    r = search_papers(papers, query="machine policy", search_type="any_field", **WIDE_YEAR)
    assert r == []


# ---------------------------------------------------------------------------
# passes_year_range — backward-compat wrapper
# ---------------------------------------------------------------------------

def test_passes_year_range_both_empty_only_matches_year_empty():
    assert passes_year_range({"year": ""}, None, None) is True
    assert passes_year_range({"year": "2020"}, None, None) is False


def test_passes_year_range_invalid_input_blocks():
    """One filled, one empty -> invalid; predicate blocks every record."""
    assert passes_year_range({"year": "2020"}, "2020", None) is False
    assert passes_year_range({"year": "2020"}, None, "2020") is False


def test_passes_year_range_range_mode_filters_correctly():
    assert passes_year_range({"year": "2020"}, "2010", "2025") is True
    assert passes_year_range({"year": "2005"}, "2010", "2025") is False
    assert passes_year_range({"year": "abc"}, "2010", "2025") is False


# ---------------------------------------------------------------------------
# Sort
# ---------------------------------------------------------------------------

def test_sort_results_title():
    papers = sample_papers()
    s = sort_results(list(reversed(papers)), "title")
    titles = [get_title(x) for x in s]
    assert titles == sorted(titles)


def test_sort_results_falls_back_to_number_for_unknown_key():
    papers = sample_papers()
    s = sort_results(papers, "completely-unknown-sort-key")
    # Default sort config sorts number "backward" (largest first).
    nums = [get_number(p) for p in s]
    assert nums == sorted(nums, key=lambda n: -int(n))
