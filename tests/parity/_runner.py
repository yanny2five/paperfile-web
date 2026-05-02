"""
Parity runner.

This script is invoked as a subprocess from parity tests. It expects:
  - CWD set to either the desktop project root (paperfile/) OR the web
    project root (paperfile-web/) so that ``modules.<X>`` resolves to that
    side's package.
  - A JSON request on stdin describing the operation and its inputs.

The runner installs a tkinter stub before any project import, so the desktop
modules (which do ``from tkinter import messagebox`` at module load) can be
imported in headless test environments.

The runner prints a single JSON response on stdout. Bytes are returned as
base64 strings inside the JSON payload.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
import types
import traceback
from pathlib import Path


def _install_tk_stub() -> None:
    """Install no-op stand-ins for tkinter / messagebox / filedialog / ttk."""
    if "tkinter" in sys.modules and getattr(sys.modules["tkinter"], "_paperfile_stub", False):
        return

    tk = types.ModuleType("tkinter")
    tk.__path__ = []  # type: ignore[attr-defined]
    tk._paperfile_stub = True  # type: ignore[attr-defined]
    sys.modules["tkinter"] = tk

    submodules = {
        "messagebox": ("showerror", "showwarning", "showinfo", "askyesno", "askokcancel"),
        "filedialog": ("askopenfilename", "asksaveasfilename", "askdirectory"),
        "ttk": ("Frame", "Label", "Button", "Combobox", "Entry", "Treeview", "Style"),
    }
    for sub, names in submodules.items():
        m = types.ModuleType(f"tkinter.{sub}")
        for fn in names:
            setattr(m, fn, lambda *a, **k: "")
        sys.modules[f"tkinter.{sub}"] = m
        setattr(tk, sub, m)

    class _Tk:
        def __init__(self, *a, **k): pass
        def __getattr__(self, _): return lambda *a, **k: None

    tk.Tk = _Tk
    tk.Toplevel = _Tk
    tk.StringVar = _Tk
    tk.IntVar = _Tk
    tk.BooleanVar = _Tk
    tk.Frame = _Tk
    tk.Label = _Tk
    tk.Button = _Tk
    tk.Listbox = _Tk
    tk.Text = _Tk
    tk.Canvas = _Tk
    tk.Scrollbar = _Tk
    tk.Entry = _Tk
    tk.Checkbutton = _Tk
    tk.Radiobutton = _Tk
    tk.Menu = _Tk

    # _tkinter is what tkinter/__init__.py imports first; provide it too.
    sys.modules["_tkinter"] = types.ModuleType("_tkinter")


def _bootstrap_path() -> None:
    """Make sure CWD (the side root) is at sys.path[0] so ``modules.X`` resolves."""
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)


# --- Operation handlers ---------------------------------------------------


def op_extract_names_process_authors(payload):
    from modules.extract_names import process_authors

    names, log = process_authors(payload["raw"])
    return {"names": list(names), "log": list(log)}


def op_extract_names_get_all_formatted_names(payload):
    from modules.extract_names import get_all_formatted_names

    return {"names": list(get_all_formatted_names(payload["records"]))}


def op_searchdata_call(payload):
    from modules.searchdata import SearchData

    method = payload["method"]
    args = payload.get("args", [])
    kwargs = payload.get("kwargs", {})

    sd = SearchData(payload["records"])
    if method == "filter_by_vita_type":
        result = sd.filter_by_vita_type(payload["data"], payload["vita_types"])
    else:
        result = getattr(sd, method)(*args, **kwargs)
    return {"records": list(result)}


def op_sortdata_sort(payload):
    from modules.sortdata import SortData

    sd = SortData(payload["records"])
    result = sd.sort_by_criteria(
        payload["sort_config"], vita_order_key=payload.get("vita_order_key", "vitord1")
    )
    return {"records": list(result)}


def op_savedata_build_record_block(payload):
    from modules.savedata import build_record_block

    return {"text": build_record_block(payload["data"])}


def op_savedata_save_to_cnt(payload):
    from modules.savedata import save_to_cnt

    path = payload["path"]
    save_to_cnt(path, payload["data"])
    with open(path, "rb") as f:
        return {"file_b64": base64.b64encode(f.read()).decode("ascii")}


def op_savedata_append_records_to_cnt(payload):
    from modules.savedata import append_records_to_cnt

    path = payload["path"]
    # Web's signature accepts gui_messages kw; desktop's does not.
    try:
        append_records_to_cnt(path, payload["records"], gui_messages=False)
    except TypeError:
        append_records_to_cnt(path, payload["records"])
    with open(path, "rb") as f:
        return {"file_b64": base64.b64encode(f.read()).decode("ascii")}


def op_savedata_overwrite_all_records_in_cnt(payload):
    from modules.savedata import overwrite_all_records_in_cnt

    path = payload["path"]
    try:
        overwrite_all_records_in_cnt(path, payload["records"], gui_messages=False)
    except TypeError:
        overwrite_all_records_in_cnt(path, payload["records"])
    with open(path, "rb") as f:
        return {"file_b64": base64.b64encode(f.read()).decode("ascii")}


def op_savedata_overwrite_record_in_cnt(payload):
    from modules.savedata import overwrite_record_in_cnt

    path = payload["path"]
    try:
        overwrite_record_in_cnt(path, payload["data"], gui_messages=False)
    except TypeError:
        # Desktop signature uses show_message
        overwrite_record_in_cnt(path, payload["data"], show_message=False)
    with open(path, "rb") as f:
        return {"file_b64": base64.b64encode(f.read()).decode("ascii")}


def op_readdata_read_cnt(payload):
    from modules.readdata import CNTReader

    reader = CNTReader(payload["path"])
    return {"records": list(reader.data)}


def op_exportdata_bibtex(payload):
    """Return the BibTeX serialization for ``records`` from this side."""
    try:
        from modules.exportdata import generate_bibtex_string

        return {"text": generate_bibtex_string(payload["records"])}
    except ImportError:
        # Desktop side: drive export_to_bibtex with a stubbed filedialog.
        from modules import exportdata

        out = tempfile.NamedTemporaryFile(
            mode="w", suffix=".bib", delete=False, encoding="utf-8"
        )
        out.close()
        # Patch filedialog.asksaveasfilename to return our temp path.
        import tkinter.filedialog as _fd

        _fd.asksaveasfilename = lambda *a, **k: out.name  # type: ignore[assignment]
        # Patch open_folder so we don't try to launch a viewer.
        exportdata.open_folder = lambda _path: None  # type: ignore[assignment]

        exportdata.export_to_bibtex(payload["records"])
        with open(out.name, "r", encoding="utf-8") as f:
            text = f.read()
        try:
            os.unlink(out.name)
        except OSError:
            pass
        return {"text": text}


def op_exportdata_xlsx(payload):
    """Return the .xlsx workbook bytes for ``records`` from this side."""
    try:
        from modules.exportdata import generate_xlsx_bytes

        data = generate_xlsx_bytes(payload["records"])
    except ImportError:
        from modules import exportdata

        out = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        out.close()
        import tkinter.filedialog as _fd

        _fd.asksaveasfilename = lambda *a, **k: out.name  # type: ignore[assignment]
        exportdata.open_folder = lambda _path: None  # type: ignore[assignment]

        exportdata.export_to_xlsx(payload["records"])
        with open(out.name, "rb") as f:
            data = f.read()
        try:
            os.unlink(out.name)
        except OSError:
            pass
    return {"bytes_b64": base64.b64encode(data).decode("ascii")}


def op_clean_database_records(payload):
    """Run clean_database on records via a temp .cnt file and return cleaned records.

    NOTE: desktop's clean_database drops the .cnt header (rewrites the file
    without preserving anything before the first record) while web's preserves
    it via overwrite_all_records_in_cnt. We measure cleaned **records** only,
    using a header-less file, so this difference does not perturb the test.
    """
    from modules import clean_database as cd
    from modules.savedata import build_record_block
    from modules.readdata import CNTReader

    tmpdir = tempfile.mkdtemp(prefix="parity_clean_")
    cnt_path = os.path.join(tmpdir, "fixture.cnt")
    blocks = []
    for r in payload["records"]:
        blocks.append(build_record_block(r))
    with open(cnt_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(blocks))

    # Web signature accepts gui_messages; desktop accepts only file_path.
    try:
        cd.clean_database(cnt_path, gui_messages=False)
    except TypeError:
        cd.clean_database(cnt_path)

    reader = CNTReader(cnt_path)
    cleaned = list(reader.data)
    try:
        os.remove(cnt_path)
        os.rmdir(tmpdir)
    except OSError:
        pass
    return {"records": cleaned}


def op_chatgpt_format_prompt(payload):
    """Capture the OpenAI request that would be sent for a given citation text.

    We monkey-patch ``openai.OpenAI`` so the call returns a sentinel without
    going to the network, while the chat.completions.create call records its
    arguments. The returned shape is the (model, messages) tuple.
    """
    sentinel = {"captured": None}

    class _Choice:
        def __init__(self, content):
            self.message = types.SimpleNamespace(content=content)

    class _Completion:
        def __init__(self, content):
            self.choices = [_Choice(content)]

    class _ChatCompletions:
        def create(self, *, model, messages, **_kwargs):
            sentinel["captured"] = {"model": model, "messages": messages}
            return _Completion("STUB")

    class _Chat:
        def __init__(self):
            self.completions = _ChatCompletions()

    class _OpenAI:
        def __init__(self, api_key=None):
            self.chat = _Chat()

    openai_stub = types.ModuleType("openai")
    openai_stub.OpenAI = _OpenAI  # type: ignore[attr-defined]
    sys.modules["openai"] = openai_stub

    os.environ.setdefault("OPENAI_API_KEY", "stub-key-for-tests")

    from modules.chatgpt_format import format_citations_with_chatgpt

    format_citations_with_chatgpt(payload["raw_text"])
    return {"capture": sentinel["captured"]}


HANDLERS = {
    "extract_names.process_authors": op_extract_names_process_authors,
    "extract_names.get_all_formatted_names": op_extract_names_get_all_formatted_names,
    "searchdata.call": op_searchdata_call,
    "sortdata.sort": op_sortdata_sort,
    "savedata.build_record_block": op_savedata_build_record_block,
    "savedata.save_to_cnt": op_savedata_save_to_cnt,
    "savedata.append_records_to_cnt": op_savedata_append_records_to_cnt,
    "savedata.overwrite_all_records_in_cnt": op_savedata_overwrite_all_records_in_cnt,
    "savedata.overwrite_record_in_cnt": op_savedata_overwrite_record_in_cnt,
    "readdata.read_cnt": op_readdata_read_cnt,
    "exportdata.bibtex": op_exportdata_bibtex,
    "exportdata.xlsx": op_exportdata_xlsx,
    "clean_database.records": op_clean_database_records,
    "chatgpt_format.prompt": op_chatgpt_format_prompt,
}


def main() -> int:
    _install_tk_stub()
    _bootstrap_path()

    # Redirect normal stdout (which the project modules pollute with
    # ``print("[INFO] ...")`` lines) to stderr, so we keep stdout clean
    # for the JSON response.
    real_stdout = sys.stdout
    sys.stdout = sys.stderr

    try:
        request = json.load(sys.stdin)
        op = request["op"]
        payload = request.get("payload", {})
        handler = HANDLERS[op]
        result = handler(payload)
        json.dump({"ok": True, "result": result}, real_stdout)
    except Exception as e:  # noqa: BLE001
        json.dump(
            {
                "ok": False,
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(),
                "side": str(Path.cwd()),
            },
            real_stdout,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
