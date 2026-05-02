"""
Composite faculty productivity reports — parity with desktop
``pages/compositesummary.py``.

Implements the same four views the desktop UI offers:

1. ``compare_output`` — single column of total publications per faculty in
   the chosen year window.
2. ``with_rank`` — ``compare_output`` plus a 1..N ranking column.
3. ``journal_power`` — mean AGECO journal rank for J-type papers per
   faculty (lower mean rank = stronger journal portfolio).
4. ``full_breakdown`` — the desktop's most detailed view: per-faculty
   per-vita-type counts split into "Total" (year window), "Per year"
   (Total / window length), and "Recent" (last 3 years of the data).
   Ends with Average / Minimum / Maximum stat rows. The vita-type bucket
   map is identical to the desktop's ``populate_table_with_faculty_names``.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional, Tuple

from modules.extract_names import process_authors
from modules.report_year_utils import extract_year_int

ALLOWED_POSITIONS = {"Assistant Professor", "Associate Professor", "Professor"}

# Bucket map mirrors desktop compositesummary.populate_table_with_faculty_names
VITATYPE_BUCKETS: List[Tuple[str, str, List[str]]] = [
    ("journal_articles", "Journal Articles", ["J", "JR"]),
    ("total_books", "Books", ["B"]),
    ("book_chapters", "Book Chapters", ["BC"]),
    ("govt_bull", "Govt/Statn Bull", ["SB"]),
    ("invited_papers", "Invited Papers", ["IP"]),
    ("prof_meet_presn", "Prof Meet Presn", ["P", "U", "PS", "SM", "SP"]),
    ("dept_center_pap", "Dept/Center Pap", ["DP", "CP"]),
    ("extension_pap", "Extension Pap", ["EC", "OP", "PO"]),
]
ALL_KEYS_BUCKET = ("all_keys", "All Keys")


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

    if mode == "full_breakdown":
        return _compute_full_breakdown(papers, faculty_data, y0, y1, journal_info)

    headers = ["Faculty", "Publications"]
    return headers, [], ""


# ---------------------------------------------------------------------------
# Full breakdown (parity with desktop populate_table_with_faculty_names)
# ---------------------------------------------------------------------------


def _empty_bucket_dict() -> Dict[str, int]:
    return {key: 0 for key, _label, _types in VITATYPE_BUCKETS}


def _bucket_for_vita(vitatype: str) -> Optional[str]:
    v = (vitatype or "").strip().upper()
    for key, _label, types in VITATYPE_BUCKETS:
        if v in types:
            return key
    return None


def _compute_full_breakdown(
    papers: List[dict],
    faculty_data: List[dict],
    y0: int,
    y1: int,
    journal_info: Dict[str, Any],
) -> Tuple[List[str], List[List[Any]], str]:
    """Produce the desktop's full per-faculty / per-vita-type breakdown.

    Layout (matches desktop column order with a flatter HTML schema):

        Faculty | Total <bucket1> | Total <bucket2> | ... | Total All Keys |
                Per Year <bucket1> | ... | Per Year All Keys |
                Since <recent_year> <bucket1> | ... | Since <recent_year> All Keys

    Trailing rows: Average / Minimum / Maximum (as on desktop).
    The "recent" cutoff is the desktop convention ``max_year - 3`` where
    ``max_year`` is computed from records' ``year`` column (capped at 2099).
    """
    names = faculty_display_list(faculty_data)
    window = max(y1 - y0 + 1, 1)
    years = []
    for r in papers or []:
        y = extract_year_int((r or {}).get("year", ""))
        if y is not None and y < 2100:
            years.append(y)
    max_year = max(years) - 3 if years else (y1 - 3)

    # Per-faculty counts
    counts: Dict[str, Dict[str, int]] = {n: _empty_bucket_dict() for n in names}
    counts_recent: Dict[str, Dict[str, int]] = {n: _empty_bucket_dict() for n in names}
    all_keys_total: Dict[str, int] = {n: 0 for n in names}
    all_keys_recent: Dict[str, int] = {n: 0 for n in names}

    name_set = set(names)
    for record in papers or []:
        rec = record or {}
        rec_year = extract_year_int(rec.get("year", ""))
        in_window = rec_year is not None and y0 <= rec_year <= y1
        in_recent = rec_year is not None and rec_year >= max_year
        if not in_window and not in_recent:
            continue
        bucket = _bucket_for_vita(rec.get("vitatyp", ""))
        if not bucket:
            continue
        parsed, _log = process_authors(rec.get("authors") or "")
        for nm in parsed:
            if nm not in name_set:
                continue
            if in_window:
                counts[nm][bucket] += 1
                all_keys_total[nm] += 1
            if in_recent:
                counts_recent[nm][bucket] += 1
                all_keys_recent[nm] += 1

    headers: List[str] = ["Faculty"]
    for _key, label, _ in VITATYPE_BUCKETS:
        headers.append(f"Total {label}")
    headers.append(f"Total {ALL_KEYS_BUCKET[1]}")
    for _key, label, _ in VITATYPE_BUCKETS:
        headers.append(f"Per Year {label}")
    headers.append(f"Per Year {ALL_KEYS_BUCKET[1]}")
    for _key, label, _ in VITATYPE_BUCKETS:
        headers.append(f"Since {max_year} {label}")
    headers.append(f"Since {max_year} {ALL_KEYS_BUCKET[1]}")

    data_rows: List[List[Any]] = []
    missing: List[str] = []
    for nm in names:
        row: List[Any] = [nm]
        for key, _label, _ in VITATYPE_BUCKETS:
            row.append(counts[nm][key])
        row.append(all_keys_total[nm])
        for key, _label, _ in VITATYPE_BUCKETS:
            row.append(round(counts[nm][key] / window, 2))
        row.append(round(all_keys_total[nm] / window, 2))
        for key, _label, _ in VITATYPE_BUCKETS:
            row.append(counts_recent[nm][key])
        row.append(all_keys_recent[nm])
        data_rows.append(row)
        if all_keys_total[nm] == 0 and all_keys_recent[nm] == 0:
            missing.append(nm)

    if data_rows:
        n_cols = len(headers)
        numeric_cols = list(range(1, n_cols))

        def _avg(idx: int) -> float:
            vals = [float(r[idx]) for r in data_rows if isinstance(r[idx], (int, float))]
            return round(sum(vals) / len(vals), 2) if vals else 0.0

        def _min(idx: int) -> float:
            vals = [float(r[idx]) for r in data_rows if isinstance(r[idx], (int, float))]
            return min(vals) if vals else 0.0

        def _max(idx: int) -> float:
            vals = [float(r[idx]) for r in data_rows if isinstance(r[idx], (int, float))]
            return max(vals) if vals else 0.0

        data_rows.append(["Average"] + [_avg(i) for i in numeric_cols])
        data_rows.append(["Minimum"] + [_min(i) for i in numeric_cols])
        data_rows.append(["Maximum"] + [_max(i) for i in numeric_cols])

    return headers, data_rows, ", ".join(missing) if missing else ""
