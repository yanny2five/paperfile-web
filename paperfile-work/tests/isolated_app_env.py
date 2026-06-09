"""
Build a temp directory with config.json, .cnt, faculty .cng, and minimal .cnj
so the full Flask app can load every screen without touching the developer machine.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

from modules.utilities_web import write_cnt_new_file


MINIMAL_CNJ = """CLASSCOUNT
1
AgEcon::1>>5

STARTJOURNALS
AgEcon>>Test Journal??10;PCT=50;Q=1;ABDC=A
"""


def _rec(**kwargs: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "location": "",
        "volume": "",
        "pages": "",
        "subject1": "",
        "subject2": "",
        "duplicateoknumber": "0",
        "pdfpresent": "0",
        "pdfpath": "",
    }
    base.update(kwargs)
    return base


def deep_sample_records() -> List[Dict[str, Any]]:
    """Papers that exercise reports (J on known journal, PR funding, dup titles)."""
    return [
        _rec(
            number="10",
            authors="McCarl, B.A. and Other, O.",
            title="Corn futures",
            bookjour="Test Journal",
            year="2019",
            vitatyp="J",
        ),
        _rec(
            number="11",
            authors="McCarl, B.A.",
            title="Water policy note",
            bookjour="Other Journal",
            year="2020",
            vitatyp="J",
        ),
        _rec(
            number="20",
            authors="Smith, J.",
            title="Book chapter text",
            bookjour="Some Press",
            year="2018",
            vitatyp="B",
        ),
        _rec(
            number="30",
            authors="McCarl, B.A.",
            title="NSF proposal alpha",
            bookjour="",
            year="2024",
            vitatyp="PR",
            funding_year="2024",
            total_amount="100000",
            usable_amount="90000",
            decision="Pending",
        ),
        _rec(
            number="31",
            authors="McCarl, B.A.",
            title="Duplicate Title Case",
            bookjour="AJAE",
            year="2021",
            vitatyp="J",
        ),
        _rec(
            number="32",
            authors="Other, O.",
            title="duplicate title case",
            bookjour="AJAE",
            year="2022",
            vitatyp="J",
        ),
    ]


def write_deep_isolated_env(root: str) -> Tuple[str, str]:
    """
    Write fixtures under ``root``. Returns (config_json_path, cnt_path).
    """
    os.makedirs(root, exist_ok=True)
    cnt = os.path.join(root, "deep.cnt")
    cfg = os.path.join(root, "config.json")
    fac = os.path.join(root, "faculty.cng")
    cnj = os.path.join(root, "journals.cnj")

    write_cnt_new_file(cnt, deep_sample_records(), None)

    fac_text = (
        "McCarl, B.A.::Professor;;2020;;150;;none;;-1;;-1;;-1;;-1;;\n"
        "Other, O.::Assoc;;2019;;50;;none;;-1;;-1;;-1;;-1;;\n"
    )
    with open(fac, "w", encoding="utf-8", newline="\n") as f:
        f.write(fac_text)

    with open(cnj, "w", encoding="utf-8", newline="\n") as f:
        f.write(MINIMAL_CNJ)

    payload = {
        "database_path": cnt,
        "faculty_file": fac,
        "journal_definition_file": cnj,
    }
    with open(cfg, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return cfg, cnt
