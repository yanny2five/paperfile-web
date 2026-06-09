"""Journal use / rank / class aggregates."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from modules.extract_names import process_authors
from modules.publication_type_report import _display_name_to_pair
from modules.report_year_utils import extract_year_int

JournalRow = Tuple[str, int, str, str, str, str, str]


def _paper_matches_pairs(
    record: dict, target_pairs: Optional[Set[Tuple[str, str]]]
) -> bool:
    if target_pairs is None:
        return True
    processed, _ = process_authors(record.get("authors") or "")
    for name in processed:
        p = _display_name_to_pair(name)
        if p and p in target_pairs:
            return True
    return False


def journal_frequency_rows(
    papers: List[dict],
    y0: int,
    y1: int,
    target_pairs: Optional[Set[Tuple[str, str]]],
    vitatypes: Tuple[str, ...] = ("J", "JR"),
) -> List[Tuple[str, int]]:
    counts: Dict[str, int] = defaultdict(int)
    for rec in papers:
        vt = str(rec.get("vitatyp", "")).strip()
        if vt not in vitatypes:
            continue
        y = extract_year_int(rec.get("year", ""))
        if y is None or not (y0 <= y <= y1):
            continue
        if not _paper_matches_pairs(rec, target_pairs):
            continue
        j = (rec.get("bookjour") or "").strip()
        if not j:
            j = "(no journal)"
        counts[j] += 1
    rows = sorted(counts.items(), key=lambda x: (-x[1], x[0].lower()))
    return rows


def journal_rows_with_ranks(
    papers: List[dict],
    y0: int,
    y1: int,
    target_pairs: Optional[Set[Tuple[str, str]]],
    journal_info: dict,
) -> List[JournalRow]:
    base = journal_frequency_rows(papers, y0, y1, target_pairs)
    out: List[JournalRow] = []
    for name, cnt in base:
        key = name.lower()
        info = journal_info.get(key) if name != "(no journal)" else None
        if isinstance(info, dict):
            out.append(
                (
                    name,
                    cnt,
                    str(info.get("rank", "")),
                    str(info.get("norm", "")),
                    str(info.get("sjr_pct", "")),
                    str(info.get("quartile", "")),
                    str(info.get("abdc", "")),
                )
            )
        else:
            out.append((name, cnt, "", "", "", "", ""))
    return out


def _lookup_journal_tuple(journal_dict: dict, jname: str):
    if not jname:
        return None
    if jname in journal_dict:
        return journal_dict[jname]
    jlower = jname.lower()
    for k, v in journal_dict.items():
        if str(k).strip().lower() == jlower:
            return v
    return None


def journal_rows_by_major_class(
    papers: List[dict],
    y0: int,
    y1: int,
    target_pairs: Optional[Set[Tuple[str, str]]],
    journal_dict: dict,
) -> List[Tuple[str, int]]:
    """
    journal_dict: name -> (class_info, rank_str) from read_journal_definition.
    """
    counts: Dict[str, int] = defaultdict(int)
    for rec in papers:
        if str(rec.get("vitatyp", "")).strip() not in ("J", "JR"):
            continue
        y = extract_year_int(rec.get("year", ""))
        if y is None or not (y0 <= y <= y1):
            continue
        if not _paper_matches_pairs(rec, target_pairs):
            continue
        jname = (rec.get("bookjour") or "").strip()
        if not jname:
            counts["(no journal)"] += 1
            continue
        tup = _lookup_journal_tuple(journal_dict or {}, jname)
        if not tup:
            counts["Unknown / not in definition"] += 1
            continue
        class_info = str(tup[0] or "")
        major = class_info.split("::")[0].strip() or "Unknown"
        counts[major] += 1
    return sorted(counts.items(), key=lambda x: (-x[1], x[0].lower()))
