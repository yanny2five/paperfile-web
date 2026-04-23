"""modules.filter_cnt_by_vita — public export drops."""

from modules.filter_cnt_by_vita import (
    DEFAULT_PUBLIC_DROP_VITATYPES,
    filter_out_vita_types,
    vitatyp_code,
    vita_types_reference_lines,
)


def test_default_drop_codes():
    assert DEFAULT_PUBLIC_DROP_VITATYPES == frozenset({"JD", "OI", "PR", "F"})


def test_vitatyp_code():
    assert vitatyp_code({"vitatyp": "j"}) == "J"
    assert vitatyp_code({}) == ""


def test_filter_removes_drops_keeps_rest():
    rows = [
        {"number": "1", "vitatyp": "J", "title": "A"},
        {"number": "2", "vitatyp": "JD", "title": "Draft"},
        {"number": "3", "vitatyp": "PR", "title": "Prop"},
        {"number": "4", "vitatyp": "B", "title": "Book"},
    ]
    kept, stats = filter_out_vita_types(rows, DEFAULT_PUBLIC_DROP_VITATYPES)
    nums = {r["number"] for r in kept}
    assert nums == {"1", "4"}
    assert stats["JD"] == 1
    assert stats["PR"] == 1


def test_vita_types_reference_nonempty():
    lines = vita_types_reference_lines()
    assert any(line.startswith("J\t") for line in lines)
    assert any("Funding Proposals" in line for line in lines)
