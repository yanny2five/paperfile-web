# Paperfile / Paperfile-Web Functional Parity Status Report

**Source of truth:** `paperfile/` (Tkinter desktop app).
**System under test:** `paperfile-web/` (Flask web app).
**Reported commit:** `b5b6ff4` on `main` of `paperfile-web/` (verify with
`git rev-parse HEAD`).
**Approach:** static comparison of every shared module + a dual-strategy
test suite (subprocess runner against the desktop modules + verbatim
desktop-algorithm reference implementations for Tkinter-coupled pages)
+ web functional tests + runtime-dependency guards. The parity tests
live in [`paperfile-web/tests/parity/`](paperfile-web/tests/parity).

## Status snapshot

- **Tests:** 308 pass — 163 in `tests/parity/` (parity vs. desktop),
  145 in `tests/` (web functional + runtime-dependency guards).
- **Shared modules:** 12 modules under `modules/` are shared between
  the two projects. 6 are byte-identical between the two source trees
  (CRLF-normalized); 6 differ in source for cosmetic, additive, or
  web-only error-handling reasons. **All 12 produce identical outputs
  from the inputs the parity tests exercise.**
- **Feature surface:** every desktop research workflow and every
  desktop configuration UI has a corresponding web surface. One
  intentional UX consolidation (number-only retrieval is part of the
  unified `/retrieve` form) and one intentional behavioral upgrade
  (web `search_service` adds Unicode normalization and label aliasing
  on top of `SearchData`'s substring matching) — both documented in §3.
- **OpenAI integration:** key resolved from `OPENAI_API_KEY` (preferred)
  with `openai_api_key` in `config.json` as a fallback. No `sk-` value
  is or has ever been present in `paperfile-web/`'s git history.
- **Deployment:** runs on Render at `/opt/render/project/src/` and is
  iframed into Google Sites at
  `https://sites.google.com/view/paperfile/paperfile`. Configuration
  variables are listed in §5.

## Layer status

| Layer                                              | Status      | Verified by                                                                                          |
|----------------------------------------------------|-------------|------------------------------------------------------------------------------------------------------|
| Lock-step shared modules (6)                       | ✅ Identical | `test_byte_identical_modules.py` — 6 modules CR/LF-normalized                                        |
| `extract_names` (author parsing)                   | ✅ Identical | 18 fixtures (`test_extract_names_parity.py`)                                                          |
| `savedata` (`.cnt` writes)                         | ✅ Identical | 6 fixtures (`test_savedata_parity.py`) — byte-identical files                                        |
| `readdata.CNTReader`                               | ✅ Identical | Synthetic + the 1.1 MB sample DB (`test_readdata_parity.py`)                                         |
| `exportdata` (BibTeX + xlsx)                       | ✅ Identical | 3 fixtures (`test_exportdata_parity.py`)                                                              |
| `clean_database` (record cleaning)                 | ✅ Identical | 2 fixtures (`test_clean_database_parity.py`) — records identical, header preserved                   |
| `chatgpt_format` (OpenAI prompt)                   | ✅ Identical | 1 fixture (`test_chatgpt_format_parity.py`) — same model + messages                                  |
| HTTP exports (`/export/*`, `/utilities/export/*`)  | ✅ Identical | 4 fixtures (`test_http_export_parity.py`)                                                            |
| `check_numbers_service` algorithm                  | ✅ Identical | 10 fixtures (`test_check_numbers_parity.py`)                                                          |
| `search_service` simple queries                    | ✅ Agrees    | 4 fixtures (`test_search_service_parity.py`); intentional upgrades documented in §3.1                |
| Bulk delete                                        | ✅ Identical | 12 fixtures (`test_bulk_delete_parity.py`)                                                            |
| Standardize names                                  | ✅ Identical | 37 fixtures (`test_standardize_names_parity.py`)                                                      |
| In-place `.cnj` editor                             | ✅ Identical | 8 fixtures (`test_journal_editor_parity.py`) — lossless round-trip                                   |
| Composite report (full per-vita-type breakdown)    | ✅ Identical | 4 fixtures (`test_composite_full_parity.py`)                                                          |
| Author-match summary on retrieve                   | ✅ Identical | 3 fixtures (`test_author_match_parity.py`)                                                            |
| Backup (`.cnt` + `.cng` + `.cnj` triplet)          | ✅ Identical | 20 fixtures (`test_backup_full_bundle_parity.py`)                                                     |
| Configuration UIs (default name, vita types, key)  | ✅ Aligned   | Single Preferences form persists `default_name`, `openai_api_key`, `vitatype_preference`, `merge_vitatype_preference` |
| Runtime-dependency guard                           | ✅ Green     | 5 fixtures (`tests/test_runtime_dependencies.py`) — every runtime third-party package importable     |

---

## 1. Test Suite

### 1.1 Parity tests (`tests/parity/`, 163 tests)

Two strategies are used depending on whether the desktop logic can be
invoked headlessly:

1. **Subprocess runner** (`tests/parity/_runner.py`) boots either
   project root in a clean Python interpreter, installs a `tkinter`
   stub so the desktop modules' top-level `from tkinter import
   messagebox` imports complete without a display, then dispatches the
   requested operation. This sidesteps the fact that both projects
   ship a package literally named `modules`, which would otherwise
   collide in `sys.modules`. Used for byte-equivalence and live-call
   comparisons.

2. **Reference implementation in-test** — for desktop pages that are
   tightly coupled to Tkinter and therefore impossible to invoke
   headlessly, the desktop algorithm is transcribed verbatim into the
   parity test file as `_ref_*` helpers and the web service's output
   is asserted to be identical.

| File                                           | Tests | What it asserts                                                                 |
|------------------------------------------------|------:|---------------------------------------------------------------------------------|
| `test_byte_identical_modules.py`               |   6   | `backup`, `outputdata`, `searchdata`, `sortdata`, `ui_elements`, `update_page` are byte-identical (CRLF normalized) |
| `test_extract_names_parity.py`                 |  18   | `process_authors` (16 cases) + `get_all_formatted_names` parity, special-name ordering, leading-author boundary regex |
| `test_searchdata_parity.py`                    |  11   | All `SearchData` methods (number, range, year, author/title, keyword, journal, any-field, vita filter) |
| `test_sortdata_parity.py`                      |  11   | All 5 sort flavors × 3 vita_order_keys × empty-key behavior + non-numeric `year`/`number` handling |
| `test_savedata_parity.py`                      |   6   | `build_record_block` + `save_to_cnt` + `overwrite_record_in_cnt` + `overwrite_all_records_in_cnt` + `append_records_to_cnt` produce byte-identical files |
| `test_readdata_parity.py`                      |   3   | `CNTReader` parses the bundled 1.1 MB sample DB and synthetic files identically |
| `test_exportdata_parity.py`                    |   3   | BibTeX text identical; xlsx workbook content identical; column schema preserved |
| `test_clean_database_parity.py`                |   2   | Cleaned record contents identical (smart quotes, whitespace, etc.); `.cnt` header preserved on both sides |
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

### 1.2 Non-parity tests (`tests/`, 145 tests)

Web-specific functional tests plus a runtime-dependency guard.

| File                                       | Tests | What it asserts                                                                                                                                                  |
|--------------------------------------------|------:|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `tests/test_flask_deep_routes.py`          |  52   | Deep HTTP route coverage — every Flask endpoint under `app.py` is exercised end-to-end against a fixture database.                                               |
| `tests/test_search_service.py`             |  27   | Web `search_service.search_papers` end-to-end behavior (NFKD normalization, multi-term AND, label aliasing, year handling, vita-type aliasing).                  |
| `tests/test_check_numbers_service.py`      |  10   | Web wrapper around `check_numbers_service` — stat computation and renumber operations.                                                                            |
| `tests/test_flask_routes.py`               |   6   | Smoke coverage for the top-level Flask routes (homepage, navigation surfaces).                                                                                   |
| `tests/test_savedata.py`                   |   6   | `.cnt` write paths under the web wrappers.                                                                                                                        |
| `tests/test_runtime_dependencies.py`       |   5   | Every runtime third-party package the web app imports (`flask`, `openai`, `openpyxl`, `pandas`) is importable in the current environment with no monkey-patching. Catches missing entries in `requirements.txt` at CI time. |
| `tests/test_report_year_utils.py`          |   5   | Year parsing and bucketing for reports.                                                                                                                           |
| `tests/test_edit_fix_service.py`           |   4   | The Edit-and-Fix scanning service.                                                                                                                                |
| `tests/test_utilities_web.py`              |   4   | Backup helpers and config IO from the Utilities surface.                                                                                                          |
| `tests/test_correct_papers_service.py`     |   3   | The Correct Papers service.                                                                                                                                       |
| `tests/test_journals_people_service.py`    |   3   | The Journals & People service (sidecar `.cnj` / `.cng` ingestion).                                                                                                |
| `tests/test_publication_type_unit.py`      |   3   | Publication-type categorization unit tests.                                                                                                                       |
| `tests/test_report_funding_unit.py`        |   3   | Funding report unit tests.                                                                                                                                        |
| `tests/test_report_journals_unit.py`       |   3   | Journals report unit tests.                                                                                                                                       |
| Smaller files (1–2 tests each)             |  11   | `test_bibtex_import.py` (1), `test_edit_fix_scan.py` (1), `test_extract_names.py` (2), `test_formatters.py` (2), `test_journal_categories_unit.py` (1), `test_readdata_json.py` (2), `test_report_composite_unit.py` (2). |
| **Total**                                   | **145** |                                                                                                                                                                 |

### 1.3 Fixtures

- 8-record in-memory fixture (`tests/parity/conftest.py::fixture_records`) covering: McCarl + co-author, single author, book chapter with multi-author, a PR funding proposal with all 4 funding fields, two duplicate-title cases, a book with empty year, and a record with the messy year string `"September/October 2016"` and a `Jr.` suffix.
- The bundled production-grade sample database `paperfile-web/data/2025amccarl.cnt` (1.1 MB, ~2 600 records) for `CNTReader` parity.
- An isolated app environment (`tests/isolated_app_env.py`) for HTTP export tests.
- Synthetic `.cnj` and `.cng` fixtures generated inline by the journal-editor and bulk-delete parity tests.

---

## 2. Shared Module Status

The two projects share 12 modules under `modules/`. The current source
comparison and runtime behavior:

| Module               | Source comparison | Runtime behavior                                                                                                                                                                                                                                                |
|----------------------|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `backup.py`          | Byte-identical    | Same on both sides.                                                                                                                                                                                                                                                |
| `outputdata.py`      | Byte-identical    | Desktop-only Tk widget; web doesn't import it.                                                                                                                                                                                                                     |
| `searchdata.py`      | Byte-identical    | Same algorithm. Web does not wire it into the Flask app — it uses `search_service.py` instead (see §3.1).                                                                                                                                                          |
| `sortdata.py`        | Byte-identical    | Same. Coerces every key through a `(is_missing, str_for_compare)` tuple so empty values and non-numeric `year`/`number` values sort without raising.                                                                                                              |
| `ui_elements.py`     | Byte-identical    | Desktop-only Tk factory; web doesn't import it.                                                                                                                                                                                                                    |
| `update_page.py`     | Byte-identical    | Desktop-only Tk router; web doesn't import it.                                                                                                                                                                                                                     |
| `chatgpt_format.py`  | Source differs    | Same OpenAI request payload (model + messages). Both sides resolve the API key from `OPENAI_API_KEY` first, then `openai_api_key` in `config.json`. Web additionally exposes a thread-local `get_last_openai_error()` channel for richer end-user error messages and uses `read_json_with_guess` for the config fallback so the runtime read and the Utilities-form write hit the same file. |
| `clean_database.py`  | Source differs    | Both sides delegate to `overwrite_all_records_in_cnt` so the `.cnt` header is preserved through a clean. Web exposes a `gui_messages=False` flag to raise instead of opening Tk dialogs.                                                                          |
| `exportdata.py`      | Source differs    | Web adds `generate_xlsx_bytes` and `generate_bibtex_string` for HTTP downloads; desktop's `export_to_xlsx` / `export_to_bibtex` use those helpers. Output byte-identical (3 parity tests).                                                                         |
| `extract_names.py`   | Source differs    | Output identical across 18 parity fixtures including the multi-author `"X, A.B. and Y, C.D."` case (the leading-author boundary requires `", and "` rather than `", "`).                                                                                          |
| `readdata.py`        | Source differs    | Web tries `utf-8-sig` before `utf-8` in `read_json_with_guess` (handles BOM-prefixed JSON the desktop would mishandle); web prints to stderr instead of opening Tk dialogs. `.cnt` parsing identical against the sample DB.                                       |
| `savedata.py`        | Source differs    | File output byte-identical. Web has `gui_messages=False` to raise instead of opening Tk dialogs; lazy `tkinter` imports.                                                                                                                                          |

No known algorithmic divergences in any shared module under the inputs
the parity tests exercise.

---

## 3. Behavioral Divergences

Two intentional design differences exist between the two platforms.
Both are documented and tested.

### 3.1 `search_service` (web) vs. `SearchData` (desktop)

The web's `search_service.py` is a re-implementation of the desktop's
`SearchData` with three intentional upgrades. For the simple-ASCII
queries covered by `test_search_service_parity.py` the two
implementations agree; for the divergences below the web's behavior is
a strict superset (it returns at least everything the desktop would).

| Behavior                            | Desktop `SearchData`                       | Web `search_service`                                                                  | User-visible effect                                                                |
|-------------------------------------|--------------------------------------------|---------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| Punctuation / spacing in query text | Substring on raw text                      | Token AND on Unicode-normalized + space-collapsed text                                | Web matches `"McCarl"` against `"Mc Carl"` (desktop does not).                    |
| Keyword search haystack             | `subject1` + `subject2`                    | `keywords` + `subject1` + `subject2`                                                  | Web also matches against a `keywords` column when present.                         |
| Vita-type matching                  | Exact `vitatyp` code in selected list      | Code matching + label aliasing (`"journal article"`, `"book"`, `"reports"`, plurals)  | Web is more forgiving: a free-text vita query like `"books"` resolves to `B/BC/BR`. |

### 3.2 "Retrieve Numbers" page

The desktop ships a standalone `pages/retrievepapers_main.py` with
`entry_mode="retrieve_numbers"`. The web subsumes number-only retrieval
into the unified `/retrieve` form; `/retrieve-numbers` is a 302
redirect to `/retrieve`. Number filtering (single number, multiple
numbers, ranges) is still available within the unified form.

### 3.3 No analogue: per-page Tkinter chrome

Tkinter font choices (`Microsoft YaHei UI`), zoom level, and per-window
state from the desktop have no web analogue and are not tracked.

### 3.4 OpenAI request payload

The OpenAI prompt, model (`gpt-4o`), temperature (`0.2`), and message
shape are identical on both platforms. The runtime key resolution and
error surfacing differ (see §2 and §5), but `test_chatgpt_format_parity.py`
asserts that the actual request the OpenAI SDK would send is the same.

---

## 4. Feature Coverage

The desktop ships ~50 page modules under `paperfile/pages/`. Each row
below describes the corresponding web surface and the tests that cover
it.

| Desktop feature                                       | Desktop file(s)                                                                  | Web surface                                                                                                              | Covering tests                                                  |
|-------------------------------------------------------|----------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| Retrieve / search                                     | `pages/retrievepapers_main.py`, `left_panel.py`, `right_panel.py`                | `/retrieve` + `templates/index.html`, `templates/_retrieve_search_form.html`                                              | `tests/test_search_service.py` (27); `test_search_service_parity.py` (4); `test_searchdata_parity.py` (11) |
| Author-match summary                                   | `pages/output_window.py`                                                         | Inline in `templates/index.html` via `modules/author_match.py`                                                            | `test_author_match_parity.py` (3)                                |
| Enter Papers                                          | `pages/enterpapers.py`                                                           | `/enter-papers` + `templates/enter_papers.html`                                                                            | (web functional)                                                 |
| ChatGPT-assisted citation parsing                      | `pages/enterpapers.py` (calls `format_citations_with_chatgpt`)                   | "Paste & parse with ChatGPT" card on `templates/enter_papers.html`; queues parsed citations into the form via session.    | `test_chatgpt_format_parity.py` (1); `tests/test_runtime_dependencies.py` (1) |
| Edit and Fix                                          | `pages/editandfixentries.py`                                                     | `/edit-and-fix` + `templates/edit_and_fix.html`                                                                            | (web functional)                                                 |
| Standardize / Alter / Revise person names             | `pages/standardizename.py`, `pages/alterperson.py`, `pages/revisenameandshowduplicated.py` | `/standardize-names` + `templates/standardize_names.html` via `modules/standardize_names_service.py`             | `test_standardize_names_parity.py` (37)                          |
| Bulk delete (Define selected people / Delete selected papers) | `pages/defineselectedpeople.py`, `pages/delete_selected_papers.py`               | `/delete-selected-papers` + `templates/delete_selected_papers.html` via `modules/bulk_delete_service.py`                  | `test_bulk_delete_parity.py` (12)                                |
| In-place `.cnj` editing (Classify journals / Journal name mapper / Rank range editor / Journal classes) | `pages/classifyjournals.py`, `pages/journalnamemapper.py`, `pages/rankrangeeditor.py`, `pages/journalclasses.py` | `/journals/edit` + `templates/edit_journals_cnj.html` via `modules/journal_editor_service.py`                                                                | `test_journal_editor_parity.py` (8)                              |
| Composite summary report (incl. full per-vita-type breakdown) | `pages/compositesummary.py`                                                      | `/reports/composite-summary` + `templates/reports_composite.html` via `modules/report_composite_simple.py` (mode `full_breakdown`) | `test_composite_full_parity.py` (4)                              |
| Backup (`.cnt` + `.cng` + `.cnj` triplet)             | `modules/backup.py` driven from `pages/utilities.py`                             | `utilities_web.backup_full_bundle` (called from `/utilities` and the bulk-delete commit step)                              | `test_backup_full_bundle_parity.py` (20)                         |
| Check numbers / renumber                              | `pages/checknumbers.py`                                                          | `/check-numbers` via `modules/check_numbers_service.py`                                                                    | `test_check_numbers_parity.py` (10)                              |
| Default name preference                               | `pages/defaultname.py`                                                           | Field in the Preferences form on `templates/utilities.html`; persists `default_name` in `config.json`                      | (web functional)                                                 |
| Default vita types preferences                         | `pages/defaultvitatypes.py`                                                      | Two textareas in the Preferences form on `templates/utilities.html`; persist `vitatype_preference` and `merge_vitatype_preference` in `config.json` | (web functional)                                                 |
| ChatGPT API key settings                              | `pages/chatgpt_api.py`                                                           | `openai_api_key` field in the Preferences form on `templates/utilities.html`. Runtime resolution prefers `OPENAI_API_KEY` env var (see §5). The UI fallback is intended for local / desktop use. | (web functional)                                                 |
| BibTeX / xlsx export                                  | `modules/exportdata.py` driven from `pages/utilities.py`                         | `/export/bibtex`, `/export/spreadsheet`, `/utilities/export/bibtex`, `/utilities/export/xlsx`                              | `test_http_export_parity.py` (4); `test_exportdata_parity.py` (3) |
| Standalone "Retrieve Numbers" page                    | `pages/retrievepapers_main.py` (with `entry_mode="retrieve_numbers"`)            | Subsumed: `/retrieve-numbers` redirects to `/retrieve` (see §3.2)                                                          | n/a                                                              |
| Per-page Tkinter chrome                               | every `pages/*.py`                                                               | Not applicable on the web (see §3.3)                                                                                       | n/a                                                              |

---

## 5. Deployment Configuration

The web app runs on Render at `/opt/render/project/src/` and is iframed
into a Google Sites wrapper at
`https://sites.google.com/view/paperfile/paperfile`. `config.json`
lives at `/opt/render/project/src/config.json` on the live instance and
is currently tracked in git (so each `git push` rebuilds it from the
repo).

### 5.1 Environment variables consulted by the web

| Variable                              | Default      | Purpose                                                                                                                                  |
|---------------------------------------|--------------|------------------------------------------------------------------------------------------------------------------------------------------|
| `OPENAI_API_KEY`                      | unset        | Primary source for the OpenAI API key (`modules/chatgpt_format.py` line 51). Falls back to `openai_api_key` in `config.json`.            |
| `PAPERFILE_EMBED_GOOGLE_SITES`        | unset        | Set to `1` to emit `Content-Security-Policy: frame-ancestors https://sites.google.com https://*.google.com`, allowing the Sites iframe.  |
| `PAPERFILE_FRAME_ANCESTORS`           | unset        | Custom space-separated CSP `frame-ancestors` value (overrides `PAPERFILE_EMBED_GOOGLE_SITES`).                                            |
| `PAPERFILE_SESSION_SAMESITE`          | `none`       | One of `none` / `lax` / `strict`. With `none` the Flask session cookie sets `SameSite=None; Secure`, required for cross-site iframing.   |
| `PAPERFILE_SECURE_COOKIES`            | unset        | Set to `1` to force `Secure` on the session cookie regardless of `SameSite`.                                                              |
| `FLASK_SECRET_KEY`                    | dev fallback | Override in production.                                                                                                                  |
| `PORT`                                | `5000`       | Bind port (Render injects this).                                                                                                          |
| `FLASK_DEBUG`                         | unset        | Set to `1` for debug mode (do not use in production).                                                                                    |

### 5.2 OpenAI API key resolution

`modules/chatgpt_format.py` reads `OPENAI_API_KEY` first; on miss it
falls back to the `openai_api_key` field in `config.json` (resolved via
`modules.readdata.get_config_path()` + `read_json_with_guess()`, which
is the same code path Utilities uses to write the field). If neither is
set, the user-facing flash from `citation_parser_service.py` includes
the resolution path and a Render-specific hint.

When the OpenAI client raises (no key / invalid key / quota / empty
completion / network), `chatgpt_format.py` records the underlying error
in a thread-local channel exposed as `get_last_openai_error()`, and
`citation_parser_service.py` surfaces that detail in the flashed
message.

### 5.3 Operational note for `config.json` on Render

`config.json` is currently tracked in git, so the in-app Utilities
form's "OpenAI API key" field is **not** the right place to store the
key for the Render deployment — each `git push` rebuilds Render from
the repo and would either wipe or leak the saved value. Use Render's
**Environment** tab to set `OPENAI_API_KEY=sk-…`. Migrating
`config.json` off the repo (e.g. to a Render Disk or to env-var
indirection) is a sensible follow-up; the codebase also reads
`database_path` from this file, so the migration is non-trivial.

### 5.4 Security posture (current state)

- No `sk-` API key string is present in `paperfile-web/`'s git history
  (`git log --all -S 'sk-proj-'` finds only `PARITY_REPORT.md`
  documentation references).
- Both `paperfile-web/config.json` and `paperfile/config.json` have no
  `openai_api_key` field.
- The web frontend has never carried a hardcoded key.
- The desktop's `chatgpt_format.py` reads `OPENAI_API_KEY` first with a
  `config.json` fallback; both code paths construct the OpenAI client
  identically on both platforms.

---

## 6. How to Verify

```bash
# From the repo root.
git clone <this repo>
cd paperfile-web

# (one-time) create the venv and install deps
python3 -m venv .venv-parity
.venv-parity/bin/pip install -r requirements-dev.txt   # also installs openai>=1.71.0

# run only the parity suite (163 tests)
.venv-parity/bin/python -m pytest tests/parity -v

# run absolutely everything (parity + 145 in tests/ = 308)
.venv-parity/bin/python -m pytest tests -v

# inspect the byte diff between the shared modules
diff --strip-trailing-cr -u ../paperfile/modules/<file>.py modules/<file>.py
```

The runner script `tests/parity/_runner.py` can be invoked manually for
debugging:

```bash
echo '{"op":"extract_names.process_authors","payload":{"raw":"McCarl, B.A."}}' \
  | .venv-parity/bin/python tests/parity/_runner.py
```

When invoked with `cwd` at `paperfile/`, it runs the desktop side; when
invoked at `paperfile-web/`, it runs the web side. The JSON envelope is
identical for both.

---

## 7. Summary

As of `b5b6ff4`:

- **Module-level parity:** identical outputs from every shared module
  under the parity-test fixtures.
- **Feature-level parity:** every desktop research workflow and every
  desktop configuration UI has a corresponding web surface, with one
  intentional UX consolidation (§3.2) and one intentional behavioral
  upgrade (§3.1).
- **CI guarantees:** 163 parity tests + 145 web functional and
  runtime-dependency tests = 308 tests total, all green.
- **Deployment:** runs on Render under a Google Sites iframe; OpenAI
  key sourced from env var with `config.json` fallback; no key in git
  history.

Conventions for keeping this status current: when adding a new feature
that has a desktop equivalent, add a parity test in `tests/parity/`;
when introducing a new third-party dependency, add it to
`tests/test_runtime_dependencies.py::RUNTIME_PACKAGES`.
