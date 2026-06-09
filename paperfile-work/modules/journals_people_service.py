"""
Parse and save faculty (.cng) and sidecar paths from config; helpers for the web Journals & People page.
"""

from __future__ import annotations

import datetime
import os
import re
import shutil
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

from modules.readdata import abs_from_config, get_config_path, read_json_with_guess, read_text_with_guess

DEFAULT_FACULTY_TAIL = "none;;-1;;-1;;-1;;-1;;"


def resolve_faculty_and_journal_paths() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Returns (config_path, faculty_abs, journal_abs)."""
    cfg = get_config_path()
    if not cfg:
        return None, None, None
    config = read_json_with_guess(cfg)
    fac = abs_from_config(cfg, config.get("faculty_file"))
    jou = abs_from_config(cfg, config.get("journal_definition_file"))
    return cfg, fac, jou


def split_faculty_line(line: str) -> Optional[Dict[str, Any]]:
    line = line.strip()
    if not line or "::" not in line:
        return None
    name, rest = line.split("::", 1)
    parts = rest.split(";;")
    positions_text = parts[0].strip() if parts else ""
    year = parts[1].strip() if len(parts) > 1 else ""
    citations = parts[2].strip() if len(parts) > 2 else ""
    tail = ";;".join(parts[3:]) if len(parts) > 3 else ""
    return {
        "name": name.strip(),
        "positions_text": positions_text,
        "year": year,
        "citations": citations,
        "tail": tail,
    }


def build_faculty_line(row: Dict[str, Any]) -> str:
    name = str(row.get("name", "")).strip()
    pos = str(row.get("positions_text", "")).strip()
    year = str(row.get("year", "")).strip()
    cit = str(row.get("citations", "")).strip()
    tail = str(row.get("tail", "")).strip()
    if not tail:
        tail = DEFAULT_FACULTY_TAIL
    return f"{name}::{pos};;{year};;{cit};;{tail}"


def load_faculty_rows(faculty_path: Optional[str]) -> List[Dict[str, Any]]:
    if not faculty_path or not os.path.isfile(faculty_path):
        return []
    _, _, lines = read_text_with_guess(faculty_path)
    out = []
    for line in lines:
        parsed = split_faculty_line(line)
        if parsed:
            parsed["tail_quoted"] = urllib.parse.quote(parsed["tail"], safe="")
            out.append(parsed)
    return out


def save_faculty_cng(faculty_path: str, rows: List[Dict[str, Any]]) -> None:
    faculty_path = os.path.abspath(faculty_path)
    text = "\n".join(build_faculty_line(r) for r in rows) + "\n"
    with open(faculty_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def backup_sidecar_file(src_path: str) -> str:
    src_path = os.path.abspath(src_path)
    if not os.path.isfile(src_path):
        raise FileNotFoundError(src_path)
    parent = os.path.dirname(src_path)
    base = os.path.basename(src_path)
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dst = os.path.join(parent, f"{base}.webbak_{ts}")
    shutil.copy2(src_path, dst)
    return dst


def faculty_rows_from_post(form) -> List[Dict[str, Any]]:
    """Rebuild faculty rows from the Journals & People POST form (any row indices)."""
    indices = set()
    for k in form:
        m = re.match(r"^f_name_(\d+)$", k)
        if m:
            indices.add(int(m.group(1)))
    if len(indices) > 20000:
        raise ValueError("Too many faculty rows in form.")
    rows: List[Dict[str, Any]] = []
    for i in sorted(indices):
        if form.get(f"f_del_{i}") == "1":
            continue
        name = (form.get(f"f_name_{i}") or "").strip()
        pos = (form.get(f"f_pos_{i}") or "").strip()
        year = (form.get(f"f_year_{i}") or "").strip()
        cit = (form.get(f"f_cit_{i}") or "").strip()
        tail_q = (form.get(f"f_tail_{i}") or "").strip()
        tail = urllib.parse.unquote(tail_q) if tail_q else ""
        if not name and not pos and not year and not cit:
            continue
        if not name:
            raise ValueError(f"Person row #{i} needs a name (or remove the row).")
        rows.append(
            {
                "name": name,
                "positions_text": pos,
                "year": year,
                "citations": cit,
                "tail": tail or DEFAULT_FACULTY_TAIL,
            }
        )
    return rows


def journal_browser_rows(journal_dict: dict, sjr_data: dict) -> List[Dict[str, str]]:
    rows = []
    for name, (clazz, rank) in (journal_dict or {}).items():
        sx = (sjr_data or {}).get(name, {})
        rows.append(
            {
                "name": name,
                "class": clazz,
                "rank": str(rank),
                "pct": str(sx.get("pct", "") or ""),
                "quartile": str(sx.get("quartile", "") or ""),
                "abdc": str(sx.get("abdc", "") or ""),
            }
        )
    rows.sort(key=lambda r: r["name"].lower())
    return rows
