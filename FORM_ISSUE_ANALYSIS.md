"""
Analysis of Form Issues with Paper Number Search

Issue 1: Text box clearing after submit
Issue 2: Wrong results when searching by number

ROOT CAUSE ANALYSIS:
"""

analysis = """
ISSUE 1: TEXT BOX CLEARS AFTER SUBMIT
=====================================

The template (index.html line 278) DOES preserve the form value:
  <input type="text" id="number_query" name="query" value="{{ request.form.get('query', '') }}">

HOWEVER, there may be a JavaScript issue. Let me check the "updateVisibleFields()" function.

The form uses multiple input fields for different search types:
  - mode-number field for "Select by Number" (line 276-279)
  - mode-multiple_numbers field for "Select multiple papers" (line 281-284)
  - mode-year field for "Select by Year" (line 291-294)
  - etc.

Each field has name="query" but different IDs and CSS classes.

When user submits with "Select by Number" (search_type=number), the form value
SHOULD be preserved... but JavaScript might be clearing it. Need to check if
JavaScript is resetting form fields on page load.


ISSUE 2: WRONG RESULTS WHEN SEARCHING FOR "10"
================================================

Looking at the form placeholder text on line 283:
  placeholder="74, 312, 708"

These are valid paper numbers in the database!

HYPOTHESIS: User accidentally selected "Select multiple papers by Number" instead of
"Select by Number"

When searching for "10" in multiple_numbers mode:
  - Query is parsed as a list: ["10"]
  - Only papers with EXACT number "10" should match
  - This is correct behavior!

BUT if there's any issue with how the form is mapping search_type to the
query function, it could cause wrong results.

TESTING RESULTS:
- search_type="number" with query="10" → Returns paper #10 only [CORRECT]
- search_type="multiple_numbers" with query="10" → Returns paper #10 only [CORRECT]


POTENTIAL CAUSES:
1. JavaScript clearing form on load
2. Different search type being submitted than expected
3. Form not properly tracking which fields have values
4. CSS hiding/showing wrong fields


RECOMMENDATION:
Modify the template to:
1. Preserve form state more explicitly
2. Clear JavaScript debouncing
3. Add form debugging to show what's being submitted
"""

print(analysis)

EOF
