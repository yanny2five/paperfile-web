"""
Filter .cnt records by vita type code (for a smaller "public" database file).

Dr. McCarl requested dropping: journal drafts (JD), inactive drafts (OI),
funding proposals (PR), contract reports (F). Codes match report_group_output.VITA_TYPE_NAMES.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from modules.report_group_output import VITA_TYPE_NAMES, VITATYPE_ORDER

# Default vita types excluded from the public / web-hosted export
DEFAULT_PUBLIC_DROP_VITATYPES: frozenset[str] = frozenset({"JD", "OI", "PR", "F"})


def vitatyp_code(record: dict) -> str:
    raw = (
        record.get("vitatyp")
        or record.get("vita_type")
        or record.get("Vitatyp")
        or ""
    )
    return str(raw).strip().upper()


def filter_out_vita_types(
    records: Sequence[dict],
    drop_codes: Iterable[str],
) -> tuple[list[dict], dict[str, int]]:
    """
    Return (kept_records, stats) where stats maps dropped code -> count removed.
    Records with unknown/empty vitatyp are kept unless their normalized code is in drop_codes.
    """
    drop = {str(c).strip().upper() for c in drop_codes if str(c).strip()}
    kept: list[dict] = []
    dropped_by: dict[str, int] = {c: 0 for c in drop}

    for rec in records:
        code = vitatyp_code(rec)
        if code in drop:
            dropped_by[code] = dropped_by.get(code, 0) + 1
            continue
        kept.append(rec)

    return kept, dropped_by


def vita_types_reference_lines() -> list[str]:
    """Code + name lines in stable order for email / /vita-types page."""
    lines: list[str] = []
    seen: set[str] = set()
    for code in VITATYPE_ORDER:
        name = VITA_TYPE_NAMES.get(code, code)
        lines.append(f"{code}\t{name}")
        seen.add(code)
    for code in sorted(VITA_TYPE_NAMES.keys()):
        if code not in seen:
            lines.append(f"{code}\t{VITA_TYPE_NAMES[code]}")
    return lines


def default_drop_summary() -> str:
    parts = []
    for c in sorted(DEFAULT_PUBLIC_DROP_VITATYPES):
        parts.append(f"{c} ({VITA_TYPE_NAMES.get(c, c)})")
    return ", ".join(parts)
