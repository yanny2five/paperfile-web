"""
Parse BibTeX files into CNT-shaped record dicts (from desktop pages/utilities.py).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


def read_text_with_guess(path: str) -> Tuple[str, str]:
    encodings_try = [
        "utf-8",
        "utf-8-sig",
        "gb18030",
        "gbk",
        "big5",
        "cp1252",
        "latin-1",
    ]
    for enc in encodings_try:
        try:
            with open(path, "r", encoding=enc) as f:
                text = f.read()
            return text, enc
        except UnicodeDecodeError:
            continue
    with open(path, "rb") as f:
        data = f.read()
    return data.decode("latin-1", errors="replace"), "latin-1"


def _extract_year_digits(s: Any) -> str:
    raw = str(s or "").strip()
    if not raw:
        return ""
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) >= 4:
        return digits[-4:]
    return digits


def _clean_bib_text(s: Any) -> str:
    t = str(s or "").replace("\r", " ").replace("\n", " ").strip()
    t = t.replace("{", "").replace("}", "")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _parse_bibtex_fields(s: str) -> dict:
    out = {}
    i = 0
    n = len(s)

    def _skip_ws(idx: int) -> int:
        while idx < n and s[idx].isspace():
            idx += 1
        return idx

    def _read_name(idx: int):
        idx = _skip_ws(idx)
        j = idx
        while j < n and (s[j].isalnum() or s[j] in "_-:"):
            j += 1
        return s[idx:j].strip().lower(), j

    def _read_value(idx: int):
        idx = _skip_ws(idx)
        if idx >= n:
            return "", idx
        if s[idx] in ['"', '{']:
            open_ch = s[idx]
            close_ch = '"' if open_ch == '"' else '}'
            idx += 1
            start = idx
            depth = 1 if open_ch == "{" else 0
            while idx < n:
                ch = s[idx]
                if open_ch == "{":
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            val = s[start:idx]
                            return val.strip(), idx + 1
                else:
                    if ch == '"':
                        val = s[start:idx]
                        return val.strip(), idx + 1
                idx += 1
            return s[start:].strip(), n
        j = idx
        while j < n and s[j] not in [",", "\n", "\r"]:
            j += 1
        return s[idx:j].strip(), j

    while i < n:
        i = _skip_ws(i)
        if i >= n:
            break
        name, i2 = _read_name(i)
        if not name:
            break
        i = _skip_ws(i2)
        if i < n and s[i] == "=":
            i += 1
        else:
            nxt = s.find(",", i)
            i = n if nxt < 0 else nxt + 1
            continue
        val, i = _read_value(i)
        out[name] = val
        i = _skip_ws(i)
        if i < n and s[i] == ",":
            i += 1
    return out


def _parse_bibtex_entries(text: str) -> List[dict]:
    entries = []
    i = 0
    n = len(text)

    def _skip_ws(idx: int) -> int:
        while idx < n and text[idx].isspace():
            idx += 1
        return idx

    while True:
        at = text.find("@", i)
        if at < 0:
            break
        i = at + 1
        j = i
        while j < n and (text[j].isalpha() or text[j] in "_"):
            j += 1
        entry_type = text[i:j].strip().lower()
        i = _skip_ws(j)
        if i >= n or text[i] not in "{(":
            continue
        open_ch = text[i]
        close_ch = "}" if open_ch == "{" else ")"
        i += 1
        depth = 1
        start_body = i
        while i < n and depth > 0:
            ch = text[i]
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
            i += 1
        body = text[start_body : i - 1].strip()
        key = ""
        fields_part = body
        comma_pos = body.find(",")
        if comma_pos >= 0:
            key = body[:comma_pos].strip()
            fields_part = body[comma_pos + 1 :].strip()
        fields = _parse_bibtex_fields(fields_part)
        fields["_type"] = entry_type
        fields["_key"] = key
        entries.append(fields)
    return entries


def bib_entry_to_cnt_record(ent: dict) -> dict:
    e_type = str(ent.get("_type", "")).lower().strip()
    title = _clean_bib_text(ent.get("title", ""))
    author = _clean_bib_text(ent.get("author", ""))
    year = _extract_year_digits(ent.get("year", ""))
    bookjour = ""
    if ent.get("journal"):
        bookjour = _clean_bib_text(ent.get("journal", ""))
    elif ent.get("booktitle"):
        bookjour = _clean_bib_text(ent.get("booktitle", ""))
    elif ent.get("publisher"):
        bookjour = _clean_bib_text(ent.get("publisher", ""))
    volume = _clean_bib_text(ent.get("volume", ""))
    number = _clean_bib_text(ent.get("number", ent.get("issue", "")))
    pages = _clean_bib_text(ent.get("pages", ""))
    vitatyp = "O"
    if e_type == "article":
        vitatyp = "J"
    elif e_type in ("inproceedings", "conference", "proceedings"):
        vitatyp = "P"
    elif e_type == "book":
        vitatyp = "B"
    elif e_type in ("incollection",):
        vitatyp = "BC"
    elif e_type in ("techreport", "report"):
        vitatyp = "SB"
    elif e_type in ("phdthesis", "mastersthesis", "thesis"):
        vitatyp = "TH"
    elif e_type in ("unpublished",):
        vitatyp = "U"
    location = ""
    if ent.get("publisher"):
        location = _clean_bib_text(ent.get("publisher", ""))
    elif ent.get("school"):
        location = _clean_bib_text(ent.get("school", ""))
    elif ent.get("address"):
        location = _clean_bib_text(ent.get("address", ""))
    if number and not location:
        location = f"No. {number}"
    return {
        "number": "",
        "authors": author,
        "title": title,
        "bookjour": bookjour,
        "location": location,
        "volume": volume,
        "pages": pages,
        "year": year,
        "vitatyp": vitatyp,
        "subject1": "",
        "subject2": "",
        "duplicateoknumber": "",
        "pdfpresent": "",
        "pdfpath": "",
    }


def parse_bibtex_file_to_records(bib_path: str) -> List[dict]:
    text, _enc = read_text_with_guess(bib_path)
    entries = _parse_bibtex_entries(text)
    records = []
    for ent in entries:
        rec = bib_entry_to_cnt_record(ent)
        if str(rec.get("authors", "")).strip() or str(rec.get("title", "")).strip():
            records.append(rec)
    return records
