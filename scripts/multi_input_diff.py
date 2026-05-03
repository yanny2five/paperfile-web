"""Run every multi-input search path against the live database with desktop
and web logic side-by-side, and report every difference.

Desktop logic is invoked via the byte-identical desktop modules at
``paperfile/modules/searchdata.py`` and the year-range / vita-type wrappers
transcribed from ``paperfile/pages/left_panel.py``. Web logic goes through
``paperfile-web/modules/search_service.py`` exactly as production calls it.

Usage:
    python scripts/multi_input_diff.py [--db data/2025amccarl.cnt]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
REPO_ROOT = os.path.abspath(os.path.join(WEB_ROOT, ".."))
DESKTOP_MOD = os.path.join(REPO_ROOT, "paperfile")

if WEB_ROOT not in sys.path:
    sys.path.insert(0, WEB_ROOT)
if DESKTOP_MOD not in sys.path:
    sys.path.insert(0, DESKTOP_MOD)

from modules.readdata import CNTReader  # noqa: E402  (web reader)
from modules.search_service import (  # noqa: E402
    passes_search_type,
    passes_vita_type,
    passes_year_range,
    search_papers,
)

# Desktop modules (byte-identical via parity guard).
import importlib  # noqa: E402

desktop_searchdata = importlib.import_module("modules.searchdata")
SearchData = desktop_searchdata.SearchData  # type: ignore[attr-defined]


# -----------------------------------------------------------------------------
# Desktop wrappers transcribed from paperfile/pages/left_panel.py
# -----------------------------------------------------------------------------

def _desktop_year_range(first_raw: str, last_raw: str) -> Optional[Dict[str, Any]]:
    """Mirror paperfile/pages/right_panel.py::get_year_range exactly."""
    first_raw = (first_raw or "").strip()
    last_raw = (last_raw or "").strip()
    if not first_raw and not last_raw:
        return {"mode": "empty_only"}
    if not first_raw or not last_raw:
        return None  # invalid -> blocks search
    if not re.fullmatch(r"\d{4}", first_raw) or not re.fullmatch(r"\d{4}", last_raw):
        return None
    fy, ly = int(first_raw), int(last_raw)
    if not (1900 <= fy <= 2100 and 1900 <= ly <= 2100):
        return None
    return {"mode": "range", "first_year": fy, "last_year": ly}


def _desktop_apply_year_filter(records: List[dict], year_range: Optional[dict]) -> List[dict]:
    """Mirror LeftPanel._apply_year_filter exactly."""
    if records is None or year_range is None:
        return []
    mode = year_range.get("mode")
    out = []
    for r in records:
        raw = str(r.get("year", "") or "").strip()
        if mode == "empty_only":
            if raw == "":
                out.append(r)
            continue
        if mode == "range":
            if not re.fullmatch(r"\d{4}", raw):
                continue
            if year_range["first_year"] <= int(raw) <= year_range["last_year"]:
                out.append(r)
    return out


_PAT_INITIALS = re.compile(r"(?:[A-Z]\.){1,}")


def _is_initials_token(t: str) -> bool:
    t = (t or "").strip().replace(" ", "")
    return "." in t and bool(_PAT_INITIALS.fullmatch(t))


def _desktop_author_variants(s: str) -> List[str]:
    """Mirror LeftPanel._author_variants exactly."""
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


def desktop_author_title_search(
    records: List[dict],
    *,
    author: str = "",
    opt_author: str = "",
    title: str = "",
    opt_title: str = "",
    year_first: str = "",
    year_last: str = "",
    vita_codes: Optional[List[str]] = None,
) -> List[dict]:
    """End-to-end mirror of LeftPanel.run_search('author_title')."""
    sd = SearchData(records)
    yr = _desktop_year_range(year_first, year_last)
    if yr is None:
        return []  # desktop blocks the search
    av = _desktop_author_variants(author)
    oav = _desktop_author_variants(opt_author)
    seen: set[str] = set()
    out: List[dict] = []
    for a1 in av:
        for a2 in oav:
            res = sd.fuzzy_search_by_author_title(a1, title, a2, opt_title) or []
            for r in res:
                num = str(r.get("number", "")).strip()
                key = num or str(id(r))
                if key in seen:
                    continue
                seen.add(key)
                out.append(r)
    out = _desktop_apply_year_filter(out, yr)
    if vita_codes:
        out = sd.filter_by_vita_type(out, vita_codes)
    return out


def desktop_keyword_search(
    records, *, keyword: str, year_first: str = "", year_last: str = "",
    vita_codes: Optional[List[str]] = None,
):
    sd = SearchData(records)
    yr = _desktop_year_range(year_first, year_last)
    if yr is None:
        return []
    res = sd.fuzzy_search_by_keyword(keyword)
    res = _desktop_apply_year_filter(res, yr)
    if vita_codes:
        res = sd.filter_by_vita_type(res, vita_codes)
    return res


def desktop_journal_search(
    records, *, journal: str, year_first: str = "", year_last: str = "",
    vita_codes: Optional[List[str]] = None,
):
    sd = SearchData(records)
    yr = _desktop_year_range(year_first, year_last)
    if yr is None:
        return []
    res = sd.fuzzy_search_by_book_journal(journal)
    res = _desktop_apply_year_filter(res, yr)
    if vita_codes:
        res = sd.filter_by_vita_type(res, vita_codes)
    return res


def desktop_anyfield_search(
    records, *, text: str, year_first: str = "", year_last: str = "",
    vita_codes: Optional[List[str]] = None,
):
    sd = SearchData(records)
    yr = _desktop_year_range(year_first, year_last)
    if yr is None:
        return []
    res = sd.fuzzy_search_by_any_field(text)
    res = _desktop_apply_year_filter(res, yr)
    if vita_codes:
        res = sd.filter_by_vita_type(res, vita_codes)
    return res


def desktop_vitatype_search(
    records, *, vita_codes: List[str], year_first: str = "", year_last: str = "",
):
    """LeftPanel.run_search('vitatype'): year filter on entire data, then vita filter."""
    sd = SearchData(records)
    yr = _desktop_year_range(year_first, year_last)
    if yr is None:
        return []
    res = _desktop_apply_year_filter(records, yr)
    res = sd.filter_by_vita_type(res, vita_codes)
    return res


def desktop_year_search(
    records, *, year_first: str, year_last: str,
    vita_codes: Optional[List[str]] = None,
):
    """LeftPanel.run_search('year'): year filter only, then vita."""
    sd = SearchData(records)
    yr = _desktop_year_range(year_first, year_last)
    if yr is None:
        return []
    res = _desktop_apply_year_filter(records, yr)
    if vita_codes:
        res = sd.filter_by_vita_type(res, vita_codes)
    return res


# -----------------------------------------------------------------------------
# Web wrappers — invoke search_service exactly the way app.py does.
# -----------------------------------------------------------------------------

def web_author_title_search(
    records,
    *,
    author: str = "",
    opt_author: str = "",
    title: str = "",
    opt_title: str = "",
    year_first: str = "",
    year_last: str = "",
    vita_codes: Optional[List[str]] = None,
    # Back-compat kwarg names retained for the harness's existing call sites:
    any_text: str = "",
):
    """Web's author/title search using the desktop-shape four-input dict.

    The legacy ``any_text`` kwarg is accepted but ignored — the combined
    "Text to find (author or title)" box was removed for desktop parity.
    """
    if any_text:
        # Combined box no longer exists; harness callers passing any_text
        # should be updated. Treat as inert.
        pass
    q = {
        "author": author or "",
        "optional_author": opt_author or "",
        "title": title or "",
        "optional_title": opt_title or "",
    }
    return search_papers(
        records,
        query=q,
        search_type="author_title",
        year_min=year_first or None,
        year_max=year_last or None,
        vita_types=vita_codes or None,
    )


def web_keyword_search(records, *, keyword, year_first="", year_last="", vita_codes=None):
    return search_papers(records, query=keyword, search_type="keyword",
                         year_min=year_first or None, year_max=year_last or None,
                         vita_types=vita_codes or None)


def web_journal_search(records, *, journal, year_first="", year_last="", vita_codes=None):
    return search_papers(records, query=journal, search_type="journal_book",
                         year_min=year_first or None, year_max=year_last or None,
                         vita_types=vita_codes or None)


def web_anyfield_search(records, *, text, year_first="", year_last="", vita_codes=None):
    return search_papers(records, query=text, search_type="any_field",
                         year_min=year_first or None, year_max=year_last or None,
                         vita_types=vita_codes or None)


def web_vitatype_search(records, *, vita_codes, year_first="", year_last=""):
    # Web's vita_type mode requires a text query, but the form's vita_types
    # filter (Restrict vita types checkbox) is the multi-select equivalent.
    # We model this exactly as production: search_type doesn't matter when
    # using restrict_vita_types -- the form posts search_type=author_title
    # with empty boxes. Replicate that.
    return search_papers(records, query={"any": "", "author": "", "title": ""},
                         search_type="author_title",
                         year_min=year_first or None, year_max=year_last or None,
                         vita_types=vita_codes or None)


def web_year_search(records, *, year_first, year_last, vita_codes=None):
    return search_papers(records, query={"any": "", "author": "", "title": ""},
                         search_type="author_title",
                         year_min=year_first or None, year_max=year_last or None,
                         vita_types=vita_codes or None)


# -----------------------------------------------------------------------------
# Diff helpers
# -----------------------------------------------------------------------------

def _nums(records: List[dict]) -> List[str]:
    return sorted(str(r.get("number", "") or "").strip() for r in records)


def diff_case(label: str, desktop: List[dict], web: List[dict]) -> Tuple[str, int, int, int, int]:
    d, w = set(_nums(desktop)), set(_nums(web))
    only_desktop = sorted(d - w)
    only_web = sorted(w - d)
    status = "OK" if not only_desktop and not only_web else "DIFF"
    return (label, len(d), len(w), len(only_desktop), len(only_web)), only_desktop, only_web  # type: ignore


def print_row(label: str, d_n: int, w_n: int, od: int, ow: int, samples_d: List[str], samples_w: List[str]):
    status = "OK   " if (od == 0 and ow == 0) else "DIFF "
    if od or ow:
        sd = "+desktop_only=" + ",".join(samples_d[:6]) + ("..." if od > 6 else "")
        sw = "+web_only=" + ",".join(samples_w[:6]) + ("..." if ow > 6 else "")
        print(f"  {status} desktop={d_n:>5}  web={w_n:>5}  Δd-only={od:>4}  Δw-only={ow:>4}  | {label}")
        if od:
            print(f"        desktop_only sample: {samples_d[:8]}")
        if ow:
            print(f"        web_only sample:     {samples_w[:8]}")
    else:
        print(f"  {status} desktop={d_n:>5}  web={w_n:>5}                          | {label}")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="data/2025amccarl.cnt")
    args = p.parse_args()

    db_path = os.path.join(WEB_ROOT, args.db) if not os.path.isabs(args.db) else args.db
    reader = CNTReader(db_path)
    reader.reload_data()
    papers = reader.get_data() or []
    n_total = len(papers)
    n_year_empty = sum(1 for r in papers if not str(r.get("year", "") or "").strip())
    print(f"\nDatabase: {db_path}")
    print(f"Total records: {n_total}   Records with empty year field: {n_year_empty}")
    print("BASELINE: text-matching cases use a wide year range (1900-2100) so the")
    print("year filter doesn't dominate the diff. Year-handling cases are reported")
    print("in their own section.\n")

    WIDE = dict(year_first="1900", year_last="2100")

    def run(label, desktop_fn, web_fn):
        d = desktop_fn(papers)
        w = web_fn(papers)
        d_set, w_set = set(_nums(d)), set(_nums(w))
        od = sorted(d_set - w_set)
        ow = sorted(w_set - d_set)
        print_row(label, len(d_set), len(w_set), len(od), len(ow), od, ow)

    print("=" * 80)
    print("§A AUTHOR / TITLE — text-matching (year filter wide-open)")
    print("=" * 80)
    AT = [
        ("author=adams (single word)",
            dict(author="adams", **WIDE),
            dict(author="adams", **WIDE)),
        ("author=adams, title=climate (dual fields)",
            dict(author="adams", title="climate", **WIDE),
            dict(author="adams", title="climate", **WIDE)),
        ("author=adams, opt_author=mearns (4-input shape; AND across boxes)",
            dict(author="adams", opt_author="mearns", **WIDE),
            dict(author="adams", opt_author="mearns", **WIDE)),
        ("title=climate, opt_title=change (4-input shape; AND across boxes)",
            dict(title="climate", opt_title="change", **WIDE),
            dict(title="climate", opt_title="change", **WIDE)),
        ("all 4 desktop boxes filled (author+opt_author / title+opt_title)",
            dict(author="adams", title="climate",
                 opt_author="mearns", opt_title="change", **WIDE),
            dict(author="adams", title="climate",
                 opt_author="mearns", opt_title="change", **WIDE)),
        ("author='B.A. McCarl' — desktop generates name variants; web does not",
            dict(author="B.A. McCarl", **WIDE),
            dict(author="B.A. McCarl", **WIDE)),
        ("author='McCarl, B.A.' (comma form -> desktop variants)",
            dict(author="McCarl, B.A.", **WIDE),
            dict(author="McCarl, B.A.", **WIDE)),
        ("author='McCarl B.A.' (last+initials form -> desktop variants)",
            dict(author="McCarl B.A.", **WIDE),
            dict(author="McCarl B.A.", **WIDE)),
        ("author='Adams' (no initials -> no desktop variants)",
            dict(author="Adams", **WIDE),
            dict(author="Adams", **WIDE)),
        ("title='climate change' (multiword phrase, words in order)",
            dict(title="climate change", **WIDE),
            dict(title="climate change", **WIDE)),
        ("title='change climate' (multiword phrase, words swapped)",
            dict(title="change climate", **WIDE),
            dict(title="change climate", **WIDE)),
    ]
    for label, d_kw, w_kw in AT:
        run(label,
            lambda P, d=d_kw: desktop_author_title_search(P, **d),
            lambda P, w=w_kw: web_author_title_search(P, **w))

    print()
    print("=" * 80)
    print("§B COMBINED 'TEXT TO FIND (AUTHOR OR TITLE)' BOX — REMOVED")
    print("=" * 80)
    print("The web-only combined box was removed for desktop parity. Verify it")
    print("is no longer accepted: any 'any_text' kwarg is silently dropped.")
    print()
    AT2 = [
        ("any='adams' (silently dropped) + title='climate' -> only title constraint",
            dict(title="climate", **WIDE),
            dict(any_text="adams", title="climate", **WIDE)),
        ("any='climate' (silently dropped) + author='adams' -> only author constraint",
            dict(author="adams", **WIDE),
            dict(any_text="climate", author="adams", **WIDE)),
    ]
    for label, d_kw, w_kw in AT2:
        run(label,
            lambda P, d=d_kw: desktop_author_title_search(P, **d),
            lambda P, w=w_kw: web_author_title_search(P, **w))

    print()
    print("=" * 80)
    print("§C YEAR-RANGE BOUNDARY HANDLING")
    print("=" * 80)
    print("These cases isolate the year-filter logic, no other text constraints.")
    print()
    YR = [
        ("both year boxes EMPTY",
            dict(),  # desktop: empty_only mode -> only year-empty records
            dict()),  # web: no filter -> all records
        ("only first year filled (=2015, last='')",
            dict(year_first="2015"),  # desktop: invalid, blocks
            dict(year_first="2015")),  # web: filters >= 2015
        ("only last year filled (first='', last=2018)",
            dict(year_last="2018"),
            dict(year_last="2018")),
        ("non-4-digit year (first='20', last='2020')",
            dict(year_first="20", year_last="2020"),  # desktop: blocks
            dict(year_first="20", year_last="2020")),  # web: int('20')=20
        ("5-digit year (first='20155', last='20200')",
            dict(year_first="20155", year_last="20200"),
            dict(year_first="20155", year_last="20200")),
        ("non-numeric year ('abc', '2020')",
            dict(year_first="abc", year_last="2020"),
            dict(year_first="abc", year_last="2020")),
        ("first > last (=2020, =2015) — invalid range",
            dict(year_first="2020", year_last="2015"),
            dict(year_first="2020", year_last="2015")),
        ("normal range 2015-2020",
            dict(year_first="2015", year_last="2020"),
            dict(year_first="2015", year_last="2020")),
    ]
    for label, d_kw, w_kw in YR:
        run(label,
            lambda P, d=d_kw: desktop_author_title_search(P, **d),
            lambda P, w=w_kw: web_author_title_search(P, **w))

    print()
    print("=" * 80)
    print("§D KEYWORD MODE (desktop: subject1 OR subject2; web: keywords + s1 + s2)")
    print("=" * 80)
    KW = [
        ("keyword=climate",
            dict(keyword="climate", **WIDE),
            dict(keyword="climate", **WIDE)),
        ("keyword='climate change' (multiword phrase)",
            dict(keyword="climate change", **WIDE),
            dict(keyword="climate change", **WIDE)),
        ("keyword='change climate' (words swapped)",
            dict(keyword="change climate", **WIDE),
            dict(keyword="change climate", **WIDE)),
        ("keyword=climate + year 2010-2020",
            dict(keyword="climate", year_first="2010", year_last="2020"),
            dict(keyword="climate", year_first="2010", year_last="2020")),
        ("keyword=climate + vita=[J]",
            dict(keyword="climate", vita_codes=["J"], **WIDE),
            dict(keyword="climate", vita_codes=["J"], **WIDE)),
    ]
    for label, d_kw, w_kw in KW:
        run(label,
            lambda P, d=d_kw: desktop_keyword_search(P, **d),
            lambda P, w=w_kw: web_keyword_search(P, **w))

    print()
    print("=" * 80)
    print("§E JOURNAL / BOOK TITLE")
    print("=" * 80)
    JB = [
        ("journal='AJAE' (single token)",
            dict(journal="AJAE", **WIDE),
            dict(journal="AJAE", **WIDE)),
        ("journal='American Journal' (multiword phrase)",
            dict(journal="American Journal", **WIDE),
            dict(journal="American Journal", **WIDE)),
        ("journal='Journal American' (words swapped)",
            dict(journal="Journal American", **WIDE),
            dict(journal="Journal American", **WIDE)),
        ("journal='AJAE' + year 2015-2020",
            dict(journal="AJAE", year_first="2015", year_last="2020"),
            dict(journal="AJAE", year_first="2015", year_last="2020")),
    ]
    for label, d_kw, w_kw in JB:
        run(label,
            lambda P, d=d_kw: desktop_journal_search(P, **d),
            lambda P, w=w_kw: web_journal_search(P, **w))

    print()
    print("=" * 80)
    print("§F ANY-FIELD (desktop: substring in ANY field; web: AND-of-tokens in concat)")
    print("=" * 80)
    AF = [
        ("any=climate (single word)",
            dict(text="climate", **WIDE),
            dict(text="climate", **WIDE)),
        ("any='climate change' (multiword phrase)",
            dict(text="climate change", **WIDE),
            dict(text="climate change", **WIDE)),
        ("any='change climate' (words swapped)",
            dict(text="change climate", **WIDE),
            dict(text="change climate", **WIDE)),
        ("any='adams climate' (cross-field tokens)",
            dict(text="adams climate", **WIDE),
            dict(text="adams climate", **WIDE)),
        ("any=climate + vita=[J]",
            dict(text="climate", vita_codes=["J"], **WIDE),
            dict(text="climate", vita_codes=["J"], **WIDE)),
    ]
    for label, d_kw, w_kw in AF:
        run(label,
            lambda P, d=d_kw: desktop_anyfield_search(P, **d),
            lambda P, w=w_kw: web_anyfield_search(P, **w))

    print()
    print("=" * 80)
    print("§G VITA-TYPE FILTER (multi-checkbox restrict)")
    print("=" * 80)
    VT = [
        ("vita=[J] only",
            dict(vita_codes=["J"], **WIDE),
            dict(vita_codes=["J"], **WIDE)),
        ("vita=[J,B] union",
            dict(vita_codes=["J", "B"], **WIDE),
            dict(vita_codes=["J", "B"], **WIDE)),
        ("vita=[J] + year 2015-2020",
            dict(vita_codes=["J"], year_first="2015", year_last="2020"),
            dict(vita_codes=["J"], year_first="2015", year_last="2020")),
        ("vita=['j'] (lowercase code) — desktop strict-equality vs web alias",
            dict(vita_codes=["j"], **WIDE),
            dict(vita_codes=["j"], **WIDE)),
        ("vita=['Journal Articles'] (label) — desktop won't match codes; web normalizes",
            dict(vita_codes=["Journal Articles"], **WIDE),
            dict(vita_codes=["Journal Articles"], **WIDE)),
    ]
    for label, d_kw, w_kw in VT:
        run(label,
            lambda P, d=d_kw: desktop_vitatype_search(P, **d),
            lambda P, w=w_kw: web_vitatype_search(P, **w))

    print()
    print("Done.\n")


if __name__ == "__main__":
    main()
