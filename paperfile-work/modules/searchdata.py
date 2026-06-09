class SearchData:
    def __init__(self, data):
        """
        Initialize the SearchData class.

        :param data: A list of dictionaries, each representing a record
        """
        self.data = data

    def search_by_number(self, paper_number, exact=True):
        """
        Search records by paper number.

        :param paper_number: The paper number to search for
        :param exact: Whether to perform an exact match (default is True)
        :return: A list of matching records
        """
        results = []
        for record in self.data:
            if "number" in record:
                try:
                    # Convert the record's number to an integer for comparison
                    record_number = int(record["number"])

                    # Perform exact match if exact is True
                    if exact and record_number == paper_number:
                        results.append(record)
                    # Perform partial match if exact is False
                    elif not exact and str(paper_number) in str(record_number):
                        results.append(record)
                except ValueError:
                    # Skip records with invalid number format
                    continue
        return results

    def search_by_number_range(self, lowest_paper, highest_paper):
        """
        Search records by number range.

        :param lowest_paper: The lowest paper number in the range
        :param highest_paper: The highest paper number in the range
        :return: A list of matching records
        """
        results = []
        for record in self.data:
            if "number" in record:
                try:
                    record_number = int(record["number"])
                    if lowest_paper <= record_number <= highest_paper:
                        results.append(record)
                except ValueError:
                    # Skip records with invalid number format
                    continue
        return results

    def search_by_year_range(self, first_year, last_year, data=None):
        """
        Search records by year range.

        :param first_year: The first year in the range
        :param last_year: The last year in the range
        :param data: Optional list of records to filter (default is self.data)
        :return: A list of matching records
        """
        if data is None:
            data = self.data

        results = []
        for record in data:
            if "year" in record:
                try:
                    record_year = int(record["year"])
                    if first_year <= record_year <= last_year:
                        results.append(record)
                except ValueError:
                    # Skip records with invalid year format
                    continue
        return results

    def fuzzy_search_by_author_title(self, author_text, title_text, optional_author_text=None,
                                     optional_title_text=None, data=None):
        """
        Perform a fuzzy search by author and title with AND logic.
        All non-empty fields must be satisfied simultaneously.
        """
        if data is None:
            data = self.data

        results = []
        for record in data:
            author_ok = True
            title_ok = True

            # Check author(s) fields (strict AND)
            if "authors" in record:
                author_field = record["authors"].lower()
                if author_text and author_text.lower() not in author_field:
                    author_ok = False
                if optional_author_text and optional_author_text.lower() not in author_field:
                    author_ok = False
            else:
                if author_text or optional_author_text:  # no authors field but input exists
                    author_ok = False

            # Check title field (strict AND)
            if "title" in record:
                title_field = record["title"].lower()
                if title_text and title_text.lower() not in title_field:
                    title_ok = False
                if optional_title_text and optional_title_text.lower() not in title_field:
                    title_ok = False
            else:
                if title_text or optional_title_text:  # no title field but input exists
                    title_ok = False

            # Add record only if all conditions are satisfied
            if author_ok and title_ok:
                results.append(record)

        return results

    def fuzzy_search_by_keyword(self, keyword_text):
        """
        Perform a fuzzy search by keyword in subject1 and subject2 fields.

        :param keyword_text: Text to find in the keyword fields (fuzzy match, case-insensitive)
        :return: A list of matching records
        """
        results = []
        for record in self.data:
            keyword_match = False

            # Check subject1 field (fuzzy match, case-insensitive)
            if "subject1" in record and keyword_text.lower() in record["subject1"].lower():
                keyword_match = True

            # Check subject2 field (fuzzy match, case-insensitive)
            if "subject2" in record and keyword_text.lower() in record["subject2"].lower():
                keyword_match = True

            # If keyword matches in either subject1 or subject2, add to results
            if keyword_match:
                results.append(record)

        return results

    def fuzzy_search_by_book_journal(self, book_journal_text):
        """
        Perform a fuzzy search by book/journal title in the bookjour field.

        :param book_journal_text: Text to find in the bookjour field (fuzzy match, case-insensitive)
        :return: A list of matching records
        """
        results = []
        for record in self.data:
            if "bookjour" in record and book_journal_text.lower() in record["bookjour"].lower():
                results.append(record)

        return results

    def fuzzy_search_by_any_field(self, any_field_text):
        """
        Perform a fuzzy search by text in any field.

        :param any_field_text: Text to find in any field (fuzzy match, case-insensitive)
        :return: A list of matching records
        """
        results = []
        for record in self.data:
            for key, value in record.items():
                if any_field_text.lower() in str(value).lower():
                    results.append(record)
                    break  # Stop checking other fields if a match is found

        return results

    def filter_by_vita_type(self, data, selected_vita_types):
        """
        Filter records by selected vita types.

        :param data: A list of records to filter
        :param selected_vita_types: A list of selected vita type codes (e.g., ['J', 'JR'])
        :return: A list of filtered records
        """
        if not selected_vita_types:  # If no vita types are selected, return all data
            return data

        filtered_results = []
        for record in data:
            if "vitatyp" in record and record["vitatyp"] in selected_vita_types:
                filtered_results.append(record)
        return filtered_results