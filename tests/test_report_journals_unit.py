"""modules.report_journals — frequency, ranks, major class."""

from __future__ import annotations

from modules.report_journals import (
    journal_frequency_rows,
    journal_rows_by_major_class,
    journal_rows_with_ranks,
)


def _papers():
    return [
        {"number": "1", "vitatyp": "J", "year": "2020", "bookjour": "AJAE", "authors": "A"},
        {"number": "2", "vitatyp": "J", "year": "2020", "bookjour": "AJAE", "authors": "B"},
        {"number": "3", "vitatyp": "B", "year": "2020", "bookjour": "Press", "authors": "C"},
    ]


def test_journal_frequency_rows_whole_window():
    rows = journal_frequency_rows(_papers(), 2019, 2021, None)
    names = {r[0]: r[1] for r in rows}
    assert names.get("AJAE") == 2
    # Default vitatypes are J/JR only — book (B) rows are excluded.
    assert "Press" not in names


def test_journal_rows_with_ranks_uses_journal_info():
    info = {"ajae": {"rank": "1", "norm": "2", "sjr_pct": "10", "quartile": "Q1", "abdc": "A"}}
    jr = journal_rows_with_ranks(_papers(), 2019, 2021, None, info)
    ajae_row = next(r for r in jr if r[0] == "AJAE")
    assert ajae_row[2] == "1"


def test_journal_rows_by_major_class():
    jdict = {"AJAE": ("AgEcon::Minor", "5")}
    rows = journal_rows_by_major_class(_papers(), 2019, 2021, None, jdict)
    assert any("AgEcon" in str(r[0]) or r[1] > 0 for r in rows)
