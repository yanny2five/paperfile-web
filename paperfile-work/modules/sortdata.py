class SortData:
    def __init__(self, data):
        """
        Initialize the SortData class.

        :param data: A list of dictionaries, each representing a record
        """
        self.data = data

        # Define the order lists for vita types
        self.vita_orders = {
            "vitord1": [
                'J', 'JR', 'PA', 'B', 'BC', 'SB', 'IP', 'P', 'SP', 'U', 'PS', 'SM', 'BR', 'EC', 'SV', 'N', 'OP', 'PO',
                'DP', 'CP', 'CD', 'WS', 'TH', 'TS', 'F', 'JD', 'PR', 'O', 'OI', 'CN', 'MS'
            ],
            "vitord2": [
                'J', 'JR', 'PA', 'B', 'BC', 'SB', 'IP', 'P', 'U', 'SP', 'PS', 'DP', 'CP', 'CD', 'SM', 'BR', 'EC', 'SV',
                'OP', 'PO', 'N', 'TH', 'TS'
            ],
            "vitordg": [
                'J', 'JR', 'PA', 'B', 'BC', 'SB', 'IP', 'P', 'U', 'SP', 'PS', 'SM', 'BR', 'EC', 'OP', 'SV', 'N', 'PO',
                'DP', 'CP', 'CD', 'WS', 'TH', 'TS', 'F', 'JD', 'PR'
            ]
        }

    def sort_by_criteria(self, sort_config, vita_order_key="vitord1"):
        """
        Sort records based on the specified sorting configuration.

        :param sort_config: A dictionary defining the sorting priority and order for each field
        :param vita_order_key: The key for the vita type order list (e.g., "vitord1", "vitord2", "vitordg")
        :return: A sorted list of records
        """

        def get_sort_key(record):
            # Initialize a list to store sorting keys based on priority
            sort_keys = []

            # Iterate through the sorting configuration
            for field, config in sorted(sort_config.items(), key=lambda x: x[1]["priority"]):
                value = record.get(field, "")

                # Handle empty values
                if value is None or value == "":
                    # Assign a special string to ensure empty values are sorted last
                    sort_keys.append("zzzzzzzz")  # A large string to ensure it sorts last
                    continue

                # Handle each field based on its sorting order
                if config["order"] == "backward":
                    # For backward order, use negative value for descending sort
                    if field in ["number", "year"]:
                        sort_keys.append(-int(value))
                    else:
                        sort_keys.append(value)  # Default to forwards for non-numeric fields
                elif config["order"] == "forwards":
                    # For forwards order, use the value as is
                    if isinstance(value, str):
                        sort_keys.append(value.lower())
                    else:
                        sort_keys.append(str(value))  # Convert non-string values to strings
                elif config["order"] == "vitord":
                    # For vitord order, use the index in the specified vita_order list
                    vita_order = self.vita_orders.get(vita_order_key, [])
                    if value in vita_order:
                        sort_keys.append(vita_order.index(value))
                    else:
                        # If value is not in the list, assign a high index to sort it last
                        sort_keys.append(len(vita_order))

            return tuple(sort_keys)

        # Sort the data using the generated sort keys
        sorted_data = sorted(self.data, key=get_sort_key)

        return sorted_data