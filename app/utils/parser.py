import re
from decimal import Decimal, InvalidOperation

_AMOUNT_RE = re.compile(r"(-?\d+(?:[.,]\d{1,2})?)")

def parse_item_and_amount(text: str) -> tuple[str, int] | None:
    """
    Extract (item_name, amount_cents) from text like:
    'Pizza 12.50', '12.50 Pizza', '$12.50 latte', 'latte $4'
    Returns cents as int.
    """
    match = None
    # Try last number in the string first (most natural: 'Pizza 12.50')
    for m in _AMOUNT_RE.finditer(text):
        match = m
    if not match:
        return None

    amount_str = match.group(1).replace(",", ".")
    try:
        amount = Decimal(amount_str)
    except InvalidOperation:
        return None

    # Item is everything except the matched amount token
    start, end = match.span()
    item = (text[:start] + text[end:]).strip()
    # If item ended up empty, flip it: treat the other side as item
    if not item:
        # If text starts with amount, attempt item from the rest
        item = text.replace(match.group(1), "").strip().strip("$").strip()

    # Normalize item spacing and remove leading currency symbol
    item = re.sub(r"\s+", " ", item)
    if item.startswith("$"):
        item = item[1:].strip()

    # Convert to cents
    cents = int((amount * 100).quantize(Decimal("1")))
    return (item if item else "Unknown"), cents
