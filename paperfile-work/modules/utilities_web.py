"""
Server-side helpers for the web Utilities page (no Tk).
"""

from __future__ import annotations

import datetime
import os
import shutil
from typing import List

from modules.check_numbers_service import parse_paper_int
from modules.readdata import get_config_path, read_json_with_guess
from modules.savedata import build_record_block, split_header_and_records


DEFAULT_CNT_HEADER_LINES = [
    "Version",
    "5",
    "McCarl, B.A.,",
    "J,U,P,B,BC,SB,F,CD,CN,PA,DP,",
    r"C:\paperfile\paperFile.mdb",
    "Ag_Economics_Dept_Journals",
    "",
    "",
]


def max_record_number(papers: List[dict]) -> int:
    mx = 0
    for rec in papers or []:
        n = parse_paper_int(rec.get("number", ""))
        if n is not None:
            mx = max(mx, n)
    return mx


def assign_sequential_numbers(records: List[dict], start_num: int) -> List[dict]:
    out = []
    cur = int(start_num)
    for r in records:
        rr = dict(r)
        rr["number"] = str(cur)
        out.append(rr)
        cur += 1
    return out


def backup_cnt_only(db_path: str) -> str:
    """
    Copy the .cnt to db_dir / {stem}_web_backup_{timestamp} / {stem}.cnt
    Returns path to the copied file.
    """
    db_path = os.path.abspath(db_path)
    if not os.path.isfile(db_path):
        raise FileNotFoundError(db_path)
    db_dir = os.path.dirname(db_path)
    stem = os.path.splitext(os.path.basename(db_path))[0]
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = os.path.join(db_dir, f"{stem}_web_backup_{ts}")
    os.makedirs(backup_dir, exist_ok=False)
    dst = os.path.join(backup_dir, f"{stem}.cnt")
    shutil.copy2(db_path, dst)
    return dst


def write_cnt_new_file(
    dest_path: str,
    data_list: List[dict],
    header_source_path: str | None,
) -> None:
    """
    Write a full .cnt (header + records). If header_source_path is an existing .cnt/.bak,
    reuse its header; otherwise write DEFAULT_CNT_HEADER_LINES.
    """
    dest_path = os.path.abspath(dest_path)
    header_lines: List[str] = []
    if header_source_path and os.path.isfile(header_source_path):
        ext = os.path.splitext(header_source_path)[1].lower()
        if ext in (".cnt", ".bak"):
            header, _ = split_header_and_records(header_source_path)
            header_lines = header
    if not header_lines:
        header_lines = [ln + "\n" for ln in DEFAULT_CNT_HEADER_LINES]
    all_blocks = [build_record_block(record).strip() for record in data_list]
    final_content = "".join(header_lines) + "\n".join(all_blocks)
    dest_dir = os.path.dirname(dest_path)
    if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)
    with open(dest_path, "w", encoding="utf-8-sig") as f:
        f.write(final_content)


def set_config_database_path(new_path: str) -> str:
    """Store absolute database path in config.json. Returns normalized absolute path."""
    cfg_path = get_config_path()
    if not cfg_path:
        raise RuntimeError("config.json not found")
    new_path = os.path.abspath(os.path.normpath(new_path))
    if not os.path.isfile(new_path):
        raise FileNotFoundError(new_path)
    try:
        cfg = read_json_with_guess(cfg_path)
    except Exception:
        cfg = {}
    cfg["database_path"] = new_path
    with open(cfg_path, "w", encoding="utf-8") as f:
        import json

        json.dump(cfg, f, indent=2, ensure_ascii=False)
    return new_path


def read_config_value(key: str, default: str = "") -> str:
    cfg_path = get_config_path()
    if not cfg_path:
        return default
    try:
        cfg = read_json_with_guess(cfg_path)
        return str(cfg.get(key, default) or default).strip()
    except Exception:
        return default


def write_config_value(key: str, value: str) -> None:
    cfg_path = get_config_path()
    if not cfg_path:
        raise RuntimeError("config.json not found")
    try:
        cfg = read_json_with_guess(cfg_path)
    except Exception:
        cfg = {}
    cfg[key] = (value or "").strip()
    with open(cfg_path, "w", encoding="utf-8") as f:
        import json

        json.dump(cfg, f, indent=2, ensure_ascii=False)
