import re

# Sentinel used so empty values sort last in any ordering, no matter the type
# of the other keys. The first slot of the tuple is the "is missing" flag
# (False sorts before True), the second slot is a comparable typed value.
_MISSING_TUPLE_INT = (True, 0)
_MISSING_TUPLE_STR = (True, "")


def _parse_int_loose(value):
    """Best-effort int from a possibly messy string ('1,234' / 'September/October 2016')."""
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if not s:
        return None
    try:
        return int(s)
    except (TypeError, ValueError):
        m = re.search(r"-?\d+", s)
        if m:
            try:
                return int(m.group(0))
            except (TypeError, ValueError):
                return None
        return None


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

        Each sort key is a 2-tuple ``(missing_flag, value)`` so empty / non-parseable
        values always sort last regardless of the other keys' type. This fixes the
        previous TypeError when ``order=backward`` and any record had an empty year
        or a messy year string like "September/October 2016".
        """

        def get_sort_key(record):
            sort_keys = []

            for field, config in sorted(sort_config.items(), key=lambda x: x[1]["priority"]):
                value = record.get(field, "")
                order = config.get("order")

                if value is None or (isinstance(value, str) and not value.strip()):
                    if order == "backward" and field in ("number", "year"):
                        sort_keys.append(_MISSING_TUPLE_INT)
                    elif order == "vitord":
                        sort_keys.append((True, len(self.vita_orders.get(vita_order_key, []))))
                    else:
                        sort_keys.append(_MISSING_TUPLE_STR)
                    continue

                if order == "backward":
                    if field in ("number", "year"):
                        n = _parse_int_loose(value)
                        if n is None:
                            sort_keys.append(_MISSING_TUPLE_INT)
                        else:
                            sort_keys.append((False, -n))
                    else:
                        sort_keys.append((False, str(value).lower()))
                elif order == "forwards":
                    if isinstance(value, str):
                        sort_keys.append((False, value.lower()))
                    else:
                        sort_keys.append((False, str(value)))
                elif order == "vitord":
                    vita_order = self.vita_orders.get(vita_order_key, [])
                    if value in vita_order:
                        sort_keys.append((False, vita_order.index(value)))
                    else:
                        sort_keys.append((True, len(vita_order)))
                else:
                    sort_keys.append((False, str(value).lower() if isinstance(value, str) else str(value)))

            return tuple(sort_keys)

        return sorted(self.data, key=get_sort_key)
