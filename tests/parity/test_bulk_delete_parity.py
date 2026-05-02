"""
Parity test: bulk-delete-papers algorithm (web ``bulk_delete_service``
vs desktop ``pages/delete_selected_papers.py``).

The desktop implementation is bound to a Tk class and can't be invoked
headlessly. We re-transcribe its rule-evaluation algorithm verbatim as a
pure reference implementation in this file, then assert that for the same
inputs the web's ``bulk_delete_service`` produces the same deletion
indices, the same name variants, the same author-membership decisions,
and the same plan summary text.

If the desktop algorithm changes, the reference functions below must be
updated to match and the web service should be re-checked against them.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = REPO_ROOT / "paperfile-web"


@pytest.fixture(autouse=True)
def _sys_path():
    if str(WEB_ROOT) not in sys.path:
        sys.path.insert(0, str(WEB_ROOT))
    yield


# --- Reference algorithm ---------------------------------------------------
# Transcribed VERBATIM from paperfile/pages/delete_selected_papers.py:
#   - _parse_int            -> _ref_parse_int
#   - _name_variants        -> _ref_name_variants
#   - _author_field_contains_name -> _ref_author_contains
#   - on_delete_click rule logic  -> _ref_compute_indices
#   - _build_delete_plan_summary  -> _ref_summary

def _ref_parse_int(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", "")
    if s == "":
        return None
    try:
        return int(s)
    except Exception:
        return None


def _ref_name_variants(name_input: str) -> List[str]:
    raw = (name_input or "").strip()
    if not raw:
        return []
    raw = re.sub(r"\s+", " ", raw).strip()
    raw = re.sub(r"\s*,\s*", ", ", raw)

    variants: List[str] = []

    def _add(x: str) -> None:
        x = (x or "").strip()
        x = re.sub(r"\s+", " ", x).strip()
        x = re.sub(r"\s*,\s*", ", ", x)
        if x and x not in variants:
            variants.append(x)

    _add(raw)
    if "," in raw:
        last, first = (p.strip() for p in raw.split(",", 1))
        _add(f"{first} {last}".strip())
    elif " " in raw:
        first, last = raw.rsplit(" ", 1)
        _add(f"{last}, {first}".strip())
    return variants


def _ref_author_contains(authors_field: str, name_input: str) -> bool:
    authors = (authors_field or "").strip()
    if not authors:
        return False
    variants = _ref_name_variants(name_input)
    if not variants:
        return False
    for v in variants:
        pat = r"(?<![A-Za-z])" + re.escape(v) + r"(?![A-Za-z])"
        if re.search(pat, authors):
            return True
    return False


def _ref_compute_indices(
    records: List[Dict[str, Any]],
    *,
    from_n: Optional[int],
    to_n: Optional[int],
    with_name: str,
    without_name: str,
) -> List[int]:
    to_delete: set = set()
    if from_n is not None or to_n is not None:
        for idx, rec in enumerate(records):
            n = _ref_parse_int(rec.get("number", ""))
            if n is None:
                continue
            if from_n is not None and to_n is not None:
                if from_n <= n <= to_n:
                    to_delete.add(idx)
            elif from_n is not None:
                if n >= from_n:
                    to_delete.add(idx)
            else:
                if n <= to_n:  # type: ignore[operator]
                    to_delete.add(idx)
    if with_name:
        for idx, rec in enumerate(records):
            if _ref_author_contains(rec.get("authors", ""), with_name):
                to_delete.add(idx)
    if without_name:
        for idx, rec in enumerate(records):
            if not _ref_author_contains(rec.get("authors", ""), without_name):
                to_delete.add(idx)
    return sorted(to_delete)


def _ref_summary(from_n, to_n, with_name, without_name) -> str:
    lines = ["You are about to delete records with the following rules:\n"]
    if from_n is not None or to_n is not None:
        if from_n is not None and to_n is not None:
            lines.append(f"- Number range: delete {from_n} to {to_n} (inclusive)")
        elif from_n is not None:
            lines.append(f"- Number range: delete >= {from_n}")
        else:
            lines.append(f"- Number range: delete <= {to_n}")
    if with_name:
        lines.append(
            f"- With author: delete records whose authors contain '{with_name}' (exact name variants)"
        )
    if without_name:
        lines.append(
            f"- Without author: delete ALL records EXCEPT those whose authors contain '{without_name}' (exact name variants)"
        )
    if len(lines) == 1:
        lines.append("- (No rule provided)")
    return "\n".join(lines)


# --- Fixtures --------------------------------------------------------------


@pytest.fixture()
def records():
    """Diverse fixture covering the rule-evaluation edge cases."""
    return [
        {"number": "1", "authors": "McCarl, B.A. and Smith, J."},
        {"number": "2", "authors": "Smith, J. and Doe, A.B."},
        {"number": "3", "authors": "Doerr, J."},
        {"number": "4", "authors": ""},
        {"number": "5", "authors": "B.A. McCarl, J. Smith"},
        {"number": "10", "authors": "Patel, R., McCarl, B.A."},
        {"number": "11", "authors": "Lee, K.; Patel, R."},
        {"number": "abc", "authors": "McCarl, B.A."},
        {"number": "20", "authors": "Smith, John and McCarl, B.A."},
        {"number": "  ", "authors": "McCarl, B.A."},
    ]


# --- Tests -----------------------------------------------------------------


@pytest.mark.parametrize(
    "from_n,to_n,with_name,without_name",
    [
        (1, 3, "", ""),
        (None, 5, "", ""),
        (10, None, "", ""),
        (None, None, "McCarl, B.A.", ""),
        (None, None, "McCarl, B.A.", "Smith, J."),
        (None, None, "", "McCarl, B.A."),
        (1, 20, "", "McCarl, B.A."),
        (None, None, "Doe, A.B.", ""),
        (None, None, "Patel, R.", ""),
        (5, 11, "Patel, R.", ""),
    ],
)
def test_compute_delete_indices_matches_desktop(records, from_n, to_n, with_name, without_name):
    from modules.bulk_delete_service import compute_delete_indices

    web = compute_delete_indices(
        records,
        from_n=from_n,
        to_n=to_n,
        with_author=with_name,
        without_author=without_name,
    )
    desk = _ref_compute_indices(
        records,
        from_n=from_n,
        to_n=to_n,
        with_name=with_name,
        without_name=without_name,
    )
    assert web == desk, f"Indices differ: web={web} desktop={desk}"


def test_compute_indices_no_rule_raises(records):
    """Both implementations refuse an empty rule set (matches desktop dialog)."""
    from modules.bulk_delete_service import compute_delete_indices

    with pytest.raises(ValueError):
        compute_delete_indices(records)


@pytest.mark.parametrize(
    "name",
    [
        "McCarl, B.A.",
        "B.A. McCarl",
        "Patel, R.",
        "Smith, J.",
        "Doerr, J.",  # must NOT cross-match Doe, J.
        "  Lee ,K. ",  # whitespace + comma normalization
        "",
    ],
)
def test_name_variants_match_desktop(name):
    from modules.bulk_delete_service import name_variants

    assert name_variants(name) == _ref_name_variants(name)


@pytest.mark.parametrize(
    "authors,query,expected",
    [
        ("McCarl, B.A. and Smith, J.", "McCarl, B.A.", True),
        ("McCarlton, B.A.", "McCarl, B.A.", False),  # token-bounded
        ("Doerr, J.", "Doe, J.", False),  # no false positive
        ("Smith, J. and Doe, A.B.", "Doe, A.B.", True),
        ("B.A. McCarl, J. Smith", "McCarl, B.A.", True),  # swapped form matches
        ("", "McCarl, B.A.", False),
        ("McCarl, B.A.", "", False),  # empty query never matches
    ],
)
def test_author_field_contains_name_matches_desktop(authors, query, expected):
    from modules.bulk_delete_service import author_field_contains_name

    web = author_field_contains_name(authors, query)
    desk = _ref_author_contains(authors, query)
    assert web == desk == expected, (
        f"contains() disagrees on ({authors!r}, {query!r}): "
        f"web={web} desktop={desk} expected={expected}"
    )


@pytest.mark.parametrize(
    "from_n,to_n,with_name,without_name",
    [
        (None, None, "Smith, J.", ""),
        (1, 5, "", ""),
        (None, 10, "", ""),
        (5, None, "", ""),
        (1, 5, "Doe, A.", "McCarl, B.A."),
        (None, None, "", "McCarl, B.A."),
    ],
)
def test_summary_matches_desktop(from_n, to_n, with_name, without_name):
    from modules.bulk_delete_service import build_delete_plan_summary

    web = build_delete_plan_summary(from_n, to_n, with_name, without_name)
    desk = _ref_summary(from_n, to_n, with_name, without_name)
    assert web == desk


def test_apply_deletion_preserves_order_and_renumber():
    from modules.bulk_delete_service import apply_deletion, renumber_in_place

    data = [
        {"number": "1", "authors": "A"},
        {"number": "2", "authors": "B"},
        {"number": "3", "authors": "C"},
        {"number": "4", "authors": "D"},
    ]
    survivors = apply_deletion(data, [1, 3])
    assert [r["authors"] for r in survivors] == ["A", "C"]
    renumber_in_place(survivors, start_at=1)
    assert [r["number"] for r in survivors] == ["1", "2"]


def test_database_number_range_skips_non_numeric():
    from modules.bulk_delete_service import database_number_range

    rs = [
        {"number": "1"},
        {"number": "abc"},
        {"number": "5"},
        {"number": ""},
        {"number": "10"},
    ]
    assert database_number_range(rs) == (1, 10)
    assert database_number_range([]) == (None, None)
    assert database_number_range([{"number": "x"}]) == (None, None)
