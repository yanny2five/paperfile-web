"""Journal ranking lookup for reports (from desktop groupoutput._load_journal_info)."""


def build_journal_info_from_reader(reader) -> dict:
    """
    Returns dict keyed by lower-cased journal name:
    { "name": { "rank", "norm", "sjr_pct", "quartile", "abdc" } }
    """
    try:
        journal_rank, journal_dict, sjr_from_file = reader.read_journal_definition()
    except Exception:
        return {}

    sjr_map = {}
    if isinstance(sjr_from_file, dict):
        for k, v in sjr_from_file.items():
            key = str(k).strip().lower()
            if not key:
                continue
            rec = {"sjr_pct": "", "quartile": "", "abdc": ""}
            if isinstance(v, dict):
                rec["sjr_pct"] = str(
                    v.get("sjr_pct", v.get("pct", v.get("PCT", v.get("sjr", "")))) or ""
                ).strip()
                rec["quartile"] = str(
                    v.get("quartile", v.get("q", v.get("Q", ""))) or ""
                ).strip()
                rec["abdc"] = str(v.get("abdc", v.get("ABDC", "")) or "").strip()
            elif isinstance(v, (list, tuple)):
                if len(v) >= 1:
                    rec["sjr_pct"] = str(v[0] or "").strip()
                if len(v) >= 2:
                    rec["quartile"] = str(v[1] or "").strip()
                if len(v) >= 3:
                    rec["abdc"] = str(v[2] or "").strip()
            sjr_map[key] = rec

    result = {}
    for name, (class_info, rank_str) in (journal_dict or {}).items():
        name_str = str(name).strip()
        if not name_str:
            continue
        major_class = str(class_info).split("::")[0].strip()
        _, norm = journal_rank.get(major_class, (None, 0))
        try:
            rank = int(str(rank_str).strip())
        except Exception:
            continue
        normalized = "1+" if rank == 0 else (rank + (norm or 0))
        key = name_str.lower()
        extra = sjr_map.get(key, {})
        result[key] = {
            "rank": rank,
            "norm": normalized,
            "sjr_pct": str(extra.get("sjr_pct", "") or "").strip(),
            "quartile": str(extra.get("quartile", "") or "").strip(),
            "abdc": str(extra.get("abdc", "") or "").strip(),
        }
    return result
