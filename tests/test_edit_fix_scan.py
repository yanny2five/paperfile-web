"""modules.edit_fix_service — funky scan."""

from __future__ import annotations

from modules.edit_fix_service import scan_funky_database


def test_scan_funky_database_clean_record():
    rows = scan_funky_database(
        [{"number": "1", "title": "Normal Title", "year": "2020", "authors": "A"}]
    )
    assert isinstance(rows, list)
