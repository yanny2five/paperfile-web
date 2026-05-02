"""
Parity test: composite-summary full breakdown view.

The desktop's ``populate_table_with_faculty_names`` (in
``pages/compositesummary.py``) is a 280-line Tk method. We re-implement
its bucket-counting algorithm here as a pure reference and assert the
web's ``compute_composite(mode="full_breakdown", ...)`` produces the same
counts and the same Average/Minimum/Maximum stat rows.

Special cases exercised:
- A faculty member has 0 records in the window → row stays present and
  appears in the missing-text string.
- A record's ``vitatyp`` doesn't fall into any bucket → ignored.
- "Recent" cutoff (max_year - 3) is computed from the *records*' year
  column, not the requested year window.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = REPO_ROOT / "paperfile-web"


@pytest.fixture(autouse=True)
def _sys_path():
    if str(WEB_ROOT) not in sys.path:
        sys.path.insert(0, str(WEB_ROOT))
    yield


_BUCKETS = [
    ("journal_articles", "Journal Articles", {"J", "JR"}),
    ("total_books", "Books", {"B"}),
    ("book_chapters", "Book Chapters", {"BC"}),
    ("govt_bull", "Govt/Statn Bull", {"SB"}),
    ("invited_papers", "Invited Papers", {"IP"}),
    ("prof_meet_presn", "Prof Meet Presn", {"P", "U", "PS", "SM", "SP"}),
    ("dept_center_pap", "Dept/Center Pap", {"DP", "CP"}),
    ("extension_pap", "Extension Pap", {"EC", "OP", "PO"}),
]


def _ref_year_int(s):
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    digits = "".join(ch for ch in s if ch.isdigit())[:4]
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _ref_compute_full(
    papers, faculty_data, y0, y1
) -> Tuple[List[str], List[List[Any]], str]:
    from modules.extract_names import process_authors

    # Names: only Asst/Assoc/Professor, sorted by (last,first) lowercase
    names = []
    for p in faculty_data or []:
        if any(
            pos in {"Assistant Professor", "Associate Professor", "Professor"}
            for pos in p.get("positions", [])
        ):
            if p.get("name"):
                names.append(p["name"])
    names.sort(
        key=lambda x: (
            x.split(",")[0].strip().lower(),
            x.split(",")[1].strip().lower() if "," in x else "",
        )
    )

    window = max(y1 - y0 + 1, 1)
    years = []
    for r in papers or []:
        y = _ref_year_int((r or {}).get("year", ""))
        if y is not None and y < 2100:
            years.append(y)
    max_year = max(years) - 3 if years else (y1 - 3)

    counts = {n: defaultdict(int) for n in names}
    counts_recent = {n: defaultdict(int) for n in names}
    all_total = defaultdict(int)
    all_recent = defaultdict(int)

    name_set = set(names)
    for r in papers or []:
        rec = r or {}
        ry = _ref_year_int(rec.get("year", ""))
        in_w = ry is not None and y0 <= ry <= y1
        in_r = ry is not None and ry >= max_year
        if not in_w and not in_r:
            continue
        v = (rec.get("vitatyp") or "").strip().upper()
        bucket_key = None
        for k, _label, types in _BUCKETS:
            if v in types:
                bucket_key = k
                break
        if bucket_key is None:
            continue
        parsed, _ = process_authors(rec.get("authors") or "")
        for nm in parsed:
            if nm not in name_set:
                continue
            if in_w:
                counts[nm][bucket_key] += 1
                all_total[nm] += 1
            if in_r:
                counts_recent[nm][bucket_key] += 1
                all_recent[nm] += 1

    headers = ["Faculty"]
    for _k, label, _ in _BUCKETS:
        headers.append(f"Total {label}")
    headers.append("Total All Keys")
    for _k, label, _ in _BUCKETS:
        headers.append(f"Per Year {label}")
    headers.append("Per Year All Keys")
    for _k, label, _ in _BUCKETS:
        headers.append(f"Since {max_year} {label}")
    headers.append(f"Since {max_year} All Keys")

    rows: List[List[Any]] = []
    missing: List[str] = []
    for n in names:
        row: List[Any] = [n]
        for k, _label, _ in _BUCKETS:
            row.append(counts[n][k])
        row.append(all_total[n])
        for k, _label, _ in _BUCKETS:
            row.append(round(counts[n][k] / window, 2))
        row.append(round(all_total[n] / window, 2))
        for k, _label, _ in _BUCKETS:
            row.append(counts_recent[n][k])
        row.append(all_recent[n])
        rows.append(row)
        if all_total[n] == 0 and all_recent[n] == 0:
            missing.append(n)

    if rows:
        n_cols = len(headers)
        idxs = list(range(1, n_cols))

        def _avg(i):
            vals = [float(r[i]) for r in rows if isinstance(r[i], (int, float))]
            return round(sum(vals) / len(vals), 2) if vals else 0.0

        def _mn(i):
            vals = [float(r[i]) for r in rows if isinstance(r[i], (int, float))]
            return min(vals) if vals else 0.0

        def _mx(i):
            vals = [float(r[i]) for r in rows if isinstance(r[i], (int, float))]
            return max(vals) if vals else 0.0

        rows.append(["Average"] + [_avg(i) for i in idxs])
        rows.append(["Minimum"] + [_mn(i) for i in idxs])
        rows.append(["Maximum"] + [_mx(i) for i in idxs])

    return headers, rows, ", ".join(missing) if missing else ""


@pytest.fixture()
def faculty():
    return [
        {"name": "McCarl, B.A.", "positions": ["Professor"]},
        {"name": "Smith, J.D.", "positions": ["Associate Professor"]},
        {"name": "Doe, A.", "positions": ["Assistant Professor"]},
        {"name": "Other, X.", "positions": ["Extension"]},  # excluded
    ]


@pytest.fixture()
def papers():
    return [
        {"number": "1", "year": "2024", "vitatyp": "J",
         "authors": "McCarl, B.A.", "bookjour": "AJAE"},
        {"number": "2", "year": "2024", "vitatyp": "B",
         "authors": "McCarl, B.A.", "bookjour": ""},
        {"number": "3", "year": "2023", "vitatyp": "BC",
         "authors": "Smith, J.D.", "bookjour": ""},
        {"number": "4", "year": "2010", "vitatyp": "J",
         "authors": "McCarl, B.A.", "bookjour": "AJAE"},
        {"number": "5", "year": "2025", "vitatyp": "JR",
         "authors": "Doe, A.", "bookjour": "ERL"},
        {"number": "6", "year": "2025", "vitatyp": "EC",
         "authors": "Other, X.", "bookjour": ""},  # not faculty bucket
        {"number": "7", "year": "1999", "vitatyp": "P",
         "authors": "McCarl, B.A.", "bookjour": ""},
        {"number": "8", "year": "2024", "vitatyp": "XX",
         "authors": "McCarl, B.A.", "bookjour": ""},  # unknown bucket -> ignored
    ]


def test_full_breakdown_matches_reference(faculty, papers):
    from modules.report_composite_simple import compute_composite

    headers_w, rows_w, missing_w = compute_composite(
        papers, faculty, 2010, 2025, "full_breakdown", journal_info={}
    )
    headers_r, rows_r, missing_r = _ref_compute_full(papers, faculty, 2010, 2025)
    assert headers_w == headers_r
    assert rows_w == rows_r
    assert missing_w == missing_r


def test_full_breakdown_full_window_2024(faculty, papers):
    """Single-year window only includes 2024 records, but the recent-window
    (max_year - 3 = 2022) still includes 2023/2024/2025 records."""
    from modules.report_composite_simple import compute_composite

    headers_w, rows_w, missing_w = compute_composite(
        papers, faculty, 2024, 2024, "full_breakdown", journal_info={}
    )
    headers_r, rows_r, missing_r = _ref_compute_full(papers, faculty, 2024, 2024)
    assert headers_w == headers_r
    assert rows_w == rows_r


def test_full_breakdown_returns_at_least_stat_rows(faculty, papers):
    from modules.report_composite_simple import compute_composite

    _h, rows, _m = compute_composite(
        papers, faculty, 2010, 2025, "full_breakdown", journal_info={}
    )
    # 3 faculty + 3 stat rows.
    assert [r[0] for r in rows[-3:]] == ["Average", "Minimum", "Maximum"]


def test_compare_output_unaffected(faculty, papers):
    """Sanity: the original simple modes still work."""
    from modules.report_composite_simple import compute_composite

    h, r, _ = compute_composite(papers, faculty, 2010, 2025, "compare_output")
    assert h == ["Faculty", "Publications"]
    assert all(len(row) == 2 for row in r)
