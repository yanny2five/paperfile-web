import datetime
import io
import json
import os
import tempfile

from flask import (
    Flask,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from markupsafe import escape

from modules.exportdata import generate_bibtex_string, generate_xlsx_bytes
from modules.extract_names import get_all_formatted_names
from modules.journal_categories_report import compute_journal_categories_report
from modules.report_composite_simple import compute_composite
from modules.report_funding import (
    author_names_from_pr_rows,
    build_funding_rows,
    filter_funding_rows,
)
from modules.report_group_output import (
    VITATYPE_ORDER,
    VITA_TYPE_NAMES,
    generate_group_output,
    load_vitatype_preference,
    ordered_people_choices,
)
from modules.report_journal_info import build_journal_info_from_reader
from modules.report_journals import (
    journal_frequency_rows,
    journal_rows_by_major_class,
    journal_rows_with_ranks,
)
from modules.report_year_utils import extract_year_int
from modules.readdata import get_config_path, read_json_with_guess
from modules.formatters import format_paper
from modules.publication_type_report import (
    compute_publication_type_report,
    faculty_ordered_names,
    min_year_in_papers,
    ordered_people_list,
    resolve_selection_to_pairs,
)
from modules.readdata import CNTReader
from modules.search_service import get_number, normalize, search_papers, sort_results
from modules.bibtex_import import parse_bibtex_file_to_records
from modules.check_numbers_service import compute_number_stats, parse_paper_int, renumber_in_range
from modules.clean_database import clean_database
from modules.correct_papers_service import record_from_correct_form, record_from_enter_form
from modules.journals_people_service import (
    backup_sidecar_file,
    faculty_rows_from_post,
    journal_browser_rows,
    load_faculty_rows,
    resolve_faculty_and_journal_paths,
    save_faculty_cng,
)
from modules.savedata import (
    append_records_to_cnt,
    overwrite_all_records_in_cnt,
    overwrite_record_in_cnt,
)
from modules.edit_fix_service import (
    build_duplicate_report_text,
    correct_elements_filter,
    get_exact_duplicate_groups,
    get_exact_title_duplicate_groups,
    remove_duplicates_keep_smallest_number,
    scan_funky_database,
)
from modules.utilities_web import (
    assign_sequential_numbers,
    backup_cnt_only,
    max_record_number,
    read_config_value,
    set_config_database_path,
    write_config_value,
    write_cnt_new_file,
)
from modules.filter_cnt_by_vita import (
    DEFAULT_PUBLIC_DROP_VITATYPES,
    filter_out_vita_types,
    vita_types_reference_lines,
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-for-production")

# --- Google Sites / iframe embedding (HTTPS only for Secure / SameSite=None) ---
# Set PAPERFILE_FRAME_ANCESTORS to a space-separated list, e.g.
#   https://sites.google.com https://*.google.com
# Or use the shortcut PAPERFILE_EMBED_GOOGLE_SITES=1 for a default Google-friendly list.
def _frame_ancestors_value() -> str | None:
    raw = os.environ.get("PAPERFILE_FRAME_ANCESTORS", "").strip()
    if raw:
        return raw
    if os.environ.get("PAPERFILE_EMBED_GOOGLE_SITES", "").lower() in ("1", "true", "yes"):
        return "https://sites.google.com https://*.google.com"
    return None


_ss = os.environ.get("PAPERFILE_SESSION_SAMESITE", "").strip().lower()
if _ss == "none":
    app.config["SESSION_COOKIE_SAMESITE"] = "None"
    app.config["SESSION_COOKIE_SECURE"] = True
elif _ss == "lax":
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
elif _ss == "strict":
    app.config["SESSION_COOKIE_SAMESITE"] = "Strict"

if os.environ.get("PAPERFILE_SECURE_COOKIES", "").lower() in ("1", "true", "yes"):
    app.config["SESSION_COOKIE_SECURE"] = True


@app.after_request
def _embed_headers(response):
    ancestors = _frame_ancestors_value()
    if ancestors:
        # Allow this app to be framed by the listed origins (e.g. Google Sites embed).
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'self' " + ancestors
        )
    return response


@app.context_processor
def inject_ui_theme():
    return {"ui_theme": "classic"}


@app.context_processor
def inject_instance_label():
    """Optional banner (e.g. Personal vs Department) from PAPERFILE_APP_LABEL."""
    return {"paperfile_instance_label": (os.environ.get("PAPERFILE_APP_LABEL") or "").strip()}


reader = CNTReader()
PAPERS = reader.get_data()


def _sync_papers_from_reader():
    global PAPERS
    reader.reload_data()
    PAPERS = reader.get_data()


def _paperfile_read_only() -> bool:
    """Set env PAPERFILE_READ_ONLY=1 on a hosted demo to block all database writes."""
    return os.environ.get("PAPERFILE_READ_ONLY", "").lower() in ("1", "true", "yes")


def _run_retrieve_form_search(papers, form):
    """Shared Retrieve / Correct Papers search form (POST)."""
    search_type = form.get("search_type", "author_title")
    sort_by = form.get("sort_by", "title")
    year_min = form.get("year_min") or None
    year_max = form.get("year_max") or None
    vita_types = form.getlist("vita_types") if form.get("restrict_vita_types") else []
    italics = "italics" in form
    omit_number = "omit_number" in form
    omit_keywords = "omit_keywords" in form
    if search_type == "author_title":
        author = (form.get("author_query") or "").strip()
        title = (form.get("title_query") or "").strip()
        combined = (form.get("query_author_title") or "").strip()
        if author or title:
            query = {"author": author, "title": title}
        elif combined:
            # "Text to find" box (query_author_title): same as desktop single-line
            # search — substring in author OR title (search_service author_title string).
            query = combined
        else:
            query = {"author": "", "title": ""}
    else:
        query_field_map = {
            "number": "query_number",
            "multiple_numbers": "query_multiple_numbers",
            "keyword": "query_keyword",
            "journal_book": "query_journal_book",
            "year": "query_year",
            "vita_type": "query_vita_type",
            "any_field": "query_author_title",
        }
        field_name = query_field_map.get(search_type, "query_author_title")
        query = form.get(field_name, "")
    results = search_papers(
        papers,
        query=query,
        search_type=search_type,
        year_min=year_min,
        year_max=year_max,
        vita_types=vita_types,
    )
    results = sort_results(results, sort_by)
    display_opts = {
        "italics": italics,
        "omit_number": omit_number,
        "omit_keywords": omit_keywords,
    }
    formatted_results = [
        format_paper(
            paper,
            italics=italics,
            omit_number=omit_number,
            omit_keywords=omit_keywords,
        )
        for paper in results
    ]
    log_info = {
        "search_type": search_type,
        "query": query,
        "year_min": year_min,
        "year_max": year_max,
        "vita_types": vita_types,
        "sort_by": sort_by,
        "n": len(results),
    }
    return results, formatted_results, display_opts, log_info


def _search_type_display_from_request():
    """Which search mode radio to show; map removed legacy modes to author/title."""
    st = request.form.get("search_type")
    if request.method == "GET" and request.args.get("search_type"):
        st = request.args.get("search_type")
    if st in ("number", "multiple_numbers"):
        st = "author_title"
    return st or "author_title"


def _paper_by_number(papers, token):
    if not str(token or "").strip():
        return None
    key = normalize(str(token).strip())
    for p in papers:
        if normalize(get_number(p)) == key:
            return p
    return None


def _vita_type_dropdown_pairs():
    """
    Vita types for web enter/edit dropdowns. Excludes types Bruce asked not to host
    on the public web (same set as public .cnt export); existing records may still
    show those codes via _vita_pairs_for_paper.
    """
    out = []
    seen = set()
    for code in VITATYPE_ORDER:
        if code in DEFAULT_PUBLIC_DROP_VITATYPES:
            continue
        if code in VITA_TYPE_NAMES:
            out.append((code, VITA_TYPE_NAMES[code]))
            seen.add(code)
    for code in sorted(VITA_TYPE_NAMES.keys()):
        if code in seen or code in DEFAULT_PUBLIC_DROP_VITATYPES:
            continue
        out.append((code, VITA_TYPE_NAMES[code]))
    return out


def _vita_pairs_for_paper(paper, base_pairs):
    vt = str(paper.get("vitatyp") or "").strip()
    codes = {c for c, _ in base_pairs}
    if vt and vt not in codes:
        return [(vt, f"{vt} (from record)")] + list(base_pairs)
    return base_pairs


def _parse_paper_numbers(raw):
    """Comma-separated paper numbers from the export form; order preserved, duplicates skipped."""
    if not raw:
        return []
    from modules.search_service import normalize

    out = []
    seen = set()
    for part in str(raw).split(","):
        n = part.strip()
        if not n:
            continue
        key = normalize(n)
        if key in seen:
            continue
        seen.add(key)
        out.append(n)
    return out


def _papers_for_numbers(papers, number_tokens):
    """Return papers in the same order as number_tokens (search_service-normalized keys)."""
    from modules.search_service import normalize

    by_key = {}
    for p in papers:
        key = normalize(get_number(p))
        if key and key not in by_key:
            by_key[key] = p

    ordered = []
    for token in number_tokens:
        k = normalize(token)
        if k in by_key:
            ordered.append(by_key[k])
    return ordered


def _staging_numbers():
    return list(session.get("export_staging") or [])


def _set_staging(nums):
    session["export_staging"] = nums
    session.modified = True


def _paper_year_bounds(papers):
    ys = []
    for p in papers or []:
        y = extract_year_int(p.get("year"))
        if y and 1900 <= y <= 2100:
            ys.append(y)
    cy = datetime.datetime.now().year
    if not ys:
        return 1900, cy
    return min(ys), max(ys)


def _save_vitatype_preference(codes):
    path = get_config_path()
    if not path:
        return
    try:
        cfg = read_json_with_guess(path)
        cfg["vitatype_preference"] = list(codes)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


def _group_output_page_title(kind, scope):
    scope_label = "whole data set" if scope == "whole" else "selected people"
    if kind == "vita":
        return f"Create a Vita ({scope_label})"
    if kind == "annual":
        return f"Create annual report ({scope_label})"
    return f"Selected year report ({scope_label})"


print("PAPERS LOADED:", len(PAPERS))
if PAPERS:
    print("FIRST PAPER:", PAPERS[0])


@app.route("/mode/<name>")
def set_ui_mode(name):
    if name in ("retrieve", "export"):
        session["ui_mode"] = name
        session.modified = True
    return redirect(url_for("retrieve"))


@app.route("/staging/add", methods=["POST"])
def staging_add():
    picks = request.form.getlist("pick")
    staging = _staging_numbers()
    seen = {normalize(x) for x in staging}
    for p in picks:
        n = str(p).strip()
        if not n:
            continue
        k = normalize(n)
        if k in seen:
            continue
        seen.add(k)
        staging.append(n)
    _set_staging(staging)
    session["ui_mode"] = "export"
    return redirect(url_for("retrieve"))


@app.route("/staging/remove", methods=["POST"])
def staging_remove():
    drop = {normalize(x) for x in request.form.getlist("staging_pick")}
    staging = [s for s in _staging_numbers() if normalize(s) not in drop]
    _set_staging(staging)
    return redirect(url_for("retrieve"))


@app.route("/staging/clear", methods=["POST"])
def staging_clear():
    _set_staging([])
    return redirect(url_for("retrieve"))


@app.route("/")
def home():
    """Landing page: go straight to retrieve (full main menu stays at /dashboard)."""
    return redirect(url_for("retrieve"))


@app.route("/dashboard")
def dashboard():
    db_path = getattr(reader, "file_path", None) or "(no database path)"
    return render_template(
        "dashboard.html",
        db_path=db_path,
        entry_count=len(PAPERS) if PAPERS else 0,
    )


@app.route("/retrieve-papers")
def retrieve_papers():
    """Desktop: Retrieve Papers -> retrievepapers_main entry_mode retrieve."""
    session["ui_mode"] = "retrieve"
    session.modified = True
    return redirect(url_for("retrieve"))


@app.route("/data-export")
def data_export_entry():
    """Desktop: Data Export -> same screen, entry_mode export."""
    session["ui_mode"] = "export"
    session.modified = True
    return redirect(url_for("retrieve"))


@app.route("/retrieve-numbers")
def retrieve_numbers():
    """Legacy URL; number-only retrieve UI removed — same as Retrieve Papers."""
    session["ui_mode"] = "retrieve"
    session.modified = True
    return redirect(url_for("retrieve"))


@app.route("/enter-papers", methods=["GET", "POST"])
def enter_papers():
    read_only = _paperfile_read_only()
    db_path = getattr(reader, "file_path", None) or ""

    if request.method == "POST":
        if read_only:
            flash("Read-only mode: saves are disabled (PAPERFILE_READ_ONLY).", "error")
            return redirect(url_for("enter_papers"))
        if not db_path or not os.path.isfile(db_path):
            flash("No active database file. Check config.json database_path.", "error")
            return redirect(url_for("enter_papers"))
        try:
            merged = record_from_enter_form(request.form)
            authors = (merged.get("authors") or "").strip()
            title = (merged.get("title") or "").strip()
            if not authors and not title:
                flash("Enter at least an author or a title before saving.", "error")
                return redirect(url_for("enter_papers"))
            reader.reload_data()
            papers = reader.get_data() or []
            next_num = max_record_number(papers) + 1
            merged["number"] = str(next_num)
            backup_msg = ""
            if request.form.get("backup") == "1":
                try:
                    bpath = backup_cnt_only(db_path)
                    backup_msg = f" Backup copy: {bpath}."
                except Exception as e:
                    flash(f"Backup failed: {e}", "error")
                    return redirect(url_for("enter_papers"))
            append_records_to_cnt(db_path, [merged], gui_messages=False)
            _sync_papers_from_reader()
            flash(
                f"Added record #{next_num} to the database (appended to your .cnt).{backup_msg}",
                "success",
            )
            return redirect(url_for("enter_papers"))
        except Exception as e:
            flash(str(e), "error")
            return redirect(url_for("enter_papers"))

    reader.reload_data()
    papers = reader.get_data() or []
    next_num = max_record_number(papers) + 1 if (papers or (db_path and os.path.isfile(db_path))) else 1
    base_vita_pairs = _vita_type_dropdown_pairs()
    return render_template(
        "enter_papers.html",
        db_path=db_path,
        next_number=next_num,
        vita_pairs=base_vita_pairs,
        read_only=read_only,
    )


@app.route("/journals-and-people", methods=["GET", "POST"])
def journals_and_people():
    cfg_path, faculty_path, journal_path = resolve_faculty_and_journal_paths()
    read_only = _paperfile_read_only()

    if request.method == "POST":
        action = (request.form.get("action") or "").strip()
        if read_only:
            flash("Read-only mode: changes are disabled (PAPERFILE_READ_ONLY).", "error")
            return redirect(url_for("journals_and_people"))
        try:
            if action == "save_faculty":
                if not faculty_path:
                    flash("config.json has no faculty_file path.", "error")
                    return redirect(url_for("journals_and_people"))
                rows = faculty_rows_from_post(request.form)
                parent = os.path.dirname(os.path.abspath(faculty_path))
                if parent and not os.path.isdir(parent):
                    flash("Faculty file directory does not exist.", "error")
                    return redirect(url_for("journals_and_people"))
                if os.path.isfile(faculty_path):
                    backup_sidecar_file(faculty_path)
                save_faculty_cng(faculty_path, rows)
                flash(
                    f"Saved faculty file ({len(rows)} people). A .webbak_ timestamp copy was saved beside it.",
                    "success",
                )
            elif action == "upload_cnj":
                if not journal_path:
                    flash("config.json has no journal_definition_file path.", "error")
                    return redirect(url_for("journals_and_people"))
                uf = request.files.get("cnj_file")
                if not uf or not uf.filename:
                    flash("Choose a .cnj file first.", "error")
                    return redirect(url_for("journals_and_people"))
                data = uf.read()
                if len(data) > 50 * 1024 * 1024:
                    flash("That file is too large (max 50 MB).", "error")
                    return redirect(url_for("journals_and_people"))
                try:
                    text = data.decode("utf-8")
                except UnicodeDecodeError:
                    text = data.decode("latin-1", errors="replace")
                if "STARTJOURNALS" not in text or "CLASSCOUNT" not in text:
                    flash(
                        "Upload rejected: file must contain CLASSCOUNT and STARTJOURNALS (standard .cnj).",
                        "error",
                    )
                    return redirect(url_for("journals_and_people"))
                parent = os.path.dirname(os.path.abspath(journal_path))
                if parent and not os.path.isdir(parent):
                    flash("Journal file directory does not exist.", "error")
                    return redirect(url_for("journals_and_people"))
                if os.path.isfile(journal_path):
                    backup_sidecar_file(journal_path)
                with open(journal_path, "wb") as out:
                    out.write(data)
                flash(
                    "Journal definition file replaced. A .webbak_ timestamp copy of the previous file was saved beside it.",
                    "success",
                )
            else:
                flash("Unknown action.", "error")
        except Exception as e:
            flash(str(e), "error")
        return redirect(url_for("journals_and_people"))

    faculty_rows = load_faculty_rows(faculty_path)
    for idx, row in enumerate(faculty_rows):
        row["form_id"] = idx
    faculty_next_id = len(faculty_rows)

    journal_rows = []
    journal_rank: dict = {}
    journal_warn = None
    try:
        reader.reload_data()
        journal_rank, journal_dict, sjr_data = reader.read_journal_definition()
        journal_rows = journal_browser_rows(journal_dict, sjr_data)
        if journal_path and os.path.isfile(journal_path) and not journal_dict:
            journal_warn = "Journal file is present but no journal lines were parsed (check CLASSCOUNT / STARTJOURNALS format)."
    except Exception as e:
        journal_warn = str(e)
        journal_rank = {}
        journal_rows = []

    journal_class_rows = sorted(
        journal_rank.items(),
        key=lambda kv: (kv[1][0], str(kv[0]).lower()),
    )

    return render_template(
        "journals_and_people.html",
        cfg_path=cfg_path or "",
        faculty_path=faculty_path or "",
        journal_path=journal_path or "",
        faculty_rows=faculty_rows,
        faculty_next_id=faculty_next_id,
        journal_rows=journal_rows,
        journal_class_rows=journal_class_rows,
        journal_warn=journal_warn,
        journal_count=len(journal_rows),
        read_only=read_only,
    )


@app.route("/journals-and-people/download")
def journals_and_people_download():
    kind = (request.args.get("kind") or "").strip()
    _, fac_path, jou_path = resolve_faculty_and_journal_paths()
    if kind == "faculty":
        if not fac_path or not os.path.isfile(fac_path):
            abort(404)
        return send_file(
            fac_path,
            as_attachment=True,
            download_name=os.path.basename(fac_path),
            mimetype="text/plain; charset=utf-8",
        )
    if kind == "journal":
        if not jou_path or not os.path.isfile(jou_path):
            abort(404)
        return send_file(
            jou_path,
            as_attachment=True,
            download_name=os.path.basename(jou_path),
            mimetype="text/plain; charset=utf-8",
        )
    abort(404)


@app.route("/correct-papers", methods=["GET", "POST"])
def correct_papers():
    _sync_papers_from_reader()
    papers = PAPERS or []
    display_opts = session.get(
        "display_opts",
        {"italics": False, "omit_number": False, "omit_keywords": False},
    )
    results = []
    formatted_results = []
    if request.method == "POST":
        results, formatted_results, display_opts, meta = _run_retrieve_form_search(
            papers, request.form
        )
        session["display_opts"] = display_opts
        print("=" * 80)
        print("CORRECT PAPERS SEARCH")
        print("=" * 80)
        print(f"Search Type:       {meta['search_type']}")
        print(f"Query:             {meta['query']}")
        print(f"Year Range:        {meta['year_min']} to {meta['year_max']}")
        print(f"Vita Types Filter: {meta['vita_types'] if meta['vita_types'] else 'None'}")
        print(f"Sort By:           {meta['sort_by']}")
        print(f"Results Found:     {meta['n']}")
        print("=" * 80)

    result_rows = [
        {"num": str(get_number(p)).strip(), "html": h}
        for p, h in zip(results, formatted_results)
    ]
    search_type_display = _search_type_display_from_request()

    return render_template(
        "correct_papers.html",
        results=results,
        result_rows=result_rows,
        search_type_display=search_type_display,
        display_opts=display_opts,
        read_only=_paperfile_read_only(),
    )


@app.route("/correct-papers/edit", methods=["GET", "POST"])
def correct_papers_edit():
    _sync_papers_from_reader()
    papers = PAPERS or []
    db_path = getattr(reader, "file_path", None) or ""
    base_vita_pairs = _vita_type_dropdown_pairs()
    read_only = _paperfile_read_only()

    if request.method == "POST":
        record_num = (request.form.get("record_number") or "").strip()
        if read_only:
            flash("Read-only mode: saves are disabled (PAPERFILE_READ_ONLY).", "error")
            if record_num:
                return redirect(url_for("correct_papers_edit", num=record_num))
            return redirect(url_for("correct_papers"))
        if not record_num or not db_path or not os.path.isfile(db_path):
            flash("Missing paper number or database file.", "error")
            return redirect(url_for("correct_papers"))
        rec = _paper_by_number(papers, record_num)
        if not rec:
            flash("Record not found for that number.", "error")
            return redirect(url_for("correct_papers"))
        try:
            merged = record_from_correct_form(rec, request.form)
            merged["number"] = record_num
            overwrite_record_in_cnt(db_path, merged, gui_messages=False)
            _sync_papers_from_reader()
            flash(
                "Saved. Record was written with the same overwrite-by-number path as desktop "
                "(build_record_block / overwrite_record_in_cnt).",
                "success",
            )
            return redirect(url_for("correct_papers_edit", num=record_num))
        except Exception as e:
            flash(str(e), "error")
            papers = reader.get_data() or []
            rec = _paper_by_number(papers, record_num) or rec
            return render_template(
                "correct_papers_edit.html",
                paper=rec,
                record_number=record_num,
                db_path=db_path,
                vita_pairs=_vita_pairs_for_paper(rec, base_vita_pairs),
                read_only=read_only,
            )

    num = (request.args.get("num") or "").strip()
    if not num:
        flash("Open Correct Papers, search, then use Edit next to a result.", "error")
        return redirect(url_for("correct_papers"))
    rec = _paper_by_number(papers, num)
    if not rec:
        flash("No record with that number.", "error")
        return redirect(url_for("correct_papers"))
    return render_template(
        "correct_papers_edit.html",
        paper=rec,
        record_number=str(get_number(rec)).strip(),
        db_path=db_path,
        vita_pairs=_vita_pairs_for_paper(rec, base_vita_pairs),
        read_only=read_only,
    )


@app.route("/edit-and-fix-entries", methods=["GET", "POST"])
def edit_and_fix_entries():
    reader.reload_data()
    papers = reader.get_data() or []
    db_path = getattr(reader, "file_path", None) or ""

    if request.method == "POST":
        if _paperfile_read_only():
            flash("Read-only mode: edits are disabled (PAPERFILE_READ_ONLY).", "error")
            return redirect(url_for("edit_and_fix_entries"))
        action = (request.form.get("action") or "").strip()
        try:
            if action == "eliminate_duplicates":
                if request.form.get("confirm") != "1":
                    flash("Confirm before removing duplicate records.", "error")
                    return redirect(url_for("edit_and_fix_entries"))
                if not db_path or not os.path.isfile(db_path):
                    flash("No database file.", "error")
                    return redirect(url_for("edit_and_fix_entries"))
                groups = get_exact_duplicate_groups(papers)
                if not groups:
                    flash("No exact duplicate groups found (same as desktop rules).", "success")
                    return redirect(url_for("edit_and_fix_entries"))
                new_data, removed = remove_duplicates_keep_smallest_number(papers, groups)
                overwrite_all_records_in_cnt(db_path, new_data, gui_messages=False)
                _sync_papers_from_reader()
                flash(f"Removed {removed} duplicate record(s); kept lowest number per group.", "success")
            elif action == "clean":
                if request.form.get("confirm") != "1":
                    flash("Confirm clean database.", "error")
                    return redirect(url_for("edit_and_fix_entries"))
                if not db_path or not os.path.isfile(db_path):
                    flash("No database file.", "error")
                    return redirect(url_for("edit_and_fix_entries"))
                clean_database(db_path, gui_messages=False)
                _sync_papers_from_reader()
                flash("Database cleaned (same routine as desktop / utilities).", "success")
            elif action == "backup_cnt":
                if not db_path or not os.path.isfile(db_path):
                    flash("No database file.", "error")
                    return redirect(url_for("edit_and_fix_entries"))
                bpath = backup_cnt_only(db_path)
                flash(f"Backup written: {bpath}", "success")
            else:
                flash("Unknown action.", "error")
        except Exception as e:
            flash(str(e), "error")
        return redirect(url_for("edit_and_fix_entries"))

    dup_groups = get_exact_duplicate_groups(papers)
    dup_remove_count = sum(len(recs) - 1 for _s, recs in dup_groups)
    funky_rows = scan_funky_database(papers)
    title_groups = get_exact_title_duplicate_groups(papers)

    return render_template(
        "edit_and_fix.html",
        db_path=db_path,
        entry_count=len(papers),
        dup_group_count=len(dup_groups),
        dup_remove_count=dup_remove_count,
        funky_count=len(funky_rows),
        title_dup_group_count=len(title_groups),
        read_only=_paperfile_read_only(),
    )


@app.route("/edit-and-fix-entries/correct-elements", methods=["GET"])
def edit_and_fix_correct_elements():
    field = (request.args.get("field") or "title").strip()
    allowed = ("title", "authors", "journal", "location", "volume", "pages", "keywords")
    if field not in allowed:
        field = "title"
    q = (request.args.get("q") or "").strip()
    reader.reload_data()
    papers = reader.get_data() or []
    rows = correct_elements_filter(papers, field, q)
    labels = {
        "title": "Titles",
        "authors": "Authors",
        "journal": "Journal (bookjour)",
        "location": "Rest of location",
        "volume": "Volume",
        "pages": "Pages",
        "keywords": "Keywords (subject1+2)",
    }
    return render_template(
        "edit_and_fix_correct_elements.html",
        field=field,
        q=q,
        rows=rows,
        row_count=len(rows),
        field_label=labels.get(field, field),
        allowed_fields=allowed,
        db_path=getattr(reader, "file_path", None) or "",
    )


@app.route("/edit-and-fix-entries/export/<kind>")
def edit_and_fix_export(kind):
    reader.reload_data()
    papers = reader.get_data() or []
    if kind == "funky-tsv":
        rows = scan_funky_database(papers)
        lines = ["number\tnotes"]
        for r in rows:
            lines.append(f"{r['number']}\t{r['notes']}")
        return Response(
            "\n".join(lines),
            mimetype="text/plain; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="funky_characters.tsv"'},
        )
    if kind == "exact-duplicates":
        groups = get_exact_duplicate_groups(papers)
        text = build_duplicate_report_text(groups)
        return Response(
            text,
            mimetype="text/plain; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="exact_duplicate_report.txt"'},
        )
    if kind == "title-duplicates":
        groups = get_exact_title_duplicate_groups(papers)
        lines = ["normalized_title\tcount\tnumbers"]

        def _num_key(n):
            try:
                return int(str(n).strip())
            except Exception:
                return 0

        for title_key, recs in groups:
            nums = sorted((str(r.get("number", "")) for r in recs), key=_num_key)
            lines.append(
                f"{title_key[:500]}\t{len(recs)}\t{', '.join(nums)}"
            )
        return Response(
            "\n".join(lines),
            mimetype="text/plain; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="title_duplicates_exact.tsv"'},
        )
    abort(404)


@app.route("/check-numbers", methods=["GET", "POST"])
def check_numbers():
    reader.reload_data()
    papers = reader.get_data()
    db_path = getattr(reader, "file_path", None) or ""
    stats = compute_number_stats(papers)

    if request.method == "POST" and request.form.get("action") == "renumber_save":
        if _paperfile_read_only():
            flash("Read-only mode: re-number is disabled (PAPERFILE_READ_ONLY).", "error")
            return redirect(url_for("check_numbers"))
        if not request.form.get("confirm"):
            flash("You must check the box to confirm rewriting the database file.", "error")
            return redirect(url_for("check_numbers"))

        start_at = parse_paper_int(request.form.get("start_at", ""))
        highest = parse_paper_int(request.form.get("highest", ""))
        if start_at is None or highest is None:
            flash("Enter valid integers for start and highest (commas allowed).", "error")
            return redirect(url_for("check_numbers"))

        if not db_path or not os.path.isfile(db_path):
            flash("No database file path is configured or the file is missing.", "error")
            return redirect(url_for("check_numbers"))

        data = [dict(r) for r in (papers or [])]
        if not data:
            flash("No records loaded.", "error")
            return redirect(url_for("check_numbers"))

        updated, changed = renumber_in_range(data, start_at, highest)
        if changed == 0:
            flash("No records had numbers in that range; nothing was written.", "warning")
            return redirect(url_for("check_numbers"))

        try:
            overwrite_all_records_in_cnt(db_path, updated, gui_messages=False)
        except Exception as e:
            flash(f"Save failed: {e}", "error")
            return redirect(url_for("check_numbers"))

        _sync_papers_from_reader()
        flash(f"Saved: re-numbered {changed} record(s) in the .cnt file.", "success")
        return redirect(url_for("check_numbers"))

    return render_template(
        "check_numbers.html",
        db_path=db_path,
        entry_count=len(papers) if papers else 0,
        stats=stats,
        default_highest=1_000_000,
    )


@app.route("/generate-reports", methods=["GET", "POST"])
def generate_reports():
    if request.method == "POST" and request.form.get("action") == "save_report_for":
        session["report_for_enabled"] = "report_for_enabled" in request.form
        person = (request.form.get("report_for_person") or "").strip()
        if person:
            session["report_for_person"] = person
        session.modified = True
        return redirect(url_for("generate_reports"))

    reader.reload_data()
    papers = reader.get_data()
    db_path = getattr(reader, "file_path", None) or "(no database path)"
    all_names = get_all_formatted_names(papers)
    return render_template(
        "reports.html",
        db_path=db_path,
        entry_count=len(papers) if papers else 0,
        report_for_enabled=bool(session.get("report_for_enabled")),
        report_for_person=session.get("report_for_person") or "",
        all_names=all_names,
    )


def _render_publication_type_page(page_title: str):
    mode = request.args.get("mode", "whole")
    if mode not in ("whole", "people"):
        mode = "whole"

    reader.reload_data()
    papers = reader.get_data()
    faculty = reader.get_faculty()

    y_floor = min_year_in_papers(papers)
    y_cap = datetime.datetime.now().year
    try:
        y0 = int(request.args.get("y0", y_floor))
    except (TypeError, ValueError):
        y0 = y_floor
    try:
        y1 = int(request.args.get("y1", y_cap))
    except (TypeError, ValueError):
        y1 = y_cap
    try:
        inc = int(request.args.get("inc", 5))
    except (TypeError, ValueError):
        inc = 5
    if inc < 1:
        inc = 1

    who_options = []
    who_selected = ""
    target_pairs = None
    report_label = "All People"

    if mode == "whole":
        target_pairs = None
        report_label = "All People"
    else:
        names_from_papers = get_all_formatted_names(papers)
        if faculty:
            ordered = faculty_ordered_names(faculty)
        else:
            ordered = ordered_people_list([], names_from_papers)
        who_options = [{"value": n, "label": n} for n in ordered]

        who_selected = (request.args.get("who") or "").strip()
        if (
            not who_selected
            and session.get("report_for_enabled")
            and session.get("report_for_person")
        ):
            cand = str(session.get("report_for_person") or "").strip()
            if cand in ordered:
                who_selected = cand
        if not who_selected and ordered:
            who_selected = ordered[0]

        if who_selected:
            target_pairs, report_label = resolve_selection_to_pairs(who_selected, faculty)
        else:
            headers, rows = ["Vita Type", "Total"], []
            if request.args.get("export") == "tsv":
                return Response(
                    "Vita Type\tTotal\n",
                    mimetype="text/plain; charset=utf-8",
                    headers={
                        "Content-Disposition": 'attachment; filename="publication_type_report.tsv"'
                    },
                )
            return render_template(
                "reports_publication_type.html",
                page_title=page_title,
                mode=mode,
                y0=y0,
                y1=y1,
                inc=inc,
                who_options=who_options,
                who_selected=who_selected,
                headers=headers,
                rows=rows,
                report_label="(no people list — add faculty file or papers with authors)",
            )

    headers, rows = compute_publication_type_report(papers, y0, y1, inc, target_pairs)

    if request.args.get("export") == "tsv":
        lines = ["\t".join(headers)]
        for row in rows:
            lines.append("\t".join(str(x) for x in row))
        text = "\n".join(lines)
        return Response(
            text,
            mimetype="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="publication_type_report.tsv"'
            },
        )

    return render_template(
        "reports_publication_type.html",
        page_title=page_title,
        mode=mode,
        y0=y0,
        y1=y1,
        inc=inc,
        who_options=who_options,
        who_selected=who_selected,
        headers=headers,
        rows=rows,
        report_label=report_label,
    )


@app.route("/reports/publication-type", methods=["GET"])
def reports_publication_type():
    return _render_publication_type_page("Publication type report")


@app.route("/reports/publication-types-time", methods=["GET"])
def reports_publication_types_time():
    return _render_publication_type_page("Publication Types (time period)")


@app.route("/reports/group-output", methods=["GET", "POST"])
def reports_group_output():
    reader.reload_data()
    papers = reader.get_data()
    faculty = reader.get_faculty()
    y_floor, y_cap = _paper_year_bounds(papers)

    kind = (request.values.get("kind") or "vita").strip()
    if kind not in ("vita", "annual", "selected"):
        kind = "vita"
    scope = (request.values.get("scope") or "whole").strip()
    if scope not in ("whole", "people"):
        scope = "whole"

    pref = load_vitatype_preference()
    pref = [c for c in pref if c not in DEFAULT_PUBLIC_DROP_VITATYPES]
    vita_options = []
    for code in VITATYPE_ORDER:
        if code in DEFAULT_PUBLIC_DROP_VITATYPES:
            continue
        if code in VITA_TYPE_NAMES:
            vita_options.append(
                {
                    "code": code,
                    "label": VITA_TYPE_NAMES[code],
                    "checked": code in pref,
                }
            )

    who_options = ordered_people_choices(faculty) if scope == "people" else []
    who_selected = "All people"
    y0, y1 = y_floor, y_cap
    year_one = str(datetime.datetime.now().year)
    add_ranking = False
    norm_ranking = True
    output_text = None
    count_rows = []
    txt_download = False

    if request.method == "POST" and request.form.get("action") == "run":
        selected_vita = request.form.getlist("vita")
        if selected_vita:
            _save_vitatype_preference(selected_vita)
        else:
            selected_vita = [o["code"] for o in vita_options if o["checked"]]
        for o in vita_options:
            o["checked"] = o["code"] in selected_vita
        add_ranking = "add_ranking" in request.form
        norm_ranking = "norm_ranking" in request.form
        if scope == "people":
            who_selected = (request.form.get("who") or "All people").strip() or "All people"
        if kind == "annual":
            year_one = (request.form.get("year_one") or year_one).strip()
            try:
                yi = int(year_one)
                y0 = y1 = yi
            except (TypeError, ValueError):
                y0 = y1 = y_cap
        else:
            try:
                y0 = int(request.form.get("y0", y_floor))
            except (TypeError, ValueError):
                y0 = y_floor
            try:
                y1 = int(request.form.get("y1", y_cap))
            except (TypeError, ValueError):
                y1 = y_cap
        journal_info = build_journal_info_from_reader(reader) if add_ranking else {}
        fallback = None
        if who_selected == "All people" and not [p for p in faculty or [] if p.get("name")]:
            fallback = get_all_formatted_names(papers)
        body, count_rows = generate_group_output(
            papers,
            faculty or [],
            who_selected,
            y0,
            y1,
            selected_vita,
            add_ranking,
            norm_ranking,
            journal_info,
            all_people_fallback_names=fallback,
        )
        output_text = body
        session["group_output_txt"] = body
        session.modified = True
        txt_download = bool(body and body.strip())
    else:
        if scope == "people":
            who_selected = (request.args.get("who") or "").strip()
            if (
                not who_selected
                and session.get("report_for_enabled")
                and session.get("report_for_person")
            ):
                cand = str(session.get("report_for_person") or "").strip()
                if cand in who_options:
                    who_selected = cand
            if not who_selected and who_options:
                who_selected = who_options[0]
            elif not who_selected:
                who_selected = "All people"

    title = _group_output_page_title(kind, scope)
    note = None
    if scope == "whole":
        note = (
            "Whole-data reports run as “All people”: every name in your faculty file is included. "
            "If there is no faculty file, all distinct author names from the database are used instead."
        )
    elif not who_options:
        note = "No faculty list found — add a people file to use person / group selection."

    return render_template(
        "reports_group_output.html",
        title=title,
        kind=kind,
        scope=scope,
        who_options=who_options,
        who_selected=who_selected,
        y0=y0,
        y1=y1,
        year_one=year_one,
        add_ranking=add_ranking,
        norm_ranking=norm_ranking,
        vita_options=vita_options,
        output_text=output_text,
        count_rows=count_rows,
        note=note,
        txt_download=txt_download,
    )


@app.route("/reports/group-output.txt")
def reports_group_output_txt():
    blob = session.get("group_output_txt")
    if not blob:
        abort(404)
    return Response(
        blob,
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="group_output.txt"'},
    )


@app.route("/reports/funding-proposals", methods=["GET"])
def reports_funding():
    reader.reload_data()
    papers = reader.get_data()
    all_rows = build_funding_rows(papers)
    author_opts = author_names_from_pr_rows(all_rows)

    y0_raw = request.args.get("y0", "").strip()
    y1_raw = request.args.get("y1", "").strip()
    y0 = int(y0_raw) if y0_raw.isdigit() else None
    y1 = int(y1_raw) if y1_raw.isdigit() else None

    author_selected = (request.args.get("author") or "").strip()
    status_selected = (request.args.get("status") or "").strip().lower()

    filtered = filter_funding_rows(
        all_rows, y0, y1, author_selected or None, status_selected or None
    )

    if request.args.get("export") == "tsv":
        lines = [
            "Number\tTitle\tAuthors\tFunding year\tTotal amount\tUsable amount\tStatus",
        ]
        for r in filtered:
            lines.append("\t".join(str(x) for x in r))
        return Response(
            "\n".join(lines),
            mimetype="text/plain; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="funding_proposals.tsv"'},
        )

    return render_template(
        "reports_funding.html",
        rows=filtered,
        row_count=len(filtered),
        y0=y0_raw,
        y1=y1_raw,
        author_options=author_opts,
        author_selected=author_selected,
        status_selected=status_selected,
    )


@app.route("/reports/journal-report", methods=["GET"])
def reports_journal_report():
    variant = (request.args.get("variant") or "use").strip()
    if variant not in ("use", "rank", "class"):
        variant = "use"
    scope = (request.args.get("scope") or "whole").strip()
    if scope not in ("whole", "people"):
        scope = "whole"

    reader.reload_data()
    papers = reader.get_data()
    faculty = reader.get_faculty()
    y_floor, y_cap = _paper_year_bounds(papers)
    try:
        y0 = int(request.args.get("y0", y_floor))
    except (TypeError, ValueError):
        y0 = y_floor
    try:
        y1 = int(request.args.get("y1", y_cap))
    except (TypeError, ValueError):
        y1 = y_cap

    who_options = []
    who_selected = ""
    target_pairs = None
    report_label = "All People"

    if scope == "people":
        names_from_papers = get_all_formatted_names(papers)
        if faculty:
            ordered = faculty_ordered_names(faculty)
        else:
            ordered = ordered_people_list([], names_from_papers)
        who_options = [{"value": n, "label": n} for n in ordered]
        who_selected = (request.args.get("who") or "").strip()
        if (
            not who_selected
            and session.get("report_for_enabled")
            and session.get("report_for_person")
        ):
            cand = str(session.get("report_for_person") or "").strip()
            if cand in ordered:
                who_selected = cand
        if not who_selected and ordered:
            who_selected = ordered[0]
        if who_selected:
            target_pairs, report_label = resolve_selection_to_pairs(
                who_selected, faculty
            )
        else:
            report_label = "(no people list)"
            target_pairs = set()

    journal_info = build_journal_info_from_reader(reader)
    try:
        _jr, journal_dict, _sjr = reader.read_journal_definition()
    except Exception:
        journal_dict = {}

    if variant == "use":
        title = f"Journal use report ({'whole data set' if scope == 'whole' else 'selected people'})"
        desc = "Counts of journal articles (J, JR) by journal name (book/journal field)."
        rows_raw = journal_frequency_rows(papers, y0, y1, target_pairs)
        headers = ["Journal", "Count"]
        rows = [[a, b] for a, b in rows_raw]
    elif variant == "rank":
        title = f"Journal rank report ({'whole data set' if scope == 'whole' else 'selected people'})"
        desc = "Same as journal use with AGECO rank, normed rank, SJR %, quartile, and ABDC when the journal definition file is configured."
        jr = journal_rows_with_ranks(papers, y0, y1, target_pairs, journal_info)
        headers = ["Journal", "Count", "Rank", "Normed", "SJR(%)", "Quartile", "ABDC"]
        rows = [list(r) for r in jr]
    else:
        title = f"Journal rank by class ({'whole data set' if scope == 'whole' else 'selected people'})"
        desc = "Totals of J/JR papers by major journal class from your journal definition."
        rows_raw = journal_rows_by_major_class(
            papers, y0, y1, target_pairs, journal_dict
        )
        headers = ["Major class", "Count"]
        rows = [[a, b] for a, b in rows_raw]

    export_url = url_for(
        "reports_journal_report",
        variant=variant,
        scope=scope,
        y0=y0,
        y1=y1,
        who=who_selected,
        export="tsv",
    )
    if request.args.get("export") == "tsv":
        lines = ["\t".join(headers)]
        for row in rows:
            lines.append("\t".join(str(x) for x in row))
        return Response(
            "\n".join(lines),
            mimetype="text/plain; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="journal_report.tsv"'},
        )

    return render_template(
        "reports_journal.html",
        title=title,
        description=desc,
        variant=variant,
        scope=scope,
        y0=y0,
        y1=y1,
        who_options=who_options,
        who_selected=who_selected,
        headers=headers,
        rows=rows,
        export_url=export_url,
        report_label=report_label,
    )


@app.route("/reports/journal-categories-time", methods=["GET"])
def reports_journal_categories_time():
    mode = request.args.get("mode", "whole")
    if mode not in ("whole", "people"):
        mode = "whole"

    reader.reload_data()
    papers = reader.get_data()
    faculty = reader.get_faculty()

    y_floor = min_year_in_papers(papers)
    y_cap = datetime.datetime.now().year
    try:
        y0 = int(request.args.get("y0", y_floor))
    except (TypeError, ValueError):
        y0 = y_floor
    try:
        y1 = int(request.args.get("y1", y_cap))
    except (TypeError, ValueError):
        y1 = y_cap
    try:
        inc = int(request.args.get("inc", 5))
    except (TypeError, ValueError):
        inc = 5
    if inc < 1:
        inc = 1

    who_options = []
    who_selected = ""
    target_pairs = None
    report_label = "All People"

    if mode == "whole":
        target_pairs = None
    else:
        names_from_papers = get_all_formatted_names(papers)
        if faculty:
            ordered = faculty_ordered_names(faculty)
        else:
            ordered = ordered_people_list([], names_from_papers)
        who_options = [{"value": n, "label": n} for n in ordered]
        who_selected = (request.args.get("who") or "").strip()
        if (
            not who_selected
            and session.get("report_for_enabled")
            and session.get("report_for_person")
        ):
            cand = str(session.get("report_for_person") or "").strip()
            if cand in ordered:
                who_selected = cand
        if not who_selected and ordered:
            who_selected = ordered[0]
        if who_selected:
            target_pairs, report_label = resolve_selection_to_pairs(who_selected, faculty)
        else:
            report_label = "(no people list — add faculty file or papers with authors)"

    headers, rows = compute_journal_categories_report(
        papers, reader, y0, y1, inc, target_pairs
    )

    export_url = url_for(
        "reports_journal_categories_time",
        mode=mode,
        y0=y0,
        y1=y1,
        inc=inc,
        who=who_selected,
        export="tsv",
    )

    if request.args.get("export") == "tsv":
        lines = ["\t".join(headers)]
        for row in rows:
            lines.append("\t".join(str(x) for x in row))
        return Response(
            "\n".join(lines),
            mimetype="text/plain; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="journal_categories.tsv"'},
        )

    return render_template(
        "reports_journal_categories.html",
        mode=mode,
        y0=y0,
        y1=y1,
        inc=inc,
        who_options=who_options,
        who_selected=who_selected,
        headers=headers,
        rows=rows,
        report_label=report_label,
        export_url=export_url,
    )


@app.route("/reports/composite-summary", methods=["GET"])
def reports_composite_summary():
    reader.reload_data()
    papers = reader.get_data()
    faculty = reader.get_faculty()
    y_floor, y_cap = _paper_year_bounds(papers)
    try:
        y0 = int(request.args.get("y0", y_floor))
    except (TypeError, ValueError):
        y0 = y_floor
    try:
        y1 = int(request.args.get("y1", y_cap))
    except (TypeError, ValueError):
        y1 = y_cap

    view = (request.args.get("view") or "compare").strip()
    if view == "rank":
        mode = "with_rank"
    elif view == "power":
        mode = "journal_power"
    else:
        mode = "compare_output"

    journal_info = build_journal_info_from_reader(reader)
    headers, rows, missing = compute_composite(
        papers, faculty or [], y0, y1, mode, journal_info
    )

    export_url = url_for(
        "reports_composite_summary",
        view=view,
        y0=y0,
        y1=y1,
        export="tsv",
    )

    if request.args.get("export") == "tsv":
        lines = ["\t".join(headers)]
        for row in rows:
            lines.append("\t".join(str(x) for x in row))
        return Response(
            "\n".join(lines),
            mimetype="text/plain; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="composite_summary.tsv"'},
        )

    return render_template(
        "reports_composite.html",
        view=view,
        y0=y0,
        y1=y1,
        headers=headers,
        rows=rows,
        missing_text=missing,
        export_url=export_url,
    )


@app.route("/utilities", methods=["GET", "POST"])
def use_utilities():
    cfg_path = get_config_path() or ""

    if request.method == "POST":
        if _paperfile_read_only():
            flash("Read-only mode: utilities that change files are disabled.", "error")
            return redirect(url_for("use_utilities"))
        action = (request.form.get("action") or "").strip()
        try:
            if action == "switch_db":
                p = (request.form.get("database_path") or "").strip().strip('"')
                if not p:
                    flash("Enter a database file path.", "error")
                else:
                    set_config_database_path(p)
                    reader.file_path = os.path.abspath(os.path.normpath(p))
                    reader.read_file()
                    _sync_papers_from_reader()
                    flash("Active database path updated and data reloaded.", "success")

            elif action == "merge":
                if request.form.get("confirm") != "1":
                    flash("Check the box to confirm merge.", "error")
                    return redirect(url_for("use_utilities"))
                other = (request.form.get("merge_path") or "").strip().strip('"')
                db_path = getattr(reader, "file_path", None) or ""
                if not db_path or not os.path.isfile(db_path):
                    flash("No active database file.", "error")
                    return redirect(url_for("use_utilities"))
                if not other or not os.path.isfile(other):
                    flash("Second file path not found.", "error")
                    return redirect(url_for("use_utilities"))
                reader.reload_data()
                main = reader.get_data() or []
                mx = max_record_number(main)
                r2 = CNTReader(other)
                d2 = r2.get_data() or []
                if not d2:
                    flash("The second file has no records.", "warning")
                    return redirect(url_for("use_utilities"))
                numbered = assign_sequential_numbers(d2, mx + 1)
                append_records_to_cnt(db_path, numbered, gui_messages=False)
                _sync_papers_from_reader()
                flash(f"Merged {len(numbered)} record(s) from the second file.", "success")

            elif action == "clean":
                if request.form.get("confirm") != "1":
                    flash("Check the box to confirm cleaning.", "error")
                    return redirect(url_for("use_utilities"))
                db_path = getattr(reader, "file_path", None) or ""
                if not db_path or not os.path.isfile(db_path):
                    flash("No active database file.", "error")
                    return redirect(url_for("use_utilities"))
                clean_database(db_path, gui_messages=False)
                _sync_papers_from_reader()
                flash("Database cleaned and saved.", "success")

            elif action == "save_as":
                if request.form.get("confirm") != "1":
                    flash("Check the box to confirm save.", "error")
                    return redirect(url_for("use_utilities"))
                dest = (request.form.get("dest_path") or "").strip().strip('"')
                if not dest:
                    flash("Enter a destination path.", "error")
                    return redirect(url_for("use_utilities"))
                reader.reload_data()
                data = [dict(r) for r in (reader.get_data() or [])]
                if not data:
                    flash("No records to save.", "warning")
                    return redirect(url_for("use_utilities"))
                src = getattr(reader, "file_path", None)
                if src and os.path.isfile(src):
                    header_src = src
                else:
                    header_src = None
                write_cnt_new_file(dest, data, header_src)
                flash(f"Wrote {len(data)} record(s) to {dest}.", "success")

            elif action == "import_bibtex":
                up = request.files.get("bib_file")
                if not up or not (up.filename or "").strip():
                    flash("Choose a BibTeX file.", "error")
                    return redirect(url_for("use_utilities"))
                db_path = getattr(reader, "file_path", None) or ""
                if not db_path or not os.path.isfile(db_path):
                    flash("No active database file.", "error")
                    return redirect(url_for("use_utilities"))
                suffix = os.path.splitext(up.filename)[1] or ".bib"
                fd, tmp_path = tempfile.mkstemp(suffix=suffix)
                os.close(fd)
                try:
                    up.save(tmp_path)
                    new_records = parse_bibtex_file_to_records(tmp_path)
                finally:
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
                if not new_records:
                    flash("No BibTeX entries were parsed.", "warning")
                    return redirect(url_for("use_utilities"))
                mode = (request.form.get("bib_mode") or "merge").strip()
                backup_msg = ""
                if request.form.get("backup") == "1":
                    try:
                        bpath = backup_cnt_only(db_path)
                        backup_msg = f" Backup: {bpath}."
                    except Exception as e:
                        flash(f"Backup failed: {e}", "error")
                        return redirect(url_for("use_utilities"))
                reader.reload_data()
                if mode == "replace":
                    numbered = assign_sequential_numbers(new_records, 1)
                    overwrite_all_records_in_cnt(db_path, numbered, gui_messages=False)
                    flash(
                        f"Replaced database with {len(numbered)} BibTeX entr(y/ies).{backup_msg}",
                        "success",
                    )
                else:
                    mx = max_record_number(reader.get_data() or [])
                    numbered = assign_sequential_numbers(new_records, mx + 1)
                    append_records_to_cnt(db_path, numbered, gui_messages=False)
                    flash(
                        f"Merged {len(numbered)} BibTeX entr(y/ies).{backup_msg}",
                        "success",
                    )
                _sync_papers_from_reader()

            elif action == "save_prefs":
                write_config_value("default_name", request.form.get("default_name", ""))
                write_config_value("openai_api_key", request.form.get("openai_api_key", ""))
                raw_lines = (request.form.get("vita_codes") or "").replace(",", "\n").splitlines()
                codes = [x.strip().upper() for x in raw_lines if x.strip()]
                if not cfg_path:
                    flash("config.json not found.", "error")
                    return redirect(url_for("use_utilities"))
                try:
                    cfg = read_json_with_guess(cfg_path)
                except Exception:
                    cfg = {}
                cfg["vitatype_preference"] = codes
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2, ensure_ascii=False)
                flash("Preferences saved.", "success")
            else:
                flash("Unknown action.", "error")
        except Exception as e:
            flash(str(e), "error")
        return redirect(url_for("use_utilities"))

    reader.reload_data()
    papers = reader.get_data() or []
    db_path = getattr(reader, "file_path", None) or ""

    vita_codes_text = ""
    if cfg_path:
        try:
            cfg = read_json_with_guess(cfg_path)
            vp = cfg.get("vitatype_preference")
            if isinstance(vp, list):
                vita_codes_text = "\n".join(str(x) for x in vp)
        except Exception:
            pass

    return render_template(
        "utilities.html",
        db_path=db_path,
        entry_count=len(papers),
        config_path=cfg_path,
        default_name=read_config_value("default_name"),
        openai_api_key=read_config_value("openai_api_key"),
        vita_codes_text=vita_codes_text,
    )


@app.route("/utilities/export/bibtex")
def utilities_export_bibtex():
    reader.reload_data()
    papers = reader.get_data() or []
    text = generate_bibtex_string(papers)
    return Response(
        text or "% Empty\n",
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="paperfile_database.bib"'},
    )


@app.route("/utilities/export/xlsx")
def utilities_export_xlsx():
    reader.reload_data()
    papers = reader.get_data() or []
    data = generate_xlsx_bytes(papers)
    if not data:
        return Response("No records to export.", 400, mimetype="text/plain; charset=utf-8")
    return send_file(
        io.BytesIO(data),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="paperfile_database.xlsx",
    )


@app.route("/vita-types")
def vita_types_plain():
    """All vitatyp codes + names (for email / review)."""
    body = "\n".join(vita_types_reference_lines()) + "\n"
    return Response(
        body,
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="paperfile-vita-types.txt"'},
    )


@app.route("/vita-types.html")
def vita_types_html():
    rows = []
    for line in vita_types_reference_lines():
        code, _, name = line.partition("\t")
        rows.append(f"<tr><td><code>{escape(code)}</code></td><td>{escape(name)}</td></tr>")
    drop = ", ".join(sorted(DEFAULT_PUBLIC_DROP_VITATYPES))
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Vita types - Paperfile</title>
<style>
body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 24px; background: #e8f0fa; }}
table {{ border-collapse: collapse; background: #fff; }}
th, td {{ border: 1px solid #ccc; padding: 8px 12px; text-align: left; }}
th {{ background: #f0f4f8; }}
.note {{ max-width: 720px; margin-bottom: 16px; }}
</style></head>
<body>
<h1>Vita type codes</h1>
<p class="note">Default types removed when building a <strong>public .cnt</strong> for the web: <code>{escape(drop)}</code>.
Use <a href="{url_for('vita_types_plain')}">plain text download</a> to copy into email.</p>
<table><thead><tr><th>Code</th><th>Name</th></tr></thead><tbody>{"".join(rows)}</tbody></table>
<p class="note"><strong>Web app:</strong> types <code>JD</code>, <code>OI</code>, <code>PR</code>, <code>F</code> are omitted from enter/edit dropdowns and vita report checkboxes (Ke / McCarl public copy policy). They still appear here for reference; existing records keep their code until changed.</p>
<p style="margin-top:20px"><a href="{url_for('dashboard')}">Main menu</a></p>
</body></html>"""
    return Response(html, mimetype="text/html; charset=utf-8")


@app.route("/utilities/export/public-cnt")
def utilities_export_public_cnt():
    """
    Download a .cnt with vita types JD, OI, PR, F removed (read-only safe).
    Optional query: drop=JD,OI,PR,F
    """
    reader.reload_data()
    papers = reader.get_data() or []
    raw = (request.args.get("drop") or "").strip()
    if raw:
        drop_codes = {x.strip().upper() for x in raw.split(",") if x.strip()}
    else:
        drop_codes = set(DEFAULT_PUBLIC_DROP_VITATYPES)
    kept, _stats = filter_out_vita_types(papers, drop_codes)
    src = getattr(reader, "file_path", None)
    fd, tmp = tempfile.mkstemp(suffix=".cnt", prefix="paperfile_public_")
    os.close(fd)
    try:
        write_cnt_new_file(tmp, kept, src if (src and os.path.isfile(src)) else None)
        with open(tmp, "rb") as f:
            data = f.read()
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    base = "paperfile_public"
    if src:
        stem = os.path.splitext(os.path.basename(src))[0]
        base = f"{stem}_public"
    return Response(
        data,
        mimetype="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{base}.cnt"'},
    )


@app.route("/retrieve", methods=["GET", "POST"])
def retrieve():
    results = []
    formatted_results = []
    ui_mode = session.get("ui_mode", "retrieve")
    display_opts = session.get(
        "display_opts",
        {"italics": False, "omit_number": False, "omit_keywords": False},
    )

    if request.method == "POST":
        results, formatted_results, display_opts, meta = _run_retrieve_form_search(
            PAPERS, request.form
        )
        session["display_opts"] = display_opts

        print("=" * 80)
        print("SEARCH EXECUTION LOG")
        print("=" * 80)
        print(f"Search Type:       {meta['search_type']}")
        print(f"Query:             {meta['query']}")
        print(f"Year Range:        {meta['year_min']} to {meta['year_max']}")
        print(f"Vita Types Filter: {meta['vita_types'] if meta['vita_types'] else 'None'}")
        print(f"Sort By:           {meta['sort_by']}")
        print(f"Results Found:     {meta['n']}")
        print("=" * 80)

    export_numbers = ""
    if results:
        export_numbers = ",".join(
            str(get_number(p)).strip() for p in results if str(get_number(p)).strip()
        )

    staging_nums = _staging_numbers()
    staging_records = _papers_for_numbers(PAPERS, staging_nums)
    staging_export_csv = ",".join(staging_nums) if staging_nums else ""
    staging_rows = [
        {
            "num": str(get_number(p)).strip(),
            "html": format_paper(
                p,
                italics=display_opts["italics"],
                omit_number=display_opts["omit_number"],
                omit_keywords=display_opts["omit_keywords"],
            ),
        }
        for p in staging_records
    ]

    result_rows = [
        {
            "num": str(get_number(p)).strip(),
            "html": h,
        }
        for p, h in zip(results, formatted_results)
    ]

    search_type_display = _search_type_display_from_request()

    return render_template(
        "index.html",
        ui_mode=ui_mode,
        results=results,
        formatted_results=formatted_results,
        result_rows=result_rows,
        staging_rows=staging_rows,
        staging_export_csv=staging_export_csv,
        export_numbers=export_numbers,
        search_type_display=search_type_display,
        query_number=request.form.get("query_number", ""),
        query_multiple_numbers=request.form.get("query_multiple_numbers", ""),
        query_keyword=request.form.get("query_keyword", ""),
        query_journal_book=request.form.get("query_journal_book", ""),
        query_year=request.form.get("query_year", ""),
        query_vita_type=request.form.get("query_vita_type", ""),
        query_author_title=request.form.get("query_author_title", ""),
        author_query=request.form.get("author_query", ""),
        title_query=request.form.get("title_query", ""),
        sort_by=request.form.get("sort_by", "title"),
        year_min=request.form.get("year_min", ""),
        year_max=request.form.get("year_max", ""),
    )


@app.route("/export/bibtex", methods=["POST"])
def export_bibtex():
    numbers = _parse_paper_numbers(request.form.get("paper_numbers", ""))
    records = _papers_for_numbers(PAPERS, numbers)
    if not records:
        return (
            "Nothing to export - no matching papers. Run a search with results first.",
            400,
        )
    text = generate_bibtex_string(records)
    return Response(
        text,
        mimetype="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="paperfile_export.bib"',
        },
    )


@app.route("/export/spreadsheet", methods=["POST"])
def export_spreadsheet():
    numbers = _parse_paper_numbers(request.form.get("paper_numbers", ""))
    records = _papers_for_numbers(PAPERS, numbers)
    if not records:
        return (
            "Nothing to export - no matching papers. Run a search with results first.",
            400,
        )
    data = generate_xlsx_bytes(records)
    return send_file(
        io.BytesIO(data),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="paperfile_export.xlsx",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)