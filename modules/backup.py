import os
import sys
import shutil
import datetime
import json
from tkinter import messagebox


# -----------------------------
# Helpers
# -----------------------------
def _get_config_path_near_main() -> str:
    """
    Return config.json path alongside exe (frozen) or alongside project root script.
    This mirrors the logic used elsewhere in your project.
    """
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        # This file is likely modules/<this_file>.py -> go up one level to project root
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "config.json")


def _read_json_guess(path: str) -> dict:
    """
    Try multiple encodings to read JSON safely.
    Return {} on failure.
    """
    encodings = ["utf-8", "utf-8-sig", "gb18030", "gbk", "big5", "cp1252", "latin-1"]
    if not os.path.exists(path):
        return {}

    last_err = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return json.load(f)
        except Exception as e:
            last_err = e
            continue

    # Do not crash; just warn user
    messagebox.showerror("Backup Failed", f"Cannot read config.json:\n{path}\n\nError: {last_err}")
    return {}


def _safe_copy(src: str, dst: str) -> None:
    """Copy file with metadata; raise if fails."""
    shutil.copy2(src, dst)


# -----------------------------
# Main function
# -----------------------------
def backup_file(file_path: str | None = None):
    """
    Backup database-related files into a timestamped folder.

    Sources (from config.json):
      - database_path -> .cnt
      - faculty_file -> .cng
      - journal_definition_file -> .cnj

    Behavior:
      - Create timestamped folder under the .cnt directory
      - Copy the three files into that folder (even if they are from different directories)
      - Rename them to share the same base name (stem) based on the .cnt file name

    :param file_path: Optional .cnt path. If provided, it will override config['database_path'].
    """
    try:
        # Load config
        cfg_path = _get_config_path_near_main()
        cfg = _read_json_guess(cfg_path)

        # Resolve three paths
        db_path = (file_path or cfg.get("database_path") or "").strip()
        fac_path = (cfg.get("faculty_file") or "").strip()
        jou_path = (cfg.get("journal_definition_file") or "").strip()

        # Normalize paths
        db_path = os.path.normpath(db_path) if db_path else ""
        fac_path = os.path.normpath(fac_path) if fac_path else ""
        jou_path = os.path.normpath(jou_path) if jou_path else ""

        # Validate existence
        missing = []
        if not (db_path and os.path.isfile(db_path)):
            missing.append(f"database_path (.cnt): {db_path or '[empty]'}")
        if not (fac_path and os.path.isfile(fac_path)):
            missing.append(f"faculty_file (.cng): {fac_path or '[empty]'}")
        if not (jou_path and os.path.isfile(jou_path)):
            missing.append(f"journal_definition_file (.cnj): {jou_path or '[empty]'}")

        if missing:
            messagebox.showerror(
                "Backup Failed",
                "Cannot find required files:\n\n" + "\n".join(missing) + f"\n\nConfig: {cfg_path}"
            )
            return

        # Build backup folder under the .cnt directory
        db_dir = os.path.dirname(os.path.abspath(db_path))
        stem = os.path.splitext(os.path.basename(db_path))[0]
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = os.path.join(db_dir, f"{stem}_backup_{ts}")

        os.makedirs(backup_dir, exist_ok=False)

        # Keep database name unchanged
        dst_cnt = os.path.join(backup_dir, f"{stem}.cnt")

        # Rename faculty file
        dst_cng = os.path.join(backup_dir, "faculty.cng")

        # Rename journal definition file
        dst_cnj = os.path.join(backup_dir, "journal.cnj")

        _safe_copy(db_path, dst_cnt)
        _safe_copy(fac_path, dst_cng)
        _safe_copy(jou_path, dst_cnj)

        messagebox.showinfo(
            "Backup Successful",
            "Backup folder created:\n"
            f"{backup_dir}\n\n"
            "Files copied:\n"
            f"{dst_cnt}\n{dst_cng}\n{dst_cnj}"
        )

    except FileExistsError:
        messagebox.showerror("Backup Failed", "Backup folder already exists. Please try again.")
    except Exception as e:
        messagebox.showerror("Backup Failed", f"An error occurred during backup:\n{str(e)}")
