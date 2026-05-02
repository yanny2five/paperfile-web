"""
Parity test: ``modules.exportdata``.

The web copy adds two new helpers — ``generate_xlsx_bytes`` and
``generate_bibtex_string`` — for in-memory HTTP downloads; the desktop copy
ships only the file-writing variants. We exercise both with identical
records and assert that the **content** they ultimately produce matches.

Notes on the comparisons:

- BibTeX is plain text, so we compare strings character-for-character.
- XLSX is a zip-of-XMLs whose bytes vary subtly across pandas/openpyxl
  versions even for identical inputs (e.g. the file ``docProps/core.xml``
  embeds a creation timestamp). We therefore unzip and compare ``sheet1.xml``
  cell values rather than the raw .xlsx bytes.
"""

from __future__ import annotations

import base64
import io
import re
import zipfile

import pytest


SAMPLE_RECORDS = [
    {
        "number": "10",
        "authors": "McCarl, B.A. and Other, O.",
        "title": "Corn Futures",
        "bookjour": "Test Journal",
        "location": "",
        "volume": "1",
        "pages": "1-2",
        "year": "2020",
        "vitatyp": "J",
        "subject1": "energy",
        "subject2": "",
        "pdfpresent": "0",
        "pdfpath": "",
    },
    {
        "number": "11",
        "authors": "Smith, J.",
        "title": "Some Book",
        "bookjour": "Big Press",
        "location": "Boston",
        "volume": "",
        "pages": "55-78",
        "year": "2018",
        "vitatyp": "B",
        "subject1": "",
        "subject2": "",
        "pdfpresent": "0",
        "pdfpath": "",
    },
    {
        "number": "12",
        "authors": "Lee, K. and Cohen, J.W.",
        "title": "Conference Paper Three",
        "bookjour": "Annual Conf Proc",
        "location": "",
        "volume": "",
        "pages": "",
        "year": "2024",
        "vitatyp": "P",
        "subject1": "",
        "subject2": "",
        "pdfpresent": "0",
        "pdfpath": "https://example.com/paper.pdf",
    },
]


def test_bibtex_output_identical(parity):
    desktop, web = parity("exportdata.bibtex", {"records": SAMPLE_RECORDS})
    assert desktop["text"] == web["text"], (
        "BibTeX export output diverges:\n"
        f"--- desktop ---\n{desktop['text']}\n"
        f"--- web ---\n{web['text']}"
    )
    # Sanity: both contain at least one @article and one @book.
    for body in (desktop["text"], web["text"]):
        assert "@article{" in body
        assert "@book{" in body
        assert "@inproceedings{" in body


def _xlsx_cells(b64: str) -> list[str]:
    """Extract a stable view of the workbook for comparison."""
    raw = base64.b64decode(b64)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = sorted(zf.namelist())
        sheet_xml = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
        try:
            shared = zf.read("xl/sharedStrings.xml").decode("utf-8")
        except KeyError:
            shared = ""
    return [names, sheet_xml, shared]


def test_xlsx_workbook_content_identical(parity):
    desktop, web = parity("exportdata.xlsx", {"records": SAMPLE_RECORDS})
    d_cells = _xlsx_cells(desktop["bytes_b64"])
    w_cells = _xlsx_cells(web["bytes_b64"])
    assert d_cells[0] == w_cells[0], (
        f"xlsx zip contents differ.\n  desktop: {d_cells[0]}\n  web:     {w_cells[0]}"
    )
    assert d_cells[1] == w_cells[1], "sheet1.xml content differs between desktop and web"
    assert d_cells[2] == w_cells[2], "sharedStrings.xml differs between desktop and web"


def test_xlsx_columns_match_spec(parity):
    """Column order is fixed by the schema: number, authors, title, bookjour,
    location, volume, pages, year, vitatyp, subject1, subject2, pdfpresent, pdfpath."""
    desktop, _web = parity("exportdata.xlsx", {"records": SAMPLE_RECORDS[:1]})
    raw = base64.b64decode(desktop["bytes_b64"])
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        sheet_xml = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
        try:
            shared = zf.read("xl/sharedStrings.xml").decode("utf-8")
        except KeyError:
            shared = ""

    # Pandas may emit headers as either shared strings or inline strings.
    headers = re.findall(r"<t[^>]*>([^<]+)</t>", shared + sheet_xml)
    expected = [
        "number", "authors", "title", "bookjour", "location",
        "volume", "pages", "year", "vitatyp",
        "subject1", "subject2", "pdfpresent", "pdfpath",
    ]
    for col in expected:
        assert col in headers, f"xlsx missing column {col}; got headers {headers}"
