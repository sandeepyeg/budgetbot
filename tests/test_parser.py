from app.utils.parser import parse_item_and_amount, extract_hashtags, parse_recurring_from_tags
from app.utils.text import normalize_merchant, progress_bar


def test_parse_item_and_amount_basic():
    item, cents = parse_item_and_amount("Pizza 12.50 #food")
    assert item == "Pizza"
    assert cents == 1250


def test_extract_hashtags():
    tags = extract_hashtags("Coffee 4.75 #food #pm_card #morning")
    assert tags == ["food", "pm_card", "morning"]


def test_parse_recurring_tags():
    cfg = parse_recurring_from_tags(["monthly", "day5", "r3"])
    assert cfg["frequency"] == "monthly"
    assert cfg["day_of_month"] == 5
    assert cfg["repeat_count"] == 3


def test_normalize_merchant():
    assert normalize_merchant("STARBUCKS, INC.") == "Starbucks"


def test_progress_bar_bounds():
    assert progress_bar(-5) == "░░░░░░░░░░"
    assert progress_bar(105) == "██████████"
