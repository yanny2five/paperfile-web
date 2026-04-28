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
    r = search_papers(papers, query="", search_type="author_title", year_min="2020", year_max="2021")
    assert len(r) == 1
    assert get_number(r[0]) == "5"


def test_search_papers_vita_types_filter():
    papers = sample_papers()
    r = search_papers(papers, query="", search_type="author_title", vita_types=["J"])
    assert len(r) == 1
    assert get_number(r[0]) == "5"


def test_search_papers_vita_types_filter_accepts_label_variants():
    papers = sample_papers()
    papers[0]["vitatyp"] = "Journal Articles"
    r = search_papers(papers, query="", search_type="author_title", vita_types=["J"])
    assert len(r) == 1
    assert get_number(r[0]) == "5"


def test_search_papers_select_by_vita_type_accepts_labels_and_codes():
    papers = sample_papers()
    papers[0]["vitatyp"] = "Journal Articles"
    r_label = search_papers(papers, query="Journal Articles", search_type="vita_type")
    assert len(r_label) == 1
    assert get_number(r_label[0]) == "5"
    r_code = search_papers(papers, query="J", search_type="vita_type")
    assert len(r_code) == 1
    assert get_number(r_code[0]) == "5"


def test_search_papers_empty_keyword_matches_nothing():
    papers = sample_papers()
    r = search_papers(papers, query="", search_type="keyword")
    assert r == []


def test_search_papers_empty_multiple_numbers_matches_nothing():
    papers = sample_papers()
    r = search_papers(papers, query="", search_type="multiple_numbers")
    assert r == []
    r2 = search_papers(papers, query="   ,  ,", search_type="multiple_numbers")
    assert r2 == []


def test_search_papers_keyword_matches_subject1_subject2():
    papers = sample_papers()
    r = search_papers(papers, query="sequestration", search_type="keyword")
    assert len(r) == 1
    assert get_number(r[0]) == "7"
    r2 = search_papers(papers, query="land use", search_type="keyword")
    assert len(r2) == 1
    assert get_number(r2[0]) == "7"


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


def test_passes_vita_type_matches_label_stored_record():
    assert passes_vita_type({"vitatyp": "Journal Articles"}, ["J"]) is True


def test_passes_vita_type_matches_plural_singular_book_variants():
    assert passes_vita_type({"vitatyp": "Book"}, ["B"]) is True
    assert passes_vita_type({"vitatyp": "Books"}, ["B"]) is True


def test_passes_vita_type_matches_plural_singular_report_variants():
    assert passes_vita_type({"vitatyp": "Contract Report"}, ["F"]) is True
    assert passes_vita_type({"vitatyp": "Contract Reports"}, ["F"]) is True


def test_passes_vita_type_matches_plural_singular_proceeding_variants():
    assert passes_vita_type({"vitatyp": "Published Proceeding"}, ["P"]) is True
    assert passes_vita_type({"vitatyp": "Published Proceedings"}, ["P"]) is True


def test_passes_vita_type_matches_legacy_group_alias_values():
    assert passes_vita_type({"vitatyp": "J"}, ["journal"]) is True
    assert passes_vita_type({"vitatyp": "BC"}, ["book"]) is True
    assert passes_vita_type({"vitatyp": "P"}, ["conference"]) is True
    assert passes_vita_type({"vitatyp": "F"}, ["report"]) is True
