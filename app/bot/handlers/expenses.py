from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from app.services.budget_service import BudgetService
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.expense_service import ExpenseService
from app.services.category_service import CategoryService
from app.services.recurring_service import RecurringService
from app.utils.parser import parse_item_and_amount, extract_hashtags, extract_note, parse_recurring_from_tags

router = Router(name="expenses")

def _split_category_and_tags(hashtags: list[str]) -> tuple[str | None, str | None]:
    if not hashtags:
        return None, None
    cat = hashtags[0]
    others = hashtags[1:]
    tags_csv = ",".join(others) if others else None
    return cat, tags_csv

@router.message(Command("add"))
async def add_cmd(message: Message, db: AsyncSession):
    text = message.text or ""
    payload = text.partition(" ")[2].strip()
    if not payload:
        await message.answer("Usage: /add <item> <amount> [#category] [#tags] [#monthly|#weekly|#daily] [#dayX] [#rN]")
        return

    parsed = parse_item_and_amount(payload)
    if not parsed:
        await message.answer("Couldn't parse amount.")
        return

    item, cents = parsed
    hashtags = extract_hashtags(payload)
    note = extract_note(payload)
    cat_token, tags_csv = _split_category_and_tags(hashtags)

    category_name = None
    if cat_token:
        cs = CategoryService(db)
        cat = await cs.get_or_create(cat_token)
        category_name = cat.name

    svc = ExpenseService(db)
    exp = await svc.add_expense_text(
        user_id=message.from_user.id,
        item_name=item,
        amount_cents=cents,
        category=category_name,
        tags=tags_csv,
        notes=note,
    )
    bsvc = BudgetService(db)
    alerts = await bsvc.check_alerts(message.from_user.id, svc)
    for alert in alerts:
        await message.answer(alert)

    dollars = cents / 100
    msg = f"✅ Added: *{item}* — ${dollars:.2f}"
    if category_name:
        msg += f" · 🏷 {category_name}"
    if tags_csv:
        msg += f" · #{tags_csv.replace(',', ' #')}"

    # --- recurring auto-detect ---
    rec_cfg = parse_recurring_from_tags(hashtags)
    if rec_cfg:
        rsvc = RecurringService(db)
        await rsvc.create(
            user_id=message.from_user.id,
            item_name=exp.item_name,
            amount_cents=exp.amount_cents,
            currency=exp.currency,
            category=exp.category,
            tags=exp.tags,
            notes=exp.notes,
            frequency=rec_cfg["frequency"],
            day_of_month=rec_cfg["day_of_month"],
            day_of_week=rec_cfg["day_of_week"],
            repeat_count=rec_cfg["repeat_count"],
        )
        msg += "\n📆 Recurring rule created automatically."

    await message.answer(msg, parse_mode="Markdown")

@router.message(F.text & ~F.text.startswith("/"))
async def add_free_text(message: Message, db: AsyncSession):
    """
    Plain text: "Pizza 12.50 #food #lunch"
    """
    parsed = parse_item_and_amount(message.text or "")
    if not parsed:
        return  # ignore non-expense messages for now

    item, cents = parsed
    hashtags = extract_hashtags(message.text or "")
    note = extract_note(message.text or "")
    cat_token, tags_csv = _split_category_and_tags(hashtags)

    category_name = None
    if cat_token:
        cs = CategoryService(db)
        cat = await cs.get_or_create(cat_token)
        category_name = cat.name

    svc = ExpenseService(db)
    exp = await svc.add_expense_text(
        user_id=message.from_user.id,
        item_name=item,
        amount_cents=cents,
        category=category_name,
        tags=tags_csv,
        notes=note
    )
    dollars = cents / 100
    suffix = f" · 🏷 {category_name}" if category_name else ""
    tags_suffix = f" · #{tags_csv.replace(',', ' #')}" if tags_csv else ""
    await message.answer(
        f"✅ Added: *{item}* — ${dollars:.2f}{suffix}{tags_suffix}\n`{exp.id}`",
        parse_mode="Markdown"
    )

@router.message(Command("settags"))
async def set_tags(message: Message, db: AsyncSession):
    """
    Usage: /settags <expense_id> tag1,tag2,tag3
    """
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /settags <expense_id> <tag1,tag2,...>")
        return

    _, expense_id, tags = parts
    svc = ExpenseService(db)
    updated = await svc.update_tags(expense_id=expense_id, user_id=message.from_user.id, tags=tags)
    if not updated:
        await message.answer("❌ Expense not found or not yours.")
        return

    await message.answer(f"✅ Tags updated for `{expense_id}` → {tags}", parse_mode="Markdown")


@router.message(Command("setnote"))
async def set_note(message: Message, db: AsyncSession):
    """
    Usage: /setnote <expense_id> some note text
    """
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /setnote <expense_id> <note text>")
        return

    _, expense_id, note = parts
    svc = ExpenseService(db)
    updated = await svc.update_note(expense_id=expense_id, user_id=message.from_user.id, note=note)
    if not updated:
        await message.answer("❌ Expense not found or not yours.")
        return

    await message.answer(f"✅ Note updated for `{expense_id}` → {note}", parse_mode="Markdown")