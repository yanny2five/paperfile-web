"""
Form-default parity with the desktop UI.

Pins two desktop behaviours the web is now expected to mirror on a fresh
Retrieve view:

1. ``First Year wanted`` / ``Last Year wanted`` are pre-filled from the
   dataset's min/max years, using the same digit-extraction logic the
   desktop's ``RightPanel.show_year_range_section`` runs at panel-show time
   (paperfile/pages/right_panel.py lines 396-421).
2. ``Sort by`` defaults to ``vita_type`` (desktop's ``self.sort_var =
   tk.StringVar(value="vitatyp")`` in paperfile/pages/left_panel.py:217).

These are GET-time defaults only — POST submissions still pass through
unchanged so the user can clear the year boxes to trigger the strict
"empty_only" filter (desktop parity).
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest.mock as mock

import pytest

from modules.utilities_web import write_cnt_new_file
from tests.conftest import sample_record


# ---------------------------------------------------------------------------
# Pure-function tests for compute_dataset_year_bounds (no Flask required).
# ---------------------------------------------------------------------------


def test_year_bounds_simple_4_digit_years():
    from app import compute_dataset_year_bounds

    papers = [
        {"year": "1985"},
        {"year": "2024"},
        {"year": "2000"},
    ]
    assert compute_dataset_year_bounds(papers) == (1985, 2024)


def test_year_bounds_extracts_last_4_digits_from_messy_strings():
    """Mirrors desktop's behaviour for entries like 'September/October 2016'
    (right_panel.py line 409: ``year_str = digits[-4:]``)."""
    from app import compute_dataset_year_bounds

    papers = [
        {"year": "September/October 2016"},
        {"year": "Spring 2020"},
        {"year": "2010"},
    ]
    assert compute_dataset_year_bounds(papers) == (2010, 2020)


def test_year_bounds_ignores_records_with_empty_year():
    from app import compute_dataset_year_bounds

    papers = [
        {"year": ""},
        {"year": "  "},
        {"year": "1999"},
        {"year": "2005"},
    ]
    assert compute_dataset_year_bounds(papers) == (1999, 2005)


def test_year_bounds_falls_back_to_any_digits_when_less_than_4():
    """Desktop fallback: ``elif digits: year_str = digits``
    (right_panel.py line 411)."""
    from app import compute_dataset_year_bounds

    # "98 (volume)" -> digits "98" -> year_str "98" -> int 98
    papers = [{"year": "98"}, {"year": "2024"}]
    assert compute_dataset_year_bounds(papers) == (98, 2024)


def test_year_bounds_returns_none_none_when_no_usable_years():
    from app import compute_dataset_year_bounds

    assert compute_dataset_year_bounds([]) == (None, None)
    assert compute_dataset_year_bounds([{"year": ""}, {"year": "n/a"}]) == (
        None,
        None,
    )


def test_year_bounds_handles_missing_year_key():
    from app import compute_dataset_year_bounds

    papers = [{}, {"year": "2010"}, {"title": "X"}]
    assert compute_dataset_year_bounds(papers) == (2010, 2010)


# ---------------------------------------------------------------------------
# Integration: GET /retrieve pre-fills year boxes from dataset bounds and
# selects "vita type" as the default sort radio.
# ---------------------------------------------------------------------------


class TestRetrieveGetDefaults:
    @classmethod
    def setup_class(cls):
        cls._root = tempfile.mkdtemp(prefix="paperfile_form_defaults_")
        root = cls._root
        cls._cnt = f"{root}/db.cnt"
        cls._cfg = f"{root}/config.json"
        recs = [
            sample_record("10", "Alpha, A.", "First", year="1985"),
            sample_record("20", "Beta, B.", "Second", year="2024"),
            sample_record("30", "Gamma, G.", "Third", year="2010"),
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

    def test_module_globals_compute_bounds_at_startup(self):
        assert self.app_module.DATASET_YEAR_MIN == 1985
        assert self.app_module.DATASET_YEAR_MAX == 2024

    def test_get_retrieve_prefills_year_boxes_from_dataset_min_max(self):
        r = self.client.get("/retrieve")
        assert r.status_code == 200
        body = r.data.decode("utf-8", errors="replace")
        # Year input value attributes should be pre-filled with the dataset
        # min/max (matches desktop's right_panel.show_year_range_section).
        assert 'name="year_min"' in body
        assert 'value="1985"' in body
        assert 'name="year_max"' in body
        assert 'value="2024"' in body

    def test_get_retrieve_defaults_sort_to_vita_type(self):
        import re

        r = self.client.get("/retrieve")
        assert r.status_code == 200
        body = r.data.decode("utf-8", errors="replace")

        def _input_for_sort_value(value):
            # Match a single <input ...> tag that has both name="sort_by"
            # and value="<value>"; DOTALL lets the tag span lines (the
            # {% if %} branch sits on its own line in the template).
            pattern = re.compile(
                r"<input\b[^>]*\bname=\"sort_by\"[^>]*\bvalue=\""
                + re.escape(value)
                + r"\"[^>]*>",
                re.DOTALL,
            )
            m = pattern.search(body)
            assert m, f"sort_by radio with value={value!r} not found"
            return m.group(0)

        vita_input = _input_for_sort_value("vita_type")
        assert "checked" in vita_input, (
            f"sort_by vita_type radio should be checked on GET; tag={vita_input!r}"
        )

        for other in ("author", "title", "journal_book"):
            tag = _input_for_sort_value(other)
            assert "checked" not in tag, (
                f"sort_by {other!r} radio must NOT be checked on a fresh GET; "
                f"tag={tag!r}"
            )

    def test_post_with_empty_year_boxes_is_preserved_not_replaced(self):
        """Strict desktop parity: an empty year box on POST must remain empty
        (triggers the empty-only filter); the GET-time default must NOT
        leak into POST handling."""
        r = self.client.post(
            "/retrieve",
            data={
                "search_type": "author_title",
                "author_query": "Alpha",
                "year_min": "",
                "year_max": "",
            },
            follow_redirects=False,
        )
        assert r.status_code == 200
        body = r.data.decode("utf-8", errors="replace")
        # No matching empty-year records exist in this fixture, so the
        # response should report 0 results (proves the empty year boxes
        # actually triggered empty_only mode).
        assert b"Showing 0 results." in r.data
        # Year boxes in the POST-response form should remain empty
        # (request.form has them as ''), not silently replaced with bounds.
        assert 'id="year_min" name="year_min" value=""' in body
        assert 'id="year_max" name="year_max" value=""' in body
