"""Funding proposals (PR) table — from desktop fundingproposalsreport.py."""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from modules.report_year_utils import extract_year_int

Row = Tuple[str, str, str, str, str, str, str]


def build_funding_rows(data: List[dict]) -> List[Row]:
    rows: List[Row] = []
    for rec in data or []:
        if str(rec.get("vitatyp", "")).strip().upper() != "PR":
            continue
        decision = str(rec.get("decision", "") or "").strip().capitalize()
        rows.append(
            (
                str(rec.get("number", "") or ""),
                str(rec.get("title", "") or ""),
                str(rec.get("authors", "") or ""),
                str(rec.get("funding_year", "") or ""),
                str(rec.get("total_amount", rec.get("amount", "")) or ""),
                str(rec.get("usable_amount", "") or ""),
                decision,
            )
        )
    return rows


def author_matches(authors_cell: str, selected_name: str) -> bool:
    if not authors_cell or not selected_name:
        return False
    text = re.sub(r"\s+", " ", authors_cell).strip()
    parts = selected_name.split(",", 1)
    if len(parts) != 2:
        return selected_name.lower() in text.lower()
    last = parts[0].strip()
    first = parts[1].strip()
    if not last or not first:
        return selected_name.lower() in text.lower()
    first_initial = re.escape(first[0])
    first_escaped = re.escape(first)
    pat1_full = rf"\b{re.escape(last)}\s*,\s*{first_escaped}(?:\s+(?:[A-Za-z]\.|[A-Za-z]+))*\b"
    pat1_initial = rf"\b{re.escape(last)}\s*,\s*{first_initial}(?:[A-Za-z]+\.?)?(?:\s+(?:[A-Za-z]\.|[A-Za-z]+))*\b"
    pat2 = rf"\b{first_escaped}(?:\s+[A-Za-z]\.)*\s+{re.escape(last)}\b"
    return (
        re.search(pat1_full, text, flags=re.IGNORECASE) is not None
        or re.search(pat1_initial, text, flags=re.IGNORECASE) is not None
        or re.search(pat2, text, flags=re.IGNORECASE) is not None
    )


def filter_funding_rows(
    rows: List[Row],
    y0: Optional[int],
    y1: Optional[int],
    author_name: Optional[str],
    status: Optional[str],
) -> List[Row]:
    out = []
    for r in rows:
        num, title, authors, fy, total_a, usable_a, dec = r
        if status:
            want = status.strip().lower()
            got = (dec or "").strip().lower()
            if want == "accept" and got != "accept":
                continue
            if want == "reject" and got != "reject":
                continue
            if want == "pending" and got != "pending":
                continue
            if want == "na" and got not in ("n/a", "na", ""):
                continue
        if author_name and author_name.strip():
            if not author_matches(authors or "", author_name.strip()):
                continue
        if y0 is not None or y1 is not None:
            yi = extract_year_int(fy)
            if yi is None:
                continue
            if y0 is not None and yi < y0:
                continue
            if y1 is not None and yi > y1:
                continue
        out.append(r)
    return out


def author_names_from_pr_rows(rows: List[Row]) -> List[str]:
    seen = set()
    names: List[str] = []
    for r in rows:
        raw = (r[2] or "").strip()
        if not raw:
            continue
        for part in re.split(r"\s+and\s+", raw, flags=re.IGNORECASE):
            part = part.strip().rstrip(";")
            if not part:
                continue
            if part.lower() not in seen:
                seen.add(part.lower())
                names.append(part)
    names.sort(key=lambda x: (x.split(",")[0].strip().lower(), x.lower()))
    return names
