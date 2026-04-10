"""modules.bibtex_import — parse BibTeX file to CNT-shaped dicts."""

from __future__ import annotations

from pathlib import Path

from modules.bibtex_import import parse_bibtex_file_to_records


def test_parse_bibtex_file_to_records_minimal(tmp_path: Path):
    bib = tmp_path / "t.bib"
    bib.write_text(
        """
@article{key2020,
  author = {Doe, Jane and Smith, John},
  title = {A Test Paper},
  journal = {Journ Name},
  year = {2020},
}
""",
        encoding="utf-8",
    )
    recs = parse_bibtex_file_to_records(str(bib))
    assert len(recs) == 1
    assert "Test Paper" in recs[0].get("title", "")
    assert recs[0].get("authors", "")
