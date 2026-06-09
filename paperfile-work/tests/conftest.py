"""Shared helpers for unit tests."""

from __future__ import annotations

from typing import Any, Dict


def sample_record(
    number: str,
    authors: str,
    title: str,
    *,
    year: str = "2020",
    vitatyp: str = "J",
    bookjour: str = "Test Journal",
) -> Dict[str, Any]:
    return {
        "number": number,
        "authors": authors,
        "title": title,
        "bookjour": bookjour,
        "location": "",
        "volume": "1",
        "pages": "1-2",
        "year": year,
        "vitatyp": vitatyp,
        "subject1": "",
        "subject2": "",
        "duplicateoknumber": "0",
        "pdfpresent": "0",
        "pdfpath": "",
    }
