import re
from typing import List, Tuple


def process_authors(raw_authors: str) -> Tuple[List[str], List[str]]:
    """
    Strictly extract author names based on database formatting rules:
    1. First comma separates Last, First of first author
    2. Remaining commas separate different authors
    3. "and" indicates last author
    """
    debug_log = []
    results = []

    try:
        debug_log.append(f"[INPUT] Raw: {repr(raw_authors)}")
        if not raw_authors.strip():
            return [], debug_log

        # Step 1: Locate the first comma → First author
        first_comma_idx = raw_authors.find(',')
        if first_comma_idx == -1:
            debug_log.append("[WARNING] No comma found, treating as one author.")
            authors = [(raw_authors.strip(), "")]  # Lastname, no firstname
        else:
            # Step 2: Get first author's Last, First
            last = raw_authors[:first_comma_idx].strip()
            rest = raw_authors[first_comma_idx + 1:].lstrip()

            # Step 3: Find where the first author's FirstName ends
            match = re.match(r'(.+?)(?:, |, and )', rest)
            if match:
                first = match.group(1).strip()
                remaining = rest[match.end():]
            else:
                first = rest.strip()
                remaining = ""

            authors = [(last, first)]

            # Step 4: Split remaining part by ", " and handle "and"
            if remaining:
                parts = re.split(r',\s*', remaining)
                for part in parts:
                    part = part.strip()
                    if part.startswith('and '):
                        part = part[4:].strip()
                    if part:
                        authors.append(part)

        # Step 5: Handle suffixes and complex last names
        final_names = []
        suffixes = {"jr.", "sr.", "ii.", "iii.", "iv.", "v."}
        compound_lastname_prefixes = {"von", "van", "de", "del", "la", "de la"}

        standardized_authors = []

        for author in authors:
            if isinstance(author, tuple):
                # Already (last, first) from the first author
                last_name, first_name = author
            else:
                tokens = author.split()
                if not tokens:
                    continue

                # Only one token, weird case
                if len(tokens) == 1:
                    last_name = tokens[0]
                    first_name = ""
                else:
                    # Detect suffix
                    if tokens[-1].lower() in suffixes and len(tokens) >= 2:
                        last_name = tokens[-2] + ' ' + tokens[-1]
                        first_name = ' '.join(tokens[:-2])
                    # Detect compound last name
                    elif len(tokens) >= 2 and tokens[-2].lower() in compound_lastname_prefixes:
                        last_name = tokens[-2] + ' ' + tokens[-1]
                        first_name = ' '.join(tokens[:-2])
                    else:
                        last_name = tokens[-1]
                        first_name = ' '.join(tokens[:-1])

            standardized_authors.append((last_name.strip(), first_name.strip()))

        # Step 6: Sort by last name, then first name
        sorted_authors = sorted(standardized_authors, key=lambda x: (
            x[0].lower(),  # last name
            x[1].lower()   # first name
        ))

        # Step 7: Reconstruct "Last, First" strings
        # Remove periods from the first-name / initials part only,
        # while keeping last name unchanged for strict matching.
        for last, first in sorted_authors:
            if first:
                normalized_first = first.replace(".", "")
                normalized_first = normalized_first.replace(" ", "")
                formatted = f"{last}, {normalized_first}"
            else:
                formatted = f"{last}"
            final_names.append(formatted)

        debug_log.append(f"[OUTPUT] {final_names}")
        return final_names, debug_log

    except Exception as e:
        debug_log.append(f"[ERROR] {str(e)}")
        return [], debug_log


def get_all_formatted_names(records: List[dict]) -> List[str]:
    """
    Extract all unique author names from a list of records,
    format them as "Last, First", and return a sorted list.

    Special character names are listed first.
    """
    all_names = set()

    for record in records:
        raw_authors = record.get("authors", "")
        if raw_authors:
            names, _ = process_authors(raw_authors)
            all_names.update(names)

    # Separate names: special character first
    special_names = []
    normal_names = []
    for name in all_names:
        first_char = name.strip()[0] if name.strip() else ''
        if not first_char.isalpha():
            special_names.append(name)
        else:
            normal_names.append(name)

    # Sort both groups separately
    special_names.sort(
        key=lambda x: (x.split(',', 1)[0].strip().lower(), x.split(',', 1)[1].strip().lower() if ',' in x else ''))
    normal_names.sort(
        key=lambda x: (x.split(',', 1)[0].strip().lower(), x.split(',', 1)[1].strip().lower() if ',' in x else ''))

    # Merge and return
    return special_names + normal_names


def _preprocess_input(text: str) -> str:
    """Clean input while preserving initials punctuation."""
    text = re.sub(r'\b(?:et\.?al|others?|unknown|n/a)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+and\s+', ', ', text, flags=re.IGNORECASE)
    return re.sub(r'([,;])\s*(?=,)', '', text).strip(' ,;')


def _split_authors(text: str) -> List[str]:
    """Split authors while preserving suffixes."""
    protected = re.sub(r"\b(Jr\.|Sr\.|II|III|IV|V)\b", r"###\1", text)
    split_parts = [
        a.replace("###", "").strip()
        for a in re.split(r',\s*(?![A-Z]\.)', protected)
        if a.strip()
    ]
    return split_parts


def _merge_initials(authors: List[str], debug_log: list) -> List[str]:
    """Merge initials with previous author segments."""
    merged = []
    previous = None
    for author in authors:
        if not previous:
            previous = author
            continue
        if re.fullmatch(r'^([A-Z]\.)+$', author):
            merged_author = f"{previous}, {author}"
            debug_log.append(f"[MERGE] {previous} + {author} → {merged_author}")
            previous = merged_author
        else:
            merged.append(previous)
            previous = author
    if previous:
        merged.append(previous)
    return merged


def _process_author(author: str) -> str:
    """Process individual author strings with suffix handling like Jr., Sr., III"""
    suffixes = {"jr.", "sr.", "ii", "iii", "iv", "v"}
    if ',' in author:
        parts = [p.strip() for p in author.split(',', 1)]
        if parts[1].lower() in suffixes:
            result = f"{parts[0]} {parts[1]}"
        else:
            result = f"{parts[0]}, {_format_initials(parts[1])}" if len(parts) > 1 else parts[0]
    else:
        components = author.split()
        last_component = components[-1].lower()
        if last_component in suffixes:
            last_name = f"{components[-2]} {components[-1]}"
            first_part = ' '.join(components[:-2])
        else:
            last_name = _find_last_name(components)
            first_part = ' '.join(components[:components.index(last_name)]) if last_name in components else ''
        result = f"{last_name}, {_format_initials(first_part)}" if last_name else author

    result = re.sub(r'^[^A-Za-z]+', '', result)
    return result


def _find_last_name(components: List[str]) -> str:
    """Identify last name using linguistic patterns."""
    for comp in reversed(components):
        if re.search(r'[a-z]', comp):
            return comp
    return components[-1] if components else ''


def _format_initials(initials: str) -> str:
    """Remove spaces inside initials while preserving dots."""
    return initials.replace(" ", "").strip()
