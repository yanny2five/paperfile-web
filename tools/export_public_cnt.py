#!/usr/bin/env python3
"""
Export a .cnt with selected vita types removed (for web / public copy).

Default drops (McCarl): JD journal drafts, OI inactive draft, PR funding proposals, F contract reports.

  python tools/export_public_cnt.py --input path/to/full.cnt --output path/to/public.cnt
  python tools/export_public_cnt.py --list-types

Uses config database if --input omitted and config.json has database_path.

Hosting (two databases / two URLs):
  - Keep the full .cnt on your PC; run this script (or Utilities -> Download filtered .cnt) for the public file.
  - Deploy a second Render service pointing at the filtered .cnt by setting env
    PAPERFILE_DATABASE_PATH=/path/or/mounted/public.cnt (overrides config.json).
  - Optional PAPERFILE_APP_LABEL=Department vs Personal shows a banner on the retrieve page.
"""

from __future__ import annotations

import argparse
import os
import sys

# Repo root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from modules.filter_cnt_by_vita import (
    DEFAULT_PUBLIC_DROP_VITATYPES,
    filter_out_vita_types,
    vita_types_reference_lines,
)
from modules.readdata import CNTReader, get_config_path, read_json_with_guess, abs_from_config
from modules.utilities_web import write_cnt_new_file


def _resolve_input_path(arg: str | None) -> str:
    if arg and arg.strip():
        return os.path.abspath(os.path.normpath(arg.strip().strip('"')))
    cfg = get_config_path()
    if not cfg:
        raise SystemExit("No --input and no config.json found.")
    data = read_json_with_guess(cfg)
    p = abs_from_config(cfg, data.get("database_path"))
    if not p or not os.path.isfile(p):
        raise SystemExit("No --input and database_path in config is missing or not a file.")
    return p


def main() -> None:
    ap = argparse.ArgumentParser(description="Write a filtered .cnt for public / web hosting.")
    ap.add_argument("--input", "-i", help="Source .cnt (default: config.json database_path)")
    ap.add_argument("--output", "-o", required=False, help="Destination .cnt path")
    ap.add_argument(
        "--drop",
        default=",".join(sorted(DEFAULT_PUBLIC_DROP_VITATYPES)),
        help="Comma-separated vitatyp codes to exclude (default: JD,OI,PR,F)",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print counts only; do not write")
    ap.add_argument("--list-types", action="store_true", help="Print all vita type codes and exit")
    args = ap.parse_args()

    if args.list_types:
        for line in vita_types_reference_lines():
            print(line)
        return

    src = _resolve_input_path(args.input)
    if not args.output and not args.dry_run:
        raise SystemExit("Provide --output or use --dry-run")

    drop_codes = {x.strip().upper() for x in args.drop.split(",") if x.strip()}
    reader = CNTReader(src)
    all_recs = reader.get_data() or []
    kept, dropped_by = filter_out_vita_types(all_recs, drop_codes)

    n_drop = len(all_recs) - len(kept)
    print(f"Source: {src}")
    print(f"Records in: {len(all_recs)}  kept: {len(kept)}  removed: {n_drop}")
    for code in sorted(dropped_by.keys()):
        if dropped_by[code]:
            print(f"  dropped {code}: {dropped_by[code]}")

    if args.dry_run:
        return

    dest = os.path.abspath(os.path.normpath(args.output.strip().strip('"')))
    write_cnt_new_file(dest, kept, src)
    print(f"Wrote: {dest}")


if __name__ == "__main__":
    main()
