"""Author-match summary helpers for the Retrieve page.

Mirrors the desktop ``LeftPanel._extract_author_keyword`` /
``LeftPanel._collect_matched_names`` logic so the web app can show the same
"N name(s) found: …" bold summary above retrieved results.

Kept as a small standalone module so it can be parity-tested without pulling
in Flask or the rest of the desktop UI stack.
"""

from __future__ import annotations

import re
from typing import Iterable, List


_PAT_INIT_LAST = re.compile(r"^\s*([A-Z](?:\.\s*[A-Z])*\.)\s+([A-Za-z\-']+)\s*$")
_PAT_INITIALS_ONLY = re.compile(r"^\s*(?:[A-Z]\.\s*)+\s*$")
_PAT_INITIALS_FULLMATCH = re.compile(r"(?:[A-Z]\.){1,}")


def _norm_initials(s: str) -> str:
    return (s or "").replace(" ", "")


def extract_author_keyword(query: str) -> str:
    """Pick the surname-ish token from a free-form author query.

    Examples (from desktop docstring):
      ``"Feldman"`` → ``"Feldman"``
      ``"P. Cal"``  → ``"Cal"``
      ``"Cal P."``  → ``"Cal"``
      ``"Cal, P."`` → ``"Cal"``
    """
    s = (query or "").strip()
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s)

    if "," in s:
        return s.split(",", 1)[0].strip()

    toks = s.split()
    if len(toks) == 1:
        return toks[0].strip()

    if _PAT_INITIALS_FULLMATCH.fullmatch(toks[0].replace(" ", "")):
        return toks[-1].strip()
    if _PAT_INITIALS_FULLMATCH.fullmatch(toks[-1].replace(" ", "")):
        return toks[0].strip()

    return toks[-1].strip()


def collect_matched_names(records: Iterable[dict], keyword: str) -> List[str]:
    """Return distinct ``"P.A. Lastname"`` strings whose surname contains ``keyword``."""
    kw = (keyword or "").strip().lower()
    if not kw:
        return []

    names_set: set[str] = set()

    for r in records or []:
        if not isinstance(r, dict):
            continue
        authors_raw = str(r.get("authors", "") or "")
        if not authors_raw.strip():
            continue

        tmp = authors_raw.replace(", and ", ", ").replace(" and ", ", ")
        parts = [p.strip() for p in tmp.split(",") if p.strip()]

        if len(parts) >= 2:
            cand_last = parts[0].strip()
            cand_init = parts[1].strip()
            if (
                cand_last
                and (kw in cand_last.lower())
                and _PAT_INITIALS_ONLY.match(cand_init)
            ):
                names_set.add(f"{_norm_initials(cand_init)} {cand_last}")

        for part in parts:
            m = _PAT_INIT_LAST.match(part)
            if m:
                init = _norm_initials(m.group(1))
                last = (m.group(2) or "").strip()
                if last and (kw in last.lower()):
                    names_set.add(f"{init} {last}")

            if "," in part:
                left, right = part.split(",", 1)
                last = left.strip()
                init = right.strip()
                if (
                    last
                    and (kw in last.lower())
                    and _PAT_INITIALS_ONLY.match(init)
                ):
                    names_set.add(f"{_norm_initials(init)} {last}")

    return sorted(names_set)


def matched_names_for_search(
    search_type: str,
    query,
    results: Iterable[dict],
) -> List[str]:
    """Return matched author names for the current search, or an empty list when
    the search type is not author-related.

    ``query`` may be either a string (legacy "any text" mode) or the
    ``{"author": ..., "title": ...}`` dict produced by ``_run_retrieve_form_search``
    for the dual-field author/title search.
    """
    if not isinstance(query, (str, dict)):
        return []

    if search_type == "author_title":
        if isinstance(query, dict):
            author = (query.get("author") or "").strip()
            if not author:
                return []
            return collect_matched_names(results, extract_author_keyword(author))
        if isinstance(query, str) and query.strip():
            return collect_matched_names(results, extract_author_keyword(query))

    return []
