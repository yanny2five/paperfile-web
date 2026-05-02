"""
Parity test: check-numbers algorithm (web ``check_numbers_service``
vs desktop ``pages/checknumbers.py``).

The web service is a non-UI port of ``CheckNumbersPage._populate_stats_from_reader``
plus ``on_renumber_click``. We re-implement the desktop logic here as a pure
reference function and assert that for the same input both implementations
agree on the produced statistics and on the renumber output.

If the desktop algorithm is ever changed, the reference implementation must
be updated and the web service should be checked against it again.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import List, Tuple

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = REPO_ROOT / "paperfile-web"


@pytest.fixture(autouse=True)
def _sys_path():
    """Make web modules importable for in-process service tests."""
    if str(WEB_ROOT) not in sys.path:
        sys.path.insert(0, str(WEB_ROOT))
    yield


# --- Reference algorithm — mirrors desktop pages/checknumbers.py exactly ---

def desktop_parse_int(v):
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
    except Exception:
        return None


def desktop_compute_stats(records):
    nums = []
    for rec in records or []:
        n = desktop_parse_int(rec.get("number", ""))
        if n is not None:
            nums.append(n)
    if not nums:
        return {
            "lowest": None,
            "highest": None,
            "missing_25": [],
            "duplicates_25": [],
        }
    lo, hi = min(nums), max(nums)
    cnt = Counter(nums)
    duplicates = sorted([n for n, c in cnt.items() if c > 1])
    missing = [n for n in range(lo, hi + 1) if cnt.get(n, 0) == 0]
    return {
        "lowest": lo,
        "highest": hi,
        "missing_25": missing[:25],
        "duplicates_25": duplicates[:25],
    }


def desktop_renumber(data, start_at, renum_highest_limit) -> Tuple[List[dict], int]:
    """Re-implementation of ``CheckNumbersPage.on_renumber_click`` core."""
    out = [dict(r) for r in data]
    in_range = []
    for idx, rec in enumerate(out):
        n = desktop_parse_int(rec.get("number", ""))
        if n is None:
            continue
        if start_at <= n <= renum_highest_limit:
            in_range.append(idx)

    if any(desktop_parse_int(out[i].get("number", "")) == 0 for i in in_range):
        start_at = 1

    if not in_range:
        return out, 0

    next_no = start_at
    for idx in in_range:
        out[idx]["number"] = str(next_no)
        next_no += 1
    return out, len(in_range)


# --- Tests ----------------------------------------------------------------

@pytest.mark.parametrize(
    "records",
    [
        # Empty
        [],
        # One number
        [{"number": "10"}],
        # Sequential, no gaps
        [{"number": str(n)} for n in range(1, 11)],
        # With gaps and duplicates
        [{"number": "1"}, {"number": "2"}, {"number": "5"}, {"number": "5"}, {"number": "8"}],
        # Mix of valid and unparseable numbers
        [
            {"number": "100"}, {"number": "  200  "}, {"number": "1,300"},
            {"number": "abc"}, {"number": ""}, {"number": None},
        ],
    ],
)
def test_compute_number_stats_matches_desktop(records):
    from modules.check_numbers_service import compute_number_stats

    web = compute_number_stats(records)
    desktop = desktop_compute_stats(records)

    assert web["lowest"] == desktop["lowest"]
    assert web["highest"] == desktop["highest"]
    assert web["missing_25"] == desktop["missing_25"]
    assert web["duplicates_25"] == desktop["duplicates_25"]


@pytest.mark.parametrize(
    "records,start_at,highest",
    [
        ([{"number": str(n)} for n in [1, 2, 3, 4, 5]], 3, 5),
        ([{"number": str(n)} for n in [10, 20, 30]], 5, 25),
        ([{"number": "0"}, {"number": "1"}, {"number": "2"}], 0, 5),  # zero handling
        ([{"number": str(n)} for n in [100, 200, 300]], 99, 99),  # nothing in range
        ([{"number": "1"}, {"number": "1"}, {"number": "2"}], 1, 5),  # duplicates
    ],
)
def test_renumber_matches_desktop(records, start_at, highest):
    from modules.check_numbers_service import renumber_in_range

    web_out, web_count = renumber_in_range(records, start_at, highest)
    desktop_out, desktop_count = desktop_renumber(records, start_at, highest)

    assert web_count == desktop_count
    assert [r["number"] for r in web_out] == [r["number"] for r in desktop_out]
