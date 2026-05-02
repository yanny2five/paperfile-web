"""
Parity test: ``modules.readdata.CNTReader``.

The two implementations have cosmetic differences and one behavioural
divergence (``read_json_with_guess`` puts ``utf-8-sig`` first on web). For
.cnt parsing, both must produce identical record lists.
"""

from __future__ import annotations

import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_CNT = REPO_ROOT / "paperfile-web" / "data" / "2025amccarl.cnt"


def test_cnt_reader_parses_real_database_identically(parity, tmp_path):
    """Both CNTReaders return the same record list for the bundled sample DB."""
    if not SAMPLE_CNT.exists():
        # The web project ships a sample .cnt; if it's missing we can't compare.
        import pytest

        pytest.skip(f"Sample .cnt missing at {SAMPLE_CNT}")

    target = tmp_path / "sample.cnt"
    shutil.copy2(SAMPLE_CNT, target)

    desktop, web = parity("readdata.read_cnt", {"path": str(target)})
    assert len(desktop["records"]) == len(web["records"]), (
        f"CNTReader returns different record counts: "
        f"desktop={len(desktop['records'])} web={len(web['records'])}"
    )
    assert desktop["records"] == web["records"], (
        "CNTReader records disagree on the sample database"
    )


def test_cnt_reader_handles_simple_synthetic_file(parity, tmp_path):
    """Synthetic two-record .cnt is parsed identically."""
    cnt = tmp_path / "synthetic.cnt"
    cnt.write_text(
        "MASTER HEADER\n"
        "number||1\nauthors||A1\ntitle||T1\nbookjour||J1\n"
        "location||\nvolume||\npages||\nyear||2020\nvitatyp||J\n"
        "subject1||\nsubject2||\nduplicateoknumber||0\npdfpresent||0\npdfpath||\n"
        "dateentered||01/01/2024 12:00:00 PM\n*********$$$$$$$$$$$$\n"
        "number||2\nauthors||A2\ntitle||T2\nbookjour||J2\n"
        "location||\nvolume||\npages||\nyear||2021\nvitatyp||J\n"
        "subject1||\nsubject2||\nduplicateoknumber||0\npdfpresent||0\npdfpath||\n"
        "dateentered||02/01/2024 12:00:00 PM\n*********$$$$$$$$$$$$\n",
        encoding="utf-8",
    )

    desktop, web = parity("readdata.read_cnt", {"path": str(cnt)})
    assert desktop == web
    nums = [r["number"] for r in desktop["records"]]
    assert nums == ["1", "2"]


def test_cnt_reader_missing_file_returns_empty(parity, tmp_path):
    """When the file doesn't exist, both return empty data without raising."""
    missing = tmp_path / "does_not_exist.cnt"
    desktop, web = parity("readdata.read_cnt", {"path": str(missing)})
    assert desktop["records"] == []
    assert web["records"] == []
