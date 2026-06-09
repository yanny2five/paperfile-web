"""
Simplified composite faculty productivity (desktop compositesummary.py is far larger).
Three modes: compare counts, ranked counts, journal-power (mean AGECO rank for J papers).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from modules.extract_names import process_authors
from modules.report_year_utils import extract_year_int

ALLOWED_POSITIONS = {"Assistant Professor", "Associate Professor", "Professor"}


def faculty_display_list(faculty_data: List[dict]) -> List[str]:
    filtered = [
        p
        for p in faculty_data or []
        if any(pos in ALLOWED_POSITIONS for pos in p.get("positions", []))
    ]
    names = [p["name"] for p in filtered if p.get("name")]
    return sorted(
        names,
        key=lambda x: (
            x.split(",")[0].strip().lower(),
            x.split(",")[1].strip().lower() if "," in x else "",
        ),
    )


def _pub_count_for_person(papers: List[dict], name: str, y0: int, y1: int) -> int:
    n = 0
    for rec in papers:
        y = extract_year_int(rec.get("year", ""))
        if y is None or not (y0 <= y <= y1):
            continue
        parsed, _ = process_authors(rec.get("authors") or "")
        if name in parsed:
            n += 1
    return n


def _mean_journal_rank(
    papers: List[dict],
    name: str,
    y0: int,
    y1: int,
    journal_info: dict,
) -> Tuple[float, int]:
    ranks: List[int] = []
    for rec in papers:
        if str(rec.get("vitatyp", "")).strip() != "J":
            continue
        y = extract_year_int(rec.get("year", ""))
        if y is None or not (y0 <= y <= y1):
            continue
        parsed, _ = process_authors(rec.get("authors") or "")
        if name not in parsed:
            continue
        jn = (rec.get("bookjour") or "").strip().lower()
        info = journal_info.get(jn) if jn else None
        if isinstance(info, dict):
            r = info.get("rank", "")
            try:
                ri = int(r)
                if ri == 0:
                    continue
                ranks.append(ri)
            except (TypeError, ValueError):
                continue
    if not ranks:
        return 0.0, 0
    return sum(ranks) / len(ranks), len(ranks)


def compute_composite(
    papers: List[dict],
    faculty_data: List[dict],
    y0: int,
    y1: int,
    mode: str,
    journal_info: Optional[dict] = None,
) -> Tuple[List[str], List[List], str]:
    journal_info = journal_info or {}
    names = faculty_display_list(faculty_data)
    missing: List[str] = []

    if mode == "compare_output":
        headers = ["Faculty", "Publications"]
        rows = []
        for nm in names:
            c = _pub_count_for_person(papers, nm, y0, y1)
            rows.append([nm, c])
            if c == 0:
                missing.append(nm)
        return headers, rows, ", ".join(missing) if missing else ""

    if mode == "with_rank":
        headers = ["Faculty", "Publications", "Rank"]
        scored = [(nm, _pub_count_for_person(papers, nm, y0, y1)) for nm in names]
        scored.sort(key=lambda x: (-x[1], x[0].lower()))
        rows = []
        for i, (nm, c) in enumerate(scored, start=1):
            rows.append([nm, c, i])
            if c == 0:
                missing.append(nm)
        return headers, rows, ", ".join(missing) if missing else ""

    if mode == "journal_power":
        headers = ["Faculty", "Mean AGECO rank (J only)", "J papers with rank"]
        rows = []
        for nm in names:
            mean_r, n = _mean_journal_rank(papers, nm, y0, y1, journal_info)
            rows.append([nm, f"{mean_r:.2f}" if n else "", n])
            if n == 0:
                missing.append(nm)
        rows.sort(key=lambda r: (-(float(r[1]) if r[1] else 0), str(r[0])))
        return headers, rows, ", ".join(missing) if missing else ""

    headers = ["Faculty", "Publications"]
    return headers, [], ""
