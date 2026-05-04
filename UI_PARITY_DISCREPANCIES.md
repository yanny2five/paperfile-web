# Paperfile — UI / UX Parity Discrepancies (Web vs Desktop)

A top-down walk through every screen in the application, comparing the
desktop application (`paperfile/`) against the web application
(`paperfile-web/`). Each section captures one menu item or one screen,
with every UI/UX divergence for that screen collected in a single table.

> **Sources of truth.** The desktop is canonical. Each row cites the desktop
> file (and line where possible) and the corresponding web file (template /
> route).
>
> **Severity legend.** **Critical** = entire feature missing or wrong;
> **High** = visible function gap or destructive action without confirm;
> **Medium** = label/flow drift or feature gap that affects user
> understanding; **Low** = wording drift or cosmetic; **OK** = matches or
> intentional platform difference; **Web superset** = web has something
> desktop doesn't.

---

## Status snapshot — fixes already shipped vs deferred

This section is the running log of which discrepancies the web is now in
parity on. Tables below retain the original wording for context but each
fixed row is annotated with **✅ FIXED** + the change description.

### Fixed in this round (regression-tested in `tests/test_ui_parity_fixes.py`)

| # | Section | Fix |
|---|---|---|
| 5 | Dashboard | Added a second "Current file | Total entries" strip below the menu grid (`templates/dashboard.html`). |
| 7 | Dashboard | Added `Retrieve Paper Numbers` tile that links to the existing `/retrieve-numbers` route. |
| 16 | Enter Papers | Save now flashes desktop-verbatim `Duplicate File Number: The file number {n} already exists in the data.` when the duplicate-OK number matches an existing record (`app.py:enter_papers`). |
| 21 | Retrieve form | Restrict-vita-types panel now shows `Select All` / `Unselect All` buttons (`templates/_retrieve_search_form.html`). |
| 22 | Retrieve form | Restrict-vita-types panel now shows the `Check vita types to INCLUDE` header. |
| 26 | Retrieve form | `Select by Vita Type` mode now shows First/Last Year wanted boxes + auto-checks the Restrict vita types checklist (and the legacy free-text `Text to find in Vita Type` input is gone). |
| 27 | Retrieve form | `Select by Year` mode now shows First/Last Year wanted boxes (and the legacy single `Year` input is gone). |
| 34–38 | Retrieve form | Field labels normalised to desktop wording: `Text in Keyword fields`, `Text in Book/Journal field`, `Text in any field`, `Optional more text in Author`, `Optional more text in Title`. |
| 39–46 | Retrieve form / engine | Per-mode validation now emits desktop-verbatim error strings (one for author/title, keyword, book/journal, any-field, vita-type, year). Banner relabelled `Invalid search criteria.` |
| 60 | Correct Papers Edit | Submit button label is now `Save changes` (was `Save to .cnt`). |
| 63 | Correct Papers Edit | Added a separate `Delete this paper` form that POSTs `action=delete` with a JS `confirm()` prompt; route handler removes the record via `overwrite_all_records_in_cnt`. |
| 64 | Correct Papers Edit | The `Number` field is now editable; saving with a number that collides with another record requires explicit overwrite confirmation (JS `confirm()` + server check + hidden `confirm_overwrite=1` flag). |
| 77 | Correct Elements | Field selector switched from a `<select>` of raw column names to radios with human-readable labels (`Titles`, `Authors`, `Journal (bookjour)`, `Rest of location`, `Volume`, `Pages`, `Keywords (subject1+2)`). |
| 143 | Delete Selected Papers | Commit-delete form now wraps submission in `window.confirm()` before posting. |

### Deferred (out-of-scope for this session) and why

| # | Item | Why deferred |
|---|---|---|
| 70, 81–83 | Examine Duplicate Titles — full interactive viewer/merger | Multi-day rebuild of a stateful side-by-side editor; web currently shows a count + scan only. Tracked separately. |
| 79 | Correct Elements — Save / Backup / Exit (full editor) | Requires per-row inline editing and a transactional save path; current web is browse-only. Will reuse the same `record_from_correct_form` + `overwrite_record_in_cnt` plumbing. |
| 98 | Classify Journals (entire screen) | Multi-thousand-line desktop subsystem (rank/category editors, batch reclassification). Will be its own change. |
| 99 | Journal Name Mapper (entire screen) | Same scale as Classify Journals — separate effort. |
| 100 | Rank Range Editor | New screen; depends on Classify Journals to land first. |
| 132 | Default Vita Types — checklist UI | Web currently has a textarea-shaped editor; replacing with a checklist is straightforward but touches the persistence path; deferred for the next batch. |

Everything else stays as documented below until reviewed.

---

## Table of contents

| # | Section | Severity highlights |
|---|---|---|
| 1 | Application shell & first-run | Medium — onboarding gap |
| 2 | Main menu / dashboard | Medium — missing tiles, no current-file strip |
| 3 | Enter Papers | High — silent duplicates, missing exit-confirm |
| 4 | Retrieve Papers (search form, per-mode fields, results) | **High×4** — broken Vita Type mode, broken Year mode, missing validation, missing results-window controls |
| 5 | Data Export | Medium — no `Add More`, no `Show/Hide Numbers` |
| 6 | Correct Papers + Edit Paper | **High** — no delete control, no "number exists" confirm |
| 7 | Edit and Fix Entries (hub) | **High** — no interactive Duplicate Titles, browse-only Correct Elements |
| 8 | Standardize Names | (UI not deeply traced — see §16) |
| 9 | Check Numbers | Low — phrasing drift |
| 10 | Journals and People (incl. Classify Journals, Journal Name Mapper, Rank Range Editor, CNJ editor, Alter Person) | **Critical×2** — Classify Journals & Journal Name Mapper entirely missing |
| 11 | Generate Reports | Medium — no copy-to-clipboard; reports not deeply traced |
| 12 | Utilities (incl. Merge, Default Vita Types, Default Name, ChatGPT API Key) | **High** — Merge has no per-vitatype filter; Default Vita Types is a textarea instead of checklist |
| 13 | Delete Selected Papers | Medium — backup affordance reduced |
| 14 | Cross-cutting (modals, error pages, copy-to-clipboard, read-only mode) | Medium |
| 15 | Web-only features (intentional supersets) | n/a |
| 16 | Method & caveats | — |

---

## 1. Application shell & first-run

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 1 | Window / page title | `Paper File System - Department of Agricultural Economics - by K.L.` (`paperfile/main.py:442`) | Per-page `<title>` tags only (e.g. `Paperfile - Main menu`, `Paperfile Search`) | OK — different platform conventions |
| 2 | Required-config first-run flow | Modal `Configure Required Files` (`pages/config_setup.py:13`) with `Database path`, `faculty_file`, `journal_definition_file` pickers + `Continue` / `Quit`; validation `Please choose valid files for all fields before continuing.` (`config_setup.py:176-179`) | **Missing** — web reads `config.json` from disk; if missing the route just errors out | Medium — onboarding gap; web cannot bootstrap a new install through the UI |
| 3 | Init-failure dialog | `Failed to initialize main page:\n{e}` (`main.py:476`); `No database file loaded. Please select a valid database file.` (`pages/mainpage.py:34`) | Generic Flask 500 / `flash()` text in some routes; no consistent error page | Low — different platform idioms |

---

## 2. Main menu / dashboard

Desktop entry: `pages/mainpage.py` (class `Toplevel1`, opened by
`pages.mainpage.start_mainpage`). Web entry: `templates/dashboard.html`
served by `dashboard()` at `app.py:646-653`.

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 4 | Header text (top of menu) | `Personal Bibliographical Database` / `Dr. Bruce A. McCarl` / `Texas A&M University` / `MAIN MENU` (`pages/mainpage.py:69-76`) | Same four lines (`dashboard.html`) | OK |
| 5 | Bottom status strip | `Current file: {path} | Total entries: {n}` (`pages/mainpage.py:114`) | **Missing** — dashboard does not show the loaded database path or record count | Medium — useful situational info — **✅ FIXED** (second strip rendered below the menu grid) |
| 6 | `Exit` button | Present (`pages/mainpage.py:97`) — saves `database_path` then destroys root | **Missing** — only a paragraph `Close this tab when finished.` | Low — browser idiom differs |
| 7 | `Retrieve Paper Numbers` button | Present (`pages/mainpage.py:88`) — opens Retrieve in `entry_mode="retrieve_numbers"` | **Missing** as a top-level tile (the route `/retrieve-numbers` exists but no link points to it) | Medium — user can't reach the numbers-only mode without typing a URL — **✅ FIXED** (tile added to dashboard) |
| 8 | Button order | `Enter Papers` → `Retrieve Papers` → `Retrieve Paper Numbers` → `Data Export` → `Generate Reports` → `Journals and People` → `Correct Papers` → `Edit and Fix Entries` → `Check Numbers` → `Use Utilities` → `Exit` (`pages/mainpage.py:79-100`) | `Enter Papers` → `Journals and People` → `Retrieve Papers` → `Correct Papers` → `Edit and Fix Entries` → `Data Export` → `Check Numbers` → `Generate Reports` → `Use Utilities` (`dashboard.html`) | Low — order differs but every shared item is present |

---

## 3. Enter Papers

Desktop: `pages/enterpapers.py` (full button grid not deeply traced — see
§16 caveats). Web: `enter_papers()` at `app.py:735-882` rendering
`templates/enter_papers.html`.

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 9 | Page title | (window title not explicitly set; uses main shell title) | `Enter Papers — Paperfile` | OK |
| 10 | Top-of-page nav | (none — desktop has window-level menu only) | Two links: `Main menu`, `Retrieve Papers` (`enter_papers.html`) | Low — web extra |
| 11 | Field set | Authors, Title, Journal/book, Location, Volume, Pages, Year, Vita type combo, Subjects (Subject1, Subject2), Funding fields (year, total_amount, usable_amount, decision), duplicateoknumber, pdfpresent, pdfpath | Same fields | OK |
| 12 | ChatGPT clipboard parser | Reachable but not surfaced as a prominent on-page card in this review | Dedicated **`Parse clipboard`** card at the top: `<textarea name="clipboard_text">` + `Parse with ChatGPT` button + conditional `Clear parsed queue` button | **Web superset** — different (arguably better) UX, but not parity |
| 13 | Save buttons | (varies by desktop internals) | `Save new record`; if ChatGPT queue non-empty, also `Save and next ({pos}/{queue})` | **Web superset** for the queue button |
| 14 | Backup-before-save option | (not exposed on Enter Papers; backup lives under Edit and Fix Entries) | Checkbox `Create a timestamped backup folder next to the database before saving (recommended).` | **Web superset** |
| 15 | Validation: failed citation parse | `Failed to process citation: {e}` (`pages/enterpapers.py:837`) | Flash messages: `ChatGPT formatting failed: …` and `ChatGPT returned no parseable entries.` | Low — phrasing drift |
| 16 | Validation: duplicate file number | `messagebox.showinfo("Duplicate File Number", "The file number {file_number} already exists in the data.")` (`enterpapers.py:1100`) | **No equivalent dialog** — web silently saves with `duplicateoknumber=0`; user has no popup distinction | High — silent vs explicit on a destructive condition — **✅ FIXED** (warning flash on save when `duplicateoknumber` matches an existing record) |
| 17 | Validation: missing path | `showerror("Error", "Invalid file path.")` (`enterpapers.py:1058`); `"File path is not set."` (`enterpapers.py:1121`) | Flash: `No active database file. Check config.json database_path.` | Low — phrasing drift |
| 18 | Validation: empty author + title | (handled implicitly in desktop save flow) | Flash: `Enter at least an author or a title before saving.` | OK — web is explicit, desktop implicit |
| 19 | Save-failed-on-exit confirmation | `askyesno("Save Failed", "Failed to save the current entry:\n{e}\n\nExit anyway?")` (`enterpapers.py:1208-1210`) | **Missing** — web has no equivalent (no dedicated exit affordance to begin with) | Low — different navigation paradigm |

---

## 4. Retrieve Papers

The single largest area of divergence. Sub-tables below cover the search
form, per-search-type field visibility, label drift, validation, and
results-window controls.

### 4.1 Form layout

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 20 | Action buttons under the form | **Two** buttons: `Retrieve`, `Done` (`pages/left_panel.py:73-77`) | **Three** affordances: `Retrieve`, `Done`, plus an extra `Data export` mode-bar link (`templates/_retrieve_search_form.html:162-165`, `templates/index.html` mode bar) | Medium — extra surface area not present in desktop |
| 21 | Restrict vita types — `Select All` / `Unselect All` buttons | Both buttons appear when the vita-type panel is shown (`pages/right_panel.py:96-105, 179-180, 193-209`) | **Missing** — user must click each checkbox individually (`templates/_retrieve_search_form.html:153-158`) | High — visible feature gap — **✅ FIXED** (`#vita_select_all`, `#vita_unselect_all`) |
| 22 | Restrict vita types — section header | Explicit `Check vita types to INCLUDE` header (`pages/right_panel.py:90-93`) | **Missing** — `vita-box` `<div>` has no section title or grouped layout (`templates/_retrieve_search_form.html:147-158`) | Medium — discoverability — **✅ FIXED** (header added) |
| 23 | Submit-button label in `edit` mode | `Selection Complete Now Edit` when `edit=True` (`pages/left_panel.py:73`) | (Web exposes this through a separate Correct Papers screen — see §6) | Medium — see §6 |

### 4.2 Per-search-type field visibility

Desktop hides/shows field groups dynamically per `LeftPanel.on_search_method_change`
(`pages/left_panel.py:88-204`). Web uses CSS `mode-<type>` classes.

| # | Search method (radio) | Desktop shows | Web shows | Severity |
|---|---|---|---|---|
| 24 | Select by Number | Single `Paper Number wanted` entry; vita-restrict section (`left_panel.py:95-106`) | (Not on Retrieve page — separate flow) | n/a |
| 25 | Select multiple papers by Number | Number-range section + `First/Last Year wanted` + vita-restrict (`left_panel.py:107-118`) | (Not on Retrieve page) | n/a |
| 26 | **Select by Vita Type** | `First/Last Year wanted` entries + the vita-type radio frame. **No** "Text to find in vita type" field exists at all. (`left_panel.py:119-130`) | Shows a single text box labelled `Text to find in Vita Type` instead of the year boxes; the vita-type radio frame is missing → pressing **Retrieve** always returns 0 results | **High** — wrong field shown, wrong control set, search returns nothing — **✅ FIXED** (year boxes shown; legacy text input removed; restrict-vita panel auto-checks) |
| 27 | **Select by Year** | **Two** entries: `First Year wanted` and `Last Year wanted` (plus vita-restrict) (`left_panel.py:131-142`, `right_panel.py:show_year_range_section` 389-427) | **One** entry labelled `Year` | **High** — single-year-only field cannot represent a range — **✅ FIXED** (First/Last Year wanted boxes are now the only inputs) |
| 28 | Select by Author and/or Title | Four entries: `Text to find in Author field`, `Optional more text in Author`, `Text to find in Title field`, `Optional more text in Title` + `First/Last Year wanted` + vita-restrict (`left_panel.py:143-154`, `right_panel.py:443-461`) | Same four entries (post strict-parity refactor) — minor label drift only (see §4.3) | OK with minor label drift |
| 29 | Select by keyword | Single entry labelled `Text in Keyword fields` + `First/Last Year wanted` + vita-restrict (`left_panel.py:155-166`, `right_panel.py:499`) | Single entry labelled `Keywords and subjects (Subject1 / Subject2)` + year boxes + vita-restrict | Low — label drift only (functional behaviour matches: searches `subject1`+`subject2`) |
| 30 | Select by book or journal title | Entry labelled `Text in Book/Journal field` + year + vita-restrict (`left_panel.py:168-179`, `right_panel.py:526`) | Entry labelled `Text to find in Journal/Book field` + year + vita-restrict | Low — label drift |
| 31 | **Select for text in any field** | Entry labelled `Text in any field` + year + vita-restrict; **on Retrieve, validates the text field has a value AND year fields are both-empty-or-both-filled, else shows an error dialog** (`left_panel.py:181-192, 996`) | Entry labelled `Text to find (any field)` + year + vita-restrict; **no client/server validation — submitting an empty text box returns search results anyway** | **High** — missing input validation + label drift |

### 4.3 Field-label drift (per input)

| # | Web label (current) | Desktop label (canonical) | Desktop reference |
|---|---|---|---|
| 32 | `Text to find in Vita Type` | (no such field exists in desktop — see #26) | n/a — **✅ FIXED** (input removed) |
| 33 | `Year` (single, in "Select by Year") | `First Year wanted` + `Last Year wanted` | `right_panel.py:364-372` — **✅ FIXED** (single input removed; year boxes used) |
| 34 | `Keywords and subjects (Subject1 / Subject2)` | `Text in Keyword fields` | `right_panel.py:499` — **✅ FIXED** |
| 35 | `Text to find in Journal/Book field` | `Text in Book/Journal field` | `right_panel.py:526` — **✅ FIXED** |
| 36 | `Text to find (any field)` | `Text in any field` | `right_panel.py:554` — **✅ FIXED** |
| 37 | `Optional more text in Author field` | `Optional more text in Author` | `right_panel.py:448` — **✅ FIXED** |
| 38 | `Optional more text in Title field` | `Optional more text in Title` | `right_panel.py:459` — **✅ FIXED** |

`Text to find in Author field` and `Text to find in Title field` already
match desktop (`right_panel.py:443, 454`).

### 4.4 Validation messages on Retrieve click

Desktop performs explicit input validation before running a search and
surfaces a `messagebox` to the user. The web currently performs **no**
client- or server-side validation for the equivalent search modes (other
than the year-range parsing wired up during the strict-parity refactor).

| # | Search method | Desktop validation message (verbatim) | Desktop reference | Web behavior today |
|---|---|---|---|---|
| 39 | Select by Number | `No records found with number: {paper_number}` / `No valid paper number entered.` | `left_panel.py:339, 341` | (Not on Retrieve in web) |
| 40 | Select multiple by Number | `No records found within the specified range.` / `Invalid range values entered.` | `left_panel.py:399, 401` | (Not on Retrieve in web) |
| 41 | Select by Vita Type | `Invalid year range values entered. Fill both year boxes or leave both empty.` / `No records found for the selected vita types.` / `No vita types selected.` | `left_panel.py:425-428, 461, 463` | No equivalent — wrong UI shown (see #26) — **✅ FIXED** (year-range error + `No vita types selected.`) |
| 42 | Select by Year | `No records found within the specified year range.` / `Invalid year range values entered.` | `left_panel.py:516, 518` | No equivalent dialog; year-range validation runs server-side but message wording differs — **✅ FIXED** (verbatim `Invalid year range values entered.`) |
| 43 | Select by Author and/or Title | `No records found matching ALL search criteria.` / `Invalid search criteria entered: At least one field must have a value, and year fields must be either both filled or both empty.` | `left_panel.py:790, 793-796` | No pre-search validation; runs search even when all four boxes are blank — **✅ FIXED** (verbatim message; search skipped when invalid) |
| 44 | Select by keyword | `No records found matching the search criteria.` / `Invalid search criteria entered: Keyword field must have a value, and year fields must be either both filled or both empty.` | `left_panel.py:857, 859-862` | No pre-search validation — **✅ FIXED** |
| 45 | Select by book/journal title | (same shape) `Invalid search criteria entered: Book/Journal Title field must have a value, …` | `left_panel.py:924-928` | No pre-search validation — **✅ FIXED** |
| 46 | Select for text in any field | `Invalid search criteria entered: Text in any field must have a value, and year fields must be either both filled or both empty.` | `left_panel.py:992-997` | No pre-search validation — submitting an empty text box returns results — **✅ FIXED** |

> The year-half-filled half-empty rule **is** already enforced by the
> server (`parse_year_range_inputs` in `paperfile-web/modules/search_service.py`),
> but the user-facing message text and the per-search-type "field must
> have a value" half are missing.

### 4.5 Results window controls

Desktop opens a secondary `Search Results` Toplevel (`pages/output_window.py`,
`top.title("Search Results")` at line 55). Web shows results inline under
`<h2>Results</h2>` on the same `/retrieve` page (`templates/index.html`).

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 47 | Results presentation | Separate window with title `Search Results` | Inline section on the same page | OK — different platform metaphor |
| 48 | `Include Journal Ranking` checkbox | Present (`output_window.py:106-109`) | **Missing** | Medium — feature gap |
| 49 | `Show Numbers` / `Hide Numbers` toggle | Present in both `Search Results` and `Data Export Results` (`output_window.py:139-143`, `data_export_window.py:157-160`) | **Missing** — `display_opts["omit_number"]` is hard-coded to `True` in `app.py:2510` | Medium — feature gap |
| 50 | `Export to Spreadsheet` button | Present in results window (`output_window.py:146`) | Present (`Export all to spreadsheet (Excel .xlsx)`) but in the inline area, not a dedicated results window | OK — different placement |
| 51 | `Export to BibTeX` button | Present (`output_window.py:152`) | Present (`Export all to BibTeX (.bib)`) | OK |
| 52 | `Done` button | Present (`output_window.py:133-137`) | (Web uses navigation links instead) | OK — different paradigm |

---

## 5. Data Export

Desktop opens dedicated `Data Export Results` Toplevel
(`pages/data_export_window.py`, `top.title("Data Export Results")` at
line 59). Web reuses `/retrieve` with `session["ui_mode"] = "export"`.

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 53 | Window title | `Data Export Results` | Same Retrieve page; mode bar shows `Data export` link | Low — different metaphor |
| 54 | Two-pane layout | `Results` (left) and `List to Export` (right) panes (`data_export_window.py:71-85`) | Two stacked panels: Results above, staging table below (`templates/index.html`) | OK |
| 55 | `Select All` / `Unselect All` (results-pane scope) | Present (`data_export_window.py:75-90`) | Present in staging form: `Select all` / `Unselect all` | OK |
| 56 | `Clear List` button | Present (`data_export_window.py`) | Present (`Clear list`) — wired to `/staging/clear`, has a `confirm()` JS prompt | OK |
| 57 | `>` (move-checked-to-list) and `X` (clear-checked) middle column | Two narrow buttons (`data_export_window.py:116-126`) | Replaced by `Add selected to export list` and `Remove selected from list` buttons | Low — labels differ but flow preserved |
| 58 | `Add More` / `Done` toggle | Single button whose label switches between `Done` and `Add More` (`data_export_window.py:151-296`) | **Missing** — user navigates back to Retrieve mode via the mode bar; no explicit affordance | Medium — discoverability |
| 59 | `Export to Spreadsheet` / `Export to BibTeX` (export-list scope) | Present (`data_export_window.py:163-174`) | Present (`Export list to BibTeX (.bib)` / `Export list to spreadsheet (Excel .xlsx)`) | OK |

---

## 6. Correct Papers + Edit Paper

Desktop: `Correct Papers` opens the Retrieve hub with `edit=True` and
`select_method="author_title"`; clicking a result opens an `EditPaper`
Toplevel (`pages/editpaper.py`). Web: `correct_papers()` at `app.py:1016`
renders `templates/correct_papers.html` (reuses `_retrieve_search_form.html`);
per-result `Edit` link opens `correct_papers_edit()` at `app.py:1060`,
rendering `templates/correct_papers_edit.html`.

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 60 | Submit-button label on the search form | `Selection Complete Now Edit` (`pages/left_panel.py:73`) when `edit=True` | `Search` (set by `correct_papers()` route) | Medium — wording drift — **✅ PARTIAL** (Edit Paper screen now uses `Save changes` instead of `Save to .cnt`; Correct Papers search-form button label still drifts) |
| 61 | Edit-record window title | (no explicit `.title()` on EditPaper — uses parent title) | `Edit paper {{ record_number }} - Paperfile` | Low |
| 62 | Save button label | (varies by EditPaper internals) | `Save to .cnt` | Low |
| 63 | **Delete-record button on edit screen** | Present — `askyesno("Confirm Deletion", "Are you sure you want to delete record #{number}?")` (`editpaper.py:1001`) | **Missing** — the web edit page has no delete control | **High** — feature gap — **✅ FIXED** (`Delete this paper` button + JS `confirm()`; route deletes via `overwrite_all_records_in_cnt`) |
| 64 | Number-already-exists confirmation | `askyesno("Number Already Exists", "Record number #{n} already exists.\n\nDo you want to overwrite the existing record with the current one?")` (`editpaper.py:863-867`) | **Missing** — no equivalent dialog | **High** — destructive action without confirmation — **✅ FIXED** (Number field is now editable; client `confirm()` + server `confirm_overwrite=1` flag required to overwrite) |
| 65 | Save error / generic | `showerror("Error", "Failed to save: {e}")` (`editpaper.py:933`) | Flash message | Low |
| 66 | Read-only banner | (n/a) | Web shows a `read_only` banner when `PAPERFILE_READ_ONLY=1` (also see §14) | **Web superset** — deployment safety |

---

## 7. Edit and Fix Entries (hub) + sub-screens

Desktop: `pages/editandfixentries.py`. Web: `edit_and_fix_entries()` at
`app.py:1124-1200` rendering `templates/edit_fix.html`.

### 7.1 Hub buttons

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 67 | Hub button: Eliminate Exact Duplicates | `Eliminate Exact Duplicates` | Form section `Eliminate exact duplicates` with confirm checkbox + `Delete duplicate records` button | OK (label drift) |
| 68 | Hub button: Add Keywords (TBD) | `Add Keywords(TBD)` (placeholder on desktop) | **Missing** | OK to omit (it's TBD on desktop too) |
| 69 | Hub button: Standardize Names | Opens `standardizename` page | Cross-link `Open standardize-names page` and also a separate Main-menu-reachable section | Low |
| 70 | Hub button: Find Funky Characters | Opens dialog flow with `No funky records found.` (`editandfixentries.py:489`) | Section `Find funky characters` with `Download tab-separated report` link only — no interactive viewer | Medium — feature gap |
| 71 | Hub button: Correct Elements | Opens `correctelements` page (radios for which field to edit, "String to find in", "(blank for all)") | Cross-link `Open correct-elements browser` (sub-screen has its own gap — see §7.2) | Low at this level |
| 72 | **Hub button: Examine Duplicate Titles** | Opens `duplicatetitles` page with interactive Start/Delete/OK/Next workflow | Replaced by **download-only** report `Download title duplicate report (.tsv)` — no interactive review/delete UI | **High** — major feature gap (see §7.3) |
| 73 | Hub button: Clean Current Database | `Clean Current Database` | Section `Clean current database` with confirm checkbox + `Clean database` button | OK |
| 74 | Hub button: Backup the File | `Backup the File` (single backup of `.cnt`) | **Two** buttons: `Create .cnt backup folder` and `Create full backup (.cnt + .cng + .cnj)` | **Web superset** — extra full-bundle option |
| 75 | Hub button: Exit | `Exit` | (none — uses browser nav) | Low |
| 76 | Web extras under Edit-and-Fix | (none) | `Delete papers in bulk` link → `delete_selected_papers` page (desktop's bulk-delete lives under Utilities) | Cosmetic — different placement |

### 7.2 Correct Elements sub-screen

Desktop: `pages/correctelements.py`. Web:
`/edit-and-fix-entries/correct-elements` at `app.py:1203-1231`.

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 77 | Field selector | **Radio group** with seven choices: `Edit Titles`, `Edit Authors`, `Edit Book or Journal Titles`, `Edit Rest of Location`, `Edit Volume`, `Edit Pages`, `Edit Keywords` (`correctelements.py:33-46`) | **Dropdown** `<select name="field">` with seven options: `title`, `authors`, `journal`, `location`, `volume`, `pages`, `keywords` — **raw codes shown to user** instead of human-readable labels | **High** — dropdown vs radios + raw codes — **✅ FIXED** (radios with human-readable labels; field labels match desktop intent) |
| 78 | Search input label | `String to find in {dynamic field}` (e.g. red `Titles`) + helper `（blank for all）` (full-width parens) (`correctelements.py:49-66`) | `Contains (blank = all)` with placeholder `substring, case-insensitive` | Medium — wording drift |
| 79 | Action buttons | `Refresh`, `Save`, `Backup`, `Exit` (`correctelements.py:69-97`) | `Refresh` only — **no save / backup / exit on this page** | **High** — desktop page allows in-place edit + save; web is browse-only |
| 80 | Validation messages | `Warning No file loaded.` / `Error Record not found for number {n}` (`correctelements.py:138, 293`) | (n/a — page is read-only) | n/a |

### 7.3 Examine Duplicate Titles sub-screen

Desktop: `pages/duplicatetitles.py`. Web: download-only on the
Edit-and-Fix-Entries hub.

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 81 | Page exists | Yes — full interactive screen | **No** equivalent screen — web only emits a `.tsv` download | **High** |
| 82 | Controls | Checkbox `Require SAME vita types`, checkbox `Safe mode (no LSH)`, buttons `Delete`, `Start searching`, `These duplicates are OK`, `Go on to next set`, `Exit` (`duplicatetitles.py:62-96`) | (n/a) | High |
| 83 | Validation messages | `No selection`, `Nothing deleted`, `No match`, `Error No database loaded.`, `Reset OK marks` askyesnocancel, `Reset complete. Updated {n} record(s).`, etc. (`duplicatetitles.py:847-1102`) | (n/a) | High |

### 7.4 Backup the File

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 84 | `Backup Failed` dialog | `showerror("Backup Failed", "Unexpected error:\n{e}")` (`editandfixentries.py:572`) | Flash message | Low |
| 85 | `No file` precondition | `showerror("No file", "No database file selected.")` (`editandfixentries.py:564`) | Flash message | Low |

---

## 8. Standardize Names

Desktop: `pages/standardizename.py` (UI not deeply traced — see §16
caveats). Web: `standardize_names()` at `app.py:1446-1533` rendering
`templates/standardize_names.html`.

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 86 | Page title | (window title not traced) | `Standardize Person Names - Paperfile` | OK |
| 87 | Filter input | (not traced) | `Filter:` + `q` text input + `Filter` button + `clear` link | **Web superset** likely |
| 88 | Suggestion row | (not traced) | Per row: hidden `name_entered`, `replacement` text input with `faculty_list` datalist, `Apply to all matching records` button | Likely OK |
| 89 | "All distinct authors" list | (not traced) | `<h2>All distinct authors ({{ all_count }})</h2>` section | Web extra |
| 90 | Validation messages | `No numbers found for {selected_name}` / `No data found for {selected_name}` (`standardizename.py:190, 199`) | Flash messages, exact wording not verified | Low |

---

## 9. Check Numbers

Desktop: `pages/checknumbers.py`. Web: `check_numbers()` at
`app.py:1630-1681` rendering `templates/check_numbers.html`.

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 91 | Page title | (window title not traced) | `Check Numbers - Paperfile` | OK |
| 92 | Inputs | `Start at paper number` and `Highest number` (text inputs) | `start_at` and `highest` text inputs | Likely matches; verbatim labels not verified |
| 93 | Confirmation control | (presumably dialog-based) | Single checkbox `I understand this will overwrite the entire .cnt file …` + `Apply re-number and save database` button | Medium — desktop dialog vs web inline checkbox |
| 94 | Validation: invalid integers | `showerror("Invalid input", "Please enter valid integers for Start at paper number and Highest number.")` (`checknumbers.py:273-275`) | Flash message; exact wording not verified to match | Low |
| 95 | Validation: no records | `showwarning("No data", "No records found in the database.")` (`checknumbers.py:286`) | Flash message | Low |
| 96 | Validation: no DB | `showerror("Error", "No database loaded.")` (`checknumbers.py:325`) | Flash message | Low |

---

## 10. Journals and People (incl. Classify Journals, Journal Name Mapper, Rank Range Editor, CNJ editor, Alter Person)

Desktop hub: `pages/journalsandpeople.py` with **four** buttons:
`Classify Journals`, `Work with journal classes`, `Define selected people`,
`Exit`. Web: `/journals-and-people` page that **combines** people-editing
and journal-file-upload into one screen, plus a link to `/journals/edit`
for the journal definition editor.

### 10.1 Hub structure

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 97 | Hub paradigm | 4 buttons → 4 dedicated screens | 1 page combining faculty editor + journal upload + cross-link to CNJ editor | High — different paradigm |

### 10.2 Classify Journals

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 98 | **Page exists** | Huge dedicated screen `pages/classifyjournals.py` — 60+ messageboxes; SJR loader + reload + apply mappings; ABDC loader; replace-journal-name workflow with `askyesno("Apply to All", "Change journal name '{a}' to '{b}' in {n} record(s)?")`; case-only-suggestions discovery flow; `Add New Journal` popup; `Edit Spreadsheet Column Notes and Version` popup; export to CSV; SJR/ABDC site browser launch with confirmation | **None** — no equivalent screen at all | **Critical** |

### 10.3 Journal Name Mapper

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 99 | **Page exists** | Dedicated screen `pages/journalnamemapper.py` (~2300 lines) — pairs Database Journals / SJR Journals / ABDC Journals lists, multi-step replace mapping, name-mismatch warnings, `askyesno("Confirm", "You selected nL left and nR right …")`, edit-mapping flow, delete-mapping flow | **None** | **Critical** |

### 10.4 Rank Range Editor

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 100 | **Page exists** | Dedicated `pages/rankrangeeditor.py` — `Rank range editor` window title (`:86`); range validation `Invalid Value Rank {r}: Please enter numeric values only.` (`:656-658`), `Out of Range … 0-100` (`:667-677`), `Invalid Range … Upper bound must be greater than lower bound.` (`:684-686`); `askyesno("Range Check", "Range issues found: …\nSave and close anyway?")` (`:694-695`) | **None** | High |

### 10.5 CNJ (journal definition) editor

Desktop: lives inside `Classify Journals`. Web: dedicated `/journals/edit`
at `app.py:1542-1627` rendering `templates/edit_journals_cnj.html`.

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 101 | Page title | (varies by parent) | `Edit Journals (.cnj) - Paperfile` | OK |
| 102 | Class definitions section | Editable table; sort + normalize fields; per-row validation `Invalid major class` / `Invalid sort` / `Invalid norm` (`pages/journalclasses.py:347-373`) | Editable table with `Add class`, `Save class block (with backup)` buttons; **no row-level validation surfaced** | Medium |
| 103 | Journal entries section | Editable table inside Classify Journals workflow; SJR/ABDC reload; rank update; replace-journal flow | Editable table with `Add journal`, `Save journal block (with backup)` + `journalFilter` text filter | Medium — web is leaner; misses the full Classify Journals workflow |
| 104 | Parse-error UI | (handled by individual save flows) | Page-level `.cnj parse error: {parse_error}` flash | OK — different pattern |
| 105 | **Standalone CNJ editor** | (not standalone — embedded in Classify Journals) | `/journals/edit` is its own page | **Web superset** — extracts what was buried in Classify Journals |

### 10.6 Define Selected People + Alter Person

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 106 | `Define Selected People` page | Dedicated `pages/defineselectedpeople.py` — faculty file load/save (`Faculty file has been saved successfully.` `:459`), `Copied Table copied to clipboard.` (`:491`), autosave warnings | Subsumed into `/journals-and-people` people-editor + `Save people` button | Medium — different paradigm; "copy table to clipboard" feature missing |
| 107 | `Alter Person` per-person dialog | Dedicated Toplevel `pages/alterperson.py` — `Invalid Name Name cannot be empty.` (`:578`), `Name Exists The name '{n}' already exists.` (`:584`), `askquestion("Name Exists","This name already exists. Overwrite it?")` (`:751-754`), `askyesno("Confirm Delete", "Are you sure you want to delete {name}?")` (`:821-824`), `Success {name} has been deleted.` (`:852-854`) | Inline row-level editing only — **no separate per-person dialog with delete confirmation** | **High** — destructive-action confirmation missing |

---

## 11. Generate Reports + sub-pages

Desktop: `pages/generatereports.py` — column-style hub with many report
buttons + `Report for` checkbutton + person combobox. Web:
`generate_reports()` at `app.py:1684-1705` rendering `templates/reports.html`.

### 11.1 Hub

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 108 | Page title / header | `Generate Reports` window | `<title>` `Generate Reports - Paperfile`; `<h1>` `Generate Reports` | OK |
| 109 | "Report for" affordance | Checkbutton `"Report for"` + combobox (`generatereports.py:178-187`) — likely persists immediately | Form with checkbox `report_for_enabled`, text input `report_for_person` (with `author-names` datalist), and explicit **`Save`** button | Low — desktop probably auto-persists; web requires Save click |
| 110 | Hub button: Funding Proposals Report | Present | Link `Funding Proposals Report` → `/reports/funding-proposals` | OK |
| 111 | Hub buttons: vita / annual / year / journal-use / journal-rank / publication-type / journal-rank-by-class — **whole** | 7 buttons | 7 links in column "whole" | OK |
| 112 | Hub buttons: same 7 — **selected people** | 7 buttons | 7 links in column "selected people" | OK |
| 113 | Hub button: Publication Types (whole) | Present | Link `Publication Types (whole)` | OK |
| 114 | Hub button: Publication Types (selected people) | Present | Link | OK |
| 115 | Hub button: Journal Categories (whole) | Present | Link | OK |
| 116 | Hub button: Journal Categories (selected people) | Present | Link | OK |
| 117 | Hub button: Composite summary | Present | Link `Composite summary` | OK |
| 118 | `Exit` button | Present | Link `Exit to main menu` | OK |
| 119 | Validation when no DB | `Error No database loaded. Please open a .cnt file first.` (`generatereports.py:326`) | (handled at app boot — no per-action message) | Low |

### 11.2 Sub-pages

| # | Sub-report | Desktop | Web | Severity / notes |
|---|---|---|---|---|
| 120 | Funding Proposals | `pages/fundingproposalsreport.py` (no messagebox calls observed) | `/reports/funding-proposals`, `templates/reports_funding.html` — `y0`/`y1`/`author`/`status` filters; `Apply filters`; `Download tab-separated (.txt)` | Likely close — line-by-line label diff not done |
| 121 | Group Output (Vita / Annual / Year / Journal-use / Journal-rank / Publication-type / Journal-rank-by-class) | `pages/groupoutput.py` + `pages/groupoutform.py` — desktop validation strings: `"Invalid year"`, `"Invalid year range"` (`groupoutform.py:234, 241`); `"Error","No database loaded."`, `"Copied to clipboard!"` (`groupoutput.py:681, 762`) | Single web template `reports_group_output.html` parameterised by `kind` and `scope`; checkboxes `Include journal ranking` and `Norm the rank`; vita-types checkbox grid; `Run report`; `Download as .txt` | Medium — desktop has separate forms for each report; web combines with parameters. Label drift likely |
| 122 | Publication type report | `pages/publicationtypereport.py` (label `Publication type report for:`) | `/reports/publication-type` and `/reports/publication-types-time` rendering `reports_publication_type.html` (mode-aware) | Likely close — not deeply traced |
| 123 | Journal categories | (handled inside Classify Journals on desktop; or separate report?) | `/reports/journal-categories-time` rendering `reports_journal_categories.html` | Unverified |
| 124 | Composite summary | `pages/compositesummary.py` (not deeply traced) | `/reports/composite-summary`; **four radio views** `Compare output`, `With rankings`, `Journal power (mean AGECO rank, J only)`, `Full per-vita-type breakdown (parity with desktop)` | **Web superset** — but the explicit "parity with desktop" radio implies a known divergence in the other views worth investigating |
| 125 | "Copied to clipboard!" feedback | `messagebox.showinfo("Copied", "Table copied to clipboard!")` in `specialreportform_1/2/3.py` and `groupoutput.py` | (n/a — web doesn't have copy-to-clipboard buttons) | Medium — feature gap |

---

## 12. Use Utilities (incl. Merge, Default Vita Types, Default Name, ChatGPT API Key)

Desktop: `pages/utilities.py` with **11 dedicated buttons** (each opening a
separate screen or invoking a flow). Web: `use_utilities()` at
`app.py:2285-2474` rendering `templates/utilities.html` — one page with
**6 forms** plus links.

| # | Concern | Desktop button → screen | Web equivalent | Severity |
|---|---|---|---|---|
| 126 | `Load Another Paper File or Backup File` | Opens file picker; loads `.cnt` or `.bak` | Form `switch_db` — text input `Path to .cnt (or .bak)` + `Switch to this file` button | Medium — file-picker vs path input |
| 127 | **`Merge Another Paper File`** | Opens dedicated `Merge database` screen (`pages/mergedatabase.py`): target picker + `Select Vita Types to Merge` checkbuttons (with `Select All` / `Unselect All`), `Merge Now`, `Exit`; `askyesno("Clean Databases", "Clean BOTH …")`; `askyesno("Confirm Merge", "{n} new entries…")`; `"Merge Completed"` | Form `merge` — text input `merge_path` + confirm checkbox + `Merge` button. **No** dedicated screen, **no** vita-type filter, **no** select all/unselect all, **no** "merge complete" success dialog | **High** — major feature gap (per-vitatype filtering during merge, confirmation flow) |
| 128 | `Clean Current Database` | Dialog flow with confirmation | Form `clean` — confirm checkbox + `Clean database` button | OK |
| 129 | `Save Current as New Paper File` | Dialog flow | Form `save_as` — text input `dest_path` + confirm + `Save copy` | OK |
| 130 | `Export Current Database to BibTeX` | Single click → file dialog | Link `Download BibTeX (.bib)` | OK |
| 131 | `Import BibTeX into Current Database` | `askyesnocancel("Import BibTeX", "...Yes = Merge...\nNo = Replace...\nCancel = Cancel")` (`utilities.py:382-387`) and `askyesnocancel("Backup Current Database?", ...)` (`utilities.py:394-399`) | Form `import_bibtex` — file upload + radios `merge` / `replace` + checkbox `backup` (default checked) + `Import` button | OK — different idiom (radios vs three-button dialog) but parity preserved |
| 132 | **`Default Vita Types`** | Dedicated screen `pages/defaultvitatypes.py` with sections **Vita** and **Merge**, full vita-type checkbox lists, `Select All`, `Unselect All`, `Default` buttons | Folded into Utilities `Save preferences` form: two textareas `vita_codes` and `merge_vita_codes` (raw text, no checkbox UI) | **High** — much worse UX (raw text vs visual checklist + select-all) |
| 133 | `Default Name When Enter New Papers` | Dedicated screen `pages/defaultname.py` with `Default Name:` entry + `Clear` + `Exit` | Folded into Utilities `Save preferences` form: text input `default_name` | Medium — no `Clear` button |
| 134 | `ChatGPT API Key` | Dedicated screen `pages/chatgpt_api.py` with key entry + multiple validation dialogs (lines 116, 130, 158, 178, 184, 200, 266-286) | Folded into Utilities `Save preferences` form: text input `openai_api_key` | Medium — no dedicated affordance |
| 135 | `Delete Selected Papers` | Dedicated screen (see §13) | Cross-link `Open bulk-delete page →` to `/delete-selected-papers` (see §13) | OK |
| 136 | `Exit` | Closes window | (none — uses browser nav) | OK |
| 137 | Whole-database Excel export | (not present anywhere on Utilities; closest desktop equivalent is per-result `Export to Spreadsheet` in the results window) | `Download Excel (.xlsx)` link on Utilities | **Web superset** |

---

## 13. Delete Selected Papers

Desktop: `pages/delete_selected_papers.py`. Web: `delete_selected_papers()`
at `app.py:1302-1437` rendering `templates/delete_selected_papers.html`.

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 138 | Workflow paradigm | Single-screen; click `Delete` → `askyesno("Confirm deletion", summary)` → `askyesnocancel("Backup Before Delete?", ...)` | Two-step: **Step 1 build plan → Preview → Step 2 review and confirm → Commit** | **Web superset** — clearer flow, but not parity |
| 139 | Section labels | `Delete papers in a number range` / `Delete papers WITH an author` / `Delete papers WITHOUT an author` (`delete_selected_papers.py:89-195`) | Step 1 form has `from_n`, `to_n`, `with_author`, `without_author` (with author datalist) — labels not verbatim-checked | Low — likely close, label drift possible |
| 140 | Database-range hint | `(Database range …)` displayed near the From/To inputs | Not verified to be present | Low |
| 141 | `Backup Before Delete?` askyesnocancel | Multi-line `Yes = backup, No = no backup, Cancel = abort` (`delete_selected_papers.py:541-546`) | Checkbox `Backup full bundle (.cnt + .cng + .cnj) into a timestamped folder first` (default ON) | Medium — three-way → boolean (loses the explicit "abort" path; user can `Cancel` button instead) |
| 142 | Renumber-after-delete option | (not present on desktop) | Checkbox `Renumber remaining records sequentially from 1 after delete` | **Web superset** |
| 143 | Final confirmation | `askyesno("Confirm deletion", summary + "\n\nTotal records to be deleted: {n}")` (`delete_selected_papers.py:534-536`) | Checkbox `I confirm: permanently delete N record(s) from {file}` + `Commit delete` button | Medium — dialog vs inline confirmation (different idioms) — **✅ FIXED** (commit-form `onsubmit` now opens a `window.confirm()` with the count + db path before posting) |
| 144 | Validation: no rules / no matched / no DB | Multiple distinct messages (`delete_selected_papers.py:469-580`) | Flash messages with similar intent; exact wording not verified to match | Low |

---

## 14. Cross-cutting concerns

| # | Concern | Desktop | Web | Severity |
|---|---|---|---|---|
| 145 | Custom error pages | Tk `messagebox` overlays for runtime errors | **No** `404.html` / `500.html` defined — Flask defaults shown | Medium — branding/UX gap |
| 146 | Modal dialogs for destructive actions | Tk `messagebox.askyesno` / `askyesnocancel` everywhere | Replaced with **inline confirm checkboxes** in most places; no JS confirm prompts (except `Clear list` on staging) | Medium — user can submit destructive POSTs without an explicit "Are you sure?" |
| 147 | Backup-before-destructive-action prompt | `askyesnocancel("Backup Current Database?", …)` before BibTeX import / merge / delete | Inline `backup` checkbox on Import / Delete forms; **no backup affordance on Merge form** | Medium — Merge gap |
| 148 | "Copied to clipboard!" feedback in reports | Present in 4 desktop report screens (specialreportform_1/2/3, groupoutput) | Absent — no copy-to-clipboard buttons on web reports | Medium — feature gap |
| 149 | Faculty / author autocomplete | (n/a — desktop uses combobox elsewhere) | Web uses HTML `<datalist>` (`author_list`, `author-names`, `faculty_list`) on multiple forms | **Web superset** (good UX) |
| 150 | Read-only ("demo") deployment mode | Not present | Web honors `PAPERFILE_READ_ONLY=1` env to disable destructive actions and show a banner | **Web superset** (deployment safety) |
| 151 | Unified flash-message bar | (n/a — desktop uses popups per action) | Web uses `get_flashed_messages(with_categories=true)` on most pages | OK — different idiom |

---

## 15. Web-only features (intentional supersets)

These are listed for transparency — they're **not** parity gaps, but they
are visible differences and any "strict desktop parity" goal should decide
whether to keep, hide, or document them.

| # | Web feature | Where | Tied to row |
|---|---|---|---|
| 152 | `Parse with ChatGPT` clipboard card on Enter Papers | `templates/enter_papers.html` | #12 |
| 153 | Backup-before-save checkbox on Enter Papers | `templates/enter_papers.html` | #14 |
| 154 | `Save and next ({pos}/{queue})` queue stepping | `enter_papers()` | #13 |
| 155 | Two-step preview-then-commit on bulk delete | `delete_selected_papers()` | #138 |
| 156 | `Renumber remaining records sequentially` option on bulk delete | `templates/delete_selected_papers.html` | #142 |
| 157 | Full-bundle backup (`.cnt + .cng + .cnj`) on Edit-and-Fix-Entries | `templates/edit_fix.html` | #74 |
| 158 | Composite summary view selector (4 radios incl. "Full per-vita-type breakdown (parity with desktop)") | `templates/reports_composite.html` | #124 |
| 159 | `PAPERFILE_READ_ONLY` env-gated banner / write-block | `app.py` + various templates | #150 |
| 160 | Whole-database Excel export | `Download Excel (.xlsx)` link on Utilities | #137 |
| 161 | Standalone CNJ editor with class-block + journal-block save buttons | `/journals/edit` | #105 |
| 162 | Faculty / author / faculty-name datalists for autocomplete | Multiple templates | #149 |
| 163 | Read-only banner shown on Enter Papers / Correct Papers | `templates/enter_papers.html`, etc. | #66, #150 |

---

## 16. Method & caveats

* **Desktop inventory** was produced by reading `paperfile/main.py`, every
  page module under `paperfile/pages/`, the navigation router
  `paperfile/modules/update_page.py`, and shared widget helpers under
  `paperfile/modules/ui_elements.py`. Visible labels, button texts, window
  titles and `messagebox` strings were captured verbatim from
  `create_label(...)`, `create_button(...)`, `create_radiobutton(...)`,
  `create_checkbutton(...)`, `messagebox.show*(...)`, `askyesno(...)`,
  `askyesnocancel(...)` and `.title(...)` calls.

* **Web inventory** was produced by reading every `@app.route(...)` handler
  in `paperfile-web/app.py` and every template under
  `paperfile-web/templates/` (including partials like
  `_retrieve_search_form.html`). Visible labels, button texts, page titles
  and flash strings were captured verbatim from the templates and from
  string literals in route handlers.

* **No source files were modified** to produce this report — it's a snapshot
  of `main` (web) and the on-disk `paperfile/` source tree at the time of
  writing.

* **Caveats and known gaps in this review:**
  - Enter Papers' full button grid (§3) was not deeply traced on either
    side; only the messagebox strings and the obvious form rows were
    compared. There may be more drift in field labels and section headers.
  - Several reports sub-pages (§11.2 — `specialreportform_1/2/3.py`,
    `publicationtypereport.py`, `fundingproposalsreport.py`,
    `compositesummary.py`) were not deeply traced for label/button parity.
  - Standardize Names desktop UI (§8) was only traced via its messagebox
    catalog.
  - Classify Journals (§10.2) and Journal Name Mapper (§10.3) are so large
    that side-by-side parity for them was not attempted; they're flagged as
    **Critical / missing entirely** because no equivalent screens exist on
    the web side.

* **Update policy.** When you fix a row, mark it ✅ in the table (and
  optionally strike through the body). New discoveries should be appended
  with the next free row number. **Don't renumber** so external references
  to row numbers (in PRs, commits, chat) stay valid.
