import os
import sys
import json


def _database_path_from_environment() -> str | None:
    """Optional override for hosted / second-instance deploys (Render, etc.)."""
    raw = (os.environ.get("PAPERFILE_DATABASE_PATH") or "").strip().strip('"')
    if not raw:
        return None
    p = os.path.abspath(os.path.normpath(raw))
    return p if os.path.isfile(p) else None


def get_config_path():
    """
    Locate config.json with a consistent strategy:
    1) If running as PyInstaller exe, look next to the executable.
    2) Dev fallback: <this file>/../config.json.
    3) As a last resort, current working directory.
    Return None if not found.
    """
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        p = os.path.join(exe_dir, "config.json")
        if os.path.exists(p):
            return p

    p = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json")
    )
    if os.path.exists(p):
        return p

    p = os.path.abspath("config.json")
    if os.path.exists(p):
        return p

    return None


def abs_from_config(cfg_path, maybe_rel):
    """
    Make a path absolute based on the directory of config.json.
    If already absolute or empty, return as-is.
    """
    if not maybe_rel:
        return None
    if os.path.isabs(maybe_rel):
        return maybe_rel
    return os.path.abspath(os.path.join(os.path.dirname(cfg_path), maybe_rel))


def read_json_with_guess(path, encodings=None):
    """
    Read a JSON file with multiple encoding fallbacks.
    """
    if encodings is None:
        # utf-8-sig before utf-8 so JSON with BOM decodes (json.load rejects BOM under utf-8)
        encodings = ["utf-8-sig", "utf-8", "utf-16", "latin-1", "ISO-8859-1", "cp1252"]

    last_err = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return json.load(f)
        except UnicodeDecodeError as e:
            last_err = e
            continue

    raise RuntimeError(f"Failed to decode JSON file {path}: {last_err}")


def read_text_with_guess(path, encodings=None):
    """
    Try multiple encodings to read a text file.
    Returns (text, encoding, lines_with_endings).
    """
    if encodings is None:
        encodings = [
            "utf-8",
            "utf-8-sig",
            "utf-16",
            "gb18030",
            "gbk",
            "big5",
            "cp1252",
            "latin-1",
            "ISO-8859-1",
        ]

    last_err = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                text = f.read()
            lines = text.splitlines(keepends=True)
            return text, enc, lines
        except UnicodeDecodeError as e:
            last_err = e
            continue

    with open(path, "rb") as f:
        data = f.read()
    text = data.decode("latin-1", errors="replace")
    lines = text.splitlines(keepends=True)
    return text, "latin-1", lines


class CNTReader:
    def __init__(self, file_path=None):
        self.data = []
        self.file_path = file_path or self._load_database_path_from_config()
        self.read_file()

    def _load_database_path_from_config(self):
        """
        Load database path from config.json with robust encoding and path resolution.
        If PAPERFILE_DATABASE_PATH is set to an existing file, it wins over config.json
        (useful for a second Render service or a filtered .cnt without editing config).
        """
        try:
            env_db = _database_path_from_environment()
            if env_db:
                return env_db

            cfg = get_config_path()
            if not cfg:
                print("[CNTReader] config.json not found (get_config_path returned None)")
                return None

            cfg_json = read_json_with_guess(cfg)
            db_path = abs_from_config(cfg, cfg_json.get("database_path"))

            if not db_path:
                print("[CNTReader] No database_path found in config.json")
                return None

            return db_path

        except Exception as e:
            print(f"[CNTReader] Failed to read config.json: {e}")
            return None

    def read_file(self):
        try:
            self.data = []

            if not self.file_path or not os.path.exists(self.file_path):
                raise FileNotFoundError(f"File {self.file_path} does not exist")

            ext = os.path.splitext(self.file_path)[1].lower()

            if ext in (".xlsx", ".csv"):
                self._read_table_file(ext)
                return

            encodings = ["utf-8", "utf-8-sig", "utf-16", "latin-1", "ISO-8859-1", "cp1252"]
            content = None

            for encoding in encodings:
                try:
                    with open(self.file_path, "r", encoding=encoding) as file:
                        content = file.read()
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                raise RuntimeError("Failed to decode the file")

            records = content.strip().split("*********$$$$$$$$$$$$")
            for record in records:
                if not record.strip():
                    continue

                record_dict = {}
                for line in record.strip().split("\n"):
                    if "||" in line:
                        key, value = line.split("||", 1)
                        record_dict[key.strip()] = value.strip()

                if record_dict:
                    self.data.append(record_dict)

        except Exception as e:
            print(f"[ERROR] An error occurred while reading the file: {e}")

    def _read_table_file(self, ext):
        """
        Read .xlsx or .csv using headers; keep values as strings to match CNT behavior.
        """
        try:
            import pandas as pd

            if ext == ".xlsx":
                df = pd.read_excel(self.file_path, dtype=str)
            else:
                df = pd.read_csv(self.file_path, dtype=str)

            df = df.fillna("")
            self.data = df.to_dict(orient="records")

        except Exception as e:
            print(f"[ERROR] An error occurred while reading the table file: {e}")

    def get_faculty(self):
        """
        Load faculty information from the path stored in config.json.
        Returns a list of dicts with keys: name, positions, year, citations.
        """
        try:
            cfg = get_config_path()
            if not cfg:
                return []

            config = read_json_with_guess(cfg)
            faculty_path = abs_from_config(cfg, config.get("faculty_file"))

            if not faculty_path or not os.path.exists(faculty_path):
                return []

            faculty_data = []
            _, enc, lines = read_text_with_guess(faculty_path)

            for line in lines:
                parts = line.strip().split("::")
                if len(parts) < 2:
                    continue

                name = parts[0].strip()
                details = parts[1].split(";;")

                position_string = details[0] if len(details) > 0 else ""
                positions = [p.strip() for p in position_string.split(",") if p.strip()]
                positions = ["MS Student" if p == "Masters Student" else p for p in positions]

                year = int(details[1]) if len(details) > 1 and details[1].isdigit() else None
                citations = int(details[2]) if len(details) > 2 and details[2].isdigit() else None

                faculty_data.append(
                    {
                        "name": name,
                        "positions": positions,
                        "year": year,
                        "citations": citations,
                    }
                )

            return faculty_data

        except Exception as e:
            print(f"Failed to load faculty: {e}")
            return []

    def read_journal_definition(self):
        """
        Robust parser for CNJ journal definition files.

        Returns:
            journal_rank: {major_class -> (sort_order, norm)}
            journal_dict: {journal_name -> ("Major::Minor", rank_str)}
            sjr_data:     {journal_name -> {"pct":..., "quartile":..., "abdc":...}}
        """
        import re

        journal_rank = {}
        journal_dict = {}
        sjr_data = {}

        try:
            cfg = get_config_path()
            if not cfg:
                raise FileNotFoundError("config.json not found")

            config = read_json_with_guess(cfg)
            file_path = abs_from_config(cfg, config.get("journal_definition_file", ""))

            if not file_path or not os.path.exists(file_path):
                raise FileNotFoundError("Journal definition file not found")

            _, enc, lines = read_text_with_guess(file_path)

            classcount_idx = -1
            startjournals_idx = -1

            for idx, line in enumerate(lines):
                if line.strip() == "CLASSCOUNT":
                    classcount_idx = idx
                elif line.strip() == "STARTJOURNALS":
                    startjournals_idx = idx

            if classcount_idx == -1 or startjournals_idx == -1:
                raise ValueError("Missing CLASSCOUNT or STARTJOURNALS")

            class_count_line = lines[classcount_idx + 1].strip()
            if not class_count_line.isdigit():
                raise ValueError("CLASSCOUNT number invalid")

            class_count = int(class_count_line)
            class_lines = lines[classcount_idx + 2 : classcount_idx + 2 + class_count]

            for ln in class_lines:
                s = ln.strip()
                if ">>" not in s or "::" not in s:
                    continue

                try:
                    major, tail = s.split("::", 1)
                    sort_order_str, norm_part = tail.split(">>", 1)
                    sort_order = int(sort_order_str.strip())

                    norm_str = norm_part.replace("zz", "").strip()
                    norm = int(norm_str) if norm_str.isdigit() else 0

                    journal_rank[major.strip()] = (sort_order, norm)

                except Exception:
                    continue

            pat = re.compile(r"^(.*?)>>(.*?)\?\?(.*)$")

            for ln in lines[startjournals_idx + 1 :]:
                s = ln.strip()
                if not s or ">>" not in s or "??" not in s:
                    continue

                m = pat.match(s)
                if not m:
                    continue

                class_part = m.group(1).strip()
                journal_name = m.group(2).strip()
                right_part = m.group(3).strip()

                parts = [p.strip() for p in right_part.split(";") if p.strip()]
                rank_str = parts[0]

                if not rank_str.isdigit():
                    digits = "".join(ch for ch in rank_str if ch.isdigit())
                    rank_str = digits if digits else "10"

                pct = ""
                quart = ""
                abdc = ""

                for token in parts[1:]:
                    up = token.upper()
                    if up.startswith("PCT="):
                        pct = token.split("=", 1)[1].strip()
                    elif up.startswith("Q="):
                        quart = token.split("=", 1)[1].strip()
                    elif up.startswith("ABDC="):
                        abdc = token.split("=", 1)[1].strip()

                journal_dict[journal_name] = (class_part, rank_str)

                if pct or quart or abdc:
                    sjr_data[journal_name] = {
                        "pct": pct,
                        "quartile": quart,
                        "abdc": abdc,
                    }

        except Exception as e:
            print(f"[ERROR] read_journal_definition: {e}")

        return journal_rank, journal_dict, sjr_data

    def reload_data(self):
        self.read_file()

    def get_data(self):
        return self.data

    def get_file_info(self):
        return self.file_path, len(self.data)