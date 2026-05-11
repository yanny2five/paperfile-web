"""Web search engine — thin desktop-faithful wrappers around modules/searchdata.py.

This module exists in two layers:

1. Field accessors (``get_authors``, ``get_title``, ``normalize``, ...). These
   are orthogonal to search semantics and used by formatters, templates, and
   tests.

2. The search runtime (``search_papers``, ``sort_results``, plus the strict
   parity helpers ``parse_year_range_inputs``, ``apply_year_filter``,
   ``author_variants``). These are thin wrappers over the byte-identical desktop
   modules ``modules.searchdata.SearchData`` and ``modules.sortdata.SortData``,
   plus desktop helpers transcribed from ``paperfile/pages/left_panel.py`` and
   ``paperfile/pages/right_panel.py``.

Behavioral guarantees (desktop parity):

* All text matching is case-insensitive **substring** matching (no Unicode NFKD
  normalization, no whitespace tokenization, no per-term AND).
* Year handling is strict: both year boxes empty -> match year-empty records
  only; one filled and the other empty -> invalid input; non-4-digit / out of
  ``[1900, 2100]`` -> invalid input. Invalid input causes ``search_papers`` to
  return ``[]`` (callers should surface a message; see ``parse_year_range_inputs``
  which returns ``None`` for invalid input so the caller can detect it).
* Author / title search ANDs every nonempty input across the four desktop
  inputs (``author``, ``optional_author``, ``title``, ``optional_title``) and,
  for author inputs, expands typed initials into desktop's ordering variants
  (``"P. Cal"`` -> ``["P. Cal", "Cal, P.", "Cal P."]``) and unions the
  per-variant result sets, deduplicating by paper ``number``.
* Vita-type filter uses strict uppercase equality on ``record["vitatyp"]``.
* ``keyword`` mode searches ``subject1`` and ``subject2`` only (the
  ``keywords`` field is ignored, matching desktop ``fuzzy_search_by_keyword``).
* ``any_field`` mode returns the record if any **single** field contains the
  literal substring (no concatenated blob, no per-token AND).

The legacy ``passes_search_type``/``passes_year_range``/``passes_vita_type``
predicates remain so existing imports keep working, but they are now thin
wrappers around the same desktop algorithms.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Union

from modules.searchdata import SearchData
from modules.sortdata import SortData


# -----------------------------------------------------------------------------
# Field accessors (orthogonal helpers; used by formatters, sort, tests)
# -----------------------------------------------------------------------------

def normalize(value):
    """Lowercase + strip + collapse whitespace.

    Used for sort keys and number/year exact-equality comparisons. **Not** used
    inside text matching — desktop matches on raw substring, so search_service
    text matchers never normalize beyond ``str(...).lower()``.
    """
    return " ".join(str(value or "").strip().lower().split())


def get_field(paper, *possible_keys):
    """Return the first matching field from the paper dict, case-insensitive."""
    lowered_map = {str(k).strip().lower(): v for k, v in paper.items()}
    for key in possible_keys:
        if key.lower() in lowered_map:
            return lowered_map[key.lower()]
    return ""


def get_authors(paper):
    return get_field(paper, "authors", "author", "author(s)")


def get_title(paper):
    return get_field(paper, "title", "paper title")


def get_journal(paper):
    return get_field(paper, "bookjour", "journal", "journal/book", "book", "journal or book")


def get_keywords(paper):
    return get_field(paper, "keywords", "keyword", "key words")


def get_year(paper):
    return get_field(paper, "year", "publication year")


def get_number(paper):
    return get_field(paper, "number", "no", "id", "paper number")


def get_vita_type(paper):
    return get_field(paper, "vitatyp", "vita_type", "vita type", "type")


# -----------------------------------------------------------------------------
# Year-range parsing (transcribed from paperfile/pages/right_panel.py::get_year_range
# and paperfile/pages/left_panel.py::_apply_year_filter; behavior must match
# byte-identically).
# -----------------------------------------------------------------------------

def parse_year_range_inputs(first_raw, last_raw):
    """Return the desktop-style year-range descriptor for a pair of form inputs.

    Returns:
        ``{"mode": "range", "first_year": int, "last_year": int}`` when both
            boxes contain a clean 4-digit year in ``[1900, 2100]``;
        ``{"mode": "empty_only"}`` when **both** boxes are empty (desktop
            interprets this as "match only records with an empty year field");
        ``None`` when input is invalid (one box empty / the other not, or any
            box contains something that is not a 4-digit year in the valid
            range). Callers should surface an error message and abort the
            search, mirroring desktop's "Invalid year range" popup.
    """
    first = (str(first_raw) if first_raw is not None else "").strip()
    last = (str(last_raw) if last_raw is not None else "").strip()
    if not first and not last:
        return {"mode": "empty_only"}
    if not first or not last:
        return None

    def _parse(s):
        if not re.fullmatch(r"\d{4}", s):
            return None
        y = int(s)
        return y if 1900 <= y <= 2100 else None

    fy, ly = _parse(first), _parse(last)
    if fy is None or ly is None:
        return None
    return {"mode": "range", "first_year": fy, "last_year": ly}


def apply_year_filter(records, year_range):
    """Apply desktop's two-mode year filter.

    Mirrors ``LeftPanel._apply_year_filter``:
      * ``mode == "range"``: keep records whose ``year`` field is a clean 4-digit
        number in ``[first_year, last_year]``;
      * ``mode == "empty_only"``: keep records whose ``year`` field is empty.
    """
    if records is None:
        return []
    if year_range is None:
        return []
    mode = year_range.get("mode")
    out = []
    for record in records:
        raw = str(record.get("year", "") or "").strip()
        if mode == "empty_only":
            if raw == "":
                out.append(record)
            continue
        if mode == "range":
            if not re.fullmatch(r"\d{4}", raw):
                continue
            y = int(raw)
            if year_range["first_year"] <= y <= year_range["last_year"]:
                out.append(record)
    return out


# -----------------------------------------------------------------------------
# Author-name variants (transcribed from paperfile/pages/left_panel.py
# ``_author_variants``). Generates ordering variants for typed initials so the
# substring search succeeds regardless of how the database stores the name.
# -----------------------------------------------------------------------------

_PAT_INITIALS_TOKEN = re.compile(r"(?:[A-Z]\.){1,}")


def _is_initials_token(t):
    t = (t or "").strip().replace(" ", "")
    return "." in t and bool(_PAT_INITIALS_TOKEN.fullmatch(t))


def author_variants(s):
    """Build author search variants exactly like desktop.

    Examples (verbatim from desktop docstring)::

        "P.  Cal"   -> ["P. Cal", "Cal, P.", "Cal P."]
        "Cal P."    -> ["Cal P.", "P. Cal", "Cal, P."]
        "Cal, P."   -> ["Cal, P.", "P. Cal", "Cal P."]
        "Adams"     -> ["Adams"]    # no initials -> no variants
        ""          -> [""]         # one empty pass-through
    """
    base = re.sub(r"\s+", " ", (s or "")).strip()
    if not base:
        return [""]
    variants = [base]
    if "," in base:
        left, right = base.split(",", 1)
        last = re.sub(r"\s+", " ", left).strip()
        init = re.sub(r"\s+", " ", right).strip().replace(" ", "")
        if last and _is_initials_token(init):
            for v in (f"{init} {last}", f"{last} {init}"):
                if v.lower() not in {x.lower() for x in variants}:
                    variants.append(v)
        return variants

    toks = base.split()
    if len(toks) < 2:
        return variants

    first = toks[0].replace(" ", "")
    last_tok = toks[-1].replace(" ", "")

    if _is_initials_token(first):
        last = " ".join(toks[1:]).strip()
        if last:
            for v in (f"{last}, {first}", f"{last} {first}"):
                if v.lower() not in {x.lower() for x in variants}:
                    variants.append(v)
        return variants

    if _is_initials_token(last_tok):
        last = " ".join(toks[:-1]).strip()
        if last:
            for v in (f"{last_tok} {last}", f"{last}, {last_tok}"):
                if v.lower() not in {x.lower() for x in variants}:
                    variants.append(v)
        return variants

    return variants


# -----------------------------------------------------------------------------
# Vita-type filter — strict desktop equality (no alias / plural / label
# normalization). Mirrors paperfile/modules/searchdata.py::filter_by_vita_type
# byte-for-byte.
# -----------------------------------------------------------------------------

def passes_vita_type(paper, vita_codes):
    """True if no codes given (no filter), or the paper's ``vitatyp`` is in
    ``vita_codes`` (strict equality, case-sensitive — matches desktop)."""
    if not vita_codes:
        return True
    raw = paper.get("vitatyp")
    if raw is None:
        return False
    return raw in vita_codes


def passes_year_range(paper, year_min, year_max):
    """Backward-compatible per-paper helper. Year inputs are parsed strictly
    (matches desktop's ``get_year_range`` + ``_apply_year_filter``); invalid
    inputs cause the predicate to return ``False`` for every record (matching
    desktop's "block the search" semantics)."""
    yr = parse_year_range_inputs(year_min, year_max)
    if yr is None:
        return False
    return bool(apply_year_filter([paper], yr))


# -----------------------------------------------------------------------------
# Per-search-type matchers — used by the legacy ``passes_search_type`` API.
# Internally just call SearchData methods on a single-element list and check
# whether the record came back, so semantics stay byte-identical to desktop.
# -----------------------------------------------------------------------------

def _author_title_dict_keys(query):
    """Normalize a dict query for author_title to the four desktop inputs."""
    if not isinstance(query, dict):
        return "", "", "", ""
    return (
        (query.get("author") or "").strip(),
        (query.get("optional_author") or "").strip(),
        (query.get("title") or "").strip(),
        (query.get("optional_title") or "").strip(),
    )


def passes_search_type(paper, query, search_type):
    """Per-paper test for ``search_type`` against ``query``. Strict desktop
    semantics; thin wrapper over the corresponding ``SearchData`` method."""
    sd = SearchData([paper])

    if search_type == "author_title":
        if isinstance(query, dict):
            a, oa, t, ot = _author_title_dict_keys(query)
            return bool(sd.fuzzy_search_by_author_title(a, t, oa, ot))
        # Legacy string form: substring in author OR title (kept for tests; not
        # invoked by production app.py anymore).
        q = (str(query) if query is not None else "").strip()
        if not q:
            return True
        return q.lower() in (str(get_authors(paper) or "")
                             + " " + str(get_title(paper) or "")).lower()

    if search_type == "multiple_numbers":
        nums = {x.strip() for x in str(query or "").split(",") if x.strip()}
        if not nums:
            return False
        try:
            return int(str(get_number(paper) or "0")) in {int(n) for n in nums if n.isdigit()}
        except (TypeError, ValueError):
            return False

    if search_type == "keyword":
        q = (str(query) if query is not None else "").strip()
        if not q:
            return False
        return bool(sd.fuzzy_search_by_keyword(q))

    if search_type == "journal_book":
        q = (str(query) if query is not None else "").strip()
        if not q:
            return True  # filter-only retrieval (no text but year/vita)
        return bool(sd.fuzzy_search_by_book_journal(q))

    if search_type == "any_field":
        q = (str(query) if query is not None else "").strip()
        if not q:
            return True
        return bool(sd.fuzzy_search_by_any_field(q))

    if search_type == "year":
        q = (str(query) if query is not None else "").strip()
        if not q:
            return False
        return q == str(get_year(paper) or "").strip()

    if search_type == "number":
        q = (str(query) if query is not None else "").strip()
        if not q:
            return False
        try:
            return int(q) == int(str(get_number(paper) or "0"))
        except (TypeError, ValueError):
            return False

    if search_type == "vita_type":
        q = (str(query) if query is not None else "").strip()
        if not q:
            return False
        return q == str(get_vita_type(paper) or "").strip()

    return False


# -----------------------------------------------------------------------------
# Main entry point: search_papers
# -----------------------------------------------------------------------------

InvalidYearInput = object()  # sentinel returned via log channel; see app.py


def _filter_by_vita_codes_strict(records, vita_codes):
    if not vita_codes:
        return list(records)
    return [r for r in records if r.get("vitatyp") in vita_codes]


def _author_title_with_variants(records, author, opt_author, title, opt_title):
    """Run the desktop author-variants cross-product search, dedup by number."""
    sd = SearchData(records)
    av = author_variants(author)
    oav = author_variants(opt_author)
    seen: set = set()
    out: List[dict] = []
    for a1 in av:
        for a2 in oav:
            res = sd.fuzzy_search_by_author_title(a1, title, a2, opt_title) or []
            for r in res:
                num = str(r.get("number", "")).strip()
                key = num or id(r)
                if key in seen:
                    continue
                seen.add(key)
                out.append(r)
    return out


def search_papers(
    papers,
    query: Union[str, Dict[str, Any]] = "",
    search_type: str = "author_title",
    year_min: Optional[str] = None,
    year_max: Optional[str] = None,
    vita_types: Optional[Iterable[str]] = None,
    year_range: Optional[Dict[str, Any]] = None,
):
    """End-to-end retrieve search, mirroring ``LeftPanel.run_search``.

    Parameters
    ----------
    papers : list of dict
        Records to search over.
    query : str or dict
        - For ``author_title``: dict with keys ``author``, ``optional_author``,
          ``title``, ``optional_title`` (any may be omitted/empty), or a legacy
          string (substring in author OR title).
        - For ``keyword``, ``journal_book``, ``any_field``, ``number``,
          ``vita_type``: a string.
        - For ``year``: the ``query`` string is ignored; desktop Select by Year
          uses only ``year_min`` / ``year_max`` (or ``year_range``).
        - For ``multiple_numbers``: a comma-separated string.
    year_min, year_max : str or None
        Raw year inputs from the form. Parsed via ``parse_year_range_inputs``
        (strict desktop semantics). If invalid, ``search_papers`` returns ``[]``
        without raising — the caller is responsible for displaying an error.
    year_range : dict or None
        Pre-parsed ``parse_year_range_inputs`` output. If supplied, takes
        precedence over ``year_min``/``year_max`` (handy for testing).
    vita_types : iterable of str
        Strict uppercase vita codes (``["J", "B"]``). Empty / None = no filter.
    """
    if year_range is None:
        year_range = parse_year_range_inputs(year_min, year_max)
    if year_range is None:
        return []  # invalid year input -> desktop blocks the search

    sd = SearchData(papers)
    vita_codes = list(vita_types or [])

    if search_type == "author_title":
        if isinstance(query, dict):
            a, oa, t, ot = _author_title_dict_keys(query)
            results = _author_title_with_variants(papers, a, oa, t, ot)
        else:
            q = (str(query) if query is not None else "").strip()
            if not q:
                results = list(papers)
            else:
                # Legacy string form: substring in author OR title. Not used by
                # production (combined "any" box was removed); preserved for
                # callers/tests that still use it.
                ql = q.lower()
                results = [
                    p for p in papers
                    if ql in str(get_authors(p) or "").lower()
                    or ql in str(get_title(p) or "").lower()
                ]
        results = apply_year_filter(results, year_range)
        return _filter_by_vita_codes_strict(results, vita_codes)

    if search_type == "keyword":
        q = (str(query) if query is not None else "").strip()
        if not q:
            results = []
        else:
            results = sd.fuzzy_search_by_keyword(q)
        results = apply_year_filter(results, year_range)
        return _filter_by_vita_codes_strict(results, vita_codes)

    if search_type == "journal_book":
        q = (str(query) if query is not None else "").strip()
        if not q:
            results = list(papers)
        else:
            results = sd.fuzzy_search_by_book_journal(q)
        results = apply_year_filter(results, year_range)
        return _filter_by_vita_codes_strict(results, vita_codes)

    if search_type == "any_field":
        q = (str(query) if query is not None else "").strip()
        if not q:
            results = list(papers)
        else:
            results = sd.fuzzy_search_by_any_field(q)
        results = apply_year_filter(results, year_range)
        return _filter_by_vita_codes_strict(results, vita_codes)

    if search_type == "year":
        # Desktop ``left_panel.py`` "year" branch: ``_apply_year_filter(data,
        # year_range)`` on the full dataset only — no separate text query. The
        # web form never posts ``query_year``; an empty query must still work.
        results = apply_year_filter(list(papers), year_range)
        return _filter_by_vita_codes_strict(results, vita_codes)

    if search_type == "number":
        q = (str(query) if query is not None else "").strip()
        if not q.isdigit():
            return []
        results = sd.search_by_number(int(q), exact=True)
        results = apply_year_filter(results, year_range)
        return _filter_by_vita_codes_strict(results, vita_codes)

    if search_type == "multiple_numbers":
        nums = [x.strip() for x in str(query or "").split(",") if x.strip()]
        if not nums:
            return []
        good = sorted({int(n) for n in nums if n.isdigit()})
        if not good:
            return []
        results = sd.search_by_number_range(good[0], good[-1])
        # search_by_number_range returns the contiguous range; restrict to the
        # exact set the user asked for.
        results = [r for r in results if int(str(r.get("number") or "0")) in set(good)]
        results = apply_year_filter(results, year_range)
        return _filter_by_vita_codes_strict(results, vita_codes)

    if search_type == "vita_type":
        q = (str(query) if query is not None else "").strip()
        if not q:
            results = list(papers)
        else:
            results = [p for p in papers if str(get_vita_type(p) or "").strip() == q]
        results = apply_year_filter(results, year_range)
        return _filter_by_vita_codes_strict(results, vita_codes)

    return []


# -----------------------------------------------------------------------------
# Sort: thin wrapper around desktop SortData
# -----------------------------------------------------------------------------

_SORT_CONFIGS = {
    "number": {
        "number": {"priority": 1, "order": "backward"},
        "authors": {"priority": 2, "order": "forwards"},
        "title": {"priority": 3, "order": "forwards"},
        "bookjour": {"priority": 4, "order": "forwards"},
        "year": {"priority": 5, "order": "backward"},
        "vitatyp": {"priority": 6, "order": "vitord"},
    },
    "author": {
        "authors": {"priority": 1, "order": "forwards"},
        "title": {"priority": 2, "order": "forwards"},
        "bookjour": {"priority": 3, "order": "forwards"},
        "vitatyp": {"priority": 4, "order": "vitord"},
        "year": {"priority": 5, "order": "backward"},
        "location": {"priority": 6, "order": "forwards"},
        "volume": {"priority": 7, "order": "forwards"},
        "pages": {"priority": 8, "order": "forwards"},
        "keyword1": {"priority": 9, "order": "forwards"},
        "keyword2": {"priority": 10, "order": "forwards"},
        "number": {"priority": 11, "order": "backward"},
    },
    "title": {
        "title": {"priority": 1, "order": "forwards"},
        "authors": {"priority": 2, "order": "forwards"},
        "bookjour": {"priority": 3, "order": "forwards"},
        "year": {"priority": 4, "order": "backward"},
        "vitatyp": {"priority": 5, "order": "vitord"},
        "number": {"priority": 6, "order": "backward"},
    },
    "journal_book": {
        "bookjour": {"priority": 1, "order": "forwards"},
        "vitatyp": {"priority": 2, "order": "vitord"},
        "authors": {"priority": 3, "order": "forwards"},
        "title": {"priority": 4, "order": "forwards"},
        "year": {"priority": 5, "order": "backward"},
        "number": {"priority": 6, "order": "backward"},
    },
    "vita_type": {
        "vitatyp": {"priority": 1, "order": "vitord"},
        "year": {"priority": 2, "order": "backward"},
        "authors": {"priority": 3, "order": "forwards"},
        "title": {"priority": 4, "order": "forwards"},
        "bookjour": {"priority": 5, "order": "forwards"},
        "number": {"priority": 6, "order": "backward"},
    },
}


def sort_results(results, sort_by):
    """Sort results using the desktop ``SortData`` engine.

    ``sort_by`` accepts ``number`` / ``author`` / ``title`` / ``journal_book``
    / ``vita_type`` (matching the web form's radio options); anything else
    falls back to the ``number`` config (desktop default).
    """
    cfg = _SORT_CONFIGS.get(sort_by, _SORT_CONFIGS["number"])
    return SortData(list(results or [])).sort_by_criteria(cfg, vita_order_key="vitord1")
