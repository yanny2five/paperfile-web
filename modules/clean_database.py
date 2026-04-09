import os
import re
import unicodedata
from modules.readdata import CNTReader
from tkinter import messagebox

REPLACEMENT_RULES = [
    ('\x93', '"'), ('\x94', '"'),
    ('[', '('), ('{', '('), (']', ')'), ('}', ')'), ('()', ''),
    ('( ', '('), (' )', ')'), (') ', ') '),
    (' :', ':'), (': ', ': '), (' ;', ';'), ('; ', ';'),
    (' ?', '?'), (' !', '!'),
    ('Texas A and M', 'Texas A&M'),
    ('doi:http', 'http'), ('doi. org/10. ', 'doi.org/10.'),
    ('doi. ', 'doi.'), ('/10. ', '/10.'),
    ('http: ', 'http:'), ('https: ', 'https:'), (': \\', ':\\'),
    (', Jr.', ' Jr.'), (',Jr.', ' Jr.'), (', Sr.', ' Sr.'), (',Sr.', ' Sr.'),
    (', III.', ' III.'), (',III.', ' III.'), (', II.', ' II.'), (',II.', ' II.'),
    (' Jr', ' Jr.'), (' Sr', ' Sr.'), (' III', ' III.'), (' IV', ' IV.'),
    ('  ', ' '), ('. ,', '.,'), (' .', '.'), ('..', '.'),
    ('. A.', '.A.'), ('. B.', '.B.'), ('. Z.', '.Z.'),
    (' /no', ''), ('/n0', ''), ('Sr.i', 'Sri'), ('Sr.a', 'Sra'), ('Sr.o', 'Sro')
]
for _ in range(4):
    REPLACEMENT_RULES.append(('  ', ' '))

# ---------- Name parsing helpers (prefix/suffix/particles aware) ----------

HONORIFICS = {
    "dr", "dr.", "prof", "prof.", "mr", "mr.", "mrs", "mrs.", "ms", "ms.",
    "miss", "sir", "dame", "rev", "rev."
}

SUFFIX_GEN = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}
SUFFIX_POSTNOM = {
    "phd", "ph.d", "ph.d.", "md", "m.d", "m.d.", "dds", "d.d.s", "dvm", "d.v.m",
    "esq", "esq.", "cpa", "mba", "msc", "m.sc", "m.sc."
}

LASTNAME_PARTICLES_1 = {
    "da", "de", "del", "della", "der", "di", "du", "la", "le",
    "van", "von", "den", "ter", "bin", "binti", "al", "el", "st", "st."
}
LASTNAME_PARTICLES_2 = {
    "van der", "de la", "de los", "de las"
}

def normalize_spaces_and_punctuation(text: str, is_authors: bool = False) -> str:
    """
    Normalize spacing and punctuation according to database cleaning rules.

    Rules:
    - Collapse repeated spaces first.
    - Remove spaces BEFORE . , : ;
    - Add exactly one space AFTER , ; : if there is not a space
    - Reduce multiple spaces AFTER , ; : to one space
    - Add exactly one space AFTER . if there is not a space (non-authors only)
    - Reduce multiple spaces AFTER . to one space (non-authors only)
    """

    if not text:
        return ""

    s = text

    # ---------- Collapse spaces ----------
    for _ in range(4):
        s = s.replace("    ", " ")

    for _ in range(2):
        s = s.replace("   ", " ")

    for _ in range(4):
        s = s.replace("  ", " ")

    # ---------- Remove spaces BEFORE punctuation ----------
    s = s.replace(" .", ".")
    s = s.replace(" ,", ",")
    s = s.replace(" :", ":")
    s = s.replace(" ;", ";")

    # ---------- Fix comma spacing ----------
    # ",xxx" -> ", xxx"   only if next char is not space
    s = re.sub(r',(?=\S)', ', ', s)
    # ",  xxx" -> ", xxx"
    s = re.sub(r',\s{2,}', ', ', s)

    # ---------- Fix semicolon spacing ----------
    # ";xxx" -> "; xxx"   only if next char is not space
    s = re.sub(r';(?=\S)', '; ', s)
    # ";  xxx" -> "; xxx"
    s = re.sub(r';\s{2,}', '; ', s)

    # ---------- Fix colon spacing ----------
    # Add one space after colon only when followed by a letter or digit,
    # but do not break URLs, paths, or protocol strings like http:// or D:\.
    s = re.sub(r':(?=[A-Za-zÀ-ÖØ-öø-ÿ0-9])', ': ', s)
    s = re.sub(r':\s{2,}(?=[A-Za-zÀ-ÖØ-öø-ÿ0-9])', ': ', s)

    # ---------- Fix period spacing (NOT for authors) ----------
    if not is_authors:
        # Only add a space after period when followed by a LETTER,
        # but do not break initials like A.B. or abbreviations like U.S.
        s = re.sub(r'(?<!\b[A-Z])\.(?=[A-ZÀ-ÖØ-Þ])', '. ', s)

        # ".  xxx" -> ". xxx"
        s = re.sub(r'\.\s{2,}', '. ', s)

    return s.strip()

def normalize_suffix_spacing(text: str) -> str:
    """
    Normalize suffix punctuation for Jr, Sr, II, III, IV.
    """
    if not text:
        return ""

    s = text
    suffixes = ["Jr", "Sr", "II", "III", "IV"]

    for suf in suffixes:
        # "Jr," -> "Jr.,"
        s = re.sub(rf"\b{suf}(?=,)", f"{suf}.", s)

        # "Jr " -> "Jr. "
        s = re.sub(rf"\b{suf}(?=\s)", f"{suf}.", s)

        # "Jr$" -> "Jr."
        s = re.sub(rf"\b{suf}$", f"{suf}.", s)

        # Collapse accidental double dots
        s = re.sub(rf"{suf}\.\.+", f"{suf}.", s)

    return s

def normalize_us_spelling(text: str) -> str:
    """
    Normalize variants of 'US' and 'U.S.'.

    Rules:
    - Normalize u.s, U.s, u.S, U.S, with or without trailing period, to U.S.
    - Normalize standalone Us / us to US.
    """
    if not text:
        return ""

    s = text

    # Normalize dotted variants such as:
    # U.s / U.s. / u.s / u.s. / u.S / u.S. / U.S / U.S.
    s = re.sub(r'\b[uU]\.[sS]\.?\b', 'U.S.', s)

    # Normalize plain Us / us to US
    s = re.sub(r'\b[Uu]s\b', 'US', s)

    return s
def normalize_period_sequences(text: str) -> str:
    """
    Collapse multiple periods into a single period.
    """
    if not text:
        return ""

    return re.sub(r'\.{2,}', '.', text)

def fix_unmatched_left_parenthesis(text: str) -> str:
    """
    If there are more left parentheses than right parentheses,
    append the missing number of right parentheses at the end.

    Rules:
    - Keep existing trailing ')' unchanged.
    - Only fix unmatched '(' by appending English ')'.
    - Do not remove any existing parentheses.
    """
    if not text:
        return ""

    s = str(text)
    diff = s.count("(") - s.count(")")
    if diff > 0:
        s = s + (")" * diff)
    return s

def fix_unmatched_parentheses_both_sides(text: str) -> str:
    """
    For location and volume:
    - If there are unmatched ')' before any matching '(',
      prepend the needed number of '(' at the beginning.
    - If there are unmatched '(' left at the end,
      append the needed number of ')' at the end.
    - This handles both count mismatch and order mismatch.
    """
    if not text:
        return ""

    s = str(text)

    balance = 0
    missing_left = 0

    for ch in s:
        if ch == "(":
            balance += 1
        elif ch == ")":
            if balance > 0:
                balance -= 1
            else:
                missing_left += 1

    missing_right = balance

    if missing_left > 0:
        s = ("(" * missing_left) + s
    if missing_right > 0:
        s = s + (")" * missing_right)

    return s

def _normalize_suffix(tok: str) -> str:
    """Normalize suffix casing/punctuation."""
    t = tok.strip().strip(",").strip()
    low = t.lower().rstrip(".")
    if low in {"jr", "sr"}:
        return low.capitalize() + "."
    if low in {"ii", "iii", "iv", "v"}:
        return low.upper()
    if low in {"phd", "ph.d"}:
        return "Ph.D."
    if low in {"md", "m.d"}:
        return "M.D."
    if low in {"dds", "d.d.s"}:
        return "DDS"
    if low in {"dvm", "d.v.m"}:
        return "DVM"
    if low == "esq":
        return "Esq."
    if low == "cpa":
        return "CPA"
    if low == "mba":
        return "MBA"
    if low in {"msc", "m.sc"}:
        return "M.Sc."
    return t

def _strip_honorifics(tokens):
    """Remove leading honorifics like 'Dr.' or 'Prof.'."""
    while tokens and tokens[0].lower().rstrip(".") in {h.rstrip(".") for h in HONORIFICS}:
        tokens.pop(0)
    return tokens

def _pull_suffixes(tokens):
    """
    Pop trailing suffix tokens (Jr., Ph.D., II, etc.).
    Return (core_tokens, suffix_list).
    Keep suffixes exactly as original (no normalization).
    """
    suffixes = []
    while tokens:
        tail = tokens[-1].strip().strip(",")
        low = tail.lower().rstrip(".")
        if low in {s.rstrip(".") for s in (SUFFIX_GEN | SUFFIX_POSTNOM)}:
            # Keep suffix exactly as written, do not normalize
            suffixes.append(tokens.pop().strip())
            continue
        if tail == "":
            tokens.pop()
            continue
        break
    suffixes.reverse()
    return tokens, suffixes


def _attach_particles_to_last(tokens):
    """
    Attach particles to last name (van der, de la, etc.).
    Apply special-case rules for O'/L' and multi-word exceptions.
    """
    if not tokens:
        return "", ""

    if re.match(r"^[OL](')?[A-Z][a-zA-Z]+$", tokens[-1]):
        last = _fix_special_lastnames(tokens[-1])
        first = " ".join(tokens[:-1]).strip()
        return first, last

    if len(tokens) == 1:
        last = _fix_special_lastnames(tokens[0])
        return "", last

    if re.match(r"^(O|L)[A-Z][a-zA-Z]+$", tokens[-1]) and "'" not in tokens[-1]:
        last = _fix_special_lastnames(tokens[-1])
        first = " ".join(tokens[:-1]).strip()
        return first, last
    # ---------------------------------------------------------------------

    # Multi-word exceptions
    exceptions_multiword = {("Cuadros", "Menaca"), ("Valdez", "Gonzalez")}
    if len(tokens) >= 2 and (tokens[-2], tokens[-1]) in exceptions_multiword:
        last = f"{tokens[-2]} {tokens[-1]}"
        first = " ".join(tokens[:-2]).strip()
        return first, last

    j = len(tokens) - 1
    last = tokens[j]
    j -= 1

    while j >= 0:
        if j - 1 >= 0:
            two = f"{tokens[j-1].lower()} {tokens[j].lower()}"
            if two in LASTNAME_PARTICLES_2:
                last = f"{tokens[j-1]} {tokens[j]} {last}"
                j -= 2
                continue
        if tokens[j].lower() in LASTNAME_PARTICLES_1:
            last = f"{tokens[j]} {last}"
            j -= 1
            continue
        break

    first = " ".join(tokens[: j + 1]).strip()
    last = _fix_special_lastnames(last)
    return first, last


def _tidy_name_text(s: str) -> str:
    """Keep Unicode letters/digits/basic punct; normalize spacing and initials."""

    # --- Fix compact Irish/French prefixes before anything else ---
    # OMalley -> O'Malley, OBrien -> O'Brien, LHoir -> L'Hoir
    s = re.sub(r"\b(O)([A-Z][a-z]+)\b", r"O'\2", s)
    s = re.sub(r"\b(L)([A-Z][a-z]+)\b", r"L'\2", s)

    # Keep Unicode letters/numbers, spaces, and selected punctuation.
    # Replace only clearly unwanted symbols with space.
    allowed_punct = set(" ,.'()-")
    cleaned_chars = []
    for ch in s:
        if ch.isalnum() or ch in allowed_punct:
            cleaned_chars.append(ch)
        else:
            cleaned_chars.append(" ")
    s = "".join(cleaned_chars)

    # Keep your initials-spacing logic, but allow Unicode surname letters after initials
    s = re.sub(r'(\b(?:[A-Z]\.){1,})\s*([A-Z][^\W\d_][^\s,]*)', r'\1 \2', s, flags=re.UNICODE)

    s = re.sub(r"\s+", " ", s).strip()
    return s


def _parse_name_to_forms(raw: str):
    """
    Parse one name into:
      - last_first:  'Last, First Middle [Suffixes]'
      - first_last:  'First Middle Last [Suffixes]'
    Handles honorifics, particles, and suffixes.
    """
    raw = _fix_initials(raw)

    s = _tidy_name_text(raw)

    # Comma form: 'Last, First Middle [, Suffix...]'
    if "," in s:
        left, right = s.split(",", 1)
        last_side = _tidy_name_text(left)
        right_tokens = [t for t in _tidy_name_text(right).replace(",", " ").split() if t]
        right_tokens = _strip_honorifics(right_tokens)
        right_tokens, suffixes = _pull_suffixes(right_tokens)
        first_side = " ".join(right_tokens).strip()
        suffix_str = (" " + " ".join(suffixes)) if suffixes else ""
        last_first = f"{last_side}, {first_side}{suffix_str}".strip()
        first_last  = f"{first_side} {last_side}{suffix_str}".strip()
        return last_first, first_last

    # Non-comma form: 'First [Middle] Last [Suffixes]'
    tokens = [t for t in s.replace(",", " ").split() if t]
    tokens = _strip_honorifics(tokens)
    tokens, suffixes = _pull_suffixes(tokens)
    first_part, last_part = _attach_particles_to_last(tokens)

    if not last_part and first_part:
        last_part, first_part = first_part, ""

    suffix_str = (" " + " ".join(suffixes)) if suffixes else ""
    if first_part:
        return f"{last_part}, {first_part}{suffix_str}".strip(), f"{first_part} {last_part}{suffix_str}".strip()
    else:
        lf = f"{last_part}{suffix_str}".strip()
        return lf, lf  # single token case

def _collapse_prior_ands_keep_last(s: str) -> str:
    """
    If an authors string contains more than one exact substring ' and ' (lowercase,
    surrounded by single spaces), convert all but the last ' and ' to ', '.
    Only matches the exact ' and ' (no case folding).
    """
    # Expect that whitespace has been normalized (single spaces)
    parts = s.split(" and ")
    if len(parts) <= 2:
        return s  # zero or one ' and ' -> nothing to do
    head = ", ".join(p.strip() for p in parts[:-1])
    tail = parts[-1].strip()
    return f"{head} and {tail}"


# ---------- Public API used by clean_database ----------

def clean_authors_field(authors_str):
    """
    Normalize an 'authors' field with awareness of prefixes/suffixes and name particles.

    Rules:
    - Single author (no 'and' and no ';'): output forced 'Last, First [Suffixes]'.
    - Otherwise:
        * Exactly two authors -> 'A and B' (no comma)
        * Three or more       -> 'A, B, and C' (Oxford comma)
      First author rendered 'Last, First ...'; others 'First Last ...'.
    """
    if not authors_str or not str(authors_str).strip():
        return ""

    s = str(authors_str).strip()
    s = re.sub(r'\s*&\s*', ' and ', s)
    s = re.sub(r'\s+', ' ', s)
    s = _collapse_prior_ands_keep_last(s)

    # Single-author path
    has_and = re.search(r'\band\b', s, flags=re.IGNORECASE) is not None
    has_semicolon = ';' in s
    if not has_and and not has_semicolon:
        last_first, _ = _parse_name_to_forms(s)
        return last_first

    # Multi-author: try to isolate final author by ' and '
    parts = s.rsplit(' and ', 1)
    if len(parts) == 2:
        main_part, last_author_raw = parts
        # Heuristic: authors before the last are most often comma-separated items.
        # This will not insert ', and' unless there are 3+ authors.
        raw_chunks = [a.strip() for a in main_part.split(',') if a.strip()]
    else:
        raw_chunks = [a.strip() for a in s.split(',') if a.strip()]
        last_author_raw = raw_chunks.pop() if raw_chunks else ""

    cleaned_authors = []
    for i, a in enumerate(raw_chunks):
        lf, fl = _parse_name_to_forms(a)
        cleaned_authors.append(lf if i == 0 else fl)

    lf_last, fl_last = _parse_name_to_forms(last_author_raw) if last_author_raw else ("", "")

    if cleaned_authors and (lf_last or fl_last):
        if len(cleaned_authors) == 1:
            # exactly two authors total
            return f"{cleaned_authors[0]} and {fl_last or lf_last}"
        else:
            # three or more; Oxford comma
            return ", ".join(cleaned_authors) + ", and " + (fl_last or lf_last)
    elif cleaned_authors:
        return ", ".join(cleaned_authors)
    else:
        # edge case: only one author survived this branch
        return lf_last or fl_last

def _fix_initials(name: str) -> str:
    """
    Normalize author initials.

    Rules:
    - Remove spaces between initials: A. B. -> A.B.
    - Ensure periods exist after single-letter initials: A B -> A.B.
    - Ensure space between last initial and surname: A.B.Carl -> A.B. Carl
    - Do not break valid initials such as A.B.
    - Do not modify suffix tokens.
    """

    # Fix compact Irish/French prefixes first
    name = re.sub(r"\b([OL])\.([A-Z][a-z][A-Za-z]+)\b", r"\1'\2", name)
    name = re.sub(r"\b([OL])([A-Z][a-z][A-Za-z]+)\b", r"\1'\2", name)

    roman_suffixes = {"II", "III", "IV", "V"}
    general_suffixes = {s.lower().rstrip(".") for s in (SUFFIX_GEN | SUFFIX_POSTNOM)}

    tokens = name.split()
    new_tokens = []

    for tok in tokens:

        # Keep suffix tokens unchanged
        if tok in roman_suffixes or tok.lower().rstrip(".") in general_suffixes:
            new_tokens.append(tok)
            continue

        # Keep O'Name / L'Name unchanged
        if re.match(r"^[OL]'.+$", tok):
            new_tokens.append(tok)
            continue

        t = tok

        # Convert single-letter tokens to initials
        # A -> A.
        t = re.sub(r"\b([A-Z])\b", r"\1.", t)

        # Convert compact initials like AB -> A.B.
        if re.fullmatch(r"[A-Z]{2,}", t):
            t = ".".join(list(t)) + "."

        new_tokens.append(t)

    s = " ".join(new_tokens)

    # Remove spaces between initials
    # A. B. -> A.B.
    s = re.sub(r"\b([A-Z])\.\s+(?=[A-Z]\.)", r"\1.", s)

    # Ensure space between final initial and surname
    # A.B.Carl -> A.B. Carl
    s = re.sub(r"((?:\b[A-Z]\.)+)([A-Z][a-z][A-Za-z\-']*)", r"\1 \2", s)

    # Collapse multiple periods
    s = re.sub(r"\.+", ".", s)

    return s


def _fix_special_lastnames(last: str) -> str:
    """
    Apply special-case corrections for last names.
    - O' prefix: ONeil -> O'Neil, OBrien -> O'Brien, OMalley -> O'Malley.
    - L' prefix: LHoir -> L'Hoir, LHeureux -> L'Heureux.
    Also accept mistakenly dotted forms like O.Malley -> O'Malley.
    """
    exceptions = {"Cuadros Menaca", "Valdez Gonzalez"}
    if last in exceptions:
        return last

    # Dotted mistaken forms -> apostrophe
    if re.match(r"^[OL]\.[A-Z][a-zA-Z]+$", last) and "'" not in last:
        return last[0] + "'" + last[2:]

    # Compact forms without apostrophe
    if re.match(r"^O[A-Z][a-zA-Z]+$", last) and "'" not in last:
        return "O'" + last[1:]
    if re.match(r"^L[A-Z][a-zA-Z]+$", last) and "'" not in last:
        return "L'" + last[1:]

    return last


def strip_edges_general(text: str) -> str:
    """
    For all non-author fields:
    - Remove leading characters until the first char is alphanumeric.
    - Remove trailing characters until the last char is alphanumeric.
    - Use Unicode-aware str.isalnum(), so letters like ä / Ö are preserved.
    """
    if text is None:
        return ""

    s = str(text).strip()

    while s and not s[0].isalnum():
        s = s[1:]

    while s and not s[-1].isalnum():
        s = s[:-1]

    return s


def strip_edges_authors(text: str) -> str:
    """
    For authors field:
    - Remove leading characters until the first char is alphanumeric.
    - Remove trailing characters until the last char is alphanumeric or period.
    - Use Unicode-aware str.isalnum(), so letters like ä / Ö are preserved.
    """
    if text is None:
        return ""

    s = str(text).strip()

    while s and not s[0].isalnum():
        s = s[1:]

    while s and not (s[-1].isalnum() or s[-1] == '.'):
        s = s[:-1]

    return s

def strip_edges_allow_parentheses(text: str) -> str:
    """
    For location and volume fields:
    - Remove leading characters until the first char is alphanumeric or '(' or ')'
    - Remove trailing characters until the last char is alphanumeric or '(' or ')'
    - Keep edge parentheses if they are part of the content.
    """
    if text is None:
        return ""

    s = str(text).strip()

    while s and not (s[0].isalnum() or s[0] in "()"):
        s = s[1:]

    while s and not (s[-1].isalnum() or s[-1] in "()"):
        s = s[:-1]

    return s

def clean_edge_symbols(text: str) -> str:
    """
    Backward-compatible wrapper for old pages.

    This keeps the old function name used by existing pages,
    while internally using the new general edge stripping logic.
    """
    return strip_edges_general(text)


def ascii_only(text: str) -> str:
    """
    Backward-compatible wrapper for old pages.

    Keep the legacy behavior:
    remove accents and convert text to ASCII when needed by old UI pages.
    """
    if text is None:
        return ""
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')

def title_case(text):
    """Capitalize words except common stopwords (unless first word).
    Preserve acronyms such as US, U.S., USDA, NASA.
    """
    stopwords = {'and', 'or', 'the', 'of', 'in', 'on', 'at', 'for', 'to', 'with', 'by'}
    words = text.split()
    titled = []

    for i, w in enumerate(words):
        clean = w.strip()

        # Preserve dotted acronyms like U.S. / U.K. with optional trailing punctuation
        if re.fullmatch(r'(?:[A-Z]\.){2,}[,;:.)]?$', clean):
            titled.append(clean)
            continue

        # Preserve all-caps acronyms like US / USDA / NASA with optional trailing punctuation
        if re.fullmatch(r'[A-Z]{2,}[,;:.)]?$', clean):
            titled.append(clean)
            continue

        if i == 0 or w.lower() not in stopwords:
            titled.append(w.capitalize())
        else:
            titled.append(w.lower())

    return ' '.join(titled)

from modules.readdata import CNTReader

def clean_database(file_path):
    try:
        reader = CNTReader(file_path)
        reader.read_file()
        original_data = reader.get_data()

        journal_map = {}
        try:
            _, journal, _ = reader.read_journal_definition()
            journal_map = {j.lower(): j for j in journal.keys()}
        except Exception as e:
            print(f"[WARNING] Could not load journal definition: {e}")

        cleaned_data = []
        for record in original_data:
            cleaned_record = {}
            for key, value in record.items():
                val = "" if value is None else str(value)

                # Bulk replacements
                for _ in range(5):
                    for old, new in REPLACEMENT_RULES:
                        val = val.replace(old, new)
                val = val.strip()

                kl = key.lower()

                if kl == 'authors':

                    val = normalize_spaces_and_punctuation(val, is_authors=True)
                    val = normalize_us_spelling(val)
                    val = normalize_period_sequences(val)
                    val = strip_edges_authors(val)

                    try:
                        val = clean_authors_field(val)
                    except Exception:
                        pass

                    val = normalize_suffix_spacing(val)

                else:
                    # Apply general cleaning to all non-author fields first
                    val = normalize_spaces_and_punctuation(val, is_authors=False)
                    val = normalize_us_spelling(val)
                    val = normalize_period_sequences(val)

                    if kl in {"location", "volume"}:
                        val = strip_edges_allow_parentheses(val)
                    else:
                        val = strip_edges_general(val)

                    if kl == 'bookjour':
                        if val:
                            low = val.lower()
                            if low in journal_map:
                                if val != journal_map[low]:
                                    print(f"[INFO] bookjour '{val}' standardized to '{journal_map[low]}'")
                                val = journal_map[low]
                            else:
                                val = title_case(val)

                        val = normalize_suffix_spacing(val)


                    elif kl == 'title':

                        if val:
                            val = title_case(val)
                            val = normalize_us_spelling(val)
                            val = fix_unmatched_left_parenthesis(val)

                        val = normalize_suffix_spacing(val)


                    elif kl == 'volume':

                        if val:
                            val = fix_unmatched_parentheses_both_sides(val)

                        val = normalize_suffix_spacing(val)


                    elif kl == 'location':

                        if val:
                            val = fix_unmatched_parentheses_both_sides(val)

                        val = normalize_suffix_spacing(val)

                    else:
                        val = normalize_suffix_spacing(val)

                cleaned_record[key] = val

            cleaned_data.append(cleaned_record)

        # Write back
        content = []
        for record in cleaned_data:
            record_content = "\n".join([f"{k}||{v}" for k, v in record.items()])
            content.append(f"{record_content}\n*********$$$$$$$$$$$$")

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(content))

        print("[INFO] Database cleaned successfully.")

    except Exception as e:
        messagebox.showerror("Error", f"Standardization failed: {str(e)}")
