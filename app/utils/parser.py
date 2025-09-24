import re
from decimal import Decimal, InvalidOperation

_AMOUNT_RE = re.compile(r"(-?\d+(?:[.,]\d{1,2})?)")
_HASHTAG_RE = re.compile(r"(?:^|\s)#([A-Za-z0-9_-]+)")
_NOTE_RE = re.compile(r"(?:note:|//)(.+)", re.IGNORECASE)

def extract_hashtags(text: str) -> list[str]:
    return [m.group(1) for m in _HASHTAG_RE.finditer(text or "")]

def extract_note(text: str) -> str | None:
    match = _NOTE_RE.search(text or "")
    if match:
        return match.group(1).strip()
    return None
def strip_hashtags(text: str) -> str:
    return _HASHTAG_RE.sub(" ", text or "").strip()

def strip_hashtags_and_note(text: str) -> str:
    no_tags = _HASHTAG_RE.sub(" ", text or "")
    no_note = _NOTE_RE.sub("", no_tags)
    return no_note.strip()

def parse_item_and_amount(text: str) -> tuple[str, int] | None:
    """
    Extract (item_name, amount_cents) from text like:
    'Pizza 12.50 #food note: dinner'
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

    item = strip_hashtags_and_note(item)
    cents = int((amount * 100).quantize(Decimal("1")))
    return (item if item else "Unknown"), cents


def parse_recurring_from_tags(tags: list[str]) -> dict | None:
    freq = None
    day_of_month = None
    day_of_week = None
    repeat_count = None

    for t in tags:
        t_low = t.lower()
        if t_low in ("daily", "weekly", "monthly"):
            freq = t_low
        elif t_low.startswith("day"):
            try:
                val = int(t_low[3:])
                if freq == "monthly":
                    day_of_month = val
                elif freq == "weekly":
                    day_of_week = val
            except ValueError:
                continue
        elif t_low.startswith("r"):
            try:
                repeat_count = int(t_low[1:])
            except ValueError:
                continue

    if not freq:
        return None

    return {
        "frequency": freq,
        "day_of_month": day_of_month,
        "day_of_week": day_of_week,
        "repeat_count": repeat_count,  # None = infinite
    }
