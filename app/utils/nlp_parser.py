import re
from datetime import datetime

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12
}

def parse_query(text: str):
    """
    Very simple rule-based query parser.
    Returns (category, year, month, period_type) or None.
    period_type = "month" | "year" | "week" | None
    """
    text = text.lower()

    # detect category (word after 'on' or known hashtags)
    category = None
    match = re.search(r"on (\w+)", text)
    if match:
        category = match.group(1).capitalize()

    # detect year
    year = None
    match = re.search(r"(19|20)\d{2}", text)
    if match:
        year = int(match.group(0))

    # detect month
    month = None
    for name, num in MONTHS.items():
        if name in text:
            month = num
            break

    # detect "this week"
    if "this week" in text:
        return category, datetime.now().year, None, "week"

    # detect "this month"
    if "this month" in text:
        return category, datetime.now().year, datetime.now().month, "month"

    # detect "this year"
    if "this year" in text:
        return category, datetime.now().year, None, "year"

    # if year+month detected
    if year and month:
        return category, year, month, "month"

    # if only year
    if year:
        return category, year, None, "year"

    return None
