"""
Flask app smoke + enter-papers POST (isolated temp DB).

Loads ``app`` once per test class with patched ``get_config_path`` so your real
config.json is never touched.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest.mock as mock

import pytest

from modules.readdata import CNTReader
from modules.utilities_web import write_cnt_new_file
from tests.conftest import sample_record


class TestFlaskAppIsolated:
    @classmethod
    def setup_class(cls):
        cls._root = tempfile.mkdtemp(prefix="paperfile_pytest_")
        root = cls._root
        cls._cnt = f"{root}/db.cnt"
        cls._cfg = f"{root}/config.json"
        recs = [
            sample_record("10", "Alpha, A.", "First"),
            sample_record("20", "Beta, B.", "Second"),
        ]
        write_cnt_new_file(cls._cnt, recs, None)
        with open(cls._cfg, "w", encoding="utf-8") as f:
            json.dump({"database_path": cls._cnt}, f)

        cls._p = mock.patch("modules.readdata.get_config_path", lambda: cls._cfg)
        cls._p.start()
        sys.modules.pop("app", None)
        import importlib

        import app as app_module

        importlib.reload(app_module)
        cls.app_module = app_module
        cls.client = app_module.app.test_client()

    @classmethod
    def teardown_class(cls):
        cls._p.stop()
        sys.modules.pop("app", None)
        shutil.rmtree(cls._root, ignore_errors=True)

    def test_dashboard_ok(self):
        r = self.client.get("/")
        assert r.status_code == 200
        assert b"MAIN MENU" in r.data or b"Main menu" in r.data
        assert b"pf-ui-classic" in r.data

    def test_enter_papers_get(self):
        r = self.client.get("/enter-papers")
        assert r.status_code == 200
        assert b"Save new record" in r.data
        assert b"Next record number" in r.data

    def test_retrieve_redirect_chain(self):
        r = self.client.get("/retrieve-papers", follow_redirects=False)
        assert r.status_code in (301, 302, 303, 307, 308)

    def test_enter_papers_post_appends(self):
        before = CNTReader(self._cnt)
        before.read_file()
        n0 = len(before.get_data() or [])
        r = self.client.post(
            "/enter-papers",
            data={
                "authors": "Gamma, G.",
                "title": "Third Paper Via Test",
                "bookjour": "J",
                "location": "",
                "volume": "",
                "pages": "",
                "year": "2024",
                "vitatyp": "J",
                "funding_year": "",
                "total_amount": "",
                "usable_amount": "",
                "decision": "",
                "subject1": "",
                "subject2": "",
                "duplicateoknumber": "0",
                "pdfpresent": "0",
                "pdfpath": "",
            },
            follow_redirects=True,
        )
        assert r.status_code == 200
        assert b"Added record" in r.data
        after = CNTReader(self._cnt)
        after.read_file()
        assert len(after.get_data() or []) == n0 + 1
