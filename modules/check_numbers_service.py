"""
Paper number statistics and re-numbering (desktop pages/checknumbers.py logic, non-UI).
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


def parse_paper_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    if not isinstance(v, str):
        try:
            return int(v)
        except Exception:
            return None
    s = v.strip().replace(",", "")
    if s == "":
        return None
    try:
        return int(s)
    except ValueError:
        return None


def compute_number_stats(papers: List[dict]) -> Dict[str, Any]:
    """
    Returns lowest, highest, first 25 missing in [lo, hi], duplicate numbers (first 25),
    and total duplicate distinct count for messaging.
    """
    nums: List[int] = []
    for rec in papers or []:
        n = parse_paper_int(rec.get("number", ""))
        if n is not None:
            nums.append(n)

    if not nums:
        return {
            "lowest": None,
            "highest": None,
            "missing_25": [],
            "missing_total": 0,
            "duplicates_25": [],
            "duplicates_total_distinct": 0,
            "suggested_start": None,
        }

    lo, hi = min(nums), max(nums)
    cnt = Counter(nums)
    dup_list = sorted([n for n, c in cnt.items() if c > 1])
    missing_list = [n for n in range(lo, hi + 1) if cnt.get(n, 0) == 0]

    return {
        "lowest": lo,
        "highest": hi,
        "missing_25": missing_list[:25],
        "missing_total": len(missing_list),
        "duplicates_25": dup_list[:25],
        "duplicates_total_distinct": len(dup_list),
        "suggested_start": hi + 1,
    }


def renumber_in_range(
    data: List[dict],
    start_at: int,
    renum_highest_limit: int,
) -> Tuple[List[dict], int]:
    """
    Return a new list (copied records) with numbers reassigned for records whose
    current number is in [start_at, renum_highest_limit], preserving list order.
    Matches desktop CheckNumbersPage.on_renumber_click.
    """
    out = [dict(r) for r in data]
    in_range_indices: List[int] = []
    for idx, rec in enumerate(out):
        n = parse_paper_int(rec.get("number", ""))
        if n is None:
            continue
        if start_at <= n <= renum_highest_limit:
            in_range_indices.append(idx)

    start = start_at
    if any(parse_paper_int(out[i].get("number", "")) == 0 for i in in_range_indices):
        start = 1

    if not in_range_indices:
        return out, 0

    next_no = start
    for idx in in_range_indices:
        out[idx]["number"] = str(next_no)
        next_no += 1
    return out, len(in_range_indices)
