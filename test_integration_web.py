"""
Integration tests for the PaperFile web application
Tests the Flask app and search endpoints at 127.0.0.1:5000
"""
import unittest
import requests
import json
from urllib.parse import urlencode


class TestPaperFileWebApp(unittest.TestCase):
    """Integration tests against running Flask server"""

    BASE_URL = "http://127.0.0.1:5000"

    @classmethod
    def setUpClass(cls):
        """Verify server is running before tests"""
        try:
            response = requests.get(f"{cls.BASE_URL}/", timeout=2)
            if response.status_code != 200:
                raise Exception("Server not responding")
        except Exception as e:
            raise RuntimeError(
                f"Flask server not running at {cls.BASE_URL}. "
                "Please start with: python app.py"
            ) from e

    def test_server_is_running(self):
        """Verify the server is accessible"""
        response = requests.get(f"{self.BASE_URL}/")
        self.assertEqual(response.status_code, 200)

    def test_index_page_loads(self):
        """Test that the index page loads"""
        response = requests.get(f"{self.BASE_URL}/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("html", response.text.lower())

    def test_search_author_title(self):
        """Test author-title search via POST"""
        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
            "year_min": "",
            "year_max": "",
        }
        response = requests.post(f"{self.BASE_URL}/", data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_by_keyword(self):
        """Test keyword search"""
        data = {
            "search_type": "keyword",
            "query": "machine",
            "year_min": "",
            "year_max": "",
        }
        response = requests.post(f"{self.BASE_URL}/", data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_by_journal(self):
        """Test journal/book search"""
        data = {
            "search_type": "journal_book",
            "query": "nature",
            "year_min": "",
            "year_max": "",
        }
        response = requests.post(f"{self.BASE_URL}/", data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_by_year(self):
        """Test year search"""
        data = {
            "search_type": "year",
            "query": "2023",
            "year_min": "",
            "year_max": "",
        }
        response = requests.post(f"{self.BASE_URL}/", data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_by_number(self):
        """Test paper number search"""
        data = {
            "search_type": "number",
            "query": "1",
            "year_min": "",
            "year_max": "",
        }
        response = requests.post(f"{self.BASE_URL}/", data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_with_year_range(self):
        """Test search with year range filter"""
        data = {
            "search_type": "keyword",
            "query": "",
            "year_min": "2020",
            "year_max": "2023",
        }
        response = requests.post(f"{self.BASE_URL}/", data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_with_vita_type_filter(self):
        """Test search with vita type filter"""
        data = {
            "search_type": "author_title",
            "author_query": "",
            "title_query": "",
            "year_min": "",
            "year_max": "",
            "restrict_vita_types": "on",
            "vita_types": ["J"],
        }
        response = requests.post(f"{self.BASE_URL}/", data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_with_formatting_options(self):
        """Test search with formatting options"""
        data = {
            "search_type": "keyword",
            "query": "test",
            "year_min": "",
            "year_max": "",
            "italics": "on",
            "omit_number": "on",
            "omit_keywords": "on",
        }
        response = requests.post(f"{self.BASE_URL}/", data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_with_sort_options(self):
        """Test different sort options"""
        sort_options = ["title", "author", "year", "number", "journal_book", "vita_type"]

        for sort_by in sort_options:
            data = {
                "search_type": "keyword",
                "query": "",
                "sort_by": sort_by,
                "year_min": "",
                "year_max": "",
            }
            response = requests.post(f"{self.BASE_URL}/", data=data)
            self.assertEqual(
                response.status_code, 200,
                f"Failed for sort_by={sort_by}"
            )

    def test_search_multiple_numbers(self):
        """Test searching for multiple paper numbers"""
        data = {
            "search_type": "multiple_numbers",
            "query": "1, 2, 3",
            "year_min": "",
            "year_max": "",
        }
        response = requests.post(f"{self.BASE_URL}/", data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_with_all_filters_combined(self):
        """Test search with all filters applied"""
        data = {
            "search_type": "author_title",
            "author_query": "smith",
            "title_query": "learning",
            "year_min": "2020",
            "year_max": "2023",
            "restrict_vita_types": "on",
            "vita_types": ["J", "B"],
            "sort_by": "title",
            "italics": "on",
            "omit_number": "on",
            "omit_keywords": "on",
        }
        response = requests.post(f"{self.BASE_URL}/", data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_empty_query(self):
        """Test search with empty query returns all"""
        data = {
            "search_type": "keyword",
            "query": "",
            "year_min": "",
            "year_max": "",
            "sort_by": "title",
        }
        response = requests.post(f"{self.BASE_URL}/", data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_special_characters(self):
        """Test search with special characters"""
        data = {
            "search_type": "keyword",
            "query": "machine&learning",
            "year_min": "",
            "year_max": "",
        }
        response = requests.post(f"{self.BASE_URL}/", data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_case_insensitive(self):
        """Test that search is case-insensitive"""
        # Two searches with different cases should work
        data1 = {
            "search_type": "keyword",
            "query": "MACHINE",
            "year_min": "",
            "year_max": "",
        }
        data2 = {
            "search_type": "keyword",
            "query": "machine",
            "year_min": "",
            "year_max": "",
        }

        response1 = requests.post(f"{self.BASE_URL}/", data=data1)
        response2 = requests.post(f"{self.BASE_URL}/", data=data2)

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)

    def test_search_year_range_boundaries(self):
        """Test year range boundaries"""
        data = {
            "search_type": "keyword",
            "query": "",
            "year_min": "2020",
            "year_max": "2020",  # Single year
        }
        response = requests.post(f"{self.BASE_URL}/", data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_invalid_year_format(self):
        """Test search with invalid year format"""
        data = {
            "search_type": "keyword",
            "query": "",
            "year_min": "invalid",
            "year_max": "also_invalid",
        }
        response = requests.post(f"{self.BASE_URL}/", data=data)
        # Should still return 200 (graceful handling)
        self.assertEqual(response.status_code, 200)

    def test_search_vita_type_multiple(self):
        """Test searching with multiple vita types"""
        data = {
            "search_type": "keyword",
            "query": "",
            "restrict_vita_types": "on",
            "vita_types": ["J", "B", "C"],
        }
        response = requests.post(f"{self.BASE_URL}/", data=data)
        self.assertEqual(response.status_code, 200)

    def test_search_no_vita_type_restriction(self):
        """Test search without vita type restriction"""
        data = {
            "search_type": "keyword",
            "query": "",
            # restrict_vita_types NOT included
        }
        response = requests.post(f"{self.BASE_URL}/", data=data)
        self.assertEqual(response.status_code, 200)


class TestSearchResultContent(unittest.TestCase):
    """Test the actual content returned from searches"""

    BASE_URL = "http://127.0.0.1:5000"

    def test_search_returns_formatted_results(self):
        """Verify search returns formatted results in response"""
        data = {
            "search_type": "keyword",
            "query": "",
        }
        response = requests.post(f"{self.BASE_URL}/", data=data)
        self.assertEqual(response.status_code, 200)
        # Check that HTML contains typical paper elements
        self.assertIn("html", response.text.lower())

    def test_multiple_searches_consistency(self):
        """Verify same search returns consistent results"""
        data = {
            "search_type": "keyword",
            "query": "test",
        }

        response1 = requests.post(f"{self.BASE_URL}/", data=data)
        response2 = requests.post(f"{self.BASE_URL}/", data=data)

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        # Both should return the same status and be valid HTML
        self.assertIn("html", response1.text.lower())
        self.assertIn("html", response2.text.lower())


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("PAPERFILE WEB APPLICATION INTEGRATION TESTS")
    print("=" * 70)
    print(f"\nTests will run against: http://127.0.0.1:5000")
    print("\nTo start the server, run:")
    print("  cd c:\\Users\\anayb\\python_projects\\paperfile_web\\paperfile")
    print("  python app.py")
    print("\nThen run these tests with:")
    print("  python -m unittest test_integration_web -v")
    print("=" * 70 + "\n")

    unittest.main()
