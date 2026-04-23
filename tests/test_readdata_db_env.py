"""PAPERFILE_DATABASE_PATH overrides config when the file exists."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_database_path_from_environment(tmp_path, monkeypatch):
    from modules import readdata

    good = tmp_path / "db.cnt"
    good.write_text("x\n", encoding="utf-8")
    monkeypatch.setenv("PAPERFILE_DATABASE_PATH", str(good))
    assert readdata._database_path_from_environment() == str(good.resolve())

    monkeypatch.setenv("PAPERFILE_DATABASE_PATH", str(tmp_path / "missing.cnt"))
    assert readdata._database_path_from_environment() is None
