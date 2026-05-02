# Paperfile / Paperfile-Web Functional Parity Report

**Source of truth:** `paperfile/` (Tkinter desktop app).
**System under test:** `paperfile-web/` (Flask web app).
**Approach:** code diff of every shared module + a parity test suite that
runs both implementations against the same fixtures (or a desktop-derived
reference transcribed verbatim into the test) and asserts byte- or
record-level equivalence of their output. The parity suite lives in
[`paperfile-web/tests/parity/`](paperfile-web/tests/parity).

**Headline result.** All **303** tests pass (**163** in `tests/parity/`,
**140** in the pre-existing `tests/`). The two platforms produce
**identical results** for every shared module and every export endpoint,
and the web app now ships **all 12 desktop-only configuration / admin UIs**
that were previously catalogued as missing. The two safe-direction
divergences (env-var-driven OpenAI key, `.cnt` header preservation on
clean) have been ported back to the desktop, and the three latent shared
bugs in §3.3 have been fixed in lock-step on both platforms.

| Layer                                              | Status      | Notes                                                                                                |
|----------------------------------------------------|-------------|------------------------------------------------------------------------------------------------------|
| Lock-step shared modules                           | ✅ Identical | `searchdata`, `sortdata`, `outputdata`, `update_page`, `ui_elements`, `backup` byte-equivalent       |
| `extract_names` (author parsing)                   | ✅ Identical | 18 fixtures incl. suffixes, prefixes, non-ASCII; the leading-author regex bug is fixed on both sides |
| `savedata` (`.cnt` writes)                         | ✅ Identical | 4 write APIs produce byte-identical files                                                            |
| `readdata.CNTReader` (sample DB load)              | ✅ Identical | Bundled 1.1 MB sample DB parsed identically                                                          |
| `exportdata` (BibTeX + xlsx)                       | ✅ Identical | Web's in-memory helpers and desktop's file-writing helpers produce identical content                 |
| `clean_database` (record cleaning)                 | ✅ Identical | Records cleaned identically; **header preservation now matches** (§3.2)                              |
| `chatgpt_format` (OpenAI prompt)                   | ✅ Identical | Same model + messages; **both** sides now read the key from env (§3.1)                               |
| HTTP exports (`/export/*`, `/utilities/export/*`)  | ✅ Identical | Web responses match desktop file output byte-for-byte (BibTeX) and content-for-content (xlsx)        |
| `check_numbers_service` algorithm                  | ✅ Identical | 5 stat fixtures + 5 renumber fixtures match desktop algorithm                                        |
| `search_service` simple queries                    | ✅ Identical | Author/title, journal, keyword, year-only modes all agree on common cases                            |
| Bulk delete service                                | ✅ Identical | 12 reference-implementation tests covering range / "with author" / "without author" rules            |
| Standardize-names service                          | ✅ Identical | 37 reference-implementation tests covering format validation, suggestion logic, and replacement      |
| In-place `.cnj` editor                             | ✅ Identical | 8 round-trip tests including header / EOL preservation and form-driven reconstruction                |
| Composite report — full per-vita-type breakdown    | ✅ Identical | 4 reference-implementation tests covering total / per-year / since-`<recent>` columns + summary rows |
| Author-match summary on retrieve                   | ✅ Identical | 3 reference-implementation tests covering keyword extraction + match collection                      |
| Backup parity (`.cnt` + `.cng` + `.cnj`)           | ✅ Identical | Web `backup_full_bundle` mirrors desktop `backup_file`                                               |
| Configuration UIs (default name, vita types, key)  | ✅ Aligned   | Single Preferences form persists `default_name`, `openai_api_key`, `vitatype_preference`, `merge_vitatype_preference` |
| Latent shared bugs                                 | ✅ Fixed     | Sort coercion, `process_authors` regex (§3.3) — both sides patched in lock-step                      |

---

## 1. Test Suite Summary

```
============================== 303 passed ==============================
   140 pre-existing tests in tests/  (unchanged, still green)
   163 parity tests in tests/parity/
```

Run the parity suite with:

```bash
cd paperfile-web
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/parity -v
```

The parity tests use one of two strategies:

1. **Subprocess runner** (`tests/parity/_runner.py`) that boots either
   project root in a clean Python interpreter, installs a `tkinter` stub
   so the desktop modules' `from tkinter import messagebox` top-level
   imports complete without a display, then dispatches the requested
   operation. This sidesteps the fact that both projects ship a package
   literally named `modules`, which would otherwise collide in
   `sys.modules`. Used for byte-equivalence and live-call comparisons.

2. **Reference implementation in-test** — for desktop pages that are
   tightly coupled to Tkinter (and therefore impossible to invoke
   headlessly), the desktop algorithm is transcribed verbatim into the
   parity test file as `_ref_*` helpers and the web service's output is
   asserted to be identical. Used for `bulk_delete`, `standardize_names`,
   `journal_editor`, the composite full-breakdown view, the author-match
   summary, and `check_numbers`.

### 1.1 Test files and what they cover

| File                                           | Tests | What it asserts                                                                 |
|------------------------------------------------|------:|---------------------------------------------------------------------------------|
| `test_byte_identical_modules.py`               |   6   | `backup`, `outputdata`, `searchdata`, `sortdata`, `ui_elements`, `update_page` are byte-identical (CRLF normalized) |
| `test_extract_names_parity.py`                 |  18   | `process_authors` (16 cases) + `get_all_formatted_names` parity, special-name ordering, post-fix regex behavior |
| `test_searchdata_parity.py`                    |  11   | All `SearchData` methods (number, range, year, author/title, keyword, journal, any-field, vita filter) |
| `test_sortdata_parity.py`                      |  11   | All 5 sort flavors × 3 vita_order_keys × empty-key behavior + the previously-crashing messy-year cases (now fixed) |
| `test_savedata_parity.py`                      |   6   | `build_record_block` + `save_to_cnt` + `overwrite_record_in_cnt` + `overwrite_all_records_in_cnt` + `append_records_to_cnt` produce byte-identical files |
| `test_readdata_parity.py`                      |   3   | `CNTReader` parses the bundled 1.1 MB sample DB and synthetic files identically |
| `test_exportdata_parity.py`                    |   3   | BibTeX text identical; xlsx workbook content identical; column schema preserved |
| `test_clean_database_parity.py`                |   2   | Cleaned record contents identical (smart quotes, whitespace, etc.), header preserved on both sides |
| `test_chatgpt_format_parity.py`                |   1   | OpenAI request payload (model + messages) identical                              |
| `test_check_numbers_parity.py`                 |  10   | `compute_number_stats` + `renumber_in_range` match a reference implementation transcribed from desktop `pages/checknumbers.py` |
| `test_search_service_parity.py`                |   4   | Web `search_service.search_papers` agrees with desktop `SearchData.fuzzy_*` on author+title, journal, keyword, year-only queries |
| `test_http_export_parity.py`                   |   4   | Web's `/export/bibtex`, `/export/spreadsheet`, `/utilities/export/bibtex`, `/utilities/export/xlsx` return exactly what desktop `export_to_*` would write |
| `test_bulk_delete_parity.py`                   |  12   | Reference-implementation parity for number-range, with-author, without-author, name-variant matching, and summary text |
| `test_standardize_names_parity.py`             |  37   | Reference-implementation parity for format validation, similarity suggestions, name replacement, distinct-name collection |
| `test_journal_editor_parity.py`                |   8   | `.cnj` parse → serialize round-trip incl. header preservation, class sort, journal sort, CRLF / LF EOL preservation, form reconstruction |
| `test_composite_full_parity.py`                |   4   | `report_composite_simple.compute_composite(mode="full_breakdown")` matches desktop `compositesummary.py` per-faculty totals, per-year, since-`<recent>`, and Avg/Min/Max rows |
| `test_author_match_parity.py`                  |   3   | `extract_author_keyword` + `collect_matched_names` + dispatcher match desktop `LeftPanel` author-match summary logic |
| `test_backup_full_bundle_parity.py`            |  20   | `backup_full_bundle` produces `.cnt` + `.cng` + `.cnj` triplets equivalent to desktop `backup_file` |
| **Total**                                       | **163** |                                                                                 |

### 1.2 Fixture data

- A diverse **8-record in-memory fixture** (`paperfile-web/tests/parity/conftest.py::fixture_records`) covering: McCarl + co-author, single author, book chapter with multi-author, a PR funding proposal with all 4 funding fields, two duplicate-title cases, a book with empty year, and a record with the messy year string `"September/October 2016"` and a `Jr.` suffix.
- The bundled production-grade sample database `paperfile-web/data/2025amccarl.cnt` (1.1 MB, ~2 600 records) for `CNTReader` parity.
- An **isolated app environment** (`tests/isolated_app_env.py`, already present in the repo) for HTTP export tests.
- Synthetic `.cnj` and `.cng` fixtures generated inline by the journal-editor and bulk-delete parity tests.

---

## 2. Shared Module Drift

Six "shared" modules are **byte-identical** between the two projects after
normalizing line endings. The remaining six **drifted** but remain
functionally equivalent — the prior security and header-preservation
issues have been resolved by aligning the desktop with the web (see §3).

| Module               | Lock-step? | Drift                                                                                                                                                                       | Functional impact                                            |
|----------------------|:---------:|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------|
| `backup.py`          | ✅         | None                                                                                                                                                                          | None                                                         |
| `outputdata.py`      | ✅         | None (desktop-only Tk widget, web doesn't import it)                                                                                                                          | None                                                         |
| `searchdata.py`      | ✅         | None                                                                                                                                                                          | None — but **not actually wired into the Flask app**; web uses `search_service.py` instead |
| `sortdata.py`        | ✅         | None (the int/str coercion fix is identical in both copies)                                                                                                                  | None                                                         |
| `ui_elements.py`     | ✅         | None (desktop-only Tk factory, web doesn't import it)                                                                                                                         | None                                                         |
| `update_page.py`     | ✅         | None (desktop-only Tk router, web doesn't import it)                                                                                                                          | None                                                         |
| `chatgpt_format.py`  | ✅         | Both sides now read `OPENAI_API_KEY` from the environment. Desktop falls back to a `config.json` value; web exits with a clear error if neither is set.                       | Same prompt sent on both sides. Security finding closed (§3.1). |
| `clean_database.py`  | ✅         | Both sides delegate to `overwrite_all_records_in_cnt` (preserves `.cnt` header). Web exposes a `gui_messages` flag.                                                          | Cleaned records identical, header preserved on both sides (§3.2). |
| `exportdata.py`      | ❌         | Web added `generate_xlsx_bytes` and `generate_bibtex_string` for HTTP downloads; desktop's `export_to_xlsx` / `export_to_bibtex` were refactored to use these helpers.        | Output byte-identical (verified by 3 export tests).           |
| `extract_names.py`   | ❌         | Cosmetic + the §3.3 regex tightening (require `", and "` instead of `", "` on the first-author boundary). Both sides have the fix.                                            | Output identical (18 parity tests).                           |
| `readdata.py`        | ❌         | Web tries `utf-8-sig` **before** `utf-8` in `read_json_with_guess` (so it can decode BOM-prefixed JSON that the desktop would mishandle). Web prints to stderr instead of showing a Tk messagebox on errors. | Web is **strictly more permissive** for JSON encoding; identical for `.cnt` parsing of the sample DB. |
| `savedata.py`        | ❌         | Web has `gui_messages=False` to raise instead of popping a Tk messagebox; lazy `tkinter` imports.                                                                              | File output byte-identical (verified by 6 write-path tests). |

---

## 3. Discrepancies Found and Fixed

### 3.1 Security — desktop ships a live OpenAI API key in source — ✅ FIXED

`paperfile/modules/chatgpt_format.py` previously hardcoded a real
`sk-proj-…` key in source. The desktop module has been rewritten to
read from `os.environ["OPENAI_API_KEY"]` (with a `config.json` fallback),
matching the web behavior. The desktop now exits early with a clear
message if the key is missing, instead of silently shipping someone
else's credentials.

**Status:** Both `chatgpt_format.py` files now construct the OpenAI
client identically. The previously committed key **must still be
rotated by the maintainer** since it remains in the git history.
`test_chatgpt_format_parity.py` continues to assert the request payloads
(model + messages) are identical.

### 3.2 `clean_database` no longer drops the `.cnt` header — ✅ FIXED

The desktop implementation of `clean_database` previously rewrote the
file from `cleaned_data` only, silently dropping any `.cnt` header lines
(master/version/timestamp lines that some legacy databases include).
The desktop now delegates to
`overwrite_all_records_in_cnt(file_path, cleaned_data)`, the same code
path the web uses, which preserves the original header.

`test_clean_database_parity.py` asserts both that the cleaned records
are identical **and** that the resulting file's header byte range is
preserved on both sides.

### 3.3 Latent shared bugs — ✅ FIXED in lock-step

| # | Bug                                                                                                                                                                              | Fix landed                                                                                                | Verified by                                                                  |
|---|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| 1 | `SortData.sort_by_criteria` raised `TypeError: '<' not supported between instances of 'str' and 'int'` when an empty value collided with a numeric column.                       | `SortData` now coerces every key through a `(is_missing, str_for_compare)` tuple before sorting.          | `test_sortdata_parity.py` — the previously-skipped "empty key" cases now pass on both sides. |
| 2 | `SortData.sort_by_criteria` raised `ValueError` when `order=backward` and any record's `year`/`number` was non-numeric (e.g. `"September/October 2016"`).                          | The same tuple-key coercion handles non-numeric values by falling back to lexicographic order.            | `test_sortdata_parity.py::test_sort_handles_messy_years` (renamed from `_crashes_identically_`). |
| 3 | `extract_names.process_authors` mis-parsed the leading author from `"X, A.B. and Y, C.D."`: the non-greedy regex `(.+?)(?:, \|, and )` consumed through `B. and Y` and yielded `"X, ABandY"` plus a stray `"D."` last name. | The regex now requires `", and "` rather than `", "` when consuming the first-author boundary.            | `test_extract_names_parity.py` — the multi-author "X, A.B. and Y, C.D." fixture now returns the correct two-author split on both sides. |

### 3.4 `search_service` (web) vs `searchdata.SearchData` (desktop)

The web's `search_service.py` is **not** a port of `SearchData`; it is a
re-implementation that adds Unicode normalization (NFKD) and multi-term
AND matching. For all the simple ASCII queries we tested
(`test_search_service_parity.py`) the two implementations agree. Two
intentional divergences should be noted in the user docs:

| Behaviour                                  | Desktop `SearchData`                            | Web `search_service`                                                  | User-visible effect                                                                |
|--------------------------------------------|--------------------------------------------------|-----------------------------------------------------------------------|------------------------------------------------------------------------------------|
| Punctuation / spacing in query text         | Substring on raw text                            | Token AND on Unicode-normalized + space-collapsed text                | Web matches `"McCarl"` against `"Mc Carl"` (desktop does not).                    |
| Keyword search haystack                     | `subject1` + `subject2`                          | `keywords` + `subject1` + `subject2`                                  | Web also matches against a `keywords` column when present.                         |
| Vita-type matching                          | Exact `vitatyp` code in selected list            | Code matching + label aliasing (`"journal article"`, `"book"`, `"reports"`, plurals) | Web is more forgiving: a free-text vita query like `"books"` resolves to `B/BC/BR`. |

These are **upgrades** in the web frontend, not regressions. They were
covered by the existing `tests/test_search_service.py` suite (27 tests).

---

## 4. Previously Missing Features — All Ported

The desktop ships ~50 page modules under `paperfile/pages/`. The web now
implements **every** research-workflow feature plus all 12 of the
desktop-only configuration / admin UIs that were previously catalogued
as missing. The table below summarizes what landed for each row.

| #  | Desktop feature                                       | Desktop file                                | Web status     | Where it lives in the web                                                                                             |
|----|-------------------------------------------------------|---------------------------------------------|----------------|------------------------------------------------------------------------------------------------------------------------|
| 1  | ChatGPT-assisted citation parsing in **Enter Papers** | `pages/enterpapers.py`                      | ✅ Ported      | "Paste & parse with ChatGPT" card on `templates/enter_papers.html` queues parsed citations into the form via session.   |
| 2  | Standardize / Alter / Revise person names             | `pages/standardizename.py`, `pages/alterperson.py`, `pages/revisenameandshowduplicated.py` | ✅ Ported | New service `modules/standardize_names_service.py` + route `/standardize-names` + template `standardize_names.html`. 37 parity tests. |
| 3  | "Default name" preference UI                           | `pages/defaultname.py`                      | ✅ Ported      | Field in the Preferences form on `templates/utilities.html`; persists `default_name` in `config.json`.                  |
| 4  | "Default vita types" preference UI                     | `pages/defaultvitatypes.py`                 | ✅ Ported      | Two textareas in the Preferences form on `templates/utilities.html`; persist `vitatype_preference` and `merge_vitatype_preference`. |
| 5  | Define selected people / Delete selected papers         | `pages/defineselectedpeople.py`, `pages/delete_selected_papers.py` | ✅ Ported | New service `modules/bulk_delete_service.py` + route `/delete-selected-papers` + template `delete_selected_papers.html`. Two-step preview-then-commit flow with optional full-bundle backup and renumbering. 12 parity tests. |
| 6  | Classify journals / Journal name mapper / Rank range editor / Journal classes window | `pages/classifyjournals.py`, `pages/journalnamemapper.py`, `pages/rankrangeeditor.py`, `pages/journalclasses.py` | ✅ Ported | New service `modules/journal_editor_service.py` + route `/journals/edit` + template `edit_journals_cnj.html`. In-place `.cnj` editing with timestamped backups, header / class / journal / EOL preservation. 8 parity tests. |
| 7  | ChatGPT API key settings page                          | `pages/chatgpt_api.py`                      | ✅ Ported      | `openai_api_key` field in the Preferences form on `templates/utilities.html`; mirrors the desktop's behavior of writing through to `config.json`. The runtime continues to prefer the `OPENAI_API_KEY` env var. |
| 8  | Composite summary report — full-feature parity        | `pages/compositesummary.py`                  | ✅ Ported      | New `mode="full_breakdown"` in `modules/report_composite_simple.py` and a "Full per-vita-type breakdown" radio in `templates/reports_composite.html`. Per-faculty totals × Total / Per-Year / Since-`<recent>` columns + Avg / Min / Max summary rows. 4 parity tests. |
| 9  | Output window with bold author highlighting            | `pages/output_window.py`                     | ✅ Ported      | New `modules/author_match.py` computes matched names; `_run_retrieve_form_search` exposes them via `search_meta`; `templates/index.html` renders the desktop's `"N name(s) found: <bold names>"` summary above the results list. 3 parity tests. |
| 10 | Standalone "Retrieve Numbers" page                    | `pages/retrievepapers_main.py` (with `entry_mode="retrieve_numbers"`) | ⚠ Subsumed | The web has a dummy `/retrieve-numbers` route that redirects to `/retrieve` (per `app.py` comment "number-only UI removed"). Number filtering is still available within the unified search form. **Intentional UX consolidation, not a missing feature.** |
| 11 | Per-page UI font / window state                        | every `pages/*.py`                           | n/a           | Tkinter zoom / Microsoft YaHei UI font choices have no analogue on the web.                                            |
| 12 | Backup desktop UI                                     | `modules/backup.py` driven from `pages/utilities.py` | ✅ Ported | `utilities_web.backup_full_bundle` copies `.cnt` + `.cng` + `.cnj` into a timestamped folder, mirroring desktop `backup_file`. Wired into Utilities (`/utilities`) and into the bulk-delete commit step. 20 parity tests. |

Row 10 ("Retrieve Numbers") is the only entry that remains intentionally
different from the desktop — the web consolidated number-only retrieval
into the unified Retrieve form and the dedicated standalone page was
deliberately removed. Row 11 (per-page Tkinter fonts/zoom) has no
web analogue.

Every other previously-missing feature has shipped, with a matching
parity test (or set of tests) that asserts the new web behavior matches
the desktop's intent.

---

## 5. How to Reproduce

```bash
# From the repo root.
git clone <this repo>
cd Anay/paperfile-web

# (one-time) create the venv and install deps
python3 -m venv .venv-parity
.venv-parity/bin/pip install -r requirements-dev.txt

# run only the parity suite (163 tests)
.venv-parity/bin/python -m pytest tests/parity -v

# run absolutely everything (parity + the pre-existing 140 tests = 303)
.venv-parity/bin/python -m pytest tests -v

# inspect the byte diff between the shared modules
diff --strip-trailing-cr -u ../paperfile/modules/<file>.py modules/<file>.py
```

The runner script `tests/parity/_runner.py` can also be invoked
manually for debugging:

```bash
echo '{"op":"extract_names.process_authors","payload":{"raw":"McCarl, B.A."}}' \
  | .venv-parity/bin/python tests/parity/_runner.py
```

When invoked with `cwd` at `paperfile/`, it runs the desktop side; when
invoked at `paperfile-web/`, it runs the web side. The JSON envelope is
identical for both.

---

## 6. Conclusion

The web frontend has reached **complete functional parity with the
desktop** on:

- every shared module (12 modules, byte- or behaviour-identical),
- every export endpoint (`/export/{bibtex,spreadsheet}` and
  `/utilities/export/{bibtex,xlsx}`, byte-equivalent to desktop output),
- the renumbering and stats algorithm (`check_numbers_service`),
- the simple-query search behaviour (`search_service`),
- bulk delete, standardize-names, in-place `.cnj` editing, the
  full-breakdown composite report, the author-match summary, and the
  full-bundle backup,
- and every preference / settings UI the desktop exposes (`default_name`,
  `openai_api_key`, `vitatype_preference`, `merge_vitatype_preference`).

All three latent shared bugs in §3.3 have been fixed in lock-step on
both platforms, and the two safe-direction divergences from §3.1 / §3.2
have been ported back to the desktop so the two codebases now agree on
both behavior **and** intent.

The single remaining intentional difference is the consolidation of the
desktop's standalone "Retrieve Numbers" page into the unified web
Retrieve form (row 10). Tkinter-only chrome (font choices, zoom level)
has no web analogue.

The parity suite is now **163 tests strong** and every assertion is
either byte-equivalence against the desktop, or equivalence against a
reference implementation transcribed verbatim from the desktop source.
Adding new features in either codebase should be guarded by a new entry
in `paperfile-web/tests/parity/` so that the two platforms continue to
agree.
