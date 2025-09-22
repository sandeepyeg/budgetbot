import re
from decimal import Decimal, InvalidOperation

_AMOUNT_RE = re.compile(r"(-?\d+(?:[.,]\d{1,2})?)")
_HASHTAG_RE = re.compile(r"(?:^|\s)#([A-Za-z0-9_-]+)")

def extract_hashtags(text: str) -> list[str]:
    return [m.group(1) for m in _HASHTAG_RE.finditer(text or "")]

def strip_hashtags(text: str) -> str:
    return _HASHTAG_RE.sub(" ", text or "").strip()

def parse_item_and_amount(text: str) -> tuple[str, int] | None:
    """
    Extract (item_name, amount_cents) from text like:
    'Pizza 12.50', '12.50 Pizza', '$12.50 latte', 'latte $4'
    Returns cents as int.
    """
    match = None
    for m in _AMOUNT_RE.finditer(text):
        match = m
    if not match:
        return None

    amount_str = match.group(1).replace(",", ".")
    try:
        amount = Decimal(amount_str)
    except InvalidOperation:
        return None

    start, end = match.span()
    item = (text[:start] + text[end:]).strip()
    if not item:
        item = text.replace(match.group(1), "").strip().strip("$").strip()

    # remove hashtags from the item text to keep it clean
    item = strip_hashtags(item)

    cents = int((amount * 100).quantize(Decimal("1")))
    return (item if item else "Unknown"), cents
