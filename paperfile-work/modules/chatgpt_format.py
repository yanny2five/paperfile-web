def format_citations_with_chatgpt(text: str) -> str:
    """
    Use ChatGPT API (gpt-4o) to format the input citation into a structured format.

    Args:
        text (str): Raw citation text to be formatted.

    Returns:
        str: A single-line formatted citation or None if failed.
    """
    import os

    import openai

    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        print("[OpenAI] Set OPENAI_API_KEY in the environment to use citation formatting.")
        return None

    try:
        client = openai.OpenAI(api_key=api_key)
    except Exception as e:
        print("[OpenAI Initialization Error]:", e)
        return None

    prompt = f"""
    You are a robust citation parser AND segmenter.

    Your task:
    - If the input contains ONE citation: output EXACTLY one line.
    - If the input contains MULTIPLE citations: split them into individual entries first, then output one line per entry.

    OUTPUT FORMAT (MUST FOLLOW):
    For EACH citation entry, output EXACTLY one line with 10 fields separated by " | " in this exact order:

    authors | title | book_or_journal | location | volume | pages | year | keyword1 | keyword2 | url

    If multiple citations are detected, output multiple such lines separated ONLY by a single newline "\\n".
    Do NOT output any extra commentary, headers, numbering, bullets, JSON, or blank lines.

    CRITICAL RULES (MUST FOLLOW):
    1) Never drop information. If any part cannot be confidently mapped to a field, append it to url.
       Do NOT use any prefix like "UNMAPPED:".
    2) Always output all 10 fields for each citation. If a field is missing, leave it blank but keep separators.
    3) Do NOT invent values. Only extract what is present.
    4) Do NOT output bullet points, explanations, JSON, or extra lines other than the required citation line(s).
    5) Do NOT include the character "|" inside any field value. If the citation contains "|", replace it with "/".
    6) If there are multiple leftover/unmapped fragments, append them in url separated by " ; ".
    7) Preserve capitalization for acronyms and abbreviations exactly as in the citation (e.g., AAEA, IEEE, AMS). Do not normalize them.
    8) If a phrase is not separated by commas in the citation text, treat it as a single indivisible unit.
       Do NOT split such phrases across multiple fields.
    9) Each piece of information may appear in ONLY ONE field.
       Once a phrase is assigned to a field, do NOT repeat it in any other field.
    10) Any phrase beginning with "presented at", "presentation at", "presented in",
        "presented during", or "presentation in" creates a LOCATION BLOCK.
        All text from that phrase up to (but not including) a date/year token
        must be placed together into the location field and must NOT be split.
    11) If a location block begins with phrases such as
        "presented at", "presentation at", "presented in", or "presentation in",
        preserve these words EXACTLY as they appear in the citation.
        Do NOT remove, paraphrase, or omit them.
    12) The input may contain multiple citations pasted from a CV. You MUST segment them into separate entries BEFORE parsing.
    13) Safely ignore ONLY leading bullet/number prefixes at the START of each entry, such as:
        "•", "-", "–", "—", "*", "1.", "55.", "56.", "(1)", "[1]".
        Remove the prefix from the entry, but DO NOT drop any other content.
    14) Author initials formatting MUST NOT contain spaces between initials:
        - "Richard T. Woodward" -> "R.T. Woodward" (NOT "R. T. Woodward")
        - Hyphenated given names MUST be collapsed to initials WITHOUT hyphen:
        - "Jing-Yue Liu" -> "J.Y. Liu" (NOT "J.-Y. Liu")
        - "Yue-Jun Zhang" -> "Y.J. Zhang" (NOT "Y.-J. Zhang")
        - "Jesse D. Backstrom" -> "J.D. Backstrom"
        For the first author in "Last, F.M." style, also join initials with no spaces: "Woodward, R.T."
        Never output "F. M." with a space. Always "F.M."
    15) Treat trailing notes like "SJR: 0.81", "Selected for ...", "Editor Highlight ..." as notes.
        Keep them (do not drop), and if they do not fit standard fields, append them to url using " ; ".
    16) Suffix handling in author names:
    If a suffix is written with comma-separated style like "Capps, Jr., O." or "Smith, III, J.D.",
    you MUST output it without the extra comma after the last name:
    "Capps Jr., O." and "Smith III, J.D.".
    Do NOT output "Last, Jr., F." in the authors field.
    17) Year field MUST be digits only:
    - The year field output must be a pure 4-digit year like "2025".
    - If the citation contains month/day text such as "September 2025", "Sep. 2025", "September/October 2016",
      you MUST output only the year digits (e.g., "2025" or "2016") in the year field.
    - Any removed month/day text MUST be appended to the url field as extra information (separated by " ; " if needed).
    - Do NOT output month names, seasons, or ranges in the year field.

    SEGMENTATION RULES (HOW TO SPLIT MULTIPLE ENTRIES):
    A) Consider each NEW citation entry to start when, after trimming leading spaces, a line begins with:
       - a bullet/number prefix (see rule 13), OR
       - an author-list pattern: a capitalized surname followed by a comma, e.g., "Zhang," "Backstrom," "Knappett,"
    B) Continuation lines belong to the previous entry if they start with:
       - "SJR:", "Impact Factor", "Selected for", "Awarded", "Editor Highlight"
       - or a bare URL/DOI line starting with "http", "https", "doi:"
    C) If an entry is split across multiple lines, merge them into ONE entry string before parsing fields.
    D) If two citations accidentally appear on the same physical line, split them when you observe a NEW author-list pattern
       (Surname, ...) followed by a year-like token (e.g., 2023, 2022) in that substring.

    FIELD GUIDANCE:
    - authors:
      - The author string may use separators: comma, ";", "&", "and".
        Treat "&" as an author separator equivalent to "and" (DO NOT drop the author after "&").
      - Parse ALL authors that appear before the year/date token.
      - Author output format:
        - First author: "Last, F.M." style (NO spaces between initials).
        - Other authors: "F.M. Last" style (NO spaces between initials).
        - Use commas between authors and "and" before the last author.
      - Name cleaning inside author parsing:
        - Remove trailing punctuation after given names/initials, e.g., "Ying." -> "Ying", "Richard.T." -> "Richard T."
          (this is only for parsing; final output must still follow the no-space initials rule like "R.T. Woodward").
        - Remove symbols like *, †, ‡, #, ^, ± from names.
          - If uncertain whether a token is an author, prefer keeping it in authors (not url) IF it matches a name-like pattern.
          - If authors still cannot be reliably parsed, leave authors blank and move the author-looking text into url.


    - title:
      - Extract the work title without quotes if possible.

    - book_or_journal:
      - Use this field for the primary container/outlet (journal/book/proceedings/report/etc.).

    - location:
      - Meeting/event context + physical location combined when applicable.
      - Do not put date strings here; dates belong in the year field.

    - volume:
      - Volume/issue/number if present (e.g., "67(3)", "20(4)", "Vol. 12, No. 3").

    - pages:
      - Page range or article number (e.g., "438–458", "435-463", "100077", "3741").

    - year:
      - Output MUST be a 4-digit year only (digits only).
      - Prefer the most specific date expression if present; else 4-digit year.
      - If multiple years/dates exist and uncertain, choose best publication date and append others to url.

    - keyword1/keyword2:
      - Keep blank unless explicitly present.

    - url:
      - Put DOI/URL/ISBN/ISSN/arXiv/report number if present.
      - Append ALL leftover/unmapped parts here (no special prefix), separated by " ; ".

    SELF-CHECK BEFORE OUTPUT:
    - If the input contains "&" or "and" in the author segment, ensure authors includes BOTH sides (do not keep only the first author).
    - Ensure bullet/number prefixes are removed from the beginning of each entry (rule 13), but nothing else is removed.
    - Ensure initials have NO spaces: "R.T." not "R. T."
    - Ensure each output line has exactly 9 separators " | " (10 fields).
    - If multiple entries are detected, output one parsed line per entry, separated only by "\\n".

    Citation(s):
    \"\"\"{text.strip()}\"\"\"
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=3000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("[GPT API Error]:", e)
        return None
