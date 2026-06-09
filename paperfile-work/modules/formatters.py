def get_field(paper, *possible_keys):
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
    return get_field(paper, "journal", "journal/book", "book", "journal or book")


def get_keywords(paper):
    return get_field(paper, "keywords", "keyword", "key words")


def get_year(paper):
    return get_field(paper, "year", "publication year")


def get_number(paper):
    return get_field(paper, "number", "no", "id", "paper number")


def format_paper(paper, italics=False, omit_number=False, omit_keywords=False):
    parts = []

    number = get_number(paper)
    authors = get_authors(paper)
    title = get_title(paper)
    journal = get_journal(paper)
    year = get_year(paper)
    keywords = get_keywords(paper)

    if not omit_number and number:
        parts.append(f"{number}.")

    if authors:
        parts.append(str(authors))

    if title:
        title_text = str(title)
        if italics:
            title_text = f"<i>{title_text}</i>"
        parts.append(title_text)

    if journal:
        parts.append(str(journal))

    if year:
        parts.append(str(year))

    if not omit_keywords and keywords:
        parts.append(f"Keywords: {keywords}")

    return ", ".join(parts)