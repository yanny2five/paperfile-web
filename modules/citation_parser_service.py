"""
Citation parser service for the web Enter Papers page.

Wraps :mod:`modules.chatgpt_format` to give the web app the same
"paste-a-citation, get pre-filled fields back" workflow that the desktop's
``pages/enterpapers.py`` implements via the "Paste in copied item" button.

Public API:

* :func:`segment_citations_cv_style` -- split CV-pasted text into per-citation
  entry blocks BEFORE sending to GPT (matches desktop heuristics).
* :func:`parse_prepared_citation` -- split one ``" | "``-separated GPT line
  into the 10 standard fields (matches desktop parser).
* :func:`clean_parsed_data` -- run the same suffix/edge/title-case clean-up
  that desktop ``EnterPapersPage.clean_parsed_data`` applies.
* :func:`format_clipboard_text` -- end-to-end: take raw clipboard text, call
  GPT once with the cleaned-but-unsegmented text (GPT segments inside its
  prompt -- same as desktop), then return ``[ {field: value}, ... ]``.

All output dicts use the **internal** record field names that the rest of
the web app expects:

    {
        "authors", "title", "bookjour", "location",
        "volume", "pages", "year", "subject1", "subject2",
        "pdfpath",     # mapped from GPT's "url"
    }

so the caller can drop the dict straight into the Enter Papers form
template (or :func:`modules.correct_papers_service.record_from_enter_form`
for saving).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Segmentation -- pre-process raw clipboard into one block per citation entry.
# Mirrors EnterPapersPage.segment_citations_cv_style and preprocess_clipboard_content.
# ---------------------------------------------------------------------------

_RE_LIST_PREFIX = re.compile(r"^\s*(?:[•\-\u2013\u2014\*]\s+|\(\d+\)\s+|\[\d+\]\s+|\d+\s*[\.\)]\s+)")
_RE_AUTHOR_START = re.compile(r"^\s*[A-Z][A-Za-z\-']+\s*,")
_RE_CONTINUATION = re.compile(
    r"^\s*(?:SJR\s*:|Impact\s*Factor|Selected\s+for|Editor\s+Highlight|https?://|doi\s*:)",
    re.IGNORECASE,
)


def preprocess_clipboard_text(content: str, every_line_carriage_return: bool = False) -> str:
    """Light pre-clean (matches desktop ``preprocess_clipboard_content``):
    strip leading ``[N]\\t`` markers, normalize ``&`` to ``and``, and drop
    blank lines but keep newlines."""
    if not content:
        return ""
    s = re.sub(r"^\[\d+\]\t", "", content, flags=re.MULTILINE)
    s = re.sub(r"&|\\&", "and", s)
    if every_line_carriage_return:
        s = re.sub(r"(?<!\n)\n(?!\n)", " ", s)
        s = re.sub(r"\n\n", "\n", s)
    s = "\n".join(line for line in s.splitlines() if line.strip())
    return s


def segment_citations_cv_style(raw: str) -> List[str]:
    """Split CV-pasted text into citation entry blocks. Returns a list of
    one-or-more-line entry strings. The desktop equivalent feeds the joined
    string back to GPT (which segments again per its prompt), but we expose
    the helper for tests + a future "no-GPT preview" UI."""
    if not raw:
        return []
    lines = raw.splitlines()
    entries: List[str] = []
    buf: List[str] = []

    def _flush() -> None:
        text = "\n".join(buf).strip()
        if text:
            entries.append(text)
        buf.clear()

    for ln in lines:
        s = ln.rstrip()
        if not s.strip():
            if buf:
                buf.append("")
            continue
        starts_new = bool(_RE_LIST_PREFIX.match(s) or _RE_AUTHOR_START.match(s))
        if starts_new:
            if _RE_CONTINUATION.match(s) and buf:
                buf.append(s)
            else:
                _flush()
                buf.append(s)
        else:
            buf.append(s)

    _flush()
    return entries


def strip_entry_leading_prefix(entry: str) -> str:
    """Remove only the leading list prefix (1., 2), [3], ... ) from the FIRST
    non-empty line of one entry."""
    if not entry:
        return entry
    pat = re.compile(r"^\s*(?:[•\-\u2013\u2014\*]\s+|\(\d+\)\s+|\[\d+\]\s+|\d+\s*[\.\)]\s+)\s*")
    out = []
    done = False
    for ln in entry.splitlines():
        if not done and ln.strip():
            out.append(pat.sub("", ln))
            done = True
        else:
            out.append(ln)
    return "\n".join(out).strip()


# ---------------------------------------------------------------------------
# Per-line GPT output parsing -- matches EnterPapersPage.parse_prepared_citation.
# ---------------------------------------------------------------------------

GPT_FIELDS = (
    "authors", "title", "book_or_journal", "location",
    "volume", "pages", "year", "keyword1", "keyword2", "url",
)


def parse_prepared_citation(line: str) -> Dict[str, str]:
    """Split a GPT-formatted citation line (``" | "``-separated, 10 fields)
    into a dict using GPT's field names (``book_or_journal``, ``url``, etc.).
    Excess ``|`` segments are merged into the trailing ``url`` slot to avoid
    silent data loss (same rule as desktop)."""
    parts = [p.strip() for p in (line or "").split("|")]
    if len(parts) > len(GPT_FIELDS):
        head = parts[: len(GPT_FIELDS) - 1]
        tail = parts[len(GPT_FIELDS) - 1:]
        parts = head + [" | ".join(tail).strip()]
    while len(parts) < len(GPT_FIELDS):
        parts.append("")
    return dict(zip(GPT_FIELDS, parts))


# ---------------------------------------------------------------------------
# Clean up parsed dict -- mirrors EnterPapersPage.clean_parsed_data.
# ---------------------------------------------------------------------------

_SUFFIX_PAT = r"(?:Jr\.?|Sr\.?|II|III|IV|V|VI|VII|VIII|IX|X)"


def _normalize_suffix_commas(authors: str) -> str:
    """``Capps, Jr., O.`` -> ``Capps Jr., O.`` (collapse the extra comma after
    a last name + suffix). Applied globally to the authors field."""
    if not authors:
        return ""
    return re.sub(
        rf"\b([A-Z][A-Za-z'\-]+)\s*,\s*({_SUFFIX_PAT})\s*,\s*",
        r"\1 \2, ",
        authors,
    )


def clean_parsed_data(parsed: Dict[str, Any]) -> Dict[str, str]:
    """Apply the desktop ``EnterPapersPage.clean_parsed_data`` rules:

    * ``authors`` -- normalize suffix-comma patterns, then run
      :func:`modules.clean_database.clean_authors_field`.
    * ``book_or_journal`` -- ``clean_edge_symbols`` + ``ascii_only`` + ``title_case``.
    * ``title`` -- ``clean_edge_symbols`` + ``title_case``.
    * Other fields are passed through unchanged (just ``str().strip()``).

    Cleaner failures are swallowed to avoid taking the form down on a single
    funky input -- same conservative behavior as desktop.
    """
    from modules.clean_database import (
        ascii_only,
        clean_authors_field,
        clean_edge_symbols,
        title_case,
    )

    out: Dict[str, str] = {}
    for key, raw in (parsed or {}).items():
        val = "" if raw is None else str(raw).strip()
        if key == "authors":
            val = _normalize_suffix_commas(val)
            try:
                val = clean_authors_field(val)
            except Exception:
                pass
        elif key == "book_or_journal":
            try:
                val = clean_edge_symbols(val)
                val = ascii_only(val)
                val = title_case(val)
            except Exception:
                pass
        elif key == "title":
            try:
                val = clean_edge_symbols(val)
                val = title_case(val)
            except Exception:
                pass
        out[key] = val
    return out


# ---------------------------------------------------------------------------
# Map GPT field names -> internal record field names used by the web app.
# Desktop EnterPapersPage.fill_fields wires these manually; we centralize the
# mapping so the Flask route can hand the dict straight to the form.
# ---------------------------------------------------------------------------

_GPT_TO_INTERNAL = {
    "authors": "authors",
    "title": "title",
    "book_or_journal": "bookjour",
    "location": "location",
    "volume": "volume",
    "pages": "pages",
    "year": "year",
    "keyword1": "subject1",
    "keyword2": "subject2",
    "url": "pdfpath",
}


def to_internal_record(parsed_clean: Dict[str, str]) -> Dict[str, str]:
    """Translate the cleaned GPT dict to the internal record field names
    the Enter Papers / Correct Papers forms understand."""
    out: Dict[str, str] = {}
    for gpt_key, val in (parsed_clean or {}).items():
        if not gpt_key:
            continue
        internal = _GPT_TO_INTERNAL.get(gpt_key)
        if internal:
            out[internal] = val
    return out


# ---------------------------------------------------------------------------
# End-to-end: clipboard text -> list of internal record dicts (one per
# citation found by GPT). This is what the Flask route calls.
# ---------------------------------------------------------------------------

def format_clipboard_text(raw_text: str) -> List[Dict[str, str]]:
    """Run the full pipeline on raw clipboard text:

    1. Light pre-clean (no segmentation -- GPT does that internally, same
       as desktop).
    2. Send the cleaned text to ``format_citations_with_chatgpt``.
    3. Split the response on newlines -> one citation per line.
    4. Parse, clean, and translate each line into an internal record dict.

    Raises:
        ValueError: if the clipboard is empty or GPT returned nothing
            usable.
        RuntimeError: if the OpenAI key is unset or the API call failed
            (the underlying module returns ``None`` in those cases).
    """
    from modules.chatgpt_format import format_citations_with_chatgpt, get_last_openai_error

    cleaned = preprocess_clipboard_text(raw_text or "")
    if not cleaned.strip():
        raise ValueError("Clipboard content is empty after removing blank lines.")

    response = format_citations_with_chatgpt(cleaned)
    if not response:
        detail = (get_last_openai_error() or "").strip()
        if not detail:
            detail = (
                "No response from the OpenAI client. Verify OPENAI_API_KEY or openai_api_key in config.json."
            )
        raise RuntimeError(
            f"ChatGPT returned no output. {detail} "
            "On hosted deployments (e.g. Render), set OPENAI_API_KEY under Environment."
        )

    response = response.strip()
    if not response:
        raise ValueError("ChatGPT returned empty output.")

    lines = [ln.strip() for ln in response.split("\n") if ln.strip()]
    if not lines:
        raise ValueError("ChatGPT returned no parseable citation lines.")

    records: List[Dict[str, str]] = []
    for ln in lines:
        parsed = parse_prepared_citation(ln)
        cleaned_parsed = clean_parsed_data(parsed)
        records.append(to_internal_record(cleaned_parsed))
    return records
