from app.utils.parser import parse_item_and_amount, extract_hashtags, parse_recurring_from_tags
from app.utils.text import normalize_merchant, progress_bar
from app.utils.text import short_ref
from app.bot.handlers.expenses import _extract_payment_method
from app.bot.keyboards import main_menu_kb


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


def test_short_ref_default_len():
    assert short_ref("1234567890abcdef") == "12345678"


def test_normalize_merchant_suffix_cleanup():
    assert normalize_merchant("Acme Co") == "Acme"


def test_extract_payment_method_from_hashtags():
    payment, cleaned = _extract_payment_method(["food", "pm_card", "morning"])
    assert payment == "card"
    assert cleaned == ["food", "morning"]


def test_main_menu_keyboard_contains_core_commands():
    kb = main_menu_kb()
    all_labels = [button.text for row in kb.keyboard for button in row]
    assert "/add" in all_labels
    assert "/budget" in all_labels
    assert "/rules" in all_labels
    assert "/menu" in all_labels
