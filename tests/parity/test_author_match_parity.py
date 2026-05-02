"""Parity tests for the web's author-match summary against the desktop logic.

The desktop algorithm (transcribed verbatim below as ``_ref_*``) lives in
``paperfile/pages/left_panel.py`` inside the Retrieve flow. The web service
under test lives in ``paperfile-web/modules/author_match.py``.
"""

from __future__ import annotations

import os
import re
import sys
from typing import List

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if WEB_ROOT not in sys.path:
    sys.path.insert(0, WEB_ROOT)

from modules.author_match import (
    collect_matched_names,
    extract_author_keyword,
    matched_names_for_search,
)


# --- Reference implementation (transcribed verbatim from desktop) ---

def _ref_extract_author_keyword(q: str) -> str:
    s = (q or "").strip()
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s)

    if "," in s:
        return s.split(",", 1)[0].strip()

    toks = s.split()
    if len(toks) == 1:
        return toks[0].strip()

    if re.fullmatch(r"(?:[A-Z]\.){1,}", toks[0].replace(" ", "")):
        return toks[-1].strip()
    if re.fullmatch(r"(?:[A-Z]\.){1,}", toks[-1].replace(" ", "")):
        return toks[0].strip()
    return toks[-1].strip()


def _ref_collect_matched_names(records: list, keyword: str) -> List[str]:
    kw = (keyword or "").strip().lower()
    if not kw:
        return []

    names_set = set()
    pat_init_last = re.compile(r"^\s*([A-Z](?:\.\s*[A-Z])*\.)\s+([A-Za-z\-']+)\s*$")
    pat_initials_only = re.compile(r"^\s*(?:[A-Z]\.\s*)+\s*$")

    def _norm_initials(s: str) -> str:
        return (s or "").replace(" ", "")

    for r in records or []:
        authors_raw = str(r.get("authors", "") or "")
        if not authors_raw.strip():
            continue
        tmp = authors_raw.replace(", and ", ", ").replace(" and ", ", ")
        parts = [p.strip() for p in tmp.split(",") if p.strip()]

        if len(parts) >= 2:
            cand_last = parts[0].strip()
            cand_init = parts[1].strip()
            if cand_last and (kw in cand_last.lower()) and pat_initials_only.match(cand_init):
                names_set.add(f"{_norm_initials(cand_init)} {cand_last}")

        for part in parts:
            m = pat_init_last.match(part)
            if m:
                init = _norm_initials(m.group(1))
                last = (m.group(2) or "").strip()
                if last and (kw in last.lower()):
                    names_set.add(f"{init} {last}")
            if "," in part:
                left, right = part.split(",", 1)
                last = left.strip()
                init = right.strip()
                if last and (kw in last.lower()) and pat_initials_only.match(init):
                    names_set.add(f"{_norm_initials(init)} {last}")
    return sorted(names_set)


# --- Tests ---

KEYWORD_CASES = [
    ("", ""),
    ("Feldman", "Feldman"),
    ("P. Cal", "Cal"),
    ("Cal P.", "Cal"),
    ("Cal, P.", "Cal"),
    ("Vali", "Vali"),
    ("McCarl, B.A.", "McCarl"),
    ("   spaces   between   words  ", "words"),
    ("P.A. McCarl", "McCarl"),
]


def test_extract_author_keyword_matches_desktop():
    for raw, _expected in KEYWORD_CASES:
        assert extract_author_keyword(raw) == _ref_extract_author_keyword(raw), raw


SAMPLE_RECORDS = [
    {"authors": "McCarl, B.A. and Smith, J.D."},
    {"authors": "P.A. Cal, J.D. Smith and B.A. McCarl"},
    {"authors": "Feldman, P.A., Cal, P. and Smith, J.D."},
    {"authors": "Smith, J. and Jones, R."},
    {"authors": ""},
    {"other": "no authors key"},
]


def test_collect_matched_names_matches_desktop():
    for kw in ["mccarl", "Smith", "feld", "Cal", "x", ""]:
        assert collect_matched_names(SAMPLE_RECORDS, kw) == _ref_collect_matched_names(
            SAMPLE_RECORDS, kw
        ), kw


def test_matched_names_for_search_dispatches_correctly():
    results = SAMPLE_RECORDS

    assert matched_names_for_search("author_title", {"author": "McCarl", "title": ""}, results) == \
        _ref_collect_matched_names(results, _ref_extract_author_keyword("McCarl"))

    assert matched_names_for_search("author_title", "McCarl", results) == \
        _ref_collect_matched_names(results, _ref_extract_author_keyword("McCarl"))

    assert matched_names_for_search("keyword", "McCarl", results) == []
    assert matched_names_for_search("author_title", {"author": "", "title": "anything"}, results) == []
    assert matched_names_for_search("author_title", "", results) == []
