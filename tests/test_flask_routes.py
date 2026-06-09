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
            # vitatyp stored as a desktop-style uppercase code (the form
            # checkboxes also submit codes via value="{{ code }}"). Strict-
            # parity vita filtering requires exact equality.
            sample_record("10", "Alpha, A.", "First", vitatyp="J"),
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

    def test_home_redirects_to_retrieve(self):
        r = self.client.get("/", follow_redirects=False)
        assert r.status_code in (301, 302, 303, 307, 308)
        assert "/retrieve" in (r.headers.get("Location") or "")

    def test_dashboard_ok(self):
        r = self.client.get("/dashboard")
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

    def test_retrieve_author_with_strict_vita_code_filter(self):
        # Vita filter is now strict desktop equality on the uppercase code.
        # The form already submits codes (the checkbox value=`{{ code }}`),
        # so this is the production path. Year boxes are filled because empty
        # means "year-empty records only" under strict desktop semantics.
        r = self.client.post(
            "/retrieve",
            data={
                "search_type": "author_title",
                "author_query": "Alpha",
                "title_query": "",
                "year_min": "1900",
                "year_max": "2100",
                "restrict_vita_types": "1",
                "vita_types": "J",
            },
            follow_redirects=True,
        )
        assert r.status_code == 200
        assert b"Showing 1 results." in r.data

    def test_retrieve_author_with_label_value_does_not_match(self):
        # Strict-parity regression: legacy "label" values like
        # "Journal Articles" must NOT match the strict uppercase code "J"
        # (this is the desktop's filter_by_vita_type behavior).
        r = self.client.post(
            "/retrieve",
            data={
                "search_type": "author_title",
                "author_query": "Alpha",
                "title_query": "",
                "year_min": "1900",
                "year_max": "2100",
                "restrict_vita_types": "1",
                "vita_types": "Journal Articles",
            },
            follow_redirects=True,
        )
        assert r.status_code == 200
        assert b"Showing 0 results." in r.data

    def test_correct_papers_delete_removes_record(self):
        r_view = self.client.get("/correct-papers/edit?num=10")
        assert r_view.status_code == 200
        assert b"delete-paper-form" in r_view.data
        before = CNTReader(self._cnt)
        before.read_file()
        count_before = len(before.get_data() or [])
        r_del = self.client.post(
            "/correct-papers/edit",
            data={
                "record_number": "10",
                "action": "delete",
                "confirm_delete": "1",
            },
            follow_redirects=True,
        )
        assert r_del.status_code == 200
        assert b"Deleted record 10" in r_del.data
        after = CNTReader(self._cnt)
        after.read_file()
        nums = [str(r.get("number", "")).strip() for r in (after.get_data() or [])]
        assert "10" not in nums
        assert len(after.get_data() or []) == count_before - 1
