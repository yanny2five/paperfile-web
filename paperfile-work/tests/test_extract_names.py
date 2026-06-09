"""modules.extract_names."""

from __future__ import annotations

from modules.extract_names import process_authors


def test_process_authors_empty():
    names, _log = process_authors("   ")
    assert names == []


def test_process_authors_simple_comma():
    names, _log = process_authors("Smith, John and Doe, Jane")
    assert len(names) >= 1
