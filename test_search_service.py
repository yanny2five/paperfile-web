"""
Unit tests for search_service.py - Search criteria and filtering functions
"""
import unittest
from modules.search_service import (
    normalize,
    get_field,
    get_authors,
    get_title,
    get_journal,
    get_keywords,
    get_year,
    get_number,
    get_vita_type,
    passes_search_type,
    passes_year_range,
    passes_vita_type,
    search_papers,
    sort_results,
)


class TestNormalize(unittest.TestCase):
    """Test the normalize function"""

    def test_normalize_empty_string(self):
        self.assertEqual(normalize(""), "")

    def test_normalize_whitespace(self):
        self.assertEqual(normalize("  hello  "), "hello")

    def test_normalize_uppercase(self):
        self.assertEqual(normalize("HELLO"), "hello")

    def test_normalize_none(self):
        self.assertEqual(normalize(None), "")

    def test_normalize_number(self):
        self.assertEqual(normalize(123), "123")

    def test_normalize_mixed(self):
        self.assertEqual(normalize("  HELLO WORLD  "), "hello world")


class TestGetField(unittest.TestCase):
    """Test the get_field function"""

    def test_get_field_exact_match(self):
        paper = {"title": "Test Title", "authors": "John Doe"}
        self.assertEqual(get_field(paper, "title"), "Test Title")

    def test_get_field_case_insensitive(self):
        paper = {"TITLE": "Test Title"}
        self.assertEqual(get_field(paper, "title"), "Test Title")

    def test_get_field_first_match(self):
        paper = {"authors": "John Doe", "author": "Jane Doe"}
        self.assertEqual(get_field(paper, "authors", "author"), "John Doe")

    def test_get_field_fallback(self):
        paper = {"author": "Jane Doe"}
        self.assertEqual(get_field(paper, "authors", "author"), "Jane Doe")

    def test_get_field_missing(self):
        paper = {"title": "Test"}
        self.assertEqual(get_field(paper, "authors", "author(s)"), "")

    def test_get_field_empty_paper(self):
        self.assertEqual(get_field({}, "title"), "")


class TestGetSpecificFields(unittest.TestCase):
    """Test individual get_* field functions"""

    def setUp(self):
        self.sample_paper = {
            "authors": "Smith, J.",
            "title": "Advanced Algorithms",
            "journal": "Nature",
            "keywords": "machine learning, AI",
            "year": "2023",
            "number": "42",
            "vita_type": "Journal Article",
        }

    def test_get_authors(self):
        self.assertEqual(get_authors(self.sample_paper), "Smith, J.")

    def test_get_authors_alternative_key(self):
        paper = {"author(s)": "Doe, J."}
        self.assertEqual(get_authors(paper), "Doe, J.")

    def test_get_title(self):
        self.assertEqual(get_title(self.sample_paper), "Advanced Algorithms")

    def test_get_journal(self):
        self.assertEqual(get_journal(self.sample_paper), "Nature")

    def test_get_journal_alternative_key(self):
        paper = {"journal/book": "Science"}
        self.assertEqual(get_journal(paper), "Science")

    def test_get_keywords(self):
        self.assertEqual(get_keywords(self.sample_paper), "machine learning, AI")

    def test_get_year(self):
        self.assertEqual(get_year(self.sample_paper), "2023")

    def test_get_number(self):
        self.assertEqual(get_number(self.sample_paper), "42")

    def test_get_vita_type(self):
        self.assertEqual(get_vita_type(self.sample_paper), "Journal Article")


class TestPassesSearchType(unittest.TestCase):
    """Test the passes_search_type function with different search types"""

    def setUp(self):
        self.paper = {
            "authors": "Smith, John",
            "title": "Advanced Machine Learning",
            "keywords": "AI, neural networks",
            "journal": "Nature Reviews",
            "year": "2023",
            "number": "101",
            "vita_type": "Journal Article",
        }

    def test_search_author_title_both_match(self):
        query = {"author": "Smith", "title": "Machine"}
        self.assertTrue(passes_search_type(self.paper, query, "author_title"))

    def test_search_author_title_author_only(self):
        query = {"author": "Smith", "title": ""}
        self.assertTrue(passes_search_type(self.paper, query, "author_title"))

    def test_search_author_title_title_only(self):
        query = {"author": "", "title": "Machine"}
        self.assertTrue(passes_search_type(self.paper, query, "author_title"))

    def test_search_author_title_author_mismatch(self):
        query = {"author": "Jones", "title": "Machine"}
        self.assertFalse(passes_search_type(self.paper, query, "author_title"))

    def test_search_author_title_title_mismatch(self):
        query = {"author": "Smith", "title": "Chemistry"}
        self.assertFalse(passes_search_type(self.paper, query, "author_title"))

    def test_search_keyword_match(self):
        self.assertTrue(
            passes_search_type(self.paper, "neural", "keyword")
        )

    def test_search_keyword_no_match(self):
        self.assertFalse(
            passes_search_type(self.paper, "quantum", "keyword")
        )

    def test_search_journal_match(self):
        self.assertTrue(
            passes_search_type(self.paper, "Nature", "journal_book")
        )

    def test_search_journal_no_match(self):
        self.assertFalse(
            passes_search_type(self.paper, "Science", "journal_book")
        )

    def test_search_year_exact_match(self):
        self.assertTrue(
            passes_search_type(self.paper, "2023", "year")
        )

    def test_search_year_no_match(self):
        self.assertFalse(
            passes_search_type(self.paper, "2022", "year")
        )

    def test_search_number_exact_match(self):
        self.assertTrue(
            passes_search_type(self.paper, "101", "number")
        )

    def test_search_number_no_match(self):
        self.assertFalse(
            passes_search_type(self.paper, "102", "number")
        )

    def test_search_multiple_numbers_match(self):
        self.assertTrue(
            passes_search_type(self.paper, "100, 101, 102", "multiple_numbers")
        )

    def test_search_multiple_numbers_no_match(self):
        self.assertFalse(
            passes_search_type(self.paper, "100, 102, 103", "multiple_numbers")
        )

    def test_search_vita_type_match(self):
        self.assertTrue(
            passes_search_type(self.paper, "Journal", "vita_type")
        )

    def test_search_vita_type_no_match(self):
        self.assertFalse(
            passes_search_type(self.paper, "Book", "vita_type")
        )

    def test_search_any_field_match(self):
        self.assertTrue(
            passes_search_type(self.paper, "Smith", "any_field")
        )

    def test_search_any_field_no_match(self):
        self.assertFalse(
            passes_search_type(self.paper, "NonExistent", "any_field")
        )

    def test_search_empty_query_returns_true(self):
        self.assertTrue(
            passes_search_type(self.paper, "", "keyword")
        )

    def test_search_case_insensitive(self):
        query = {"author": "SMITH", "title": "machine"}
        self.assertTrue(passes_search_type(self.paper, query, "author_title"))


class TestPassesYearRange(unittest.TestCase):
    """Test the passes_year_range function"""

    def setUp(self):
        self.paper_2023 = {"year": "2023"}
        self.paper_invalid_year = {"year": "invalid"}
        self.paper_no_year = {}

    def test_year_range_within_bounds(self):
        self.assertTrue(
            passes_year_range(self.paper_2023, "2020", "2025")
        )

    def test_year_range_exact_min(self):
        self.assertTrue(
            passes_year_range(self.paper_2023, "2023", "2025")
        )

    def test_year_range_exact_max(self):
        self.assertTrue(
            passes_year_range(self.paper_2023, "2020", "2023")
        )

    def test_year_range_below_min(self):
        self.assertFalse(
            passes_year_range(self.paper_2023, "2024", "2025")
        )

    def test_year_range_above_max(self):
        self.assertFalse(
            passes_year_range(self.paper_2023, "2020", "2022")
        )

    def test_year_range_min_only(self):
        self.assertTrue(
            passes_year_range(self.paper_2023, "2020", None)
        )

    def test_year_range_max_only(self):
        self.assertTrue(
            passes_year_range(self.paper_2023, None, "2025")
        )

    def test_year_range_no_constraints(self):
        self.assertTrue(
            passes_year_range(self.paper_2023, None, None)
        )

    def test_year_range_invalid_year_with_constraints(self):
        self.assertFalse(
            passes_year_range(self.paper_invalid_year, "2020", "2025")
        )

    def test_year_range_invalid_year_no_constraints(self):
        self.assertTrue(
            passes_year_range(self.paper_invalid_year, None, None)
        )

    def test_year_range_missing_year_field_with_constraints(self):
        self.assertFalse(
            passes_year_range(self.paper_no_year, "2020", "2025")
        )

    def test_year_range_missing_year_field_no_constraints(self):
        self.assertTrue(
            passes_year_range(self.paper_no_year, None, None)
        )

    def test_year_range_invalid_min_value(self):
        self.assertTrue(
            passes_year_range(self.paper_2023, "invalid", "2025")
        )

    def test_year_range_invalid_max_value(self):
        self.assertTrue(
            passes_year_range(self.paper_2023, "2020", "invalid")
        )


class TestPassesVitaType(unittest.TestCase):
    """Test the passes_vita_type function"""

    def test_vita_type_empty_filter(self):
        paper = {"vita_type": "J"}
        self.assertTrue(passes_vita_type(paper, []))

    def test_vita_type_single_match(self):
        paper = {"vita_type": "J"}
        self.assertTrue(passes_vita_type(paper, ["J"]))

    def test_vita_type_multiple_options_match(self):
        paper = {"vita_type": "J"}
        self.assertTrue(
            passes_vita_type(paper, ["B", "J"])
        )

    def test_vita_type_no_match(self):
        paper = {"vita_type": "J"}
        self.assertFalse(
            passes_vita_type(paper, ["B", "CN"])
        )

    def test_vita_type_case_insensitive(self):
        paper = {"vita_type": "Journal"}
        self.assertTrue(passes_vita_type(paper, ["journal"]))

    def test_vita_type_exact_match_required(self):
        # vita_type filter requires exact match, not partial
        paper = {"vita_type": "J"}
        self.assertFalse(passes_vita_type(paper, ["JA"]))

    def test_vita_type_missing_field(self):
        paper = {}
        self.assertFalse(passes_vita_type(paper, ["J"]))


class TestSearchPapers(unittest.TestCase):
    """Test the main search_papers function"""

    def setUp(self):
        self.papers = [
            {
                "authors": "Smith, John",
                "title": "Machine Learning Basics",
                "keywords": "AI, ML",
                "journal": "Nature",
                "year": "2020",
                "number": "1",
                "vita_type": "J",
            },
            {
                "authors": "Doe, Jane",
                "title": "Advanced AI Systems",
                "keywords": "deep learning",
                "journal": "Science",
                "year": "2022",
                "number": "2",
                "vita_type": "J",
            },
            {
                "authors": "Johnson, Bob",
                "title": "Neural Networks Guide",
                "keywords": "neural networks, deep learning",
                "journal": "IEEE",
                "year": "2023",
                "number": "3",
                "vita_type": "B",
            },
        ]

    def test_search_all_papers(self):
        results = search_papers(self.papers)
        self.assertEqual(len(results), 3)

    def test_search_by_author_title(self):
        query = {"author": "Smith", "title": "Machine"}
        results = search_papers(
            self.papers, query=query, search_type="author_title"
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["authors"], "Smith, John")

    def test_search_by_keyword(self):
        results = search_papers(
            self.papers, query="deep learning", search_type="keyword"
        )
        self.assertEqual(len(results), 2)

    def test_search_by_year_range(self):
        results = search_papers(
            self.papers, year_min="2021", year_max="2023"
        )
        self.assertEqual(len(results), 2)

    def test_search_by_vita_type(self):
        results = search_papers(
            self.papers, vita_types=["J"]
        )
        self.assertEqual(len(results), 2)

    def test_search_combined_criteria(self):
        query = {"author": "", "title": ""}
        results = search_papers(
            self.papers,
            query=query,
            search_type="author_title",
            year_min="2022",
            year_max="2023",
            vita_types=["J"],
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["number"], "2")

    def test_search_no_results(self):
        results = search_papers(
            self.papers, query="Quantum Computing", search_type="keyword"
        )
        self.assertEqual(len(results), 0)

    def test_search_empty_papers(self):
        results = search_papers([], query="test")
        self.assertEqual(len(results), 0)


class TestSortResults(unittest.TestCase):
    """Test the sort_results function"""

    def setUp(self):
        self.papers = [
            {
                "authors": "Zanzibar, Alice",
                "title": "Zebra Patterns",
                "number": "3",
                "vita_type": "J",
                "journal": "Zoology Today",
                "year": "2020",
            },
            {
                "authors": "Apple, Bob",
                "title": "Algorithms",
                "number": "1",
                "vita_type": "B",
                "journal": "Archives",
                "year": "2025",
            },
            {
                "authors": "Monkey, Charlie",
                "title": "Machine Learning",
                "number": "2",
                "vita_type": "CN",
                "journal": "Medical Science",
                "year": "2022",
            },
        ]

    def test_sort_by_title(self):
        results = sort_results(self.papers, "title")
        titles = [p["title"] for p in results]
        self.assertEqual(titles, ["Algorithms", "Machine Learning", "Zebra Patterns"])

    def test_sort_by_author(self):
        results = sort_results(self.papers, "author")
        authors = [p["authors"] for p in results]
        self.assertEqual(
            authors, ["Apple, Bob", "Monkey, Charlie", "Zanzibar, Alice"]
        )

    def test_sort_by_number(self):
        results = sort_results(self.papers, "number")
        numbers = [p["number"] for p in results]
        self.assertEqual(numbers, ["1", "2", "3"])

    def test_sort_by_vita_type(self):
        results = sort_results(self.papers, "vita_type")
        types = [p["vita_type"] for p in results]
        self.assertEqual(types, ["B", "CN", "J"])

    def test_sort_by_journal(self):
        results = sort_results(self.papers, "journal_book")
        journals = [p["journal"] for p in results]
        self.assertEqual(
            journals, ["Archives", "Medical Science", "Zoology Today"]
        )

    def test_sort_by_year(self):
        results = sort_results(self.papers, "year")
        years = [p["year"] for p in results]
        self.assertEqual(years, ["2020", "2022", "2025"])

    def test_sort_default_to_title(self):
        results = sort_results(self.papers, "unknown")
        titles = [p["title"] for p in results]
        self.assertEqual(titles, ["Algorithms", "Machine Learning", "Zebra Patterns"])

    def test_sort_empty_list(self):
        results = sort_results([], "title")
        self.assertEqual(results, [])


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and special scenarios"""

    def test_paper_with_missing_fields(self):
        paper = {"number": "1"}
        self.assertEqual(get_authors(paper), "")
        self.assertEqual(get_title(paper), "")
        self.assertEqual(get_journal(paper), "")

    def test_normalize_with_special_characters(self):
        result = normalize("  Test@123!  ")
        self.assertEqual(result, "test@123!")

    def test_search_with_special_characters_in_query(self):
        paper = {"keywords": "AI & ML"}
        self.assertTrue(
            passes_search_type(paper, "AI &", "keyword")
        )

    def test_year_range_with_single_digit_year(self):
        paper = {"year": "5"}
        self.assertTrue(
            passes_year_range(paper, "0", "10")
        )

    def test_multiple_numbers_with_whitespace(self):
        paper = {"number": "101"}
        self.assertTrue(
            passes_search_type(
                paper, "  100  ,  101  ,  102  ", "multiple_numbers"
            )
        )


if __name__ == "__main__":
    unittest.main()
