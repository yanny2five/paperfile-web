import io
import os
import platform
import subprocess

# Vitatyp to verbose mapping
vita_type_mapping = {
    "J": "Journal Articles", "JD": "Drafts of Journal Articles", "PA": "Published Abstracts",
    "B": "Books", "BC": "Book Chapters", "SB": "Govt/Univ/Research Reports",
    "IP": "Invited Papers", "P": "Published Proceedings", "U": "Unpublished Proceedings",
    "SP": "Selected Papers", "PS": "Posters", "F": "Contract Reports",
    "DP": "Departmental Papers", "CP": "Center Papers", "SM": "Seminar Papers",
    "BR": "Book Reviews", "CD": "Computer Programs and Documentations", "WS": "Web Sites",
    "PR": "Funding Proposals", "EC": "Extension Publications", "OP": "Outreach Presentations",
    "PO": "Popular Articles", "N": "Newsletters", "SV": "Slides and Video Materials",
    "CN": "Class Notes and Materials", "TH": "Theses", "TS": "Theses Supervised",
    "O": "Other Misc.", "OI": "Inactive Draft", "MS": "No vita type specified"
}

# Minimal BibTeX type mapping
bibtex_type_map = {
    "J": "article", "JD": "article", "PA": "article",
    "B": "book", "BC": "incollection",
    "SB": "techreport", "F": "techreport",
    "P": "inproceedings", "IP": "inproceedings", "U": "inproceedings",
    "PR": "techreport", "DP": "techreport", "CP": "techreport",
    "TH": "phdthesis", "TS": "phdthesis",
    "CD": "manual", "WS": "misc",
    "BR": "misc", "PS": "misc", "SP": "misc",
    "SM": "misc", "EC": "misc", "OP": "misc", "PO": "misc", "N": "misc", "SV": "misc", "CN": "misc",
    "O": "misc", "OI": "misc", "MS": "misc"
}


def open_folder(file_path):
    folder = os.path.dirname(file_path)
    if platform.system() == "Windows":
        os.startfile(folder)
    elif platform.system() == "Darwin":
        subprocess.run(["open", folder])
    else:
        subprocess.run(["xdg-open", folder])


_XLSX_FIELDS = [
    "number",
    "authors",
    "title",
    "bookjour",
    "location",
    "volume",
    "pages",
    "year",
    "vitatyp",
    "subject1",
    "subject2",
    "pdfpresent",
    "pdfpath",
]


def _records_for_xlsx(records):
    return [{k: v for k, v in r.items() if k in _XLSX_FIELDS} for r in records]


def generate_xlsx_bytes(records):
    """Build an Excel workbook in memory (for web download)."""
    if not records:
        return b""
    import pandas as pd

    filtered = _records_for_xlsx(records)
    df = pd.DataFrame(filtered)
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def export_to_xlsx(records):
    from tkinter import filedialog, messagebox

    if not records:
        messagebox.showwarning("Warning", "No records to export.")
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
    )
    if not file_path:
        return

    try:
        data = generate_xlsx_bytes(records)
        with open(file_path, "wb") as f:
            f.write(data)
        open_folder(file_path)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to export: {e}")

def _clean_bib_value(v):
    """
    Clean BibTeX field value to reduce formatting issues:
    - Convert to string
    - Collapse whitespace
    - Remove outer newlines
    """
    s = "" if v is None else str(v)
    s = s.replace("\r", " ").replace("\n", " ").strip()
    while "  " in s:
        s = s.replace("  ", " ")
    return s


def _to_bibtex_author(authors_raw: str) -> str:
    """
    Convert internal authors string to BibTeX 'author' field.
    BibTeX expects authors separated by ' and '.

    Supported common internal separators:
    - ';'  -> ' and '
    - '|'  -> ' and '
    - ' & ' -> ' and '
    """
    s = _clean_bib_value(authors_raw)
    if not s:
        return ""

    # Normalize separators to semicolon first
    s = s.replace(" & ", ";")
    s = s.replace("|", ";")

    # If it already contains ' and ', assume it's BibTeX-ready
    if " and " in s:
        return s

    # Split on ';' and re-join with ' and '
    parts = [p.strip() for p in s.split(";") if p.strip()]
    if not parts:
        return ""

    return " and ".join(parts)


def generate_bibtex_key(record):
    lastname = record.get("authors", "").split(",")[0].strip().replace(" ", "")
    number = record.get("number", "").strip()
    title_words = record.get("title", "").split()
    first_word = title_words[0] if title_words else "untitled"
    last_word = title_words[-1] if len(title_words) > 1 else first_word
    year = record.get("year", "").strip()
    return f"{lastname}{number}{first_word}{last_word}{year}"


def generate_bibtex_string(records):
    """
    Serialize records to a BibTeX document (for web download or file save).
    Same field mapping as export_to_bibtex.
    """
    if not records:
        return ""

    chunks = []
    for record in records:
        bib_type = bibtex_type_map.get(record.get("vitatyp", ""), "misc")
        bib_key = generate_bibtex_key(record)

        title = _clean_bib_value(record.get("title", ""))
        author = _to_bibtex_author(record.get("authors", ""))
        year = _clean_bib_value(record.get("year", ""))
        volume = _clean_bib_value(record.get("volume", ""))
        pages = _clean_bib_value(record.get("pages", ""))
        address = _clean_bib_value(record.get("location", ""))
        url = _clean_bib_value(record.get("pdfpath", ""))
        bookjour = _clean_bib_value(record.get("bookjour", ""))

        chunks.append(f"@{bib_type}{{{bib_key},\n")

        if author:
            chunks.append(f"  author = {{{author}}},\n")
        if title:
            chunks.append(f"  title = {{{title}}},\n")

        if bib_type == "article":
            if bookjour:
                chunks.append(f"  journal = {{{bookjour}}},\n")
        elif bib_type in ("inproceedings", "incollection"):
            if bookjour:
                chunks.append(f"  booktitle = {{{bookjour}}},\n")
        elif bib_type == "book":
            if bookjour:
                chunks.append(f"  publisher = {{{bookjour}}},\n")
        else:
            if bookjour:
                chunks.append(f"  howpublished = {{{bookjour}}},\n")

        if year:
            chunks.append(f"  year = {{{year}}},\n")
        if volume:
            chunks.append(f"  volume = {{{volume}}},\n")
        if pages:
            chunks.append(f"  pages = {{{pages}}},\n")
        if address:
            chunks.append(f"  address = {{{address}}},\n")
        if url:
            chunks.append(f"  url = {{{url}}},\n")

        chunks.append("}\n\n")

    return "".join(chunks)


def export_to_bibtex(records):
    """
    Export records to BibTeX using standard field names similar to Google Scholar.
    Key changes:
    - authors -> author (BibTeX standard, joined by ' and ')
    - bookjour -> journal (for article) OR booktitle (for inproceedings/incollection)
    - location -> address
    - pdfpath -> url
    - DO NOT export internal record 'number' as BibTeX 'number' (issue). It is an internal id.
    - DO NOT export 'vitatyp' as note by default (Scholar usually does not include it).
    """
    from tkinter import filedialog, messagebox

    if not records:
        messagebox.showwarning("Warning", "No records to export.")
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".bib",
        filetypes=[("BibTeX files", "*.bib"), ("All files", "*.*")]
    )
    if not file_path:
        return

    try:
        text = generate_bibtex_string(records)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
        open_folder(file_path)

    except Exception as e:
        messagebox.showerror("Error", f"Failed to export: {e}")
