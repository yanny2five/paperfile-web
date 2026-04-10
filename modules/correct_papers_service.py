"""
Correct Papers: merge HTML form into an existing record dict (desktop EditPaper fields).
Preserves keys not listed here (e.g. unexpected .cnt fields) and keeps dateentered unless overridden.
"""

from __future__ import annotations

from typing import Any, Dict

# Fields edited in the web form (matches build_record_block / editpaper core)
CORRECT_FORM_KEYS = [
    "authors",
    "title",
    "bookjour",
    "location",
    "volume",
    "pages",
    "year",
    "vitatyp",
    "funding_year",
    "total_amount",
    "usable_amount",
    "decision",
    "subject1",
    "subject2",
    "duplicateoknumber",
    "pdfpresent",
    "pdfpath",
]


def record_from_correct_form(original: Dict[str, Any], form_data: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(original)
    for k in CORRECT_FORM_KEYS:
        if k in form_data:
            out[k] = "" if form_data.get(k) is None else str(form_data.get(k, "")).strip()
    return out


# Defaults for a brand-new record (web Enter Papers); vitatyp MS = "No vita type specified" in desktop mapping.
DEFAULT_NEW_PAPER: Dict[str, Any] = {
    "authors": "",
    "title": "",
    "bookjour": "",
    "location": "",
    "volume": "",
    "pages": "",
    "year": "",
    "vitatyp": "MS",
    "funding_year": "",
    "total_amount": "",
    "usable_amount": "",
    "decision": "",
    "subject1": "",
    "subject2": "",
    "duplicateoknumber": "0",
    "pdfpresent": "0",
    "pdfpath": "",
}


def record_from_enter_form(form_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a new record dict from the enter-papers HTML form (same fields as correct-papers edit)."""
    return record_from_correct_form(dict(DEFAULT_NEW_PAPER), form_data)
