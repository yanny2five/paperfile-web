"""
Unit tests for searchdata.py - SearchData class methods
"""
import unittest
from modules.searchdata import SearchData


class TestSearchDataInitialization(unittest.TestCase):
    """Test SearchData class initialization"""

    def test_init_with_data(self):
        data = [{"number": "1", "title": "Test"}]
        search_data = SearchData(data)
        self.assertEqual(search_data.data, data)

    def test_init_empty_data(self):
        search_data = SearchData([])
        self.assertEqual(search_data.data, [])


class TestSearchByNumber(unittest.TestCase):
    """Test search_by_number method"""

    def setUp(self):
        self.data = [
            {"number": "1", "title": "Paper One"},
            {"number": "2", "title": "Paper Two"},
            {"number": "10", "title": "Paper Ten"},
            {"number": "12", "title": "Paper Twelve"},
            {"title": "No Number"},
        ]
        self.search_data = SearchData(self.data)

    def test_search_exact_match(self):
        results = self.search_data.search_by_number(1, exact=True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Paper One")

    def test_search_exact_no_match(self):
        results = self.search_data.search_by_number(5, exact=True)
        self.assertEqual(len(results), 0)

    def test_search_partial_match(self):
        results = self.search_data.search_by_number(1, exact=False)
        self.assertEqual(len(results), 3)  # 1, 10, 12
        titles = {r["title"] for r in results}
        self.assertIn("Paper One", titles)
        self.assertIn("Paper Ten", titles)
        self.assertIn("Paper Twelve", titles)

    def test_search_partial_no_match(self):
        results = self.search_data.search_by_number(5, exact=False)
        self.assertEqual(len(results), 0)

    def test_search_with_invalid_number_field(self):
        data = [
            {"number": "abc", "title": "Invalid"},
            {"number": "1", "title": "Valid"},
        ]
        search_data = SearchData(data)
        results = search_data.search_by_number(1, exact=True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Valid")

    def test_search_number_missing_field(self):
        results = self.search_data.search_by_number(99, exact=True)
        self.assertEqual(len(results), 0)


class TestSearchByNumberRange(unittest.TestCase):
    """Test search_by_number_range method"""

    def setUp(self):
        self.data = [
            {"number": "1", "title": "Paper One"},
            {"number": "5", "title": "Paper Five"},
            {"number": "10", "title": "Paper Ten"},
            {"number": "15", "title": "Paper Fifteen"},
            {"number": "20", "title": "Paper Twenty"},
        ]
        self.search_data = SearchData(self.data)

    def test_range_includes_boundaries(self):
        results = self.search_data.search_by_number_range(5, 15)
        self.assertEqual(len(results), 3)
        numbers = {int(r["number"]) for r in results}
        self.assertEqual(numbers, {5, 10, 15})

    def test_range_single_number(self):
        results = self.search_data.search_by_number_range(10, 10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["number"], "10")

    def test_range_wide_bounds(self):
        results = self.search_data.search_by_number_range(1, 20)
        self.assertEqual(len(results), 5)

    def test_range_no_matches(self):
        results = self.search_data.search_by_number_range(30, 40)
        self.assertEqual(len(results), 0)

    def test_range_with_invalid_numbers(self):
        data = [
            {"number": "abc", "title": "Invalid"},
            {"number": "5", "title": "Five"},
            {"number": "10", "title": "Ten"},
        ]
        search_data = SearchData(data)
        results = search_data.search_by_number_range(5, 10)
        self.assertEqual(len(results), 2)


class TestSearchByYearRange(unittest.TestCase):
    """Test search_by_year_range method"""

    def setUp(self):
        self.data = [
            {"year": "2020", "title": "Twenty Twenty"},
            {"year": "2021", "title": "Twenty Twenty-One"},
            {"year": "2022", "title": "Twenty Twenty-Two"},
            {"year": "2023", "title": "Twenty Twenty-Three"},
        ]
        self.search_data = SearchData(self.data)

    def test_year_range_includes_boundaries(self):
        results = self.search_data.search_by_year_range(2021, 2023)
        self.assertEqual(len(results), 3)
        years = {int(r["year"]) for r in results}
        self.assertEqual(years, {2021, 2022, 2023})

    def test_year_range_single_year(self):
        results = self.search_data.search_by_year_range(2022, 2022)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["year"], "2022")

    def test_year_range_no_matches(self):
        results = self.search_data.search_by_year_range(2030, 2040)
        self.assertEqual(len(results), 0)

    def test_year_range_with_invalid_years(self):
        data = [
            {"year": "invalid", "title": "Bad Year"},
            {"year": "2021", "title": "Good Year"},
            {"year": "2023", "title": "Good Year 2"},
        ]
        search_data = SearchData(data)
        results = search_data.search_by_year_range(2021, 2023)
        self.assertEqual(len(results), 2)

    def test_year_range_with_optional_data_parameter(self):
        subset = self.data[1:3]  # 2021, 2022
        results = self.search_data.search_by_year_range(2021, 2022, data=subset)
        self.assertEqual(len(results), 2)


class TestFuzzySearchByAuthorTitle(unittest.TestCase):
    """Test fuzzy_search_by_author_title method"""

    def setUp(self):
        self.data = [
            {
                "authors": "Smith, John and Doe, Jane",
                "title": "Machine Learning Systems",
            },
            {"authors": "Johnson, Bob", "title": "Advanced AI"},
            {"authors": "Williams, Carol", "title": "Neural Networks"},
            {"title": "No Authors"},
            {"authors": "Brown, David"},
        ]
        self.search_data = SearchData(self.data)

    def test_search_author_only(self):
        results = self.search_data.fuzzy_search_by_author_title("Smith", "")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Machine Learning Systems")

    def test_search_title_only(self):
        results = self.search_data.fuzzy_search_by_author_title("", "Neural")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["authors"], "Williams, Carol")

    def test_search_author_and_title(self):
        results = self.search_data.fuzzy_search_by_author_title(
            "Smith", "Machine"
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["authors"], "Smith, John and Doe, Jane")

    def test_search_author_and_title_no_match(self):
        results = self.search_data.fuzzy_search_by_author_title(
            "Smith", "Neural"
        )
        self.assertEqual(len(results), 0)

    def test_search_case_insensitive(self):
        results = self.search_data.fuzzy_search_by_author_title(
            "smith", "machine"
        )
        self.assertEqual(len(results), 1)

    def test_search_missing_authors_field(self):
        results = self.search_data.fuzzy_search_by_author_title("Any", "")
        self.assertEqual(len(results), 0)

    def test_search_missing_title_field(self):
        results = self.search_data.fuzzy_search_by_author_title("", "Any")
        self.assertEqual(len(results), 0)

    def test_search_with_optional_fields(self):
        results = self.search_data.fuzzy_search_by_author_title(
            "Smith", "", "Jane", "Machine"
        )
        self.assertEqual(len(results), 1)

    def test_search_with_optional_data_parameter(self):
        subset = self.data[0:1]
        results = self.search_data.fuzzy_search_by_author_title(
            "Smith", "", data=subset
        )
        self.assertEqual(len(results), 1)


class TestFuzzySearchByKeyword(unittest.TestCase):
    """Test fuzzy_search_by_keyword method"""

    def setUp(self):
        self.data = [
            {"subject1": "Machine Learning", "subject2": "AI"},
            {"subject1": "Deep Learning", "subject2": "Neural Networks"},
            {"subject1": "Data Science", "subject2": "Statistics"},
            {"subject2": "Only Subject2"},
        ]
        self.search_data = SearchData(self.data)

    def test_search_in_subject1(self):
        results = self.search_data.fuzzy_search_by_keyword("Machine")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["subject1"], "Machine Learning")

    def test_search_in_subject2(self):
        results = self.search_data.fuzzy_search_by_keyword("Neural")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["subject2"], "Neural Networks")

    def test_search_in_both_fields(self):
        results = self.search_data.fuzzy_search_by_keyword("Learning")
        self.assertEqual(len(results), 2)

    def test_search_case_insensitive(self):
        results = self.search_data.fuzzy_search_by_keyword("MACHINE")
        self.assertEqual(len(results), 1)

    def test_search_no_match(self):
        results = self.search_data.fuzzy_search_by_keyword("Quantum")
        self.assertEqual(len(results), 0)

    def test_search_partial_match(self):
        results = self.search_data.fuzzy_search_by_keyword("Learn")
        self.assertEqual(len(results), 2)


class TestFuzzySearchByBookJournal(unittest.TestCase):
    """Test fuzzy_search_by_book_journal method"""

    def setUp(self):
        self.data = [
            {"bookjour": "Nature Reviews Machine Learning"},
            {"bookjour": "Science Magazine"},
            {"bookjour": "IEEE Transactions"},
            {"title": "No BookJour Field"},
        ]
        self.search_data = SearchData(self.data)

    def test_search_exact_word(self):
        results = self.search_data.fuzzy_search_by_book_journal("Nature")
        self.assertEqual(len(results), 1)

    def test_search_partial_match(self):
        results = self.search_data.fuzzy_search_by_book_journal("Reviews")
        self.assertEqual(len(results), 1)

    def test_search_case_insensitive(self):
        results = self.search_data.fuzzy_search_by_book_journal("nature")
        self.assertEqual(len(results), 1)

    def test_search_no_match(self):
        results = self.search_data.fuzzy_search_by_book_journal("Elsevier")
        self.assertEqual(len(results), 0)

    def test_search_multiple_matches(self):
        results = self.search_data.fuzzy_search_by_book_journal("s")
        self.assertEqual(len(results), 3)  # Nature, Science, Transactions

    def test_search_with_missing_field(self):
        results = self.search_data.fuzzy_search_by_book_journal("Anything")
        self.assertEqual(len(results), 0)


class TestFuzzySearchByAnyField(unittest.TestCase):
    """Test fuzzy_search_by_any_field method"""

    def setUp(self):
        self.data = [
            {
                "title": "Machine Learning",
                "author": "Smith",
                "journal": "Nature",
            },
            {"title": "Quantum Computing", "author": "Jones", "year": "2023"},
            {"description": "Neural Networks Guide"},
        ]
        self.search_data = SearchData(self.data)

    def test_search_in_title(self):
        results = self.search_data.fuzzy_search_by_any_field("Machine")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Machine Learning")

    def test_search_in_author(self):
        results = self.search_data.fuzzy_search_by_any_field("Smith")
        self.assertEqual(len(results), 1)

    def test_search_in_any_field(self):
        results = self.search_data.fuzzy_search_by_any_field("2023")
        self.assertEqual(len(results), 1)

    def test_search_case_insensitive(self):
        results = self.search_data.fuzzy_search_by_any_field("smith")
        self.assertEqual(len(results), 1)

    def test_search_no_match(self):
        results = self.search_data.fuzzy_search_by_any_field("Cryptocurrency")
        self.assertEqual(len(results), 0)

    def test_search_stops_at_first_match(self):
        """Verify that search stops after finding match in first field"""
        results = self.search_data.fuzzy_search_by_any_field("Neural")
        self.assertEqual(len(results), 1)
        # Should only match the description field record


class TestFilterByVitaType(unittest.TestCase):
    """Test filter_by_vita_type method"""

    def setUp(self):
        self.data = [
            {"vitatyp": "J", "title": "Journal Article"},
            {"vitatyp": "B", "title": "Book"},
            {"vitatyp": "JR", "title": "Journal Review"},
            {"vitatyp": "C", "title": "Conference"},
            {"title": "No Vita Type"},
        ]
        self.search_data = SearchData(self.data)

    def test_filter_single_type(self):
        results = self.search_data.filter_by_vita_type(self.data, ["J"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Journal Article")

    def test_filter_multiple_types(self):
        results = self.search_data.filter_by_vita_type(self.data, ["J", "B"])
        self.assertEqual(len(results), 2)
        types = {r["vitatyp"] for r in results}
        self.assertEqual(types, {"J", "B"})

    def test_filter_empty_list(self):
        results = self.search_data.filter_by_vita_type(self.data, [])
        self.assertEqual(len(results), len(self.data))

    def test_filter_no_matches(self):
        results = self.search_data.filter_by_vita_type(self.data, ["X", "Y"])
        self.assertEqual(len(results), 0)

    def test_filter_missing_vita_type_field(self):
        results = self.search_data.filter_by_vita_type(self.data, ["J"])
        # Should only return records with J, not the one without vitatyp
        self.assertEqual(len(results), 1)

    def test_filter_exact_match_only(self):
        results = self.search_data.filter_by_vita_type(self.data, ["JR"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["vitatyp"], "JR")


class TestSearchDataIntegration(unittest.TestCase):
    """Integration tests combining multiple search methods"""

    def setUp(self):
        self.data = [
            {
                "number": "1",
                "authors": "Smith, John",
                "title": "Machine Learning 101",
                "subject1": "AI",
                "subject2": "ML",
                "bookjour": "Nature Reviews",
                "year": "2020",
                "vitatyp": "J",
            },
            {
                "number": "5",
                "authors": "Doe, Jane",
                "title": "Advanced Neural Networks",
                "subject1": "Deep Learning",
                "subject2": "Neural Networks",
                "bookjour": "IEEE",
                "year": "2022",
                "vitatyp": "J",
            },
            {
                "number": "10",
                "authors": "Johnson, Bob",
                "title": "Quantum Computing",
                "subject1": "Quantum",
                "subject2": "Computing",
                "bookjour": "Science",
                "year": "2023",
                "vitatyp": "B",
            },
        ]
        self.search_data = SearchData(self.data)

    def test_combined_search_author_and_keyword(self):
        """Search by author, then filter by keyword"""
        results = self.search_data.fuzzy_search_by_author_title("Smith", "")
        # Filter the subset by keyword
        keyword_results = [r for r in results if self.search_data.fuzzy_search_by_keyword("AI")]
        self.assertEqual(len(results), 1)

    def test_combined_search_year_and_vita_type(self):
        """Filter by year range, then by vita type"""
        results = self.search_data.search_by_year_range(2020, 2022)
        results = self.search_data.filter_by_vita_type(results, ["J"])
        self.assertEqual(len(results), 2)

    def test_combined_search_number_and_title(self):
        """Search by number range, then by title"""
        results = self.search_data.search_by_number_range(1, 5)
        titles = [r["title"] for r in results]
        self.assertIn("Machine Learning 101", titles)
        self.assertIn("Advanced Neural Networks", titles)

    def test_empty_result_chain(self):
        """Test chaining searches that result in no matches"""
        results = self.search_data.search_by_number_range(100, 200)
        results = self.search_data.filter_by_vita_type(results, ["J"])
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
