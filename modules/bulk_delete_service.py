"""
Bulk-delete-papers service for paperfile-web.

Mirrors the desktop's ``pages/delete_selected_papers.py`` semantics. The
desktop page lets a user delete papers matching any UNION of three rules:

1. By ``number`` range (open-ended on either side).
2. WITH a given author (delete records whose ``authors`` field contains the
   given name, in either ``"Last, First"`` or ``"First Last"`` form, with
   token boundaries so a query for ``"Doe, J."`` does NOT match
   ``"Doerr, J."``).
3. WITHOUT a given author (delete records whose ``authors`` field does NOT
   contain that name — i.e. keep only those that do).

After computing the target set, the desktop offers an optional backup
before overwriting the .cnt with ``overwrite_all_records_in_cnt`` (which
preserves the file header). This module exposes the same logic as plain
functions so the Flask layer can preview the planned deletion and then
commit it on a separate POST.

The math here is intentionally identical to the desktop so a parity test
can drive both implementations against the same fixture and assert the
same record indices come out.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple


_INT_RE = re.compile(r"-?\d+")


def parse_int_loose(value: Any) -> Optional[int]:
    """Return an int from messy text, or None if it can't be coerced.

    Mirrors the desktop's ``DeleteSelectedPapersPage._parse_int`` (which
    strips commas before ``int()``). Empty/whitespace-only inputs and
    inputs with no digits return ``None``.
    """
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if not s:
        return None
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


def name_variants(name_input: str) -> List[str]:
    """Return canonical "Last, First" + "First Last" variants for a name.

    Same algorithm as desktop ``_name_variants``: normalize whitespace,
    normalize comma spacing, then add the swapped variant. Returns an
    ordered, de-duplicated list. Empty input yields ``[]``.
    """
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


def author_field_contains_name(authors_field: str, name_input: str) -> bool:
    """Token-bounded match for ``name_input`` inside an authors string.

    Uses the desktop's regex pattern ``(?<![A-Za-z])<variant>(?![A-Za-z])``
    so that ``"McCarl"`` does NOT match ``"McCarlton"`` and
    ``"Doe, J."`` does NOT match ``"Doerr, J."``. Returns True if any
    variant of the input matches.
    """
    authors = (authors_field or "").strip()
    if not authors:
        return False
    variants = name_variants(name_input)
    if not variants:
        return False
    for v in variants:
        pat = r"(?<![A-Za-z])" + re.escape(v) + r"(?![A-Za-z])"
        if re.search(pat, authors):
            return True
    return False


def database_number_range(records: Iterable[Dict[str, Any]]) -> Tuple[Optional[int], Optional[int]]:
    """Return ``(min_number, max_number)`` from records' ``number`` fields.

    Skips non-numeric entries. Returns ``(None, None)`` if no numeric
    record numbers are present (matches desktop's empty-DB display).
    """
    nums: List[int] = []
    for r in records or []:
        n = str((r or {}).get("number", "")).strip()
        if n.isdigit():
            nums.append(int(n))
    if not nums:
        return None, None
    return min(nums), max(nums)


def compute_delete_indices(
    records: List[Dict[str, Any]],
    *,
    from_n: Optional[int] = None,
    to_n: Optional[int] = None,
    with_author: str = "",
    without_author: str = "",
) -> List[int]:
    """Return the sorted list of record indices that match the rules.

    The rules are UNION-ed (matches the desktop). At least one of the four
    inputs must be set/non-empty, otherwise ``ValueError`` is raised
    (matches desktop's "No rule" warning). Range-rule semantics:

    - both ``from_n`` and ``to_n``: ``from_n <= number <= to_n``
    - only ``from_n``: ``number >= from_n``
    - only ``to_n``: ``number <= to_n``
    """
    with_author = (with_author or "").strip()
    without_author = (without_author or "").strip()
    if from_n is None and to_n is None and not with_author and not without_author:
        raise ValueError(
            "Provide at least one delete rule (range, with-author, or without-author)."
        )

    to_delete: set[int] = set()

    if from_n is not None or to_n is not None:
        for idx, rec in enumerate(records):
            n = parse_int_loose(rec.get("number", ""))
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

    if with_author:
        for idx, rec in enumerate(records):
            if author_field_contains_name(rec.get("authors", ""), with_author):
                to_delete.add(idx)

    if without_author:
        for idx, rec in enumerate(records):
            if not author_field_contains_name(rec.get("authors", ""), without_author):
                to_delete.add(idx)

    return sorted(to_delete)


def build_delete_plan_summary(
    from_n: Optional[int],
    to_n: Optional[int],
    with_name: str,
    without_name: str,
) -> str:
    """Human-readable summary, matches desktop's confirmation dialog text.

    The desktop dialog leaves a literal blank line between the header and
    the first rule (its header string ends with ``\\n``); we preserve that
    here so the two summaries are byte-identical.
    """
    lines: List[str] = ["You are about to delete records with the following rules:\n"]
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
            f"- Without author: delete ALL records EXCEPT those whose authors contain "
            f"'{without_name}' (exact name variants)"
        )
    if len(lines) == 1:
        lines.append("- (No rule provided)")
    return "\n".join(lines)


def renumber_in_place(records: List[Dict[str, Any]], start_at: int = 1) -> None:
    """Renumber ``records`` sequentially in-place. Matches desktop.

    Used after a bulk delete when the user opts in.
    """
    n = int(start_at)
    for rec in records:
        rec["number"] = str(n)
        n += 1


def apply_deletion(
    records: List[Dict[str, Any]], to_delete_idx: Iterable[int]
) -> List[Dict[str, Any]]:
    """Return a new list with the given indices removed (preserves order)."""
    skip = set(to_delete_idx)
    return [rec for i, rec in enumerate(records) if i not in skip]
