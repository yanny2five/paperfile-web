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
    # Keep this close to desktop output ordering/field style.
    parts = []
    number = get_number(paper)
    authors = (get_authors(paper) or "").strip()
    title = (get_title(paper) or "").strip()
    bookjour = (
        get_field(paper, "bookjour", "journal", "journal/book", "book", "journal or book") or ""
    ).strip()
    publication = (get_field(paper, "publication", "publisher", "source", "source1") or "").strip()
    proceedings = (get_field(paper, "proceedings", "conference", "meeting", "conference/proceedings") or "").strip()
    chapter = (get_field(paper, "chapter") or "").strip()
    volume = (get_field(paper, "volume") or "").strip()
    location = (get_field(paper, "location") or "").strip()
    pages = (get_field(paper, "pages", "page") or "").strip()
    year = (get_year(paper) or "").strip()
    keywords = (get_keywords(paper) or "").strip()

    if not omit_number and number:
        parts.append(f"{number}.")
    if authors:
        parts.append(authors)
    if title:
        title_text = title
        if italics:
            title_text = f"<i>{title_text}</i>"
        parts.append(title_text)
    if bookjour:
        parts.append(bookjour)
    if publication:
        parts.append(publication)
    if proceedings:
        parts.append(proceedings)
    chapter_text = chapter
    volume_text = volume
    if not chapter_text and volume_text.lower().startswith("chapter"):
        chapter_text = volume_text
        volume_text = ""
    if chapter_text:
        if chapter_text.lower().startswith("chapter"):
            parts.append(chapter_text)
        else:
            parts.append(f"Chapter {chapter_text}")
    if volume_text:
        parts.append(volume_text)
    if location:
        parts.append(location)
    if pages:
        parts.append(f"page: {pages}")
    if year:
        parts.append(year)
    if not omit_keywords and keywords:
        parts.append(f"Keywords: {keywords}")

    return ", ".join(p for p in parts if p)