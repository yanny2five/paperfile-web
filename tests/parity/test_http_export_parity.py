"""
HTTP-level parity test for the web app's export endpoints.

For ``/export/bibtex``, ``/export/spreadsheet``, and ``/utilities/export/{bibtex,xlsx}``
the bytes the web app returns to the user must match what the desktop
``modules.exportdata`` writes to disk for the same set of records.

This is the user-visible contract: a researcher should be able to export the
same database from either platform and get the same bibliographic file.
"""

from __future__ import annotations

import base64
import io
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = REPO_ROOT / "paperfile-web"
DESKTOP_ROOT = REPO_ROOT / "paperfile"


@pytest.fixture
def web_app(tmp_path, monkeypatch):
    """Boot a Flask test client with a tiny isolated database."""
    sys.path.insert(0, str(WEB_ROOT))

    from tests.isolated_app_env import write_deep_isolated_env

    cfg, cnt = write_deep_isolated_env(str(tmp_path))

    # The app reads config via modules.utilities_web.config_path; force it
    # to our temp config.
    monkeypatch.setenv("PAPERFILE_CONFIG_OVERRIDE", cfg)

    # Re-import app fresh so it picks up the temp config via session state.
    for k in list(sys.modules):
        if k == "app" or k.startswith("modules."):
            sys.modules.pop(k, None)

    import app as web_app_module

    # Force reader to load from our temp .cnt and rebuild PAPERS.
    web_app_module.reader = web_app_module.CNTReader(cnt)
    web_app_module._sync_papers_from_reader()

    web_app_module.app.config["TESTING"] = True
    client = web_app_module.app.test_client()
    yield client, web_app_module
    sys.path.remove(str(WEB_ROOT))


def _desktop_bibtex_for(records):
    """Run the desktop exportdata.export_to_bibtex via the parity runner."""
    from tests.parity.conftest import _run_side, DESKTOP_ROOT as DR

    return _run_side(DR, "exportdata.bibtex", {"records": records})["text"]


def _desktop_xlsx_for(records):
    from tests.parity.conftest import _run_side, DESKTOP_ROOT as DR

    return base64.b64decode(
        _run_side(DR, "exportdata.xlsx", {"records": records})["bytes_b64"]
    )


def _xlsx_signature(raw: bytes):
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = sorted(zf.namelist())
        sheet = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
        try:
            shared = zf.read("xl/sharedStrings.xml").decode("utf-8")
        except KeyError:
            shared = ""
    return names, sheet, shared


def test_export_bibtex_matches_desktop(web_app):
    client, mod = web_app

    # Pick a few records by number.
    numbers = [str(p.get("number")) for p in mod.PAPERS[:3]]
    expected_records = [p for p in mod.PAPERS if str(p.get("number")) in numbers]

    resp = client.post("/export/bibtex", data={"paper_numbers": ",".join(numbers)})
    assert resp.status_code == 200, resp.data[:500]
    assert resp.headers["Content-Disposition"].endswith('paperfile_export.bib"') or \
        "paperfile_export.bib" in resp.headers["Content-Disposition"]

    web_text = resp.data.decode("utf-8")
    desktop_text = _desktop_bibtex_for(expected_records)
    assert web_text == desktop_text, (
        "Web /export/bibtex output differs from desktop export_to_bibtex on the same records.\n"
        f"--- web ---\n{web_text[:600]}\n--- desktop ---\n{desktop_text[:600]}"
    )


def test_export_spreadsheet_matches_desktop(web_app):
    client, mod = web_app

    numbers = [str(p.get("number")) for p in mod.PAPERS[:3]]
    expected_records = [p for p in mod.PAPERS if str(p.get("number")) in numbers]

    resp = client.post("/export/spreadsheet", data={"paper_numbers": ",".join(numbers)})
    assert resp.status_code == 200, resp.data[:500]

    web_xlsx = resp.data
    desktop_xlsx = _desktop_xlsx_for(expected_records)

    assert _xlsx_signature(web_xlsx) == _xlsx_signature(desktop_xlsx), (
        "Web /export/spreadsheet workbook content differs from desktop export_to_xlsx"
    )


def test_utilities_export_bibtex_full_db_matches_desktop(web_app):
    client, mod = web_app
    resp = client.get("/utilities/export/bibtex")
    assert resp.status_code == 200
    web_text = resp.data.decode("utf-8")
    desktop_text = _desktop_bibtex_for(list(mod.PAPERS))
    assert web_text == desktop_text


def test_utilities_export_xlsx_full_db_matches_desktop(web_app):
    client, mod = web_app
    resp = client.get("/utilities/export/xlsx")
    assert resp.status_code == 200
    web_xlsx = resp.data
    desktop_xlsx = _desktop_xlsx_for(list(mod.PAPERS))
    assert _xlsx_signature(web_xlsx) == _xlsx_signature(desktop_xlsx)
