import tkinter as tk


class OutputData:
    def __init__(self, listbox):
        """
        Initialize the OutputData class.

        :param listbox: The Listbox widget where data will be displayed
        """
        self.listbox = listbox

    def clear_listbox(self):
        """
        Clear all items from the Listbox.
        """
        self.listbox.delete(0, tk.END)

    def load_data(self, data):
        """
        Load data into the Listbox.

        :param data: A list of dictionaries, each representing a record
        """
        self.clear_listbox()  # Clear existing items
        for i, record in enumerate(data):
            # Format the record as a string and insert into the Listbox
            record_str = self.format_record(record)
            self.listbox.insert(tk.END, record_str)

            # Add an empty line between every two records
            if i < len(data) - 1:  # Don't add an empty line after the last record
                self.listbox.insert(tk.END, "")  # Insert an empty line

    def format_record(self, record):
        """
        Format a record into a string for display in the Listbox.

        :param record: A dictionary representing a record
        :return: A formatted string
        """
        formatted_parts = []
        for key, value in record.items():
            # Skip fields with empty values, values equal to 0 (int or str), or None
            if value is None or value == 0 or value == "0" or value == "":
                continue

            # Format the field based on its key
            if key == "pages":
                formatted_parts.append(f"page: {value}")
            else:
                formatted_parts.append(str(value))

        # Join the parts with ", " and return the result
        return ", ".join(formatted_parts)