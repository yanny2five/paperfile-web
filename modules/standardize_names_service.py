"""
Standardize-names service for paperfile-web.

Mirrors the algorithm in
``paperfile/pages/standardizename.py`` + ``paperfile/pages/collapsenameform.py``:

1. Walk every paper, run ``process_authors`` on the ``authors`` field, and
   collect the set of distinct formatted names (``"Last, I.N."`` form).
2. For each formatted name, decide whether it is in correct format using
   the same set of regexes as the desktop's ``CollapseNameForm.is_correct_format``.
3. For each name, compute a suggested replacement using the desktop's
   ``find_similar_names`` algorithm: only suggest something that already
   exists in the faculty file (``.cng``) and shares the same base last
   name. Two suggestion strategies are tried:

   - If the entered first-name is *not* in initials form (e.g.
     ``"McCarl, Bruce"``), suggest the abbreviated faculty form
     (``"McCarl, B."``).
   - If the entered first-name is in initials form (e.g. ``"Ribera, L."``),
     suggest a longer initials form with the same base last name
     (``"Ribera, L.A.L."``) or the same initials with a suffix added to
     the last name (``"Rosson, C.P." -> "Rosson III., C.P."``).

4. Provide a UNION of incorrect-format names + suspect-pair names so the
   UI can show every actionable row at the top of the page.
5. Provide ``apply_replacement_to_records`` which mirrors
   ``CollapseNameForm.replace_name_in_authors`` (Last,First and First Last
   forms are both swapped).

The service is pure: it takes records + faculty-name list as inputs and
returns plain dicts/lists. The Flask route is responsible for loading
those inputs and writing the resulting records back to the .cnt file.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from modules.extract_names import process_authors


# --- Format-detection regexes (verbatim from desktop CollapseNameForm) ----

SUFFIX_RE = re.compile(
    r"^(?:Jr\.?|Sr\.?|II|III|IV|V|VI|VII|VIII|IX|X)$", re.IGNORECASE
)

INITIALS_LAST_SUFFIX_STRICT_RE = re.compile(
    r"^(?:[A-Z]\.)+"
    r"(?:\s+(?:von|van|de|del|la|le|di|da|du))*"
    r"\s+[A-Z][A-Za-z\'-]+"
    r"\s+(?:Jr\.?|Sr\.?|II|III|IV|V|VI|VII|VIII|IX|X)$"
)

SUFFIX_COMMA_INITIALS_LAST_RE = re.compile(
    r"^(?P<suff>Jr\.?|Sr\.?|II|III|IV|V|VI|VII|VIII|IX|X)\s*,\s*"
    r"(?P<inits>(?:[A-Z]\.)+)"
    r"(?:\s+(?P<parts>(?:von|van|de|del|la|le|di|da|du)"
    r"(?:\s+(?:von|van|de|del|la|le|di|da|du))*))?"
    r"\s+(?P<last>[A-Z][A-Za-z\'-]+)$"
)

META_TOKENS_RE = re.compile(r"(?i)(?:^|\s)(?:et\s+al\.?|others|et|al\.?)(?:\s|$)")


def _fix_suffix_first_if_any(s: str) -> str:
    """If ``s`` looks like ``Suffix, I.N. [particles] Last``, return the
    re-ordered ``I.N. [particles] Last Suffix``; otherwise return ``s``
    unchanged. Matches desktop helper exactly."""
    m = SUFFIX_COMMA_INITIALS_LAST_RE.match(s)
    if not m:
        return s
    parts = m.group("parts")
    if parts:
        return f"{m.group('inits')} {parts} {m.group('last')} {m.group('suff')}"
    return f"{m.group('inits')} {m.group('last')} {m.group('suff')}"


def is_correct_format(name: str) -> bool:
    """True iff ``name`` matches the desktop's accepted "Last, I.N." spec."""
    s = name if isinstance(name, str) else ""
    if not s:
        return False
    if s != s.strip():
        return False
    s = _fix_suffix_first_if_any(s)
    if INITIALS_LAST_SUFFIX_STRICT_RE.match(s):
        return True
    if not re.match(r"^[^,]+,\s(?:[A-Z]\.)+$", s):
        return False
    last_part = s.split(",", 1)[0]
    tokens = last_part.split()
    if not tokens:
        return False
    if SUFFIX_RE.match(tokens[-1]):
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


def has_meta_tokens(name: str) -> bool:
    """True if ``name`` contains author meta-tokens (et al., others, etc.)."""
    if not isinstance(name, str):
        return False
    return META_TOKENS_RE.search(name.strip()) is not None


def _normalize_for_grouping(name: str) -> str:
    """Lowercase + strip punctuation key used to coalesce variants of the same name."""
    cleaned = re.sub(r"[^a-zA-Z,]", "", (name or "").strip().lower())
    parts = [p.strip() for p in cleaned.split(",", 1)]
    if len(parts) == 1:
        return parts[0] + ","
    return ",".join(parts)


def normalize_for_replacement_lookup(name: str) -> str:
    """The exact key the standardize page uses to look up record numbers
    for a displayed name. Same as desktop ``standardizename._normalize_name``.
    """
    return _normalize_for_grouping(name)


# --- Suggestion algorithm (mirrors desktop find_similar_names) ------------


def _extract_initial_letters(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    initials = re.findall(r"([A-Za-z])\.", s)
    if initials:
        return "".join(ch.upper() for ch in initials)
    parts = [p for p in re.split(r"\s+", s) if p]
    return "".join(p[0].upper() for p in parts if p and p[0].isalpha())


def _is_initials_form(s: str) -> bool:
    s = (s or "").strip()
    return bool(re.fullmatch(r"(?:[A-Za-z]\.)+", s.replace(" ", "")))


def _split_name_safe(name: str) -> Tuple[str, str]:
    try:
        parts = (name or "").strip().split(",", 1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
        return (name or "").strip(), ""
    except Exception:
        return (name or "").strip(), ""


def _split_last_and_suffix(last: str) -> Tuple[str, str]:
    s = (last or "").strip()
    if not s:
        return "", ""
    tokens = s.split()
    if not tokens:
        return "", ""
    suffix = ""
    if SUFFIX_RE.match(tokens[-1]):
        suffix = re.sub(r"[^A-Za-z0-9]", "", tokens[-1]).lower()
        tokens = tokens[:-1]
    base = " ".join(tokens).strip().lower()
    base = re.sub(r"[^a-z\s'-]", "", base)
    base = re.sub(r"\s+", " ", base).strip()
    return base, suffix


def _same_base_last_name(db_last: str, cand_last: str) -> bool:
    db_base, _ = _split_last_and_suffix(db_last)
    cand_base, _ = _split_last_and_suffix(cand_last)
    return bool(db_base) and db_base == cand_base


def _candidate_adds_suffix_only(db_last: str, cand_last: str) -> bool:
    db_base, db_suffix = _split_last_and_suffix(db_last)
    cand_base, cand_suffix = _split_last_and_suffix(cand_last)
    if not db_base or not cand_base or db_base != cand_base:
        return False
    if db_suffix:
        return False
    return bool(cand_suffix)


def find_similar_names(
    all_names: Iterable[str],
    faculty_names: Iterable[str],
) -> List[Tuple[str, str]]:
    """Return ``[(entered_name, suggested_faculty_name), ...]`` pairs.

    Mirrors ``CollapseNameForm.find_similar_names`` exactly: only proposes
    suggestions that already exist in the faculty list and share the same
    base last name; never suggests cross-spelling fixes.
    """
    faculty_set = set(faculty_names)
    faculty_candidates: List[Dict[str, Any]] = []
    for fname in faculty_set:
        if not is_correct_format(fname):
            continue
        f_last, f_first = _split_name_safe(fname)
        base, suffix = _split_last_and_suffix(f_last)
        faculty_candidates.append(
            {
                "full": fname,
                "last_raw": f_last,
                "first_raw": f_first,
                "base_last": base,
                "suffix": suffix,
                "initials": _extract_initial_letters(f_first),
                "is_initials": _is_initials_form(f_first),
            }
        )

    suspects: List[Tuple[str, str]] = []
    for name in all_names:
        if has_meta_tokens(name):
            continue
        if name in faculty_set:
            continue
        db_last, db_first = _split_name_safe(name)
        db_initials = _extract_initial_letters(db_first)
        db_is_initials = _is_initials_form(db_first)
        if not db_last or not db_initials:
            continue
        same_last_candidates = [
            f for f in faculty_candidates
            if f["full"] in faculty_set and _same_base_last_name(db_last, f["last_raw"])
        ]
        if not same_last_candidates:
            continue

        best_candidate: Optional[Dict[str, Any]] = None
        if not db_is_initials:
            valid = [
                f for f in same_last_candidates
                if f["is_initials"]
                and f["initials"]
                and f["initials"][0] == db_initials[0]
            ]
            if valid:
                valid.sort(
                    key=lambda x: (
                        len(x["initials"]),
                        1 if x["suffix"] else 0,
                        x["full"].lower(),
                    )
                )
                best_candidate = valid[0]
        else:
            valid = [
                f for f in same_last_candidates
                if (
                    f["initials"].startswith(db_initials)
                    and len(f["initials"]) > len(db_initials)
                )
                or (
                    f["initials"] == db_initials
                    and _candidate_adds_suffix_only(db_last, f["last_raw"])
                )
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
                best_candidate = valid[0]

        if best_candidate:
            cand = best_candidate["full"]
            if cand in faculty_set and cand.strip().lower() != name.strip().lower():
                suspects.append((name, cand))
    return suspects


# --- Page-level helpers ---------------------------------------------------


def collect_distinct_names(records: Iterable[Dict[str, Any]]) -> Tuple[List[str], Dict[str, List[str]]]:
    """Return ``(distinct_formatted_names_sorted, name_to_record_numbers)``.

    Output ordering matches desktop standardizename.extract_and_display_names:
    special (non-alpha first character) names sorted first, then alphabetic.
    """
    processed: List[Dict[str, str]] = []
    name_to_numbers: Dict[str, List[str]] = {}
    for record in records or []:
        raw_authors = (record or {}).get("authors", "")
        number = str((record or {}).get("number", "")).strip()
        if not raw_authors:
            continue
        formatted_names, _ = process_authors(raw_authors)
        for name in formatted_names:
            normalized = _normalize_for_grouping(name)
            processed.append({"raw": raw_authors, "formatted": name, "normalized": normalized})
            name_to_numbers.setdefault(normalized, []).append(number)
            name_to_numbers.setdefault(name, []).append(number)

    unique: Dict[str, str] = {}
    for item in processed:
        key = item["normalized"]
        if key not in unique:
            unique[key] = item["formatted"]

    special: List[Tuple[str, str]] = []
    normal: List[Tuple[str, str]] = []
    for norm, formatted in unique.items():
        first_char = formatted.strip()[0] if formatted.strip() else ""
        if not first_char.isalpha():
            special.append((norm, formatted))
        else:
            normal.append((norm, formatted))

    def _sort_key(pair: Tuple[str, str]):
        norm = pair[0]
        last_part = norm.split(",", 1)[0].strip().lower()
        first_part = norm.split(",", 1)[1].strip().lower() if "," in norm else ""
        return (last_part, first_part)

    special.sort(key=_sort_key)
    normal.sort(key=_sort_key)
    return [name for _norm, name in special + normal], name_to_numbers


def _first_initials_letter_count(name: str) -> int:
    """Count alphabetic letters in the abbreviated first name (matches desktop)."""
    try:
        last, first = name.strip().split(",", 1)
        first_parts = first.strip().split()
        if all(p.endswith(".") for p in first_parts):
            return sum(1 for ch in first if ch.isalpha())
        initials = [p[0].upper() + "." for p in first_parts if p]
        return sum(1 for ch in " ".join(initials) if ch.isalpha())
    except Exception:
        return 0


def actionable_rows(
    distinct_names: Iterable[str],
    faculty_names: Iterable[str],
) -> List[Dict[str, str]]:
    """Return the rows the UI should display at the top of the page.

    Each row is ``{"name": ..., "suggestion": ..., "kind": "incorrect"|"suspect"}``.
    Order: incorrect-format rows first (excluding ones with >=2 initials and
    meta-token rows), then any suspect-pair rows not already added. Mirrors
    the desktop's ``populate_table``.
    """
    suspects = find_similar_names(distinct_names, faculty_names)
    suggestion_dict = dict(suspects)
    rows: List[Dict[str, str]] = []
    seen: set = set()

    for name in distinct_names:
        if has_meta_tokens(name):
            continue
        if is_correct_format(name):
            continue
        if _first_initials_letter_count(name) >= 2:
            continue
        rows.append(
            {
                "name": name,
                "suggestion": suggestion_dict.get(name, ""),
                "kind": "incorrect",
            }
        )
        seen.add(name)

    for name, suggestion in suspects:
        if name in seen:
            continue
        rows.append({"name": name, "suggestion": suggestion, "kind": "suspect"})
        seen.add(name)

    return rows


# --- Replacement -----------------------------------------------------------


def replace_name_in_authors(authors_str: str, name_entered: str, suggestion: str) -> str:
    """Replace ``name_entered`` with ``suggestion`` in the authors string.

    Tries both ``Last, First`` and ``First Last`` orderings (matches desktop
    ``CollapseNameForm.replace_name_in_authors``). Returns the original
    string unchanged if neither form is present.
    """
    try:
        name_entered_clean = (name_entered or "").strip()
        suggestion_clean = (suggestion or "").strip()
        last, first = (s.strip() for s in name_entered_clean.split(","))
        abbrev_format1 = f"{last}, {first}"
        abbrev_format2 = f"{first} {last}"
        sugg_last, sugg_first = (s.strip() for s in suggestion_clean.split(","))
        suggestion_format1 = f"{sugg_last}, {sugg_first}"
        suggestion_format2 = f"{sugg_first} {sugg_last}"
        if abbrev_format1 in (authors_str or ""):
            return authors_str.replace(abbrev_format1, suggestion_format1)
        if abbrev_format2 in (authors_str or ""):
            return authors_str.replace(abbrev_format2, suggestion_format2)
        return authors_str or ""
    except Exception:
        return authors_str or ""


def apply_replacement_to_records(
    records: List[Dict[str, Any]],
    name_entered: str,
    suggestion: str,
    target_numbers: Optional[Iterable[str]] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """Return ``(modified_records, count_changed)``.

    Walks each record (optionally filtered to ``target_numbers``) and
    rewrites its ``authors`` field via :func:`replace_name_in_authors`.
    The returned list contains *only* the records whose authors actually
    changed, so callers can pass them to ``overwrite_record_in_cnt``.
    """
    target_set: Optional[set] = None
    if target_numbers is not None:
        target_set = {str(n).strip() for n in target_numbers}
    modified: List[Dict[str, Any]] = []
    for rec in records or []:
        if not rec:
            continue
        num = str(rec.get("number", "")).strip()
        if target_set is not None and num not in target_set:
            continue
        original = rec.get("authors", "") or ""
        updated = replace_name_in_authors(original, name_entered, suggestion)
        if updated != original:
            new_rec = dict(rec)
            new_rec["authors"] = updated
            modified.append(new_rec)
    return modified, len(modified)
