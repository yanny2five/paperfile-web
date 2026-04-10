"""
Publication type counts by year bins — logic aligned with desktop publicationtypereport.py
(hide_listbox / filtered paths).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from modules.extract_names import process_authors

VITA_TYPES = [
    "Total",
    "Journal Articles",
    "Journal not Refereed",
    "Drafts of Journal Articles",
    "Published Abstracts",
    "Books",
    "Book Chapters",
    "Govt/Univ/Research Reports",
    "Invited Papers",
    "Published Proceedings",
    "Unpublished Proceedings",
    "Selected Papers",
    "Posters",
    "Contract Reports",
    "Departmental Papers",
    "Center Papers",
    "Seminar Papers",
    "Book Reviews",
    "Computer Programs and Documentations",
    "Web Sites",
    "Funding Proposals",
    "Extension Publications",
    "Outreach Presentations",
    "Popular Articles",
    "Newsletters",
    "Slides and Video Materials",
    "Class Notes and Materials",
    "Theses",
    "Theses Supervised",
    "Other Misc.",
    "Inactive Draft",
    "No vita type specified",
]

VITA_TYPE_MAPPING = {
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

GROUP_POSITION_MAP = {
    "Professor": ["Professor"],
    "Associate Professor": ["Associate Professor"],
    "Assistant Professor": ["Assistant Professor"],
    "PhD Student": ["PhD Student"],
    "MS Student": ["MS Student"],
    "Undergraduate": ["Undergraduate"],
    "Extension": ["Extension"],
    "University": ["University"],
    "PhD Faculty": ["PhD Faculty"],
    "Research": ["Research"],
    "Joint Appointment": ["Joint Appointment"],
    "Emeritus": ["Emeritus"],
    "Agribusiness": ["Agribusiness"],
    "Former": ["Former"],
    "Teaching": ["Teaching"],
}


def year_bins_from_range(first: int, last: int, inc: int) -> List[Tuple[int, int]]:
    bins: List[Tuple[int, int]] = []
    y = first
    while y + inc - 1 < last:
        bins.append((y, y + inc - 1))
        y += inc
    if y <= last:
        bins.append((y, last))
    return bins


def trimmed_bin_indexes(counts: Dict[str, List[int]], num_bins: int) -> List[int]:
    keep: List[int] = []
    trimming = True
    for i in range(num_bins):
        is_zero = all(counts[vtype][i] == 0 for vtype in counts)
        if trimming and is_zero:
            continue
        trimming = False
        keep.append(i)
    return keep


def _display_name_to_pair(name: str) -> Optional[Tuple[str, str]]:
    if "," not in name:
        return None
    last, first = name.split(",", 1)
    last = last.strip().lower()
    fi = first.strip()[0].lower() if first.strip() else ""
    return (last, fi)


def names_to_target_pairs(names: List[str]) -> Set[Tuple[str, str]]:
    pairs: Set[Tuple[str, str]] = set()
    for name in names:
        p = _display_name_to_pair(name)
        if p:
            pairs.add(p)
    return pairs


def ordered_people_list(faculty_data: List[dict], override_names: List[str]) -> List[str]:
    """Match desktop publicationtypereport ordered listbox when override_names is used."""
    special_names = []
    normal_names = []
    for name in override_names:
        first_char = name.strip()[0] if name.strip() else ""
        if not first_char.isalpha():
            special_names.append(name)
        else:
            normal_names.append(name)

    def sort_key(x: str):
        parts = x.split(",", 1)
        a = parts[0].strip().lower()
        b = parts[1].strip().lower() if len(parts) > 1 else ""
        return (a, b)

    special_sorted = sorted(special_names, key=sort_key)
    normal_sorted = sorted(normal_names, key=sort_key)
    return special_sorted + normal_sorted


def faculty_ordered_names(faculty_data: List[dict]) -> List[str]:
    """Desktop generate_ordered_names when not using override."""
    position_order = [
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
    result = ["All faculty"] + position_order
    professor_related = []
    others = []
    for person in faculty_data:
        name = person.get("name", "")
        positions = person.get("positions", [])
        if any(
            pos in positions
            for pos in ["Professor", "Associate Professor", "Assistant Professor"]
        ):
            professor_related.append(name)
        else:
            others.append(name)
    professor_related = sorted(professor_related)
    others = sorted(others)
    return result + professor_related + others


def resolve_selection_to_pairs(
    selected: str, faculty_data: List[dict]
) -> Tuple[Optional[Set[Tuple[str, str]]], str]:
    """
    Returns (target_pairs, label). None pairs => whole database (no author filter).
    """
    if selected == "__ALL_PAPERS__":
        return None, "All People"

    if selected == "All faculty":
        names = [p["name"] for p in faculty_data]
        return names_to_target_pairs(names), "All faculty"

    if selected in GROUP_POSITION_MAP:
        want = GROUP_POSITION_MAP[selected]
        names = [
            p["name"]
            for p in faculty_data
            if any(pos in p.get("positions", []) for pos in want)
        ]
        return names_to_target_pairs(names), selected

    pairs = names_to_target_pairs([selected])
    return pairs, selected


def compute_publication_type_report(
    papers: List[dict],
    first_year: int,
    last_year: int,
    increment: int,
    target_pairs: Optional[Set[Tuple[str, str]]],
) -> Tuple[List[str], List[List]]:
    """
    Returns (column_headers, rows). Rows are lists of cell values (strings for display).
    """
    year_bins = year_bins_from_range(first_year, last_year, increment)
    num_bins = len(year_bins)
    if num_bins == 0:
        return ["Vita Type", "Total"], []

    base_headers = ["Vita Type", "Total"] + [
        f"{a}-{b}" for a, b in year_bins
    ]

    counts: Dict[str, List[int]] = {
        v: [0] * num_bins for v in VITA_TYPES if v != "Total"
    }

    for record in papers:
        year_str = record.get("year", "")
        if not str(year_str).isdigit():
            continue
        year = int(year_str)
        vitatype_code = str(record.get("vitatyp", "")).strip()
        full_type = VITA_TYPE_MAPPING.get(vitatype_code)
        if not full_type:
            continue

        if target_pairs is not None:
            authors_raw = record.get("authors", "")
            processed, _ = process_authors(authors_raw)
            matched = False
            for name in processed:
                p = _display_name_to_pair(name)
                if p and p in target_pairs:
                    matched = True
                    break
            if not matched:
                continue

        for i, (start, end) in enumerate(year_bins):
            if start <= year <= end:
                if full_type in counts:
                    counts[full_type][i] += 1
                break

    for vtype in VITA_TYPES:
        if vtype != "Total" and vtype not in counts:
            counts[vtype] = [0] * num_bins

    bin_ix = trimmed_bin_indexes(counts, num_bins)
    headers = ["Vita Type", "Total"] + [base_headers[2 + i] for i in bin_ix]

    rows: List[List] = []
    for vtype in VITA_TYPES:
        if vtype == "Total":
            year_totals = [
                sum(counts[vt][i] for vt in counts)
                for i in range(num_bins)
            ]
            year_totals = [year_totals[i] for i in bin_ix]
            total_sum = sum(year_totals)
            rows.append([vtype, total_sum] + year_totals)
        else:
            yc = [counts[vtype][i] for i in bin_ix]
            total = sum(yc)
            if total == 0:
                continue
            rows.append([vtype, total] + yc)

    return headers, rows


def min_year_in_papers(papers: List[dict]) -> int:
    ys = []
    for r in papers:
        y = r.get("year", "")
        if str(y).isdigit() and int(y) > 1900:
            ys.append(int(y))
    return min(ys) if ys else 2000
