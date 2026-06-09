"""modules.readdata — JSON helpers (no live config required)."""

from __future__ import annotations

import json
from pathlib import Path

from modules.readdata import read_json_with_guess


def test_read_json_with_guess_utf8(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert read_json_with_guess(str(p)) == {"a": 1}


def test_read_json_with_guess_utf8_bom(tmp_path: Path):
    p = tmp_path / "bom.json"
    p.write_bytes(b"\xef\xbb\xbf" + b'{"k": "v"}')
    assert read_json_with_guess(str(p)) == {"k": "v"}
