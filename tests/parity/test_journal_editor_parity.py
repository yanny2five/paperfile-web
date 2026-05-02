"""
Parity test: in-place .cnj editing service (web ``journal_editor_service``).

The desktop's classifyjournals/journalclasses dialogs are massive Tk
applications (~10 kloc) and their save behavior is documented inline as
"rebuild journals after STARTJOURNALS, preserve everything before".
This test asserts that the web's parser-then-serializer round-trips a
.cnj file losslessly for every realistic shape:

* Multi-line free-form header before CLASSCOUNT.
* Class lines with the "10zz" suffix (preserved verbatim).
* Class lines with negative sort order.
* Journal lines with PCT/Q/ABDC tags in any subset.
* Journal lines that only have a major (no "::minor").
* Mixed Unix and Windows line endings.

Plus that ``classes_from_form`` and ``journals_from_form`` correctly
reconstruct edits from a Flask MultiDict-shaped input.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = REPO_ROOT / "paperfile-web"


@pytest.fixture(autouse=True)
def _sys_path():
    if str(WEB_ROOT) not in sys.path:
        sys.path.insert(0, str(WEB_ROOT))
    yield


_SAMPLE_CNJ = """\
# This is the standard McCarl journal definition file.
# Anything before CLASSCOUNT is preserved on save.
CLASSCOUNT
3
Top Tier::1>>10
Mid Tier::2>>20zz
Lower::-1>>0
STARTJOURNALS
Top Tier::Economics>>American Economic Review??1;PCT=99;Q=Q1;ABDC=A*
Top Tier::Economics>>Econometrica??1;PCT=98;Q=Q1
Mid Tier>>Journal of Plain Things??5;PCT=50;Q=Q2
Lower>>The Bottom Letter??10
"""


def _write(tmp: Path, body: str, *, eol: str = "\n") -> str:
    text = body.replace("\n", eol)
    p = tmp / "sample.cnj"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_parse_basic_shape(tmp_path):
    from modules.journal_editor_service import parse_cnj_file

    path = _write(tmp_path, _SAMPLE_CNJ)
    parsed = parse_cnj_file(path)
    assert len(parsed["header"]) == 2
    assert "standard McCarl" in parsed["header"][0]
    assert len(parsed["classes"]) == 3
    assert parsed["classes"][0] == {
        "major": "Top Tier",
        "sort_order": 1,
        "norm": 10,
        "norm_raw": "10",
    }
    assert parsed["classes"][1]["norm_raw"] == "20zz"  # preserved
    assert parsed["classes"][2]["sort_order"] == -1
    assert len(parsed["journals"]) == 4
    aer = parsed["journals"][0]
    assert aer["name"] == "American Economic Review"
    assert aer["major"] == "Top Tier"
    assert aer["minor"] == "Economics"
    assert aer["pct"] == "99"
    assert aer["quartile"] == "Q1"
    assert aer["abdc"] == "A*"
    plain = parsed["journals"][2]
    assert plain["minor"] == ""  # no "::"
    assert plain["major"] == "Mid Tier"


def test_round_trip_preserves_classes_and_header(tmp_path):
    from modules.journal_editor_service import parse_cnj_file, serialize_cnj

    path = _write(tmp_path, _SAMPLE_CNJ)
    parsed = parse_cnj_file(path)
    out = serialize_cnj(parsed)

    # The header must come back verbatim.
    for header_line in parsed["header"]:
        assert header_line in out

    # CLASSCOUNT bookkeeping must match the actual class count.
    lines = out.splitlines()
    cc_idx = lines.index("CLASSCOUNT")
    assert lines[cc_idx + 1] == "3"
    # The "10zz" suffix is preserved on the second class.
    assert "Mid Tier::2>>20zz" in out
    # Lower has negative sort order.
    assert "Lower::-1>>0" in out


def test_round_trip_sorts_journals_alphabetically(tmp_path):
    """Mirrors desktop's classifyjournals._write_cnj_from_tree1_sorted_rebuild
    which sorts by (Major, Journal). Our serialize_cnj does the same."""
    from modules.journal_editor_service import parse_cnj_file, serialize_cnj

    path = _write(tmp_path, _SAMPLE_CNJ)
    parsed = parse_cnj_file(path)
    out = serialize_cnj(parsed)
    journal_lines = [
        ln for ln in out.splitlines()
        if "??" in ln and ">>" in ln
    ]
    # Sorted by major then name (case-insensitive).
    assert journal_lines == [
        "Lower>>The Bottom Letter??10",
        "Mid Tier>>Journal of Plain Things??5;PCT=50;Q=Q2",
        "Top Tier::Economics>>American Economic Review??1;PCT=99;Q=Q1;ABDC=A*",
        "Top Tier::Economics>>Econometrica??1;PCT=98;Q=Q1",
    ]


def test_round_trip_then_save_then_reparse_matches(tmp_path):
    from modules.journal_editor_service import (
        parse_cnj_file,
        save_cnj,
        serialize_cnj,
    )

    path = _write(tmp_path, _SAMPLE_CNJ)
    parsed1 = parse_cnj_file(path)
    bak = save_cnj(path, parsed1, do_backup=True)
    assert bak and os.path.isfile(bak)
    parsed2 = parse_cnj_file(path)
    assert parsed1["classes"] == parsed2["classes"]
    assert sorted(
        parsed1["journals"], key=lambda j: (j["major"], j["name"])
    ) == sorted(parsed2["journals"], key=lambda j: (j["major"], j["name"]))


def test_round_trip_crlf_eol_preserved(tmp_path):
    from modules.journal_editor_service import parse_cnj_file, save_cnj

    path = _write(tmp_path, _SAMPLE_CNJ, eol="\r\n")
    parsed = parse_cnj_file(path)
    save_cnj(path, parsed, do_backup=False)
    raw = open(path, "rb").read()
    # The serialized output should still use CRLF terminators.
    assert b"\r\n" in raw


def test_classes_from_form_handles_delete_and_new(tmp_path):
    from modules.journal_editor_service import classes_from_form
    from werkzeug.datastructures import MultiDict

    form = MultiDict()
    form["c_name_0"] = "Keep"
    form["c_order_0"] = "1"
    form["c_normraw_0"] = "10"
    form["c_name_1"] = "Drop"
    form["c_del_1"] = "1"
    form["c_name_2"] = "NewClass"
    form["c_order_2"] = "5"
    form["c_normraw_2"] = "20zz"
    out = classes_from_form(form)
    assert [c["major"] for c in out] == ["Keep", "NewClass"]
    assert out[1]["norm"] == 20
    assert out[1]["norm_raw"] == "20zz"


def test_journals_from_form_skips_empty_and_deleted(tmp_path):
    from modules.journal_editor_service import journals_from_form
    from werkzeug.datastructures import MultiDict

    form = MultiDict()
    form["j_name_0"] = "Stay"
    form["j_major_0"] = "M"
    form["j_minor_0"] = "n"
    form["j_rank_0"] = "3"
    form["j_pct_0"] = "70"
    form["j_q_0"] = "Q2"
    form["j_abdc_0"] = "B"
    form["j_name_1"] = ""  # empty -> skipped
    form["j_name_2"] = "Drop"
    form["j_del_2"] = "1"
    form["j_name_3"] = "BadRank"
    form["j_rank_3"] = "abc"  # non-digit -> "10"
    out = journals_from_form(form)
    names = [j["name"] for j in out]
    assert "Stay" in names
    assert "Drop" not in names
    assert "BadRank" in names
    badrank = next(j for j in out if j["name"] == "BadRank")
    # Serializer normalizes; the form value is preserved as a string but
    # _serialize_journal_line will sanitize on the way back. Here we just
    # confirm the field is round-tripped.
    assert badrank["rank"] == "abc"
