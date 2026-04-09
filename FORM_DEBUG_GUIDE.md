# Form Field Value Issue - Debugging Guide

## Problem Description
When searching by paper number, the form appears to auto-default to values like "1, 100, 1000" instead of using the number you typed.

---

## How to Debug This

### Step 1: Check the Flask Console
Add this to your browser's developer tools. When you submit a search, the Flask console will show:

```
================================================================================
SEARCH EXECUTION LOG
================================================================================
Search Type:       number
Query:             [the value actually submitted]
Year Range:        None to None
Vita Types Filter: None
Sort By:           title
Results Found:     X
================================================================================
```

**IMPORTANT:** Report what `Query:` shows. This is what the form actually submitted.

### Step 2: Check Browser Console
1. Open browser Developer Tools (F12)
2. Go to Console tab
3. Try searching by number
4. Look for console.log output showing:
   - "Switching to mode: number"
   - "Activated field: number_query"
   - "Clearing hidden field: ..." (for other fields)
   - "Form submitting with search_type: number"

This will show us which field is active and which are being cleared.

### Step 3: Inspect the Form
1. Open Developer Tools (F12)
2. Go to Elements/Inspector tab
3. Look for the input field with `placeholder="e.g., 10"`
4. Right-click it → Inspect Element
5. Check the value attribute

Should show: `value=""` (empty) or `value="10"` (your typed number)
Should NOT show: `value="1, 100, 1000"` or placeholder text

---

## Possible Causes & Solutions

### Cause 1: Multiple Fields Being Submitted
**Problem:** Several `<input name="query">` fields exist, and wrong one is being sent

**Solution Applied:** JavaScript now clears hidden field values before form submission

**To Test:** Type "10" in number field, submit, and check Flask console for `Query: 10`

---

### Cause 2: Browser Caching Form Data
**Problem:** Browser remembers previous form values

**Solution:**
1. Hard refresh page (Ctrl+Shift+R on Windows/Linux, Cmd+Shift+R on Mac)
2. Clear browser cache
3. Close and reopen browser

---

### Cause 3: JavaScript Not Running
**Problem:** Form visibility JavaScript isn't executing

**Solution:** Check browser console for any JavaScript errors

---

## Step-by-Step Test Procedure

1. **Clear browser cache** (Ctrl+Shift+Delete)
2. **Open the search form in fresh browser tab**
3. **Select "Select by Number"** radio button
4. **Type "10"** in the field
5. **Open Browser Dev Tools** (F12) → Console
6. **Click "Retrieve"** (or press Enter)
7. **Look at Flask server console** - show me what you see under `Query:`
8. **Report results** - Tell me what the Flask server shows was submitted

---

## What to Report If It's Still Broken

If the form still defaults incorrectly, please tell me:

1. **What you typed:** (e.g., "10")
2. **What search type was selected:** (e.g., "Select by Number")
3. **What results you got:** (e.g., "papers #1, #100, #1000")
4. **What Flask console shows under "Query:":** (the actual submitted value)
5. **Browser console logs:** (any messages starting with "Switching to mode" or "Clearing hidden field")
6. **Any JavaScript errors** in console

---

## Fixes Applied in This Update

1. **Improved JavaScript field visibility control**
   - Now explicitly manages `.field-row` elements
   - Adds console logging to show which fields are active
   - Clears ALL hidden query field values before submission

2. **Form submission cleanup**
   - Clears year filters for search types that don't use them
   - Ensures only active field value is submitted

3. **Better debugging**
   - Console.log messages show form state
   - Makes it easier to identify which field is active

---

## Technical Details

### How Field Visibility Works

```
User selects "Select by Number" radio button
  ↓
JavaScript detects change event
  ↓
updateVisibleFields() function called
  ↓
Removes .active class from ALL .field-row elements
  ↓
Adds .active class to .mode-number elements only
  ↓
CSS displays only .field-row.active (the number field)
  ↓
All other fields are display:none
  ↓
User types "10" in the visible number field
  ↓
User clicks Submit
  ↓
Form submission handler fires:
  - Clears all .field-row input values except the active one
  - Ensures search_type is set correctly
  - Submits form with only active field's value
```

---

## If Issue Continues

The best diagnostic is the Flask console output. Once you provide what the Flask console shows under `Query:`, I can identify the exact cause and fix it.

Common values that would help:
- `Query: 10` → Working correctly
- `Query: 1, 100, 1000` → Wrong field being submitted (placeholder text)
- `Query: ` (empty) → Field not being captured
- `Query: <special characters>` → Other issue
