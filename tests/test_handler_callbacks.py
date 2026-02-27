from types import SimpleNamespace

import pytest

from app.bot.handlers import recurring as recurring_handler
from app.bot.handlers import reports as reports_handler


class DummyMessage:
    def __init__(self):
        self.answer_calls = []
        self.edit_reply_markup_calls = []

    async def answer(self, text, **kwargs):
        self.answer_calls.append({"text": text, "kwargs": kwargs})

    async def edit_reply_markup(self, **kwargs):
        self.edit_reply_markup_calls.append(kwargs)


class DummyCallback:
    def __init__(self, data: str, user_id: int = 1):
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = DummyMessage()
        self.answer_calls = []

    async def answer(self, text=None, **kwargs):
        self.answer_calls.append({"text": text, "kwargs": kwargs})


@pytest.mark.asyncio
async def test_recurring_quick_action_pause_success(monkeypatch):
    class FakeRecurringService:
        def __init__(self, db):
            self.db = db

        async def update_state(self, ref, user_id, **kwargs):
            assert ref == "abc12345"
            assert user_id == 1
            assert kwargs == {"paused": True}
            return object()

    monkeypatch.setattr(recurring_handler, "RecurringService", FakeRecurringService)

    callback = DummyCallback("recurring:pause:abc12345")
    await recurring_handler.recurring_quick_action(callback, db=object())

    assert len(callback.message.edit_reply_markup_calls) == 1
    assert callback.answer_calls[0]["text"] == "⏸ Paused"


@pytest.mark.asyncio
async def test_recurring_quick_action_cancel_not_found(monkeypatch):
    class FakeRecurringService:
        def __init__(self, db):
            self.db = db

        async def update_state(self, ref, user_id, **kwargs):
            assert ref == "missing99"
            assert user_id == 1
            assert kwargs == {"active": False}
            return None

    monkeypatch.setattr(recurring_handler, "RecurringService", FakeRecurringService)

    callback = DummyCallback("recurring:cancel:missing99")
    await recurring_handler.recurring_quick_action(callback, db=object())

    assert callback.answer_calls[0]["text"] == "Not found"
    assert callback.answer_calls[0]["kwargs"]["show_alert"] is True


@pytest.mark.asyncio
async def test_reports_nav_to_menu_uses_main_keyboard():
    callback = DummyCallback("nav:menu")

    await reports_handler.nav_to_menu(callback)

    assert callback.answer_calls[0]["text"] is None
    assert callback.message.answer_calls[0]["text"] == "📋 Main menu"
    reply_markup = callback.message.answer_calls[0]["kwargs"]["reply_markup"]
    labels = [button.text for row in reply_markup.keyboard for button in row]
    assert "/menu" in labels


@pytest.mark.asyncio
async def test_reports_search_quick_routes_keyword(monkeypatch):
    captured = {}

    async def fake_send_search_results(target, db, user_id, keyword):
        captured["target"] = target
        captured["db"] = db
        captured["user_id"] = user_id
        captured["keyword"] = keyword

    monkeypatch.setattr(reports_handler, "_send_search_results", fake_send_search_results)

    callback = DummyCallback("search:kw:coffee", user_id=42)
    fake_db = object()

    await reports_handler.search_quick(callback, db=fake_db)

    assert captured["target"] is callback.message
    assert captured["db"] is fake_db
    assert captured["user_id"] == 42
    assert captured["keyword"] == "coffee"
    assert callback.answer_calls[0]["text"] is None


@pytest.mark.asyncio
async def test_reports_report_period_quick_month_last(monkeypatch):
    class FixedDateTime:
        @classmethod
        def now(cls):
            return SimpleNamespace(year=2026, month=1)

    captured = {}

    async def fake_send_month_report(target, db, user_id, year, month):
        captured["target"] = target
        captured["db"] = db
        captured["user_id"] = user_id
        captured["year"] = year
        captured["month"] = month

    monkeypatch.setattr(reports_handler, "datetime", FixedDateTime)
    monkeypatch.setattr(reports_handler, "_send_month_report", fake_send_month_report)

    callback = DummyCallback("report:month:last", user_id=7)
    fake_db = object()

    await reports_handler.report_period_quick(callback, db=fake_db)

    assert captured["target"] is callback.message
    assert captured["db"] is fake_db
    assert captured["user_id"] == 7
    assert captured["year"] == 2025
    assert captured["month"] == 12
    assert callback.answer_calls[0]["text"] is None
