"""
Edit / fix helpers aligned with desktop pages/editandfixentries.py where noted.
"""

from __future__ import annotations

import datetime
import json
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

# Same as desktop eliminate-duplicates (and funky report strip)
DEFAULT_DUP_IGNORE = frozenset(
    {"dateentered", "number", "subject1", "subject2", "duplicateoknumber"}
)


def _safe_int(x: Any) -> float:
    try:
        return int(str(x).strip())
    except Exception:
        return float("inf")


def _build_signature(rec: dict, ignore_keys: Set[str]) -> Tuple[Tuple[str, str], ...]:
    filtered = {k: v for k, v in rec.items() if k not in ignore_keys}
    normalized = {k: ("" if v is None else str(v).strip()) for k, v in filtered.items()}
    return tuple(sorted((k, normalized.get(k, "")) for k in sorted(normalized)))


def get_exact_duplicate_groups(
    records: List[dict],
    ignore_keys: Optional[Set[str]] = None,
) -> List[Tuple[Any, List[dict]]]:
    """
    Desktop editandfixentries._get_exact_duplicate_groups — same signature rules.
    Returns list of (signature_tuple, [records...]) with len(records) >= 2.
    """
    if ignore_keys is None:
        ignore_keys = set(DEFAULT_DUP_IGNORE)
    sig_map: Dict[Tuple, List[dict]] = defaultdict(list)
    for r in records:
        sig_map[_build_signature(r, ignore_keys)].append(r)
    dup_groups = [(sig, recs) for sig, recs in sig_map.items() if len(recs) >= 2]
    dup_groups.sort(
        key=lambda t: (min(_safe_int(r.get("number")) for r in t[1]), -len(t[1]))
    )
    return dup_groups


def build_duplicate_report_text(
    dup_groups: List[Tuple[Any, List[dict]]],
    ignore_keys: Optional[Set[str]] = None,
) -> str:
    """Desktop _build_duplicate_report_text (JSON lines per record)."""
    if ignore_keys is None:
        ignore_keys = set(DEFAULT_DUP_IGNORE)
    lines: List[str] = []
    total_groups = len(dup_groups)
    total_recs = sum(len(recs) for _s, recs in dup_groups)
    total_would_remove = sum(len(recs) - 1 for _s, recs in dup_groups)
    lines.append(f"Duplicate groups: {total_groups}")
    lines.append(f"Total records inside these groups: {total_recs}")
    lines.append(
        f"Total records that would be removed (keep 1 per group): {total_would_remove}"
    )
    lines.append("")

    def strip_ignored(d: dict) -> dict:
        return {k: v for k, v in d.items() if k not in ignore_keys}

    for idx, (_sig, recs) in enumerate(dup_groups, 1):
        numbers = [r.get("number") for r in recs]
        lines.append(
            f"[Group {idx}] occurrences={len(recs)} | numbers={sorted(numbers, key=lambda n: _safe_int(n))}"
        )
        for j, r in enumerate(sorted(recs, key=lambda x: _safe_int(x.get("number"))), 1):
            try:
                rec_str = json.dumps(r, ensure_ascii=False, sort_keys=True)
            except Exception:
                rec_str = str(r)
            lines.append(f"    #{j}: {rec_str}")
        lines.append("")
    return "\n".join(lines)


def remove_duplicates_keep_smallest_number(
    data: List[dict], dup_groups: List[Tuple[Any, List[dict]]]
) -> Tuple[List[dict], int]:
    """
    Keep one record per group (smallest numeric number); same rule as desktop do_delete.
    """
    to_remove: List[dict] = []
    for _sig, recs in dup_groups:
        if not recs:
            continue
        recs_sorted = sorted(recs, key=lambda r: _safe_int(r.get("number")))
        to_remove.extend(recs_sorted[1:])
    remove_ids = {id(r) for r in to_remove}
    new_data = [r for r in data if id(r) not in remove_ids]
    return new_data, len(to_remove)


def _visualize_invalid_chars(char_list: List[str]) -> str:
    """Desktop visualize_invalid_chars."""
    visual = []
    for ch in sorted(set(char_list)):
        if ch == " ":
            visual.append("[space]")
        elif ch == "\u3000":
            visual.append("[full-width space]")
        elif ch == "\t":
            visual.append("[tab]")
        elif ch == "\n":
            visual.append("[\\n]")
        elif ch == "\r":
            visual.append("[\\r]")
        elif ch == "\u200b":
            visual.append("[zero-width space]")
        elif ch == "\xa0":
            visual.append("[non-breaking space]")
        elif ch.isprintable():
            visual.append(f"{ch}")
        else:
            visual.append(f"[U+{ord(ch):04X}]")
    return " ".join(visual)


def find_funky_issues_for_record(entry: dict, current_year: Optional[int] = None) -> List[str]:
    """
    Desktop find_funky_characters_button_click checks (per record with non-empty number).
    Returns list of issue strings (empty if none).
    """
    if current_year is None:
        current_year = datetime.datetime.now().year
    issues: List[str] = []
    authors = entry.get("authors", "")
    title = entry.get("title", "")
    bookjour = entry.get("bookjour", "")
    vitatype = entry.get("vitatyp", "")
    location = entry.get("location", "")
    volume = entry.get("volume", "")
    pages = entry.get("pages", "")
    year = entry.get("year", "")

    invalid_chars_authors = re.findall(r"[^a-zA-Z0-9.,()'\- ]", authors)
    if invalid_chars_authors:
        issues.append(
            f"Authors contain invalid characters: {_visualize_invalid_chars(invalid_chars_authors)}"
        )
    if authors.count("(") != authors.count(")"):
        issues.append("Unmatched parentheses in authors")

    invalid_chars_title = re.findall(r'[^a-zA-Z0-9.,\'"\-()/?:$%&?! ]', title)
    if invalid_chars_title:
        issues.append(
            f"Title contains invalid characters: {_visualize_invalid_chars(invalid_chars_title)}"
        )
    if title.count("(") != title.count(")"):
        issues.append("Unmatched parentheses in title")
    if title.count("'") % 2 != 0:
        issues.append("Unmatched single quotes in title")
    if title.count('"') % 2 != 0:
        issues.append("Unmatched double quotes in title")

    invalid_chars_bookjour = re.findall(r"[^a-zA-Z0-9.,()&':$?&\- ]", bookjour)
    if invalid_chars_bookjour:
        issues.append(
            f"Bookjour contains invalid characters: {_visualize_invalid_chars(invalid_chars_bookjour)}"
        )
    if vitatype == "J" and not str(bookjour).strip():
        issues.append("Missing bookjour for Journal (J) type")

    for field_name, field_value in [
        ("bookjour", bookjour),
        ("location", location),
        ("volume", volume),
        ("pages", pages),
    ]:
        field_str = str(field_value).strip()
        if not field_str:
            continue
        if "(" in field_str or ")" in field_str:
            if field_str.count("(") != field_str.count(")"):
                issues.append(f"Unmatched parentheses in {field_name}")

    year_str = str(year).strip()
    if not re.fullmatch(r"\d{4}", year_str):
        issues.append("Invalid year value")
    else:
        year_int = int(year_str)
        if not (1900 <= year_int <= current_year):
            issues.append("Invalid year value")

    for field_name, field_value in [("title", title), ("bookjour", bookjour), ("pages", pages)]:
        if re.search(r"\.\s", field_value):
            issues.append(f"{field_name} has dot followed by space")

    if "." in bookjour:
        issues.append("Bookjour contains a period (.)")

    for field_name, field_value in [
        ("title", title),
        ("bookjour", bookjour),
        ("location", location),
        ("volume", volume),
        ("pages", pages),
        ("year", year),
    ]:
        if str(field_value).strip().endswith(",") or str(field_value).strip().endswith(" "):
            issues.append(f"{field_name} ends with a comma or space")

    return issues


def scan_funky_database(records: List[dict]) -> List[Dict[str, str]]:
    """Returns rows {number, notes} for records with issues (sorted by number)."""
    out: List[Dict[str, str]] = []
    for entry in records:
        number = str(entry.get("number", "")).strip()
        if not number:
            continue
        issues = find_funky_issues_for_record(entry)
        if issues:
            out.append({"number": number, "notes": "; ".join(issues)})
    out.sort(key=lambda x: _safe_int(x["number"]))
    return out


def normalize_title_key(title: str) -> str:
    return " ".join(str(title or "").lower().split())


def get_exact_title_duplicate_groups(records: List[dict]) -> List[Tuple[str, List[dict]]]:
    """
    Web helper: same normalized title (case/space collapsed), 2+ records.
    Not the desktop duplicatetitles.py LSH/similarity workflow.
    """
    m: Dict[str, List[dict]] = defaultdict(list)
    for r in records:
        k = normalize_title_key(str(r.get("title", "")))
        if k:
            m[k].append(r)
    groups = [(k, recs) for k, recs in m.items() if len(recs) >= 2]
    groups.sort(key=lambda t: (-len(t[1]), t[0][:80]))
    return groups


def correct_elements_filter(
    records: List[dict], field: str, keyword: str
) -> List[Tuple[str, str]]:
    """
    Desktop correctelements.refresh_table filter: keyword in value.lower(), empty keyword = all.
    field: title|authors|journal|location|volume|pages|keywords
    """
    keyword = (keyword or "").strip().lower()
    matched: List[Tuple[str, str]] = []
    for record in records:
        if field == "journal":
            value = record.get("bookjour", "")
        elif field == "keywords":
            sub1 = record.get("subject1", "")
            sub2 = record.get("subject2", "")
            value = f"{sub1} {sub2}"
        else:
            value = record.get(field, "")
        if keyword == "" or keyword in str(value).lower():
            matched.append((str(record.get("number", "")), str(value)))
    matched.sort(key=lambda x: (str(x[1]).lower(), _safe_int(x[0])))
    return matched
