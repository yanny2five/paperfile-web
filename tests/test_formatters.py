"""modules.formatters — display strings for search results."""

from __future__ import annotations

from modules.formatters import format_paper


def test_format_paper_basic():
    p = {
        "number": "7",
        "authors": "Smith, J.",
        "title": "A Title",
        "journal": "Journ",
        "year": "2020",
    }
    s = format_paper(p, italics=False, omit_number=False, omit_keywords=True)
    assert "7." in s
    assert "Smith" in s
    assert "A Title" in s


def test_format_paper_italics_and_omit_number():
    p = {"number": "1", "authors": "A", "title": "T", "year": ""}
    s = format_paper(p, italics=True, omit_number=True, omit_keywords=True)
    assert "<i>T</i>" in s
    assert "1." not in s
