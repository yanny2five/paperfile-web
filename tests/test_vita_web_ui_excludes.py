"""Web UI omits McCarl public-drop vita types from enter-papers (Ke policy)."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest.mock as mock

import pytest


def test_enter_papers_select_excludes_jd_pr():
    root = tempfile.mkdtemp(prefix="pf_vita_")
    try:
        cnt = f"{root}/db.cnt"
        with open(cnt, "w", encoding="utf-8") as f:
            f.write(
                "Version\n5\n\n"
                "number||1\nauthors||A\ntitle||T\nbookjour||J\nlocation||\n"
                "volume||\npages||\nyear||2020\nvitatyp||J\nsubject1||\nsubject2||\n"
                "duplicateoknumber||0\npdfpresent||0\npdfpath||\ndateentered||\n"
                "*********$$$$$$$$$$$$\n"
            )
        cfg = f"{root}/config.json"
        with open(cfg, "w", encoding="utf-8") as f:
            json.dump({"database_path": cnt}, f)

        p = mock.patch("modules.readdata.get_config_path", lambda: cfg)
        p.start()
        sys.modules.pop("app", None)
        import importlib

        m = importlib.reload(importlib.import_module("app"))
        r = m.app.test_client().get("/enter-papers")
        p.stop()
        sys.modules.pop("app", None)

        assert r.status_code == 200
        body = r.data
        assert b'value="JD"' not in body
        assert b'value="OI"' not in body
        assert b'value="PR"' not in body
        assert b'value="F"' not in body
        assert b'value="J"' in body
    finally:
        shutil.rmtree(root, ignore_errors=True)
