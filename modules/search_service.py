import re
import unicodedata

from modules.report_group_output import VITA_TYPE_NAMES


def normalize(value):
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _query_terms(value):
    q = normalize(value)
    if not q:
        return []
    return q.split()


def _contains_all_terms(text, query):
    hay = normalize(text)
    hay_compact = hay.replace(" ", "")
    terms = _query_terms(query)
    if not terms:
        return True
    # Match terms against both space-preserving and space-collapsed text so
    # punctuation/spacing variants (e.g., "Mc Carl" vs "McCarl") still match.
    return all((term in hay) or (term in hay_compact) for term in terms)


def get_field(paper, *possible_keys):
    """
    Return the first matching field from the paper dict, case-insensitive.
    """
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


def get_keyword_search_blob(paper):
    """Haystack for keyword mode: keywords column plus subject1/subject2 (desktop parity)."""
    parts = (
        get_keywords(paper),
        get_field(paper, "subject1", "subject 1"),
        get_field(paper, "subject2", "subject 2"),
    )
    return normalize(" ".join(str(p) for p in parts))


def get_year(paper):
    return get_field(paper, "year", "publication year")


def get_number(paper):
    return get_field(paper, "number", "no", "id", "paper number")


def get_vita_type(paper):
    return get_field(paper, "vitatyp", "vita_type", "vita type", "type")


def _vita_aliases_for(code, label):
    def _last_word_plural_forms(text):
        words = [w for w in text.split() if w]
        if not words:
            return set()
        last = words[-1]
        out = set()
        # Very small, safe inflection set for vita labels.
        if last.endswith("ies") and len(last) > 3:
            out.add(" ".join(words[:-1] + [last[:-3] + "y"]))
        elif last.endswith("s") and len(last) > 1:
            out.add(" ".join(words[:-1] + [last[:-1]]))
        else:
            out.add(" ".join(words[:-1] + [last + "s"]))
            if last.endswith("y") and len(last) > 1:
                out.add(" ".join(words[:-1] + [last[:-1] + "ies"]))
        return {x for x in out if x and x != text}

    code_n = normalize(code)
    label_n = normalize(label)
    out = {code_n, label_n}
    if label_n:
        out.update(_last_word_plural_forms(label_n))
    if str(code).strip().upper() == "J":
        out.update(
            {
                "journal article",
                "journal articles",
                "refereed journal article",
                "refereed journal articles",
                "journals",
            }
        )
    return {x for x in out if x}


def _vita_alias_lookup():
    by_alias = {}
    for code, label in VITA_TYPE_NAMES.items():
        code_u = str(code).strip().upper()
        for alias in _vita_aliases_for(code_u, label):
            by_alias.setdefault(alias, set()).add(code_u)
    return by_alias


def _resolve_selected_vita_codes(selected_values):
    selected_norm = {normalize(v) for v in selected_values if str(v or "").strip()}
    if not selected_norm:
        return set(), set()
    alias_lookup = _vita_alias_lookup()
    codes = set()
    unresolved = set()
    for v in selected_norm:
        hit = alias_lookup.get(v)
        if hit:
            codes.update(hit)
        elif v.upper() in VITA_TYPE_NAMES:
            codes.add(v.upper())
        else:
            unresolved.add(v)
    return codes, unresolved


def _paper_vita_aliases(paper):
    raw = str(get_vita_type(paper) or "").strip()
    code_u = raw.upper()
    label = VITA_TYPE_NAMES.get(code_u, raw)
    aliases = {normalize(raw), normalize(label)}
    if code_u in VITA_TYPE_NAMES:
        aliases.update(_vita_aliases_for(code_u, VITA_TYPE_NAMES[code_u]))
    return {a for a in aliases if a}


def passes_search_type(paper, query, search_type):
    # Author + title (dict): each nonempty term must appear in its field (AND).
    # Both empty => True so search_papers can still narrow by year / vita only.
    if search_type == "author_title" and isinstance(query, dict):
        author_q = query.get("author", "")
        title_q = query.get("title", "")

        author_text = get_authors(paper)
        title_text = get_title(paper)

        author_ok = _contains_all_terms(author_text, author_q)
        title_ok = _contains_all_terms(title_text, title_q)

        return author_ok and title_ok

    # Author + title (legacy string): substring in author OR title; empty => True
    # for year-only / vita-only searches through search_papers.
    if search_type == "author_title" and not isinstance(query, dict):
        terms = _query_terms(query)
        if not terms:
            return True
        combined = f"{get_authors(paper)} {get_title(paper)}"
        return all(t in normalize(combined) for t in terms)

    # Comma-separated numbers; empty / whitespace-only list matches nothing.
    if search_type == "multiple_numbers":
        nums = {x.strip().lower() for x in str(query or "").split(",") if x.strip()}
        if not nums:
            return False
        return normalize(get_number(paper)) in nums

    # Empty query behavior:
    # - text-search modes should allow "filter-only" retrieval (e.g., vita type +
    #   year range with no text entered), same as desktop usage.
    # - exact-id modes (number/year/vita_type) still require text.
    q = normalize(query)
    terms = _query_terms(query)
    if not q:
        return search_type in {"journal_book", "any_field"}

    if search_type == "keyword":
        blob = get_keyword_search_blob(paper)
        return all(t in blob for t in terms)

    if search_type == "journal_book":
        journal_norm = normalize(get_journal(paper))
        journal_compact = journal_norm.replace(" ", "")
        return all((t in journal_norm) or (t in journal_compact) for t in terms)

    if search_type == "year":
        return q == normalize(get_year(paper))

    if search_type == "number":
        return q == normalize(get_number(paper))

    if search_type == "vita_type":
        selected_codes, unresolved = _resolve_selected_vita_codes([query])
        paper_aliases = _paper_vita_aliases(paper)
        paper_code = str(get_vita_type(paper) or "").strip().upper()
        if paper_code in selected_codes:
            return True
        if selected_codes and (paper_aliases & set().union(*[_vita_aliases_for(c, VITA_TYPE_NAMES.get(c, c)) for c in selected_codes])):
            return True
        return bool(unresolved and paper_aliases.intersection(unresolved))

    if search_type == "any_field":
        all_text = " ".join(normalize(v) for v in paper.values())
        return all(t in all_text for t in terms)

    return False


def passes_year_range(paper, year_min, year_max):
    raw = str(get_year(paper)).strip()

    if not raw.isdigit():
        return False if (year_min or year_max) else True

    y = int(raw)

    if year_min:
        try:
            if y < int(year_min):
                return False
        except ValueError:
            pass

    if year_max:
        try:
            if y > int(year_max):
                return False
        except ValueError:
            pass

    return True


def passes_vita_type(paper, vita_types):
    if not vita_types:
        return True

    selected_codes, unresolved = _resolve_selected_vita_codes(vita_types)
    paper_aliases = _paper_vita_aliases(paper)
    paper_code = str(get_vita_type(paper) or "").strip().upper()

    if paper_code in selected_codes:
        return True
    if selected_codes:
        selected_aliases = set()
        for c in selected_codes:
            selected_aliases.update(_vita_aliases_for(c, VITA_TYPE_NAMES.get(c, c)))
        if paper_aliases.intersection(selected_aliases):
            return True
    return bool(unresolved and paper_aliases.intersection(unresolved))


def search_papers(
    papers,
    query="",
    search_type="author_title",
    year_min=None,
    year_max=None,
    vita_types=None
):
    results = []

    for paper in papers:
        if not passes_search_type(paper, query, search_type):
            continue
        if not passes_year_range(paper, year_min, year_max):
            continue
        if not passes_vita_type(paper, vita_types):
            continue
        results.append(paper)

    return results


def sort_results(results, sort_by):
    def sort_value(paper):
        if sort_by == "number":
            return normalize(get_number(paper))
        if sort_by == "author":
            return normalize(get_authors(paper))
        if sort_by == "title":
            return normalize(get_title(paper))
        if sort_by == "vita_type":
            return normalize(get_vita_type(paper))
        if sort_by == "journal_book":
            return normalize(get_journal(paper))
        if sort_by == "year":
            return normalize(get_year(paper))
        return normalize(get_title(paper))

    return sorted(results, key=sort_value)