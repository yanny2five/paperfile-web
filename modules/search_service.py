def normalize(value):
    return str(value or "").strip().lower()


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


def get_year(paper):
    return get_field(paper, "year", "publication year")


def get_number(paper):
    return get_field(paper, "number", "no", "id", "paper number")


def get_vita_type(paper):
    return get_field(paper, "vitatyp", "vita_type", "vita type", "type")


def passes_search_type(paper, query, search_type):
    # 🔥 NEW: special handling for author/title split queries
    if search_type == "author_title" and isinstance(query, dict):
        author_q = normalize(query.get("author", ""))
        title_q = normalize(query.get("title", ""))

        author_text = normalize(get_authors(paper))
        title_text = normalize(get_title(paper))

        author_ok = True if not author_q else author_q in author_text
        title_ok = True if not title_q else title_q in title_text

        return author_ok and title_ok

    # 🔥 fallback: author_title search with string query (search both author and title)
    if search_type == "author_title" and not isinstance(query, dict):
        q = normalize(query)
        if not q:
            return True
        author_text = normalize(get_authors(paper))
        title_text = normalize(get_title(paper))
        return q in author_text or q in title_text

    # 🔥 fallback for normal single query modes
    q = normalize(query)

    if not q:
        return True

    if search_type == "keyword":
        return q in normalize(get_keywords(paper))

    if search_type == "journal_book":
        return q in normalize(get_journal(paper))

    if search_type == "year":
        return q == normalize(get_year(paper))

    if search_type == "number":
        return q == normalize(get_number(paper))

    if search_type == "multiple_numbers":
        nums = {x.strip().lower() for x in str(query).split(",") if x.strip()}
        return normalize(get_number(paper)) in nums

    if search_type == "vita_type":
        return q in normalize(get_vita_type(paper))

    if search_type == "any_field":
        return any(q in normalize(v) for v in paper.values())

    return True


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

    paper_type = normalize(get_vita_type(paper))
    selected = {normalize(v) for v in vita_types}

    # 🔥 exact match
    return paper_type in selected


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