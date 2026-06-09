"""Year parsing for reports (aligns with desktop group output where years are non-numeric strings)."""


def extract_year_int(val) -> int | None:
    """Extract a 4-digit year from strings like 'September/October 2016'."""
    s = "" if val is None else str(val).strip()
    if not s:
        return None
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) >= 4:
        try:
            return int(digits[-4:])
        except ValueError:
            return None
    return None
