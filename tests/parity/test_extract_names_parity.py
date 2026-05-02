"""
Parity test: ``modules.extract_names``.

The web copy was reformatted (single → double quotes, comment trims) but
should be semantically identical to the desktop copy. We exercise both
``process_authors`` and ``get_all_formatted_names`` with realistic and
adversarial inputs.
"""

from __future__ import annotations

import pytest


PROCESS_AUTHORS_CASES = [
    "McCarl, B.A.",
    "McCarl, B.A. and Other, O.",
    "McCarl, B.A., J.W. Mjelde, and X.X. Fan",
    "Cohen, J.W., Jr. and Lee, K.",
    "von Neumann, J. and Morgenstern, O.",
    "de la Cruz, M. and Lee, K.",
    "Smith J.",
    "",
    "   ",
    "Single",
    "Etemadi, A. et al.",
    "Smith, J., others",
    "Brown,A.B. and  Green, C.D.",
    "  Brown ,  A.B.  ",
    # Authors with diacritics / non-ASCII first chars (test `special_names` order)
    "Žižek, S. and Smith, J.",
    "李, K. and McCarl, B.A.",
]


@pytest.mark.parametrize("raw", PROCESS_AUTHORS_CASES)
def test_process_authors_parity(parity, raw):
    desktop, web = parity("extract_names.process_authors", {"raw": raw})
    assert desktop["names"] == web["names"], (
        f"process_authors disagrees for {raw!r}\n"
        f"  desktop: {desktop['names']}\n"
        f"  web:     {web['names']}"
    )


def test_get_all_formatted_names_parity(parity, fixture_records):
    desktop, web = parity(
        "extract_names.get_all_formatted_names", {"records": fixture_records}
    )
    assert desktop["names"] == web["names"], (
        "get_all_formatted_names disagrees\n"
        f"  desktop: {desktop['names']}\n"
        f"  web:     {web['names']}"
    )


def test_get_all_formatted_names_special_names_first(parity):
    """Spec: names whose first char is non-alpha sort BEFORE alpha names.

    NOTE: ``str.isalpha`` returns True for letters with diacritics (Ž, é, …)
    so they are treated as alpha and sorted with normal names. The
    "specials first" bucket is for names that start with non-letter
    characters (e.g. punctuation in legacy data exports).
    """
    records = [
        {"authors": "*Anonymous, X."},
        {"authors": "Brown, A. and Green, C."},
    ]
    desktop, web = parity(
        "extract_names.get_all_formatted_names", {"records": records}
    )
    assert desktop["names"] == web["names"]
    assert desktop["names"], "expected at least one name"
    first = desktop["names"][0]
    assert not first.lstrip()[0].isalpha(), (
        f"non-alpha name should sort first; got {desktop['names']}"
    )
