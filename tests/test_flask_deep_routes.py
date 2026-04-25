"""
Deep Flask coverage: every HTTP route with a rich isolated DB (faculty + .cnj + PR rows).

Uses a fresh temp tree and patched ``get_config_path`` — never your real ``config.json``.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest.mock as mock

import pytest

from tests.isolated_app_env import write_deep_isolated_env


@pytest.mark.parametrize(
    "path,ok_codes,follow",
    [
        ("/", (301, 302, 303, 307, 308), False),
        ("/enter-papers", (200,), False),
        ("/retrieve-papers", (200,), True),
        ("/data-export", (200,), True),
        ("/retrieve-numbers", (200,), True),
        ("/journals-and-people", (200,), False),
        ("/correct-papers", (200,), False),
        ("/correct-papers/edit?num=10", (200,), False),
        ("/edit-and-fix-entries", (200,), False),
        ("/edit-and-fix-entries/correct-elements?field=title&q=corn", (200,), False),
        ("/check-numbers", (200,), False),
        ("/generate-reports", (200,), False),
        ("/reports/publication-type", (200,), False),
        ("/reports/publication-types-time", (200,), False),
        ("/reports/publication-type?mode=people", (200,), False),
        ("/reports/group-output", (200,), False),
        ("/reports/funding-proposals", (200,), False),
        ("/reports/journal-report", (200,), False),
        ("/reports/journal-report?variant=rank&scope=whole", (200,), False),
        ("/reports/journal-report?variant=class&scope=whole", (200,), False),
        ("/reports/journal-categories-time", (200,), False),
        ("/reports/journal-categories-time?mode=people", (200,), False),
        ("/reports/composite-summary", (200,), False),
        ("/reports/composite-summary?view=rank", (200,), False),
        ("/reports/composite-summary?view=power", (200,), False),
        ("/reports/composite-summary?export=tsv", (200,), False),
        ("/utilities", (200,), False),
        ("/retrieve", (200,), False),
        ("/mode/retrieve", (200,), True),
        ("/journals-and-people/download?kind=faculty", (200,), False),
        ("/journals-and-people/download?kind=journal", (200,), False),
        # Exports (plain text / binary)
        ("/edit-and-fix-entries/export/funky-tsv", (200,), False),
        ("/edit-and-fix-entries/export/exact-duplicates", (200,), False),
        ("/edit-and-fix-entries/export/title-duplicates", (200,), False),
        ("/utilities/export/bibtex", (200,), False),
        ("/utilities/export/xlsx", (200,), False),
        ("/reports/journal-report?export=tsv&variant=use&scope=whole", (200,), False),
        ("/reports/funding-proposals?export=tsv", (200,), False),
        ("/reports/publication-type?export=tsv", (200,), False),
        ("/reports/journal-categories-time?export=tsv", (200,), False),
        # Expected failures
        ("/reports/group-output.txt", (404,), False),
        ("/edit-and-fix-entries/export/unknown-kind", (404,), False),
        ("/journals-and-people/download?kind=nope", (404,), False),
    ],
)
def test_flask_get_routes_deep(path, ok_codes, follow):
    root = tempfile.mkdtemp(prefix="pf_route_")
    p = None
    try:
        cfg_path, _cnt = write_deep_isolated_env(root)
        p = mock.patch("modules.readdata.get_config_path", lambda: cfg_path)
        p.start()
        sys.modules.pop("app", None)
        import importlib

        import app as app_module

        importlib.reload(app_module)
        client = app_module.app.test_client()
        r = client.get(path, follow_redirects=follow)
        assert r.status_code in ok_codes, f"{path} -> {r.status_code}"
    finally:
        if p is not None:
            p.stop()
        sys.modules.pop("app", None)
        shutil.rmtree(root, ignore_errors=True)


def test_flask_group_output_txt_download_uses_session():
    """``.txt`` route only returns 200 when session holds non-empty output (empty string -> 404)."""
    root = tempfile.mkdtemp(prefix="pf_grp_")
    p = None
    try:
        cfg_path, _ = write_deep_isolated_env(root)
        p = mock.patch("modules.readdata.get_config_path", lambda: cfg_path)
        p.start()
        sys.modules.pop("app", None)
        import importlib

        import app as app_module

        importlib.reload(app_module)
        client = app_module.app.test_client()
        with client.session_transaction() as sess:
            sess["group_output_txt"] = "line1\nline2\n"
        r_txt = client.get("/reports/group-output.txt")
        assert r_txt.status_code == 200
        assert b"line1" in r_txt.data
    finally:
        if p:
            p.stop()
        sys.modules.pop("app", None)
        shutil.rmtree(root, ignore_errors=True)


def test_flask_retrieve_post_search():
    root = tempfile.mkdtemp(prefix="pf_ret_")
    p = None
    try:
        cfg_path, _ = write_deep_isolated_env(root)
        p = mock.patch("modules.readdata.get_config_path", lambda: cfg_path)
        p.start()
        sys.modules.pop("app", None)
        import importlib

        import app as app_module

        importlib.reload(app_module)
        client = app_module.app.test_client()
        r = client.post(
            "/retrieve",
            data={
                "search_type": "author_title",
                "author_query": "McCarl",
                "title_query": "",
                "sort_by": "title",
            },
            follow_redirects=True,
        )
        assert r.status_code == 200
        assert b"McCarl" in r.data or b"Result" in r.data or b"retrieve" in r.data.lower()
    finally:
        if p:
            p.stop()
        sys.modules.pop("app", None)
        shutil.rmtree(root, ignore_errors=True)


def test_flask_retrieve_post_author_title_respects_text_to_find():
    """query_author_title must be used when author/title boxes are empty (author OR title)."""
    root = tempfile.mkdtemp(prefix="pf_ret2_")
    p = None
    try:
        cfg_path, _ = write_deep_isolated_env(root)
        p = mock.patch("modules.readdata.get_config_path", lambda: cfg_path)
        p.start()
        sys.modules.pop("app", None)
        import importlib

        import app as app_module

        importlib.reload(app_module)
        client = app_module.app.test_client()
        r = client.post(
            "/retrieve",
            data={
                "search_type": "author_title",
                "query_author_title": "McCarl",
                "author_query": "",
                "title_query": "",
                "sort_by": "title",
            },
            follow_redirects=True,
        )
        assert r.status_code == 200
        assert b"McCarl" in r.data
    finally:
        if p:
            p.stop()
        sys.modules.pop("app", None)
        shutil.rmtree(root, ignore_errors=True)


def test_flask_export_bibtex_from_retrieve():
    root = tempfile.mkdtemp(prefix="pf_ebib_")
    p = None
    try:
        cfg_path, _ = write_deep_isolated_env(root)
        p = mock.patch("modules.readdata.get_config_path", lambda: cfg_path)
        p.start()
        sys.modules.pop("app", None)
        import importlib

        import app as app_module

        importlib.reload(app_module)
        client = app_module.app.test_client()
        r = client.post(
            "/export/bibtex",
            data={"paper_numbers": "10,11"},
        )
        assert r.status_code == 200
        assert b"@" in r.data or b"article" in r.data or b"book" in r.data
    finally:
        if p:
            p.stop()
        sys.modules.pop("app", None)
        shutil.rmtree(root, ignore_errors=True)


def test_flask_export_spreadsheet_from_retrieve():
    root = tempfile.mkdtemp(prefix="pf_exls_")
    p = None
    try:
        cfg_path, _ = write_deep_isolated_env(root)
        p = mock.patch("modules.readdata.get_config_path", lambda: cfg_path)
        p.start()
        sys.modules.pop("app", None)
        import importlib

        import app as app_module

        importlib.reload(app_module)
        client = app_module.app.test_client()
        r = client.post(
            "/export/spreadsheet",
            data={"paper_numbers": "10"},
        )
        assert r.status_code == 200
        assert r.mimetype and "spreadsheet" in r.mimetype
        assert len(r.data) > 100
    finally:
        if p:
            p.stop()
        sys.modules.pop("app", None)
        shutil.rmtree(root, ignore_errors=True)


def test_flask_staging_flow():
    root = tempfile.mkdtemp(prefix="pf_stg_")
    p = None
    try:
        cfg_path, _ = write_deep_isolated_env(root)
        p = mock.patch("modules.readdata.get_config_path", lambda: cfg_path)
        p.start()
        sys.modules.pop("app", None)
        import importlib

        import app as app_module

        importlib.reload(app_module)
        client = app_module.app.test_client()
        r1 = client.post("/staging/add", data={"pick": ["10", "11"]}, follow_redirects=True)
        assert r1.status_code == 200
        r2 = client.post("/staging/clear", follow_redirects=True)
        assert r2.status_code == 200
    finally:
        if p:
            p.stop()
        sys.modules.pop("app", None)
        shutil.rmtree(root, ignore_errors=True)


def test_flask_export_mode_keeps_last_retrieve_results():
    root = tempfile.mkdtemp(prefix="pf_modeexp_")
    p = None
    try:
        cfg_path, _ = write_deep_isolated_env(root)
        p = mock.patch("modules.readdata.get_config_path", lambda: cfg_path)
        p.start()
        sys.modules.pop("app", None)
        import importlib

        import app as app_module

        importlib.reload(app_module)
        client = app_module.app.test_client()

        # First run a retrieve search to seed session-backed results.
        r1 = client.post(
            "/retrieve",
            data={"search_type": "author_title", "query_author_title": "corn", "sort_by": "title"},
            follow_redirects=True,
        )
        assert r1.status_code == 200

        # Enter export mode and confirm rows remain available for selection.
        r2 = client.get("/mode/export", follow_redirects=True)
        assert r2.status_code == 200
        assert b"Add selected to export list" in r2.data
        assert b"name=\"pick\"" in r2.data
    finally:
        if p:
            p.stop()
        sys.modules.pop("app", None)
        shutil.rmtree(root, ignore_errors=True)


def test_flask_correct_papers_edit_redirect_without_num():
    root = tempfile.mkdtemp(prefix="pf_cred_")
    p = None
    try:
        cfg_path, _ = write_deep_isolated_env(root)
        p = mock.patch("modules.readdata.get_config_path", lambda: cfg_path)
        p.start()
        sys.modules.pop("app", None)
        import importlib

        import app as app_module

        importlib.reload(app_module)
        client = app_module.app.test_client()
        r = client.get("/correct-papers/edit", follow_redirects=False)
        assert r.status_code in (302, 303, 307, 308)
    finally:
        if p:
            p.stop()
        sys.modules.pop("app", None)
        shutil.rmtree(root, ignore_errors=True)
