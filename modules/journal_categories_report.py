"""Journal major-class counts by year bins (simplified specialreportform_3 journal categories)."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from modules.extract_names import process_authors
from modules.publication_type_report import (
    _display_name_to_pair,
    trimmed_bin_indexes,
    year_bins_from_range,
)
from modules.report_journals import _lookup_journal_tuple
from modules.report_year_utils import extract_year_int


def compute_journal_categories_report(
    papers: List[dict],
    reader,
    first_year: int,
    last_year: int,
    increment: int,
    target_pairs: Optional[Set[Tuple[str, str]]],
) -> Tuple[List[str], List[List]]:
    try:
        _jr, journal_dict, _sjr = reader.read_journal_definition()
    except Exception:
        journal_dict = {}

    year_bins = year_bins_from_range(first_year, last_year, increment)
    num_bins = len(year_bins)
    if num_bins == 0:
        return ["Major class", "Total"], []

    base_headers = ["Major class", "Total"] + [f"{a}-{b}" for a, b in year_bins]
    counts: Dict[str, List[int]] = defaultdict(lambda: [0] * num_bins)

    def matches(rec: dict) -> bool:
        if target_pairs is None:
            return True
        parsed, _ = process_authors(rec.get("authors") or "")
        for name in parsed:
            p = _display_name_to_pair(name)
            if p and p in target_pairs:
                return True
        return False

    for record in papers:
        if str(record.get("vitatyp", "")).strip() not in ("J", "JR"):
            continue
        if not matches(record):
            continue
        y = extract_year_int(record.get("year", ""))
        if y is None or not (first_year <= y <= last_year):
            continue
        jname = (record.get("bookjour") or "").strip()
        if not jname:
            major = "(no journal)"
        else:
            tup = _lookup_journal_tuple(journal_dict or {}, jname)
            if not tup:
                major = "Unknown / not in definition"
            else:
                major = str(tup[0] or "").split("::")[0].strip() or "Unknown"

        for i, (start, end) in enumerate(year_bins):
            if start <= y <= end:
                counts[major][i] += 1
                break

    bin_ix = trimmed_bin_indexes(counts, num_bins)
    headers = ["Major class", "Total"] + [base_headers[2 + i] for i in bin_ix]
    rows: List[List] = []
    for major in sorted(counts.keys(), key=lambda x: x.lower()):
        yt = [counts[major][i] for i in range(num_bins)]
        yt_trim = [yt[i] for i in bin_ix]
        total_sum = sum(yt_trim)
        rows.append([major, total_sum] + yt_trim)
    rows.sort(key=lambda r: (-int(r[1] or 0), str(r[0]).lower()))
    return headers, rows
