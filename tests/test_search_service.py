"""modules.search_service — normalization, filters, search_papers, sort_results."""

from __future__ import annotations

import pytest

from modules.search_service import (
    get_authors,
    get_number,
    get_title,
    get_vita_type,
    get_year,
    normalize,
    passes_search_type,
    passes_vita_type,
    passes_year_range,
    search_papers,
    sort_results,
)


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
    ]


def test_passes_search_type_author_title_dict():
    p = sample_papers()[0]
    assert passes_search_type(p, {"author": "smith", "title": "corn"}, "author_title") is True
    assert passes_search_type(p, {"author": "smith", "title": "wheat"}, "author_title") is False
    assert passes_search_type(p, {"author": "", "title": ""}, "author_title") is True


def test_passes_search_type_author_title_string():
    p = sample_papers()[0]
    assert passes_search_type(p, "machine", "author_title") is True
    assert passes_search_type(p, "nope", "author_title") is False


@pytest.mark.parametrize(
    "stype,q,expect_idx",
    [
        ("number", "5", 0),
        ("number", "12", 1),
        ("journal_book", "jfe", 0),
        ("year", "2018", 1),
        ("vita_type", "b", 1),
        ("keyword", "water", 1),
        ("multiple_numbers", "5,12", None),  # both match — check count
    ],
)
def test_search_papers_single_mode(stype, q, expect_idx):
    papers = sample_papers()
    r = search_papers(papers, query=q, search_type=stype)
    if stype == "multiple_numbers":
        assert len(r) == 2
    else:
        assert len(r) == 1
        assert get_number(r[0]) == papers[expect_idx]["number"]


def test_search_papers_year_range():
    papers = sample_papers()
    r = search_papers(papers, query="", search_type="author_title", year_min="2019", year_max="2021")
    assert len(r) == 1
    assert get_number(r[0]) == "5"


def test_search_papers_vita_types_filter():
    papers = sample_papers()
    r = search_papers(papers, query="", search_type="author_title", vita_types=["J"])
    assert len(r) == 1
    assert get_number(r[0]) == "5"


def test_passes_year_range_non_digit_year():
    p = {"year": "n/a"}
    assert passes_year_range(p, None, None) is True
    assert passes_year_range(p, "2010", None) is False


def test_sort_results_title():
    papers = sample_papers()
    s = sort_results(list(reversed(papers)), "title")
    titles = [get_title(x) for x in s]
    assert titles == sorted(titles)


def test_passes_vita_type_empty_list():
    assert passes_vita_type({"vitatyp": "J"}, []) is True
