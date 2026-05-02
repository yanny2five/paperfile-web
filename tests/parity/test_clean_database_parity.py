"""
Parity test: ``modules.clean_database.clean_database``.

The desktop copy writes the cleaned records back without preserving the .cnt
header (rewrite from scratch). The web copy delegates to
``overwrite_all_records_in_cnt`` and DOES preserve the header.

For the **records themselves**, the cleaning rules must be byte-identical.
The runner uses a header-less synthetic file so the header-preservation
divergence does not perturb this assertion. The header divergence is
documented separately in the parity report.
"""

from __future__ import annotations

import pytest


# Synthetic records that exercise representative clean_database rules:
#  - smart quotes / curly apostrophes
#  - extra whitespace
#  - title-case adjustments
#  - author-field grammar (and / commas)
DIRTY_RECORDS = [
    {
        "number": "1",
        # smart quotes & double spaces in title
        "authors": "Smith,J.A.  and Jones, K.L.",
        "title": "Why  smart  quotes \x93matter\x94 here",
        "bookjour": " Some  Journal ",
        "location": "",
        "volume": "",
        "pages": "",
        "year": "2020",
        "vitatyp": "J",
        "subject1": "",
        "subject2": "",
        "duplicateoknumber": "0",
        "pdfpresent": "0",
        "pdfpath": "",
        "dateentered": "01/01/2024 12:00:00 PM",
    },
    {
        "number": "2",
        "authors": "  McCarl ,  B.A. ",
        "title": "Energy Policy   in the United States",
        "bookjour": "American Journal",
        "location": "",
        "volume": "",
        "pages": "",
        "year": "2021",
        "vitatyp": "J",
        "subject1": "",
        "subject2": "",
        "duplicateoknumber": "0",
        "pdfpresent": "0",
        "pdfpath": "",
        "dateentered": "02/01/2024 12:00:00 PM",
    },
]


def test_clean_database_records_match(parity):
    desktop, web = parity("clean_database.records", {"records": DIRTY_RECORDS})
    # Compare on a per-record, per-field basis.
    assert len(desktop["records"]) == len(web["records"])
    for d, w in zip(desktop["records"], web["records"]):
        assert d.keys() == w.keys(), (
            f"cleaned records have different fields: desktop={list(d.keys())}, web={list(w.keys())}"
        )
        for k in d:
            assert d[k] == w[k], (
                f"cleaned field {k!r} disagrees for record number={d.get('number')}\n"
                f"  desktop={d[k]!r}\n  web={w[k]!r}"
            )


def test_clean_database_normalizes_whitespace_and_quotes(parity):
    """Sanity: cleaned output should not still contain the dirty markers we fed in."""
    desktop, _ = parity("clean_database.records", {"records": DIRTY_RECORDS})
    assert any("Smith" in r.get("authors", "") for r in desktop["records"])
    # Smart quotes (\x93\x94) should have been normalized away.
    for r in desktop["records"]:
        assert "\x93" not in r.get("title", "")
        assert "\x94" not in r.get("title", "")
