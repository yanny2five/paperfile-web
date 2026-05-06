"""
Shared fixtures and helpers for the parity test suite.

Each parity test runs the same operation against both the desktop project
(``paperfile/``) and the web project (``paperfile-web/``) using a subprocess
runner. This avoids the ``modules`` package collision that would happen if
both sides were imported into the same interpreter.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest


# parity/conftest.py → …/paperfile/tests/parity/conftest.py
# parents[2] = paperfile app root (modules/, app.py)
# parents[3] = outer folder (e.g. paperfile_web/) when the repo is paperfile_web/paperfile/
REPO_ROOT = Path(__file__).resolve().parents[3]
DESKTOP_ROOT = REPO_ROOT / "paperfile"
_WEB_SEPARATE = REPO_ROOT / "paperfile-web"
# CI / typical clone: web and Tk sources both live under `paperfile/` (no second tree).
WEB_ROOT = _WEB_SEPARATE if _WEB_SEPARATE.is_dir() else DESKTOP_ROOT
RUNNER = Path(__file__).parent / "_runner.py"


def _python() -> str:
    """Return the Python interpreter that should run the runner subprocess."""
    return sys.executable


def _run_side(side_root: Path, op: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke the runner with cwd at ``side_root`` and return its parsed JSON."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(side_root) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [_python(), str(RUNNER)],
        cwd=str(side_root),
        env=env,
        input=json.dumps({"op": op, "payload": payload}),
        text=True,
        capture_output=True,
        timeout=120,
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        raise RuntimeError(
            f"Runner failed (side={side_root.name}, op={op}):\n"
            f"stderr:\n{proc.stderr}\nstdout:\n{proc.stdout}"
        )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Runner returned non-JSON (side={side_root.name}, op={op}): {e}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        ) from e

    if not data.get("ok"):
        raise RuntimeError(
            f"Runner reported error (side={side_root.name}, op={op}): "
            f"{data.get('error')}\n{data.get('traceback', '')}"
        )
    return data["result"]


@pytest.fixture(scope="session")
def parity():
    """Return a callable ``parity(op, payload)`` -> (desktop_result, web_result)."""
    if not DESKTOP_ROOT.is_dir():
        pytest.skip(f"Desktop tree not found at {DESKTOP_ROOT}")
    if not WEB_ROOT.is_dir():
        pytest.skip(f"Web tree not found at {WEB_ROOT}")

    def _run(op: str, payload: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
        desktop = _run_side(DESKTOP_ROOT, op, payload)
        web = _run_side(WEB_ROOT, op, payload)
        return desktop, web

    return _run


@pytest.fixture
def temp_cnt_pair() -> tuple[Path, Path]:
    """Yield two distinct temp .cnt paths (one for each side)."""
    tmp = tempfile.mkdtemp(prefix="parity_cnt_")
    a = Path(tmp) / "desktop.cnt"
    b = Path(tmp) / "web.cnt"
    yield a, b
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="session")
def fixture_records() -> list[dict]:
    """A diverse, deterministic record set that exercises sort/search/clean rules."""
    return [
        {
            "number": "10",
            "authors": "McCarl, B.A. and Other, O.",
            "title": "Corn Futures and Climate",
            "bookjour": "Test Journal",
            "location": "",
            "volume": "1",
            "pages": "1-10",
            "year": "2019",
            "vitatyp": "J",
            "subject1": "energy",
            "subject2": "policy",
            "duplicateoknumber": "0",
            "pdfpresent": "0",
            "pdfpath": "",
            "dateentered": "01/01/2024 12:00:00 PM",
        },
        {
            "number": "11",
            "authors": "McCarl, B.A.",
            "title": "Water Policy Note",
            "bookjour": "Other Journal",
            "location": "",
            "volume": "",
            "pages": "",
            "year": "2020",
            "vitatyp": "J",
            "subject1": "water",
            "subject2": "",
            "duplicateoknumber": "0",
            "pdfpresent": "0",
            "pdfpath": "",
            "dateentered": "02/01/2024 12:00:00 PM",
        },
        {
            "number": "20",
            "authors": "Smith, J. and Jones, K.L.",
            "title": "A Book Chapter on Methods",
            "bookjour": "Some Press",
            "location": "Boston",
            "volume": "",
            "pages": "55-78",
            "year": "2018",
            "vitatyp": "B",
            "subject1": "methods",
            "subject2": "",
            "duplicateoknumber": "0",
            "pdfpresent": "0",
            "pdfpath": "",
            "dateentered": "03/01/2024 12:00:00 PM",
        },
        {
            "number": "30",
            "authors": "McCarl, B.A.",
            "title": "NSF Proposal Alpha",
            "bookjour": "",
            "location": "",
            "volume": "",
            "pages": "",
            "year": "2024",
            "vitatyp": "PR",
            "subject1": "",
            "subject2": "",
            "funding_year": "2024",
            "total_amount": "100000",
            "usable_amount": "90000",
            "decision": "Pending",
            "duplicateoknumber": "0",
            "pdfpresent": "0",
            "pdfpath": "",
            "dateentered": "04/01/2024 12:00:00 PM",
        },
        {
            "number": "31",
            "authors": "McCarl, B.A.",
            "title": "Duplicate Title Case",
            "bookjour": "American Journal",
            "location": "",
            "volume": "",
            "pages": "",
            "year": "2021",
            "vitatyp": "J",
            "subject1": "duplicate",
            "subject2": "",
            "duplicateoknumber": "0",
            "pdfpresent": "0",
            "pdfpath": "",
            "dateentered": "05/01/2024 12:00:00 PM",
        },
        {
            "number": "32",
            "authors": "Other, O.",
            "title": "duplicate title case",
            "bookjour": "American Journal",
            "location": "",
            "volume": "",
            "pages": "",
            "year": "2022",
            "vitatyp": "J",
            "subject1": "",
            "subject2": "",
            "duplicateoknumber": "0",
            "pdfpresent": "0",
            "pdfpath": "",
            "dateentered": "06/01/2024 12:00:00 PM",
        },
        {
            "number": "40",
            "authors": "von Neumann, J. and Morgenstern, O.",
            "title": "Theory of Games",
            "bookjour": "Princeton",
            "location": "",
            "volume": "",
            "pages": "",
            "year": "",
            "vitatyp": "B",
            "subject1": "game theory",
            "subject2": "",
            "duplicateoknumber": "0",
            "pdfpresent": "0",
            "pdfpath": "",
            "dateentered": "07/01/2024 12:00:00 PM",
        },
        {
            "number": "41",
            "authors": "Lee, K. and Cohen, J.W., Jr.",
            "title": "Suffix Handling in Names",
            "bookjour": "Journal of Things",
            "location": "",
            "volume": "",
            "pages": "100-120",
            "year": "September/October 2016",
            "vitatyp": "JR",
            "subject1": "",
            "subject2": "",
            "duplicateoknumber": "0",
            "pdfpresent": "0",
            "pdfpath": "",
            "dateentered": "08/01/2024 12:00:00 PM",
        },
    ]
