"""
Parity test: shared modules that should be byte-identical across desktop & web.

After normalizing line endings (CRLF vs LF), these files MUST match between
``paperfile/modules/`` and ``paperfile-web/modules/``. Any drift here means
the two platforms have started to diverge silently for that piece of logic.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DESKTOP_MODULES = REPO_ROOT / "paperfile" / "modules"
WEB_MODULES = REPO_ROOT / "paperfile-web" / "modules"


# Modules that the project intends to keep in lock-step. If any of these
# diverges, we want a loud test failure so the parity report flags it.
LOCKSTEP_MODULES = [
    "backup.py",
    "outputdata.py",
    "searchdata.py",
    "sortdata.py",
    "ui_elements.py",
    "update_page.py",
]


def _normalized_sha(path: Path) -> str:
    """SHA-256 of the file with CRLF normalized to LF and trailing whitespace stripped per line."""
    text = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    # Don't strip trailing whitespace, the diff already showed only line-ending drift.
    return hashlib.sha256(text).hexdigest()


@pytest.mark.parametrize("name", LOCKSTEP_MODULES)
def test_lockstep_modules_byte_identical(name):
    desktop = DESKTOP_MODULES / name
    web = WEB_MODULES / name
    assert desktop.is_file(), f"missing desktop module: {desktop}"
    assert web.is_file(), f"missing web module: {web}"

    d = _normalized_sha(desktop)
    w = _normalized_sha(web)
    assert d == w, (
        f"{name} has drifted between desktop and web "
        f"(sha desktop={d}, web={w}). Run `diff --strip-trailing-cr -u "
        f"{desktop} {web}` to see the difference."
    )
