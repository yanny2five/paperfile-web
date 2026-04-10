"""modules.report_year_utils."""

from __future__ import annotations

import pytest

from modules.report_year_utils import extract_year_int


@pytest.mark.parametrize(
    "val,expected",
    [
        ("2016", 2016),
        ("September/October 2016", 2016),
        ("", None),
        (None, None),
        ("no-digits", None),
    ],
)
def test_extract_year_int(val, expected):
    assert extract_year_int(val) == expected
