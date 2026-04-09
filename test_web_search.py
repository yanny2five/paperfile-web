"""
Test script for web version search functionality
"""

import sys
import os
import json

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'paperfile'))

from modules.readdata import CNTReader
from modules.search_service import search_papers

def test_web_searches():
    """Test the web version searches against expected results."""
    
    print("\n" + "=" * 80)
    print("WEB VERSION SEARCH TEST")
    print("=" * 80)
    
    # Load data
    reader = CNTReader()
    papers = reader.get_data()
    
    print(f"\n✓ Loaded {len(papers)} records\n")
    
    # TEST 1: Number Search (exact)
    print("TEST 1: Search by Number (Exact)")
    print("-" * 80)
    
    test_numbers = [1, 5, 10, 100]
    for num in test_numbers:
        results = search_papers(papers, query=str(num), search_type="number")
        print(f"Number {num}: {len(results)} result(s)")
        if results:
            print(f"  → {results[0].get('number', 'N/A')}: {results[0].get('title', 'N/A')[:60]}")
    
    # TEST 2: Multiple Numbers
    print("\n\nTEST 2: Multiple Numbers Search")
    print("-" * 80)
    
    test_cases = ["1,2,3", "1,5,10"]
    for nums in test_cases:
        results = search_papers(papers, query=nums, search_type="multiple_numbers")
        print(f"Numbers '{nums}': {len(results)} result(s)")
    
    # TEST 3: Year Range
    print("\n\nTEST 3: Year Range Search")
    print("-" * 80)
    
    ranges = [(2020, 2023), (2015, 2020), (2010, 2025)]
    for y_min, y_max in ranges:
        results = search_papers(papers, year_min=str(y_min), year_max=str(y_max))
        print(f"Years {y_min}-{y_max}: {len(results)} result(s)")
    
    # TEST 4: Author/Title Search
    print("\n\nTEST 4: Author & Title Search")
    print("-" * 80)
    
    test_cases = [
        ({"author": "Smith", "title": ""}, "Author 'Smith' only"),
        ({"author": "", "title": "learning"}, "Title 'learning' only"),
        ({"author": "Smith", "title": "learning"}, "Author 'Smith' AND Title 'learning'"),
    ]
    for query, desc in test_cases:
        results = search_papers(papers, query=query, search_type="author_title")
        print(f"{desc}: {len(results)} result(s)")
    
    # TEST 5: Journal Search
    print("\n\nTEST 5: Journal/Book Search")
    print("-" * 80)
    
    journals = ["Science", "Nature", "Journal", "IEEE", "ACM"]
    for journal in journals:
        results = search_papers(papers, query=journal, search_type="journal_book")
        print(f"Journal '{journal}': {len(results)} result(s)")
    
    # TEST 6: Vita Type Filter
    print("\n\nTEST 6: Vita Type Filter")
    print("-" * 80)
    
    single_types = ["B", "BC"]
    for vita_type in single_types:
        results = search_papers(papers, vita_types=[vita_type])
        print(f"Vita Type '{vita_type}': {len(results)} result(s)")
    
    # Combined
    results = search_papers(papers, vita_types=["B", "BC", "BR"])
    print(f"Combined B+BC+BR: {len(results)} result(s)")
    
    print("\n" + "=" * 80)
    print("TESTS COMPLETE - Compare these numbers with desktop version")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    try:
        test_web_searches()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
