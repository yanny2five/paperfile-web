"""
In-place .cnj editor service for paperfile-web.

This module is the web's analogue of the desktop's class definition + journal
editing dialogs (``pages/classifyjournals.py``, ``pages/journalclasses.py``,
``pages/rankrangeeditor.py``, ``pages/journalnamemapper.py``). The full
desktop dialogs are ~10 kloc of Tkinter glue; this service ports the
*authoritative* on-disk format so the user can:

1. View every class definition (CLASSCOUNT block) with its sort order and
   ``norm`` value.
2. Edit, reorder, add, or delete class definitions in place.
3. View every journal line (everything after STARTJOURNALS) with its
   class / rank / SJR pct / Q / ABDC.
4. Edit, add, or delete journal entries.
5. Save back to the original .cnj path while preserving the file header
   (every line above CLASSCOUNT) and the encoding the desktop reader
   detected. A timestamped backup is written next to the file before
   overwriting (matches the desktop's own dialog).

The format is documented in ``readdata.CNTReader.read_journal_definition``:

    <free header lines>
    CLASSCOUNT
    N
    Major1::sort_order>>norm_part
    Major2::sort_order>>norm_part
    ...
    STARTJOURNALS
    Major::Minor>>Journal Name??rank;PCT=...;Q=...;ABDC=...
    ...

This service deliberately preserves any unknown lines between blocks so a
hand-curated .cnj that has comments/extra metadata is not destroyed by a
round-trip through the web UI.
"""

from __future__ import annotations

import datetime
import os
import re
import shutil
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

from modules.readdata import read_text_with_guess


# --- Parsing --------------------------------------------------------------


_CLASS_LINE_RE = re.compile(r"^(?P<major>[^:]+)::(?P<order>-?\d+)>>(?P<norm>.+)$")
_JOURNAL_LINE_RE = re.compile(r"^(?P<class>.+?)>>(?P<name>.+?)\?\?(?P<rest>.+)$")


def _parse_classes_block(class_lines: List[str]) -> List[Dict[str, Any]]:
    classes: List[Dict[str, Any]] = []
    for raw in class_lines:
        s = raw.rstrip("\r\n")
        if not s.strip():
            continue
        m = _CLASS_LINE_RE.match(s.strip())
        if not m:
            continue
        major = m.group("major").strip()
        try:
            order = int(m.group("order").strip())
        except ValueError:
            order = 0
        norm_raw = m.group("norm").strip()
        norm_clean = norm_raw.replace("zz", "").strip()
        try:
            norm = int(norm_clean) if norm_clean else 0
        except ValueError:
            norm = 0
        classes.append(
            {
                "major": major,
                "sort_order": order,
                "norm": norm,
                "norm_raw": norm_raw,  # preserve original suffix (e.g. "10zz")
            }
        )
    return classes


def _parse_journal_line(line: str) -> Optional[Dict[str, Any]]:
    s = line.strip()
    if not s or ">>" not in s or "??" not in s:
        return None
    m = _JOURNAL_LINE_RE.match(s)
    if not m:
        return None
    class_part = m.group("class").strip()
    name = m.group("name").strip()
    rest = m.group("rest").strip()
    parts = [p.strip() for p in rest.split(";") if p.strip()]
    rank_str = parts[0] if parts else "10"
    if not rank_str.isdigit():
        digits = "".join(ch for ch in rank_str if ch.isdigit())
        rank_str = digits if digits else "10"
    pct = quart = abdc = ""
    for tok in parts[1:]:
        up = tok.upper()
        if up.startswith("PCT="):
            pct = tok.split("=", 1)[1].strip()
        elif up.startswith("Q="):
            quart = tok.split("=", 1)[1].strip()
        elif up.startswith("ABDC="):
            abdc = tok.split("=", 1)[1].strip()
    if "::" in class_part:
        major, minor = (p.strip() for p in class_part.split("::", 1))
    else:
        major, minor = class_part, ""
    return {
        "major": major,
        "minor": minor,
        "name": name,
        "rank": rank_str,
        "pct": pct,
        "quartile": quart,
        "abdc": abdc,
    }


def parse_cnj_file(path: str) -> Dict[str, Any]:
    """Parse a .cnj file at ``path`` into a dict ``{header, classes, journals, encoding, eol}``.

    - ``header`` is every line that appears BEFORE ``CLASSCOUNT`` (raw lines
      with their newlines stripped — the writer adds ``\\n`` back).
    - ``classes`` is a list of class dicts (see :func:`_parse_classes_block`).
    - ``journals`` is a list of journal dicts (see :func:`_parse_journal_line`).
    - ``encoding`` is the encoding the file was decoded with (carried so
      the writer can round-trip without altering byte semantics).
    - ``eol`` is the dominant line ending observed in the source file
      (``"\\r\\n"`` if any CR is seen, else ``"\\n"``).
    """
    if not path or not os.path.isfile(path):
        raise FileNotFoundError(path)
    raw_path, enc, lines = read_text_with_guess(path)
    # `read_text_with_guess` opens the file in text mode, which transparently
    # converts \r\n -> \n. To detect the on-disk EOL we must re-read the
    # raw bytes and look for at least one CR-LF pair.
    eol = "\n"
    try:
        with open(path, "rb") as _f:
            head = _f.read(65536)
        if b"\r\n" in head:
            eol = "\r\n"
    except Exception:
        pass
    norm_lines = [ln.rstrip("\r\n") for ln in lines]
    classcount_idx = -1
    startjournals_idx = -1
    for i, ln in enumerate(norm_lines):
        if ln.strip() == "CLASSCOUNT":
            classcount_idx = i
        elif ln.strip() == "STARTJOURNALS":
            startjournals_idx = i
    if classcount_idx == -1 or startjournals_idx == -1:
        raise ValueError("Missing CLASSCOUNT or STARTJOURNALS in .cnj file")

    header_lines = norm_lines[:classcount_idx]
    count_line = norm_lines[classcount_idx + 1].strip() if (classcount_idx + 1) < len(norm_lines) else "0"
    try:
        n = int(count_line)
    except ValueError:
        n = 0
    class_lines = norm_lines[classcount_idx + 2 : classcount_idx + 2 + n]
    classes = _parse_classes_block(class_lines)

    # Anything between the end of class block and STARTJOURNALS (rare but possible)
    interlude_lines = norm_lines[classcount_idx + 2 + n : startjournals_idx]
    journals: List[Dict[str, Any]] = []
    for ln in norm_lines[startjournals_idx + 1 :]:
        parsed = _parse_journal_line(ln)
        if parsed:
            journals.append(parsed)

    return {
        "header": header_lines,
        "classes": classes,
        "interlude": interlude_lines,
        "journals": journals,
        "encoding": enc,
        "eol": eol,
        "source_path": raw_path,
    }


# --- Serialization --------------------------------------------------------


def _serialize_class_line(c: Dict[str, Any]) -> str:
    """Render one class line. If ``norm_raw`` is present and non-empty, use
    it verbatim (preserves suffixes like ``10zz``); otherwise use ``norm``."""
    major = str(c.get("major") or "").strip()
    try:
        order = int(c.get("sort_order") or 0)
    except (TypeError, ValueError):
        order = 0
    norm_raw = (c.get("norm_raw") or "").strip()
    if not norm_raw:
        try:
            norm_raw = str(int(c.get("norm") or 0))
        except (TypeError, ValueError):
            norm_raw = "0"
    return f"{major}::{order}>>{norm_raw}"


def _serialize_journal_line(j: Dict[str, Any]) -> str:
    major = str(j.get("major") or "").strip()
    minor = str(j.get("minor") or "").strip()
    cls = f"{major}::{minor}" if minor else major
    name = str(j.get("name") or "").strip()
    rank = str(j.get("rank") or "10").strip() or "10"
    if not rank.isdigit():
        digits = "".join(ch for ch in rank if ch.isdigit())
        rank = digits if digits else "10"
    parts = [rank]
    pct = str(j.get("pct") or "").strip()
    q = str(j.get("quartile") or "").strip()
    abdc = str(j.get("abdc") or "").strip()
    if pct:
        parts.append(f"PCT={pct}")
    if q:
        parts.append(f"Q={q}")
    if abdc:
        parts.append(f"ABDC={abdc}")
    return f"{cls}>>{name}??" + ";".join(parts)


def serialize_cnj(parsed: Dict[str, Any]) -> str:
    """Render a parsed dict back to .cnj text using the recorded EOL."""
    eol = parsed.get("eol") or "\n"
    out: List[str] = []
    out.extend(parsed.get("header") or [])
    out.append("CLASSCOUNT")
    classes = list(parsed.get("classes") or [])
    out.append(str(len(classes)))
    for c in classes:
        line = _serialize_class_line(c)
        if line:
            out.append(line)
    interlude = parsed.get("interlude") or []
    out.extend(interlude)
    out.append("STARTJOURNALS")
    journals = list(parsed.get("journals") or [])
    journals_sorted = sorted(
        journals,
        key=lambda j: ((j.get("major") or "").lower(), (j.get("name") or "").lower()),
    )
    for j in journals_sorted:
        line = _serialize_journal_line(j)
        if line:
            out.append(line)
    return eol.join(out) + eol


def backup_cnj(path: str) -> str:
    """Copy ``path`` to a timestamped sibling and return the backup path."""
    src = os.path.abspath(path)
    if not os.path.isfile(src):
        raise FileNotFoundError(src)
    parent = os.path.dirname(src)
    base = os.path.basename(src)
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dst = os.path.join(parent, f"{base}.webbak_{ts}")
    shutil.copy2(src, dst)
    return dst


def save_cnj(path: str, parsed: Dict[str, Any], *, do_backup: bool = True) -> Optional[str]:
    """Write ``parsed`` back to ``path``. Returns the backup path (or None).

    Uses the encoding recorded in ``parsed["encoding"]`` (falls back to
    ``utf-8``). Newlines are written as ``parsed["eol"]`` so a CRLF source
    file stays CRLF.
    """
    if not path:
        raise ValueError("Empty .cnj path.")
    backup_path: Optional[str] = None
    if do_backup and os.path.isfile(path):
        backup_path = backup_cnj(path)
    text = serialize_cnj(parsed)
    enc = parsed.get("encoding") or "utf-8"
    with open(path, "wb") as f:
        f.write(text.encode(enc, errors="replace"))
    return backup_path


# --- Form decoding -------------------------------------------------------


_CLASS_FIELD_RE = re.compile(r"^c_(name|order|norm)_(\d+)$")
_JOURNAL_FIELD_RE = re.compile(r"^j_(major|minor|name|rank|pct|q|abdc)_(\d+)$")


def classes_from_form(form, max_rows: int = 5000) -> List[Dict[str, Any]]:
    """Reconstruct the classes list from POST form fields.

    Recognized field names: ``c_name_<i>``, ``c_order_<i>``, ``c_norm_<i>``,
    ``c_normraw_<i>`` (preserves textual suffix), ``c_del_<i>``.
    """
    indices: set = set()
    for k in form:
        m = _CLASS_FIELD_RE.match(k)
        if m:
            indices.add(int(m.group(2)))
    if len(indices) > max_rows:
        raise ValueError("Too many class rows submitted.")
    out: List[Dict[str, Any]] = []
    for i in sorted(indices):
        if form.get(f"c_del_{i}") == "1":
            continue
        name = (form.get(f"c_name_{i}") or "").strip()
        order_raw = (form.get(f"c_order_{i}") or "0").strip()
        norm_raw = (form.get(f"c_normraw_{i}") or form.get(f"c_norm_{i}") or "0").strip()
        if not name:
            continue
        try:
            order = int(order_raw)
        except ValueError:
            order = 0
        try:
            norm_int = int(norm_raw.replace("zz", "")) if norm_raw.replace("zz", "") else 0
        except ValueError:
            norm_int = 0
        out.append(
            {
                "major": name,
                "sort_order": order,
                "norm": norm_int,
                "norm_raw": norm_raw,
            }
        )
    return out


def journals_from_form(form, max_rows: int = 200000) -> List[Dict[str, Any]]:
    indices: set = set()
    for k in form:
        m = _JOURNAL_FIELD_RE.match(k)
        if m:
            indices.add(int(m.group(2)))
    if len(indices) > max_rows:
        raise ValueError("Too many journal rows submitted.")
    out: List[Dict[str, Any]] = []
    for i in sorted(indices):
        if form.get(f"j_del_{i}") == "1":
            continue
        name = (form.get(f"j_name_{i}") or "").strip()
        if not name:
            continue
        major = (form.get(f"j_major_{i}") or "").strip()
        minor = (form.get(f"j_minor_{i}") or "").strip()
        rank = (form.get(f"j_rank_{i}") or "10").strip() or "10"
        pct = (form.get(f"j_pct_{i}") or "").strip()
        q = (form.get(f"j_q_{i}") or "").strip()
        abdc = (form.get(f"j_abdc_{i}") or "").strip()
        out.append(
            {
                "major": major,
                "minor": minor,
                "name": name,
                "rank": rank,
                "pct": pct,
                "quartile": q,
                "abdc": abdc,
            }
        )
    return out


# --- Convenience wrappers ------------------------------------------------


def attach_form_ids(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Attach a stable ``form_id`` to each class/journal so the template
    can render numbered field names. Returns the input dict (mutated)."""
    for i, c in enumerate(parsed.get("classes") or []):
        c["form_id"] = i
    for i, j in enumerate(parsed.get("journals") or []):
        j["form_id"] = i
    return parsed


def encode_form_tail(s: str) -> str:
    """URL-encode a string so it can be safely round-tripped through a hidden form field."""
    return urllib.parse.quote(s or "", safe="")


def decode_form_tail(s: str) -> str:
    return urllib.parse.unquote(s or "")
