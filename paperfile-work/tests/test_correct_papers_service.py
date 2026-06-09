"""modules.correct_papers_service — merge form dicts, enter-papers defaults."""

from __future__ import annotations

from modules.correct_papers_service import (
    DEFAULT_NEW_PAPER,
    record_from_correct_form,
    record_from_enter_form,
)


def test_record_from_correct_form_preserves_unlisted_keys():
    orig = {"number": "1", "authors": "A", "title": "T", "dateentered": "01/01/2020", "extra": "x"}
    form = {"authors": "B", "title": "T2"}
    out = record_from_correct_form(orig, form)
    assert out["authors"] == "B"
    assert out["title"] == "T2"
    assert out["dateentered"] == "01/01/2020"
    assert out["extra"] == "x"
    assert out["number"] == "1"


def test_record_from_enter_form_defaults_ms_vitatyp():
    form = {"authors": "X", "title": "Y", "vitatyp": "J"}
    out = record_from_enter_form(form)
    assert out["authors"] == "X"
    assert out["title"] == "Y"
    assert out["vitatyp"] == "J"
    assert DEFAULT_NEW_PAPER["vitatyp"] == "MS"


def test_record_from_enter_form_empty_form_uses_defaults():
    out = record_from_enter_form({})
    assert out["duplicateoknumber"] == "0"
    assert out["pdfpresent"] == "0"
