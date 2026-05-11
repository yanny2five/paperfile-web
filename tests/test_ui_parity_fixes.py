"""
UI-parity regression tests for the fixes applied in response to
``UI_PARITY_DISCREPANCIES.md``. Each test pins one of the desktop behaviours
the web is now expected to mirror so future template / route refactors
cannot silently drop a fix.

Sections, in the order they appear:

1.  Retrieve search form (templates/_retrieve_search_form.html)
    - Label-drift: §4 rows 34-38
    - Vita-restrict header: §4 row 22
    - Select All / Unselect All buttons: §4 row 21
    - Per-mode visibility for Vita Type and Year: §4 rows 26 + 27

2.  Server-side validation messages: §4 rows 39-46

3.  Dashboard:
    - Bottom "Current file | Total entries" strip: §2 row 5
    - Retrieve Paper Numbers tile: §2 row 7

4.  Correct Papers Edit:
    - Delete this paper button: §6 row 63
    - Save changes label: §6 row 60
    - Editable Number field for renumber/overwrite: §6 row 64

5.  Enter Papers:
    - Duplicate File Number warning: §3 row 16

6.  Bulk delete confirm: §13 row 143

7.  Correct Elements field selector: §7 row 77
"""

from __future__ import annotations

import importlib
import json
import re
import shutil
import sys
import tempfile
import unittest.mock as mock

import pytest

from modules.utilities_web import write_cnt_new_file
from tests.conftest import sample_record


# ---------------------------------------------------------------------------
# Shared fixture: spin up a Flask client backed by an isolated .cnt file so
# every UI route can be exercised end-to-end. The same pattern is used by
# tests/test_form_defaults.py.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def web_client():
    root = tempfile.mkdtemp(prefix="paperfile_ui_fixes_")
    try:
        cnt = f"{root}/db.cnt"
        cfg = f"{root}/config.json"
        recs = [
            sample_record("10", "Alpha, A.", "First", year="1985"),
            sample_record("20", "Beta, B.", "Second", year="2024", vitatyp="B"),
            sample_record("30", "Gamma, G.", "Third", year="2010"),
        ]
        write_cnt_new_file(cnt, recs, None)
        with open(cfg, "w", encoding="utf-8") as f:
            json.dump({"database_path": cnt}, f)

        p = mock.patch("modules.readdata.get_config_path", lambda: cfg)
        p.start()
        try:
            sys.modules.pop("app", None)
            import app as app_module

            importlib.reload(app_module)
            client = app_module.app.test_client()
            yield {
                "client": client,
                "module": app_module,
                "cnt": cnt,
                "cfg": cfg,
                "root": root,
            }
        finally:
            p.stop()
            sys.modules.pop("app", None)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _body(resp):
    return resp.data.decode("utf-8", errors="replace")


# ===========================================================================
# Section 1: Retrieve search form
# ===========================================================================


class TestRetrieveSearchFormLabels:
    """§4 rows 34-38 — desktop-verbatim label drift."""

    def test_keyword_field_label_matches_desktop(self, web_client):
        body = _body(web_client["client"].get("/retrieve"))
        # Desktop: "Text in Keyword fields" (no parenthetical Subject1/Subject2)
        assert ">Text in Keyword fields<" in body
        # Stale wording must not survive
        assert "Keywords and subjects (Subject1 / Subject2)" not in body

    def test_journal_book_field_label_matches_desktop(self, web_client):
        body = _body(web_client["client"].get("/retrieve"))
        assert ">Text in Book/Journal field<" in body
        assert "Text to find in Journal/Book field" not in body

    def test_any_field_label_matches_desktop(self, web_client):
        body = _body(web_client["client"].get("/retrieve"))
        assert ">Text in any field<" in body
        assert "Text to find (any field)" not in body

    def test_optional_author_label_drops_redundant_field_suffix(self, web_client):
        body = _body(web_client["client"].get("/retrieve"))
        assert ">Optional more text in Author<" in body
        assert "Optional more text in Author field" not in body

    def test_optional_title_label_drops_redundant_field_suffix(self, web_client):
        body = _body(web_client["client"].get("/retrieve"))
        assert ">Optional more text in Title<" in body
        assert "Optional more text in Title field" not in body


class TestVitaRestrictControls:
    """§4 rows 21 + 22 — header + Select All / Unselect All buttons."""

    def test_vita_box_has_check_to_include_header(self, web_client):
        body = _body(web_client["client"].get("/retrieve"))
        assert "Check vita types to INCLUDE" in body

    def test_vita_box_has_select_all_and_unselect_all_buttons(self, web_client):
        body = _body(web_client["client"].get("/retrieve"))
        assert 'id="vita_select_all"' in body
        assert ">Select All<" in body
        assert 'id="vita_unselect_all"' in body
        assert ">Unselect All<" in body


class TestPerModeFieldVisibility:
    """§4 rows 26 + 27 — Vita Type and Year modes show year boxes."""

    def test_year_min_and_year_max_rows_are_visible_in_year_mode(self, web_client):
        body = _body(web_client["client"].get("/retrieve"))
        # The mode-year class must be on BOTH year_min and year_max rows so
        # that "Select by Year" shows First/Last Year wanted (not a single
        # free-text Year box).
        first_row_re = re.compile(
            r'<div class="field-row[^"]*\bmode-year\b[^"]*"[^>]*>\s*'
            r'<label for="year_min">First Year wanted</label>',
            re.DOTALL,
        )
        last_row_re = re.compile(
            r'<div class="field-row[^"]*\bmode-year\b[^"]*"[^>]*>\s*'
            r'<label for="year_max">Last Year wanted</label>',
            re.DOTALL,
        )
        assert first_row_re.search(body), (
            "First Year wanted row must carry mode-year for §4 row 27"
        )
        assert last_row_re.search(body), (
            "Last Year wanted row must carry mode-year for §4 row 27"
        )

    def test_year_min_and_year_max_rows_are_visible_in_vita_type_mode(self, web_client):
        body = _body(web_client["client"].get("/retrieve"))
        first_row_re = re.compile(
            r'<div class="field-row[^"]*\bmode-vita_type\b[^"]*"[^>]*>\s*'
            r'<label for="year_min">First Year wanted</label>',
            re.DOTALL,
        )
        last_row_re = re.compile(
            r'<div class="field-row[^"]*\bmode-vita_type\b[^"]*"[^>]*>\s*'
            r'<label for="year_max">Last Year wanted</label>',
            re.DOTALL,
        )
        assert first_row_re.search(body), (
            "First Year wanted row must carry mode-vita_type for §4 row 26"
        )
        assert last_row_re.search(body), (
            "Last Year wanted row must carry mode-vita_type for §4 row 26"
        )

    def test_legacy_text_to_find_in_vita_type_input_is_removed(self, web_client):
        body = _body(web_client["client"].get("/retrieve"))
        # Desktop has NO "Text to find in Vita Type" free-text input.
        assert "Text to find in Vita Type" not in body
        assert 'id="vita_query"' not in body

    def test_legacy_single_year_input_is_removed(self, web_client):
        body = _body(web_client["client"].get("/retrieve"))
        # The standalone "Year" text box (mode-year only, free text) must
        # be gone — replaced by First/Last Year wanted boxes.
        assert 'id="year_query"' not in body


# ===========================================================================
# Section 2: Server-side validation messages — desktop-verbatim wording
# ===========================================================================


class TestSearchValidationMessages:
    def _post(self, web_client, **fields):
        return web_client["client"].post("/retrieve", data=fields)

    def test_author_title_with_no_text_emits_desktop_verbatim_error(self, web_client):
        body = _body(self._post(web_client, search_type="author_title"))
        assert (
            "Invalid search criteria entered: At least one field must have "
            "a value, and year fields must be either both filled or both "
            "empty." in body
        )

    def test_keyword_with_blank_query_emits_desktop_verbatim_error(self, web_client):
        body = _body(self._post(web_client, search_type="keyword"))
        assert (
            "Invalid search criteria entered: Keyword field must have a "
            "value, and year fields must be either both filled or both empty."
            in body
        )

    def test_journal_book_with_blank_query_emits_desktop_verbatim_error(
        self, web_client
    ):
        body = _body(self._post(web_client, search_type="journal_book"))
        assert (
            "Invalid search criteria entered: Book/Journal Title field must "
            "have a value, and year fields must be either both filled or "
            "both empty." in body
        )

    def test_any_field_with_blank_query_emits_desktop_verbatim_error(self, web_client):
        body = _body(self._post(web_client, search_type="any_field"))
        assert (
            "Invalid search criteria entered: Text in any field must have "
            "a value, and year fields must be either both filled or both empty."
            in body
        )

    def test_vita_type_with_no_checked_codes_emits_no_vita_types_error(
        self, web_client
    ):
        body = _body(
            self._post(
                web_client,
                search_type="vita_type",
                year_min="1900",
                year_max="2100",
            )
        )
        assert "No vita types selected." in body

    def test_vita_type_with_unmatched_year_boxes_emits_year_error(self, web_client):
        body = _body(
            self._post(
                web_client,
                search_type="vita_type",
                year_min="1990",
                year_max="",
                restrict_vita_types="1",
                vita_types="J",
            )
        )
        assert (
            "Invalid year range values entered. Fill both year boxes or "
            "leave both empty." in body
        )

    def test_year_with_invalid_range_emits_year_error(self, web_client):
        body = _body(
            self._post(
                web_client,
                search_type="year",
                year_min="1990",
                year_max="",
            )
        )
        assert "Invalid year range values entered." in body

    def test_year_mode_with_valid_range_shows_matching_papers(self, web_client):
        """Select by Year has no query field; range alone must retrieve rows."""
        body = _body(
            self._post(
                web_client,
                search_type="year",
                year_min="2024",
                year_max="2024",
            )
        )
        assert "Invalid year range values entered." not in body
        assert "Second" in body

    def test_search_error_banner_uses_invalid_search_criteria_headline(
        self, web_client
    ):
        body = _body(
            self._post(
                web_client,
                search_type="keyword",
                year_min="1900",
                year_max="2100",
            )
        )
        # Generic banner replaces the old "Invalid year input." headline.
        assert "<strong>Invalid search criteria.</strong>" in body
        assert "Invalid year input." not in body


# ===========================================================================
# Section 3: Dashboard
# ===========================================================================


class TestDashboard:
    def test_dashboard_renders_file_strip_twice_for_top_and_bottom(self, web_client):
        body = _body(web_client["client"].get("/dashboard"))
        # The "Current file" strip must appear both above AND below the
        # menu grid (§2 row 5).
        assert body.count('class="file-line"') >= 2

    def test_dashboard_exposes_retrieve_paper_numbers_tile(self, web_client):
        body = _body(web_client["client"].get("/dashboard"))
        assert "Retrieve Paper Numbers" in body
        # And the tile must point at the dedicated /retrieve-numbers route.
        assert 'href="/retrieve-numbers"' in body


# ===========================================================================
# Section 4: Correct Papers Edit
# ===========================================================================


class TestCorrectPapersEdit:
    def test_edit_form_now_exposes_editable_number_field(self, web_client):
        body = _body(web_client["client"].get("/correct-papers/edit?num=10"))
        # The Number input is what enables desktop's "renumber" + "overwrite
        # confirm" flow on save (§6 row 64).
        assert 'id="number"' in body
        assert 'data-original-number="10"' in body

    def test_edit_form_save_button_says_save_changes_not_save_to_cnt(
        self, web_client
    ):
        body = _body(web_client["client"].get("/correct-papers/edit?num=10"))
        # §6 row 60 — desktop says "Save changes", not "Save to .cnt"
        assert ">Save changes<" in body
        assert "Save to .cnt" not in body

    def test_edit_form_now_exposes_delete_button(self, web_client):
        body = _body(web_client["client"].get("/correct-papers/edit?num=10"))
        # §6 row 63 — Desktop has a "Delete this paper" button on Edit Paper.
        # The label is whitespace-padded inside the button, so substring-match.
        assert "Delete this paper" in body
        assert 'id="delete-paper-form"' in body

    def test_edit_form_includes_existing_numbers_for_overwrite_confirm(
        self, web_client
    ):
        body = _body(web_client["client"].get("/correct-papers/edit?num=10"))
        # The JS overwrite-confirm needs the list of existing numbers; the
        # template renders it via existing_numbers_json.
        # The list must include at least the two OTHER records 20 and 30.
        m = re.search(r"var existingNumbers\s*=\s*(\[[^\]]*\])", body)
        assert m, "existingNumbers JSON literal must be embedded for overwrite-confirm"
        nums = json.loads(m.group(1))
        assert "20" in nums
        assert "30" in nums


# ===========================================================================
# Section 5: Enter Papers
# ===========================================================================


class TestEnterPapersDuplicateFileNumber:
    def test_enter_papers_template_supports_warning_flash_class(self, web_client):
        body = _body(web_client["client"].get("/enter-papers"))
        # The .flash.warning style must be present so the duplicate-file-
        # number warning is rendered with desktop-equivalent emphasis.
        assert ".flash.warning" in body


# ===========================================================================
# Section 6: Bulk delete commit confirm
# ===========================================================================


class TestBulkDeleteCommitConfirm:
    def test_commit_form_has_onsubmit_confirm_for_delete_action(self, web_client):
        # First trigger a preview so the commit form is rendered.
        web_client["client"].post(
            "/delete-selected-papers",
            data={"action": "preview", "from_n": "10", "to_n": "10"},
        )
        body = _body(web_client["client"].get("/delete-selected-papers"))
        # If the preview produced a plan, the commit form must wrap its
        # submit in a JS confirm() call (§13 row 143).
        if "value=\"commit\"" in body:
            assert "window.confirm(" in body
            assert "Permanently delete" in body


# ===========================================================================
# Section 7: Correct Elements field radios
# ===========================================================================


class TestCorrectElementsFieldRadios:
    def test_field_chooser_uses_radios_with_human_readable_labels(self, web_client):
        body = _body(
            web_client["client"].get("/edit-and-fix-entries/correct-elements")
        )
        # §7 row 77 — desktop presents radios with human-readable labels;
        # the web previously used a <select> populated with raw column names.
        assert 'type="radio"' in body
        assert 'name="field"' in body
        # Spot-check several human-readable labels (these match the labels
        # dict in app.edit_and_fix_correct_elements).
        for label in (
            "Titles",
            "Authors",
            "Journal (bookjour)",
            "Rest of location",
            "Volume",
            "Pages",
            "Keywords (subject1+2)",
        ):
            assert label in body, f"Missing human-readable field label: {label!r}"
