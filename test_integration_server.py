"""
Integration tests for Flask API endpoints at 127.0.0.1:5000
Tests the search_papers functionality through the Flask web interface
"""
import unittest
import requests
import json


class TestFlaskServerIntegration(unittest.TestCase):
    """Integration tests for Flask search endpoints"""

    BASE_URL = "http://127.0.0.1:5000"

    def test_server_is_running(self):
        """Verify server is accessible"""
        try:
            response = requests.get(self.BASE_URL, timeout=5)
            self.assertIn(response.status_code, [200, 405])
        except requests.ConnectionError:
            self.fail("Flask server at 127.0.0.1:5000 is not running")

    def test_get_index_page(self):
        """Test GET request to index page"""
        response = requests.get(self.BASE_URL)
        self.assertEqual(response.status_code, 200)
        self.assertIn("html", response.text.lower())

    def test_search_by_author_title(self):
        """Test search by author and title"""
        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
            "sort_by": "title",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)
        # Should return results in HTML form
        self.assertIn("html", response.text.lower())

    def test_search_by_keyword(self):
        """Test search by keyword"""
        data = {
            "search_type": "keyword",
            "query": "learning",
            "sort_by": "title",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_by_journal(self):
        """Test search by journal/book"""
        data = {
            "search_type": "journal_book",
            "query": "",
            "sort_by": "title",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_by_year(self):
        """Test search by year"""
        data = {
            "search_type": "year",
            "query": "2023",
            "sort_by": "year",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_by_number(self):
        """Test search by paper number"""
        data = {
            "search_type": "number",
            "query": "1",
            "sort_by": "number",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_with_year_range(self):
        """Test search with year range filter"""
        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
            "year_min": "2020",
            "year_max": "2023",
            "sort_by": "year",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_with_vita_types(self):
        """Test search with vita type filter"""
        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
            "restrict_vita_types": "on",
            "vita_types": ["J"],
            "sort_by": "title",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_with_multiple_vita_types(self):
        """Test search with multiple vita type filters"""
        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
            "restrict_vita_types": "on",
            "vita_types": ["J", "B"],
            "sort_by": "title",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_with_formatting_options(self):
        """Test search with formatting checkboxes"""
        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
            "italics": "on",
            "omit_number": "on",
            "omit_keywords": "on",
            "sort_by": "title",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_sort_by_title(self):
        """Test sorting results by title"""
        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
            "sort_by": "title",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_sort_by_author(self):
        """Test sorting results by author"""
        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
            "sort_by": "author",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_sort_by_number(self):
        """Test sorting results by number"""
        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
            "sort_by": "number",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_sort_by_year(self):
        """Test sorting results by year"""
        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
            "sort_by": "year",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_empty_query_all_results(self):
        """Test that empty search returns all results"""
        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)
        # Should have results
        self.assertGreater(len(response.text), 100)

    def test_search_nonexistent_author(self):
        """Test search with non-existent author"""
        data = {
            "search_type": "author_title",
            "author_query": "XYZNonExistentAuthorXYZ",
            "title_query": "",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_nonexistent_keyword(self):
        """Test search with non-existent keyword"""
        data = {
            "search_type": "keyword",
            "query": "XYZNonExistentKeywordXYZ",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_year_range_narrow(self):
        """Test with narrow year range"""
        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
            "year_min": "2023",
            "year_max": "2023",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_year_range_invalid(self):
        """Test with invalid year range (min > max)"""
        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
            "year_min": "2025",
            "year_max": "2020",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_with_vita_type_no_restrict(self):
        """Test vita_types parameter without restrict flag"""
        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
            "vita_types": ["J"],
            # Note: restrict_vita_types not set
            "sort_by": "title",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_combined_all_filters(self):
        """Test search with all filters combined"""
        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
            "year_min": "2020",
            "year_max": "2024",
            "restrict_vita_types": "on",
            "vita_types": ["J"],
            "sort_by": "year",
            "italics": "on",
            "omit_number": "on",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)

    def test_response_has_html_structure(self):
        """Test that response contains expected HTML elements"""
        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
        }
        response = requests.post(self.BASE_URL, data=data)
        self.assertEqual(response.status_code, 200)
        # Check for HTML structure
        self.assertIn("<", response.text)
        self.assertIn(">", response.text)

    def test_response_status_consistency(self):
        """Test multiple requests return consistent status"""
        for _ in range(3):
            data = {
                "search_type": "keyword",
                "query": "test",
            }
            response = requests.post(self.BASE_URL, data=data)
            self.assertEqual(response.status_code, 200)

    def test_search_different_types_consistency(self):
        """Test that different search types all return 200"""
        search_types = [
            "author_title",
            "keyword",
            "journal_book",
            "year",
            "number",
        ]
        for search_type in search_types:
            with self.subTest(search_type=search_type):
                data = {
                    "search_type": search_type,
                    "author_query": "",
                    "title_query": "",
                    "query": "",
                }
                response = requests.post(self.BASE_URL, data=data)
                self.assertEqual(response.status_code, 200)


class TestFlaskServerPerformance(unittest.TestCase):
    """Performance tests for Flask server"""

    BASE_URL = "http://127.0.0.1:5000"

    def test_search_response_time(self):
        """Test that search responds within reasonable time"""
        import time

        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
        }
        start = time.time()
        response = requests.post(self.BASE_URL, data=data)
        elapsed = time.time() - start

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 5.0, f"Search took {elapsed}s, expected < 5s")

    def test_multiple_searches_responsive(self):
        """Test server remains responsive with multiple searches"""
        import time

        queries = [
            {"query": "machine", "type": "keyword"},
            {"query": "2023", "type": "year"},
            {"query": "1", "type": "number"},
        ]

        for query in queries:
            start = time.time()
            data = {
                "search_type": query["type"],
                "author_query": "",
                "title_query": "",
                "query": query["query"],
            }
            response = requests.post(self.BASE_URL, data=data)
            elapsed = time.time() - start

            self.assertEqual(response.status_code, 200)
            self.assertLess(elapsed, 5.0)


if __name__ == "__main__":
    unittest.main()
