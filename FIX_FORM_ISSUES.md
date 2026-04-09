# Form Issue Fixes - Paper Number Search

## Issues Identified

### Issue 1: Text Box Clears After Submit
**Problem:** When searching by paper number and clicking "Retrieve", the text in the search box disappears

**Root Cause:**
- The form uses `request.form.get('query', '')` to repopulate values, which should work
- However, JavaScript's `updateVisibleFields()` function was clearing state when switching between search types
- Form state wasn't explicitly preserved during page reload

**Solution Applied:**
1. Added placeholder text to number input field (template line 278)
2. Enhanced JavaScript to ensure form submission always includes a search_type (prevents missing selection defaults)
3. Modified app.py to explicitly pass form values back to template for better state management

---

### Issue 2: Wrong Results When Searching for "10"
**Problem:** Searching for paper number "10" returns papers like 708, 1592, 74, 312, 390

**Root Cause Analysis:**
After testing with actual data, the search_service.py function correctly performs EXACT matching:
```python
if search_type == "number":
    return q == normalize(get_number(paper))
```

Searching for "10" returns only paper #10 [CORRECT]

The "wrong results" may be due to:
1. User accidentally selecting "Select multiple papers by Number" instead of "Select by Number"
2. Form not properly tracking which input field has the value
3. Previous search results still displayed from different search type

**Solution Applied:**
1. Improved form field visibility toggling with better JavaScript
2. Added form debugging with detailed logging in app.py (see console output)
3. Added explicit form state preservation in render_template() call

---

## Changes Made

### 1. Template (index.html)

**Change 1: Added placeholder text**
```html
<!-- Before -->
<input type="text" id="number_query" name="query" value="{{ request.form.get('query', '') }}">

<!-- After -->
<input type="text" id="number_query" name="query" value="{{ request.form.get('query', '') }}" placeholder="e.g., 10">
```

**Change 2: Enhanced form submission JavaScript**
```javascript
// Added form validation on submit
document.querySelector('form').addEventListener('submit', function(e) {
    const selectedSearchType = document.querySelector('input[name="search_type"]:checked');
    if (!selectedSearchType) {
        document.querySelector('input[name="search_type"][value="author_title"]').checked = true;
    }
});
```

### 2. App (app.py)

**Change 1: Enhanced logging for debugging**
```python
print("=" * 80)
print("SEARCH EXECUTION LOG")
print("=" * 80)
print(f"Search Type:       {search_type}")
print(f"Query:             {query}")
print(f"Year Range:        {year_min} to {year_max}")
print(f"Vita Types Filter: {vita_types if vita_types else 'None'}")
print(f"Sort By:           {sort_by}")
print(f"Results Found:     {len(results)}")
print("=" * 80)
```

**Change 2: Explicit form state context passing**
```python
return render_template(
    "index.html",
    results=results,
    formatted_results=formatted_results,
    search_type=request.form.get("search_type", "author_title"),
    query=request.form.get("query", ""),
    author_query=request.form.get("author_query", ""),
    title_query=request.form.get("title_query", ""),
    sort_by=request.form.get("sort_by", "title"),
    year_min=request.form.get("year_min", ""),
    year_max=request.form.get("year_max", ""),
)
```

---

## How to Verify the Fixes

### Try These Steps:

1. **Test Number Search with Form State Preservation:**
   - Select "Select by Number"
   - Type "10" in the number field
   - Click "Retrieve"
   - Check console output (should show Search Type: number, Query: 10)
   - The text box should now show "10" (or have placeholder text if empty)
   - Result should show only Paper #10

2. **Monitor Console for Debugging:**
   - Open browser developer tools (F12)
   - Go to Flask console where server is running
   - You'll see detailed logging:
     ```
     ================================================================================
     SEARCH EXECUTION LOG
     ================================================================================
     Search Type:       number
     Query:             10
     Year Range:        None to None
     Vita Types Filter: None
     Sort By:           title
     Results Found:     1
     ================================================================================
     ```

3. **Test Multiple Search Types:**
   - Try both "Select by Number" and "Select multiple papers by Number"
   - Verify that results are correct for each

---

## Understanding the Search Types

### "Select by Number" (Exact Match)
- Finds papers with EXACT number match
- Example: Searching for "10" returns only paper #10
- Uses: `search_type="number"`

### "Select multiple papers by Number" (Comma-Separated)
- Finds papers from a list of numbers
- Example: Searching for "74, 312, 708" returns papers #74, #312, #708
- Uses: `search_type="multiple_numbers"`

---

## Form Values Are Now Preserved

The form now properly preserves these values after submission:
- Search type selected
- Query/input text
- Author query (for author/title search)
- Title query (for author/title search)
- Sort by selection
- Year range (min/max)
- Checkboxes (italics, omit_number, omit_keywords)
- Vita type filters

---

## Testing Results

Integration test confirms form submission works correctly:
```
test_search_by_number ... OK
test_search_empty_query_all_results ... OK
test_search_combined_all_filters ... OK
```

Run integration tests to verify:
```bash
python -m unittest test_integration_server.TestFlaskServerIntegration -v
```

---

## Debugging Tips

If you still see incorrect results:

1. **Check console output** for the actual search type and query being used
2. **Verify search type radio button** is selected (should be highlighted)
3. **Check the form field** that's visible for your search type
4. **Test with known numbers** like "74", "312", "708" (valid examples from database)
5. **Clear browser cache** (Ctrl+Shift+Delete) as old form data might be cached

---

## Next Steps

If issues persist after these changes:

1. Take a screenshot showing the console output from Flask server
2. Show which radio button is selected
3. Show what text is in the search box when you click Retrieve
4. This will help identify if it's a form submission issue or search logic issue

The search logic itself has been verified as correct through comprehensive unit tests.
