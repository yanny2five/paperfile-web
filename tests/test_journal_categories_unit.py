"""modules.journal_categories_report."""

from __future__ import annotations

from unittest.mock import MagicMock

from modules.journal_categories_report import compute_journal_categories_report
from tests.conftest import sample_record


def test_compute_journal_categories_report_shape():
    papers = [
        sample_record("1", "McCarl, B.A.", "T", bookjour="AJAE", year="2020"),
    ]
    reader = MagicMock()
    reader.read_journal_definition.return_value = ({}, {"AJAE": ("AgEcon::X", "1")}, {})
    headers, rows = compute_journal_categories_report(
        papers, reader, 2018, 2022, 5, None
    )
    assert "Major class" in headers
    assert isinstance(rows, list)
