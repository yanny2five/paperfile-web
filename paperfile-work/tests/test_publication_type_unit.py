"""modules.publication_type_report — bins and table."""

from __future__ import annotations

from modules.publication_type_report import (
    compute_publication_type_report,
    min_year_in_papers,
    year_bins_from_range,
)


def test_year_bins_from_range():
    bins = year_bins_from_range(2018, 2022, 2)
    assert len(bins) >= 1


def test_min_year_in_papers():
    p = [{"year": "n/a"}, {"year": "2019"}, {"year": "2021"}]
    assert min_year_in_papers(p) == 2019


def test_compute_publication_type_report_shape():
    papers = [
        {"vitatyp": "J", "year": "2020", "authors": "A"},
        {"vitatyp": "B", "year": "2021", "authors": "B"},
    ]
    headers, rows = compute_publication_type_report(papers, 2018, 2023, 5, None)
    assert "Vita Type" in headers
    assert len(rows) >= 1
