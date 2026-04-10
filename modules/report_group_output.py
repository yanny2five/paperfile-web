"""
Vita / annual / selected-year group output (desktop pages/groupoutput.py on_listbox_select).
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Sequence, Tuple

from modules.extract_names import process_authors
from modules.readdata import get_config_path, read_json_with_guess
from modules.report_year_utils import extract_year_int

VITA_TYPE_NAMES = {
    "J": "Journal Articles",
    "JR": "Journal not Refereed",
    "JD": "Drafts of Journal Articles",
    "PA": "Published Abstracts",
    "B": "Books",
    "BC": "Book Chapters",
    "SB": "Govt/Univ/Research Reports",
    "IP": "Invited Papers",
    "P": "Published Proceedings",
    "U": "Unpublished Proceedings",
    "SP": "Selected Papers",
    "PS": "Posters",
    "F": "Contract Reports",
    "DP": "Departmental Papers",
    "CP": "Center Papers",
    "SM": "Seminar Papers",
    "BR": "Book Reviews",
    "CD": "Computer Programs and Documentations",
    "WS": "Web Sites",
    "PR": "Funding Proposals",
    "EC": "Extension Publications",
    "OP": "Outreach Presentations",
    "PO": "Popular Articles",
    "N": "Newsletters",
    "SV": "Slides and Video Materials",
    "CN": "Class Notes and Materials",
    "TH": "Theses",
    "TS": "Theses Supervised",
    "O": "Other Misc.",
    "OI": "Inactive Draft",
    "MS": "No vita type specified",
}

VITATYPE_ORDER = [
    "J",
    "JR",
    "JD",
    "PA",
    "B",
    "BC",
    "SB",
    "IP",
    "P",
    "U",
    "SP",
    "PS",
    "F",
    "DP",
    "CP",
    "SM",
    "BR",
    "CD",
    "WS",
    "PR",
    "EC",
    "OP",
    "PO",
    "N",
    "SV",
    "CN",
    "TH",
    "TS",
    "O",
    "OI",
    "MS",
]

DEFAULT_VITA_PREFERENCE = [
    "J",
    "PA",
    "B",
    "BC",
    "SB",
    "IP",
    "P",
    "U",
    "SP",
    "PS",
    "DP",
    "CP",
    "SM",
    "BR",
    "CD",
    "EC",
    "OP",
    "PO",
    "N",
    "SV",
    "CN",
    "TH",
    "TS",
    "O",
    "OI",
    "MS",
]


def load_vitatype_preference() -> List[str]:
    path = get_config_path()
    if not path:
        return list(DEFAULT_VITA_PREFERENCE)
    try:
        cfg = read_json_with_guess(path)
        return cfg.get("vitatype_preference", DEFAULT_VITA_PREFERENCE)
    except Exception:
        return list(DEFAULT_VITA_PREFERENCE)


def ordered_people_choices(faculty_data: List[dict]) -> List[str]:
    position_order = [
        "All people",
        "Professor",
        "Associate Professor",
        "Assistant Professor",
        "PhD Student",
        "MS Student",
        "Undergraduate",
        "Extension",
        "University",
        "PhD Faculty",
        "Research",
        "Joint Appointment",
        "Emeritus",
        "Agribusiness",
        "Former",
        "Teaching",
    ]
    professor_related = []
    others = []
    for person in faculty_data or []:
        name = person.get("name", "")
        positions = person.get("positions", [])
        if any(
            pos in positions
            for pos in ["Professor", "Associate Professor", "Assistant Professor"]
        ):
            professor_related.append(name)
        else:
            others.append(name)
    return position_order + sorted(professor_related) + sorted(others)


def _sort_year_val(val) -> int:
    y = extract_year_int(val)
    return y if y is not None else 0


def resolve_names_to_match(
    selected: str,
    faculty_data: List[dict],
    all_people_fallback_names: Optional[Sequence[str]] = None,
) -> List[str]:
    if selected == "All people":
        names = [p["name"] for p in (faculty_data or []) if p.get("name")]
        if names:
            return names
        if all_people_fallback_names:
            return list(all_people_fallback_names)
        return []
    if any(person.get("name") == selected for person in faculty_data or []):
        return [selected]
    return [
        p["name"]
        for p in faculty_data or []
        if selected in p.get("positions", [])
    ]


def generate_group_output(
    all_records: List[dict],
    faculty_data: List[dict],
    selected: str,
    first_year: int,
    last_year: int,
    selected_vita_types: Sequence[str],
    add_ranking: bool,
    norm_ranking: bool,
    journal_info: Optional[dict] = None,
    all_people_fallback_names: Optional[Sequence[str]] = None,
) -> Tuple[str, List[Tuple[str, int]]]:
    journal_info = journal_info or {}
    names_to_match = resolve_names_to_match(
        selected, faculty_data, all_people_fallback_names
    )

    matched_records = []
    for record in all_records:
        y_int = extract_year_int(record.get("year", ""))
        if y_int is None:
            continue
        if not (first_year <= y_int <= last_year):
            continue
        authors_raw = record.get("authors", "")
        parsed_names, _ = process_authors(authors_raw or "")
        if names_to_match and any(tgt in parsed_names for tgt in names_to_match):
            matched_records.append(record)

    sorted_records = sorted(
        [
            r
            for r in matched_records
            if r.get("vitatyp") in selected_vita_types
        ],
        key=lambda r: (
            VITATYPE_ORDER.index(r.get("vitatyp", "MS"))
            if r.get("vitatyp") in VITATYPE_ORDER
            else len(VITATYPE_ORDER),
            -_sort_year_val(r.get("year", "")),
            r.get("authors", ""),
            r.get("title", ""),
        ),
    )

    lines: List[str] = []
    last_type = None
    for record in sorted_records:
        vtype = record.get("vitatyp", "MS")
        if vtype != last_type:
            lines.append("")
            lines.append(VITA_TYPE_NAMES.get(vtype, vtype))
            lines.append("")
            last_type = vtype

        main_chunks: List[str] = []
        pending: List[str] = []
        for k, v in record.items():
            if v is None or v == "0" or v == "":
                continue
            if k in {"number", "vitatyp", "dateentered"}:
                continue
            if k == "bookjour":
                if pending:
                    main_chunks.append(", ".join(pending) + ", ")
                    pending = []
                main_chunks.append(str(v))
                main_chunks.append(", ")
            elif k == "title":
                pending.append(f'"{v}"')
            elif k == "pages":
                pending.append(f"page: {v}")
            else:
                pending.append(str(v))
        if pending:
            main_chunks.append(", ".join(pending))
        main_line = "".join(main_chunks).rstrip().rstrip(",")
        if main_line:
            lines.append(main_line)

        if add_ranking and record.get("bookjour"):
            journal_name = (record.get("bookjour") or "").strip().lower()
            info = journal_info.get(journal_name) if isinstance(journal_info, dict) else None
            if isinstance(info, dict):
                rank_number = info.get("rank", "")
                norm_val = info.get("norm", "")
                sjr_pct = info.get("sjr_pct", "")
                quartile = info.get("quartile", "")
                abdc = info.get("abdc", "")
                parts = []
                rank_to_show = norm_val if norm_ranking else rank_number
                if rank_to_show != "" and rank_to_show is not None:
                    try:
                        rank_display = int(rank_to_show)
                    except Exception:
                        rank_display = rank_to_show
                    if rank_display == 0:
                        rank_display = "1+"
                    parts.append(f"AGECO Rank: {rank_display}")
                if sjr_pct:
                    parts.append(f"SJR(%): {sjr_pct}")
                if quartile:
                    parts.append(f"SJR Quartile: {quartile}")
                if abdc:
                    parts.append(f"ABDC: {abdc}")
                if parts:
                    lines.append(" | ".join(parts))

        lines.append("")

    counts = Counter(
        r["vitatyp"]
        for r in sorted_records
        if r.get("vitatyp") in selected_vita_types
    )
    count_rows: List[Tuple[str, int]] = []
    for vt in selected_vita_types:
        c = counts.get(vt, 0)
        if c:
            count_rows.append((VITA_TYPE_NAMES.get(vt, vt), c))

    body = "\n".join(lines).strip()
    return body, count_rows
