"""
Parity test: standardize-person-names algorithm (web ``standardize_names_service``
vs desktop ``pages/standardizename.py`` + ``pages/collapsenameform.py``).

Both desktop pages are deeply Tk-coupled, so we transcribe their pure
algorithmic helpers (``is_correct_format``, ``find_similar_names``,
``replace_name_in_authors``, ``_normalize_name``) verbatim into this file
as a reference and assert that the web service matches.

The fixture data targets the trickiest categories called out in
PARITY_REPORT.md and the desktop docstrings:
    - bare last name + initials                ("McCarl, B.A.")
    - particles (von, de, van, ...)            ("von Neumann, J.")
    - "Suffix, I.N. Last" mis-ordering         ("II, B.L. Turner")
    - "I.N. Last Suffix" strict accepted form  ("B.L. Turner II")
    - non-abbreviated entered first name       ("McCarl, Bruce")
    - abbreviated, but suggestion has more inits or a suffix
    - meta-author tokens skipped               ("McCarl, B.A. et al.")
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = REPO_ROOT / "paperfile-web"


@pytest.fixture(autouse=True)
def _sys_path():
    if str(WEB_ROOT) not in sys.path:
        sys.path.insert(0, str(WEB_ROOT))
    yield


# --- Reference algorithm (verbatim from desktop CollapseNameForm) ----------


_SUFFIX_RE = re.compile(
    r"^(?:Jr\.?|Sr\.?|II|III|IV|V|VI|VII|VIII|IX|X)$", re.IGNORECASE
)
_INITIALS_LAST_SUFFIX_STRICT_RE = re.compile(
    r"^(?:[A-Z]\.)+"
    r"(?:\s+(?:von|van|de|del|la|le|di|da|du))*"
    r"\s+[A-Z][A-Za-z\'-]+"
    r"\s+(?:Jr\.?|Sr\.?|II|III|IV|V|VI|VII|VIII|IX|X)$"
)
_SUFFIX_COMMA_INITIALS_LAST_RE = re.compile(
    r"^(?P<suff>Jr\.?|Sr\.?|II|III|IV|V|VI|VII|VIII|IX|X)\s*,\s*"
    r"(?P<inits>(?:[A-Z]\.)+)"
    r"(?:\s+(?P<parts>(?:von|van|de|del|la|le|di|da|du)"
    r"(?:\s+(?:von|van|de|del|la|le|di|da|du))*))?"
    r"\s+(?P<last>[A-Z][A-Za-z\'-]+)$"
)
_META_TOKENS_RE = re.compile(r"(?i)(?:^|\s)(?:et\s+al\.?|others|et|al\.?)(?:\s|$)")


def _ref_fix_suffix_first(s: str) -> str:
    m = _SUFFIX_COMMA_INITIALS_LAST_RE.match(s)
    if not m:
        return s
    parts = m.group("parts")
    if parts:
        return f"{m.group('inits')} {parts} {m.group('last')} {m.group('suff')}"
    return f"{m.group('inits')} {m.group('last')} {m.group('suff')}"


def _ref_is_correct_format(name: str) -> bool:
    s = name if isinstance(name, str) else ""
    if not s:
        return False
    if s != s.strip():
        return False
    s = _ref_fix_suffix_first(s)
    if _INITIALS_LAST_SUFFIX_STRICT_RE.match(s):
        return True
    if not re.match(r"^[^,]+,\s(?:[A-Z]\.)+$", s):
        return False
    last_part = s.split(",", 1)[0]
    tokens = last_part.split()
    if not tokens:
        return False
    if _SUFFIX_RE.match(tokens[-1]):
        tokens = tokens[:-1]
        if not tokens:
            return False
    if len(tokens) >= 3 and tokens[0].lower() == "de" and tokens[1].lower() == "la":
        return tokens[2][0].isupper()
    joined = " ".join(tokens)
    if re.match(r"^(da|de)[A-Z]", joined):
        return True
    if re.match(r"^dela[A-Z]", joined):
        return True
    if re.match(r"^de la [A-Z]", joined):
        return True
    if re.match(r"^de la-[A-Z]", joined):
        return True
    prefix_set = {"von", "van", "de", "del", "la"}
    if tokens[0].lower() in prefix_set and len(tokens) > 1:
        return tokens[1][0].isupper()
    return tokens[0][0].isupper()


def _ref_extract_initial_letters(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    initials = re.findall(r"([A-Za-z])\.", s)
    if initials:
        return "".join(c.upper() for c in initials)
    parts = [p for p in re.split(r"\s+", s) if p]
    return "".join(p[0].upper() for p in parts if p and p[0].isalpha())


def _ref_is_initials_form(s: str) -> bool:
    s = (s or "").strip()
    return bool(re.fullmatch(r"(?:[A-Za-z]\.)+", s.replace(" ", "")))


def _ref_split_name_safe(name: str) -> Tuple[str, str]:
    try:
        parts = (name or "").strip().split(",", 1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
        return (name or "").strip(), ""
    except Exception:
        return (name or "").strip(), ""


def _ref_split_last_and_suffix(last: str) -> Tuple[str, str]:
    s = (last or "").strip()
    if not s:
        return "", ""
    tokens = s.split()
    if not tokens:
        return "", ""
    suffix = ""
    if _SUFFIX_RE.match(tokens[-1]):
        suffix = re.sub(r"[^A-Za-z0-9]", "", tokens[-1]).lower()
        tokens = tokens[:-1]
    base = " ".join(tokens).strip().lower()
    base = re.sub(r"[^a-z\s'-]", "", base)
    base = re.sub(r"\s+", " ", base).strip()
    return base, suffix


def _ref_same_base(db_last: str, cand_last: str) -> bool:
    db_base, _ = _ref_split_last_and_suffix(db_last)
    cand_base, _ = _ref_split_last_and_suffix(cand_last)
    return bool(db_base) and db_base == cand_base


def _ref_adds_suffix_only(db_last: str, cand_last: str) -> bool:
    db_base, db_suffix = _ref_split_last_and_suffix(db_last)
    cand_base, cand_suffix = _ref_split_last_and_suffix(cand_last)
    if not db_base or not cand_base or db_base != cand_base:
        return False
    if db_suffix:
        return False
    return bool(cand_suffix)


def _ref_find_similar(all_names: List[str], faculty_names: List[str]) -> List[Tuple[str, str]]:
    faculty_set = set(faculty_names)
    faculty_candidates = []
    for fname in faculty_names:
        if not _ref_is_correct_format(fname):
            continue
        f_last, f_first = _ref_split_name_safe(fname)
        base, suffix = _ref_split_last_and_suffix(f_last)
        faculty_candidates.append(
            {
                "full": fname,
                "last_raw": f_last,
                "first_raw": f_first,
                "base_last": base,
                "suffix": suffix,
                "initials": _ref_extract_initial_letters(f_first),
                "is_initials": _ref_is_initials_form(f_first),
            }
        )
    suspects = []
    for name in all_names:
        if _META_TOKENS_RE.search((name or "").strip()):
            continue
        if name in faculty_set:
            continue
        db_last, db_first = _ref_split_name_safe(name)
        db_initials = _ref_extract_initial_letters(db_first)
        db_is_initials = _ref_is_initials_form(db_first)
        if not db_last or not db_initials:
            continue
        same_last = [
            f for f in faculty_candidates
            if f["full"] in faculty_set and _ref_same_base(db_last, f["last_raw"])
        ]
        if not same_last:
            continue
        best = None
        if not db_is_initials:
            valid = [
                f for f in same_last
                if f["is_initials"] and f["initials"] and f["initials"][0] == db_initials[0]
            ]
            if valid:
                valid.sort(key=lambda x: (len(x["initials"]), 1 if x["suffix"] else 0, x["full"].lower()))
                best = valid[0]
        else:
            valid = [
                f for f in same_last
                if (f["initials"].startswith(db_initials) and len(f["initials"]) > len(db_initials))
                or (f["initials"] == db_initials and _ref_adds_suffix_only(db_last, f["last_raw"]))
            ]
            if valid:
                valid.sort(
                    key=lambda x: (
                        0 if len(x["initials"]) > len(db_initials) else 1,
                        len(x["initials"]),
                        0 if x["suffix"] else 1,
                        x["full"].lower(),
                    )
                )
                best = valid[0]
        if best:
            cand = best["full"]
            if cand in faculty_set and cand.strip().lower() != name.strip().lower():
                suspects.append((name, cand))
    return suspects


def _ref_replace_name_in_authors(authors_str: str, name_entered: str, suggestion: str) -> str:
    try:
        last, first = (s.strip() for s in name_entered.strip().split(","))
        ab1 = f"{last}, {first}"
        ab2 = f"{first} {last}"
        sl, sf = (s.strip() for s in suggestion.strip().split(","))
        sg1 = f"{sl}, {sf}"
        sg2 = f"{sf} {sl}"
        if ab1 in authors_str:
            return authors_str.replace(ab1, sg1)
        if ab2 in authors_str:
            return authors_str.replace(ab2, sg2)
        return authors_str
    except Exception:
        return authors_str


# --- Tests -----------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "McCarl, B.A.",
        "McCarl, Bruce",
        "B.A. McCarl",
        "B.L. Turner II",
        "C.A. Pope III",
        "II, B.L. Turner",  # mis-ordered suffix that the helper reorders
        "Ribera, L.",
        "Ribera, L.A.",
        "Ribera, L.A.L.",
        "Rosson, C.P.",
        "Rosson III., C.P.",
        "  McCarl, B.A.",  # leading whitespace -> bad
        "von Neumann, J.",
        "Doe",
        "Doe,",
        "Doe, ",
        "",
        "X, A.B. and Y, C.D.",
        "deAraujo, S.",
    ],
)
def test_is_correct_format_matches_desktop(name):
    from modules.standardize_names_service import is_correct_format

    assert is_correct_format(name) == _ref_is_correct_format(name)


@pytest.fixture()
def faculty():
    return [
        "McCarl, B.A.",
        "Smith, J.D.",
        "Ribera, L.A.L.",
        "Rosson III., C.P.",
        "von Neumann, J.",
        "Pope, C.A.",
    ]


@pytest.mark.parametrize(
    "names",
    [
        ["McCarl, Bruce"],
        ["McCarl, B."],
        ["Ribera, L."],
        ["Ribera, L.A."],
        ["Rosson, C.P."],
        ["Smith, J."],
        ["Pope, C."],
        ["McCarl, B.A. et al."],
        ["von Neumann, John"],
        ["McCarl, B.A.", "Ribera, L.A.", "Smith, John D.", "Rosson, C.P.", "Doerr, J."],
        ["McCarl, B.A."],  # already faculty -> no suggestion
    ],
)
def test_find_similar_names_matches_desktop(faculty, names):
    from modules.standardize_names_service import find_similar_names

    web = find_similar_names(names, faculty)
    desk = _ref_find_similar(names, faculty)
    assert web == desk, f"\nweb={web}\ndesk={desk}"


@pytest.mark.parametrize(
    "authors,entered,suggestion,expected",
    [
        ("McCarl, B. and Smith, J.", "McCarl, B.", "McCarl, B.A.", "McCarl, B.A. and Smith, J."),
        ("B. McCarl, J. Smith", "McCarl, B.", "McCarl, B.A.", "B.A. McCarl, J. Smith"),
        ("Smith, J.", "McCarl, B.", "McCarl, B.A.", "Smith, J."),  # not present -> unchanged
        ("Ribera, L.", "Ribera, L.", "Ribera, L.A.L.", "Ribera, L.A.L."),
    ],
)
def test_replace_name_in_authors_matches_desktop(authors, entered, suggestion, expected):
    from modules.standardize_names_service import replace_name_in_authors

    web = replace_name_in_authors(authors, entered, suggestion)
    desk = _ref_replace_name_in_authors(authors, entered, suggestion)
    assert web == desk == expected


def test_actionable_rows_orders_incorrect_first(faculty):
    from modules.standardize_names_service import actionable_rows

    # "McCarl, Bruce" is incorrect format
    # "McCarl, B."   is correct format but a suspect of McCarl, B.A.
    # "Doerr, J."    is correct format and has no faculty look-alike (Doe, J. != Doerr)
    distinct = ["McCarl, Bruce", "McCarl, B.", "Doerr, J."]
    rows = actionable_rows(distinct, faculty)
    names = [r["name"] for r in rows]
    assert "McCarl, Bruce" in names
    assert "McCarl, B." in names
    assert "Doerr, J." not in names
    # incorrect-format rows come first
    assert rows[0]["name"] == "McCarl, Bruce"
    assert rows[0]["kind"] == "incorrect"
    suspect_row = next(r for r in rows if r["name"] == "McCarl, B.")
    assert suspect_row["kind"] == "suspect"
    assert suspect_row["suggestion"] == "McCarl, B.A."


def test_collect_distinct_names_smoke():
    """``process_authors`` strips the periods from initials when forming the
    output token, so e.g. ``"McCarl, B.A."`` becomes ``"McCarl, BA"`` in the
    distinct-names list. This is by design — the standardize page uses the
    same normalization to coalesce all variants of a name. We use
    single-author records here because PARITY_REPORT.md §3.3 documents
    ``process_authors`` quirks on multi-author strings; that quirk is
    held identically by the desktop and is out of scope for this test."""
    from modules.standardize_names_service import collect_distinct_names

    records = [
        {"number": "1", "authors": "McCarl, B.A."},
        {"number": "2", "authors": "Smith, J.D."},
        {"number": "5", "authors": "McCarl, B.A."},
        {"number": "3", "authors": ""},
    ]
    names, mapping = collect_distinct_names(records)
    assert "McCarl, BA" in names
    assert "Smith, JD" in names
    mccarl_key = "mccarl,ba"
    assert sorted(set(mapping[mccarl_key])) == ["1", "5"]


def test_apply_replacement_filters_by_target_numbers(faculty):
    from modules.standardize_names_service import apply_replacement_to_records

    records = [
        {"number": "1", "authors": "McCarl, B. and Smith, J."},
        {"number": "2", "authors": "McCarl, B."},
        {"number": "3", "authors": "Doe, J."},  # ignored: not in target_numbers
    ]
    modified, count = apply_replacement_to_records(
        records, "McCarl, B.", "McCarl, B.A.", target_numbers=["1", "2"]
    )
    assert count == 2
    assert {r["number"] for r in modified} == {"1", "2"}
    assert all("McCarl, B.A." in r["authors"] for r in modified)
