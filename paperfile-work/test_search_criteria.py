# -*- coding: utf-8 -*-
"""
Reference counts for Paperfile web search parity.

Run from this directory (same folder as app.py):
    python test_search_criteria.py

Uses the same database as the Flask app (config.json -> database_path) and the
same logic as modules.search_service.search_papers (what the web app calls).

Paste line for testers:
    Run the desktop reference with: python test_search_criteria.py
    using the same config.json / database file as the web app. In the web UI,
    repeat the searches in the printed table (same modes, fields, and year
    ranges). Compare result counts; they should match.

How to decide "same":
  - Primary: For each line, result count in the web app = COUNT printed here.
  - Secondary: Spot-check one or two cases (e.g. exact number search for 100
    should be one row with that paper number).

Known differences vs desktop SearchData (tkinter):
  - Keyword: web matches the same subject1/subject2 blob as desktop, and also
    any explicit "keywords" column on the record.
  - Partial paper number: web has no partial mode; this script prints desktop
    counts in section 1b using SearchData for comparison only.
  - Vita "Restrict" checkboxes: web sends labels (journal, book, ...); record
    vitatyp is a code (J, B, ...). Section 8 uses vita_type text mode and
    vita_types code list to match search_service, not the broken checkbox path.
"""

from __future__ import annotations

from modules.readdata import CNTReader
from modules.search_service import get_number, search_papers
from modules.searchdata import SearchData


def _count(results: list) -> int:
    return len(results)


def _numbers_csv(results: list, limit: int = 3) -> str:
    nums = [str(get_number(p)).strip() for p in results[:limit]]
    return ", ".join(nums) if nums else "(none)"


def _range_to_multiple_numbers_query(lo: int, hi: int) -> str:
    """Web has no number-range mode; multiple_numbers with a comma list is equivalent."""
    return ",".join(str(i) for i in range(lo, hi + 1))


def main() -> None:
    reader = CNTReader()
    papers = reader.get_data()
    db_path = reader.file_path or "(unknown)"
    sd = SearchData(papers)

    print("=" * 80)
    print("Paperfile search reference (WEB-IDENTICAL: search_service.search_papers)")
    print(f"Database: {db_path}")
    print(f"Records:  {len(papers)}")
    print("=" * 80)

    # --- 1 Exact by number ---
    print("\n#1  By number (exact) - web: Select by Number")
    for n in (1, 5, 10, 100):
        r = search_papers(papers, query=str(n), search_type="number")
        print(f"    number={n!r}  COUNT={_count(r)}  first_numbers={_numbers_csv(r)}")

    # --- 1b Partial (desktop only) ---
    print("\n#1b By number (partial) - DESKTOP SearchData only (web has no partial mode)")
    for n in (1, 5, 10, 100):
        r = sd.search_by_number(n, exact=False)
        print(f"    partial={n!r}  COUNT={_count(r)}")

    # --- 2 Number range (via multiple_numbers) ---
    print("\n#2  Number range - web: Select multiple papers by Number (comma-separated)")
    for lo, hi in ((1, 5), (10, 20), (50, 100)):
        q = _range_to_multiple_numbers_query(lo, hi)
        r = search_papers(papers, query=q, search_type="multiple_numbers")
        print(f"    range {lo}-{hi}  COUNT={_count(r)}  first_numbers={_numbers_csv(r)}")

    # --- 3 Year range ---
    print("\n#3  Year range - web: Author/Title mode, empty author & title, set First/Last year")
    for ymin, ymax in ((2020, 2023), (2015, 2020), (2010, 2025)):
        r = search_papers(
            papers,
            query={"author": "", "title": ""},
            search_type="author_title",
            year_min=str(ymin),
            year_max=str(ymax),
        )
        print(f"    years {ymin}-{ymax}  COUNT={_count(r)}  first_numbers={_numbers_csv(r)}")

    # --- 4 Author / title (substring, AND) ---
    print("\n#4  Author / title - web: Select by Author and/or Title")
    cases = [
        ("Smith", ""),
        ("", "learning"),
        ("Smith", "learning"),
        ("John", "network"),
    ]
    for author, title in cases:
        r = search_papers(
            papers,
            query={"author": author, "title": title},
            search_type="author_title",
        )
        print(
            f"    author={author!r} title={title!r}  COUNT={_count(r)}  first_numbers={_numbers_csv(r)}"
        )

    # --- 5 Keyword ---
    print("\n#5  Keyword - web: Select by keyword (matches keywords / keyword fields)")
    for kw in ("machine", "data", "network", "algorithm", "learning"):
        r = search_papers(papers, query=kw, search_type="keyword")
        print(f"    keyword={kw!r}  COUNT={_count(r)}  first_numbers={_numbers_csv(r)}")

    # --- 6 Book / journal ---
    print("\n#6  Book/journal - web: Select by book or journal title")
    for text in ("IEEE", "Science", "Nature", "ACM", "Journal"):
        r = search_papers(papers, query=text, search_type="journal_book")
        print(f"    text={text!r}  COUNT={_count(r)}  first_numbers={_numbers_csv(r)}")

    # --- 7 Any field ---
    print("\n#7  Any field - web: Select for text in any field")
    for text in ("neural", "quantum", "blockchain", "2023", "prediction"):
        r = search_papers(papers, query=text, search_type="any_field")
        print(f"    text={text!r}  COUNT={_count(r)}  first_numbers={_numbers_csv(r)}")

    # --- 8 Vita type (codes) ---
    print("\n#8  Vita type - web: Select by Vita Type (substring on vitatyp code)")
    codes = ("B", "BC", "BR", "CD", "CN")
    for code in codes:
        r = search_papers(papers, query=code, search_type="vita_type")
        print(f"    vita query={code!r}  COUNT={_count(r)}  first_numbers={_numbers_csv(r)}")

    print("\n#8c Combined B + BC + BR - web equivalent: restrict by codes (see note below)")
    r = search_papers(
        papers,
        query={"author": "", "title": ""},
        search_type="author_title",
        vita_types=["B", "BC", "BR"],
    )
    print(f"    vita_types=['B','BC','BR'] (AND year unrestricted)  COUNT={_count(r)}")
    print(f"    first_numbers={_numbers_csv(r)}")

    print("\n" + "-" * 80)
    print(
        "NOTE: Web 'Restrict vita types' checkboxes send names (journal, book, ...) but\n"
        "records use codes (J, B, ...), so counts may NOT match #8c until the UI sends codes.\n"
        "Script section #8/#8c uses search_service exactly; use Vita Type text mode for #8."
    )
    print("-" * 80)


if __name__ == "__main__":
    main()
