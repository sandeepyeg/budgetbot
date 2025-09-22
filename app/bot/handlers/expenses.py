from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.expense_service import ExpenseService
from app.services.category_service import CategoryService
from app.utils.parser import parse_item_and_amount, extract_hashtags

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
    """
    Usage:
      /add Pizza 12.50
      /add Pizza 12.50 #food #lunch
    """
    text = message.text or ""
    payload = text.partition(" ")[2].strip()
    if not payload:
        await message.answer("Usage: /add <item> <amount> [#category] [#tag1 #tag2]\nExample: /add Pizza 12.50 #food #lunch")
        return

    parsed = parse_item_and_amount(payload)
    if not parsed:
        await message.answer("Couldn't parse amount. Try: /add Latte 4.25 #food")
        return

    item, cents = parsed
    hashtags = extract_hashtags(payload)
    cat_token, tags_csv = _split_category_and_tags(hashtags)

    category_name = None
    if cat_token:
        cs = CategoryService(db)
        cat = await cs.get_or_create(cat_token)  # canonicalize via slug & stored name
        category_name = cat.name

    svc = ExpenseService(db)
    exp = await svc.add_expense_text(
        user_id=message.from_user.id,
        item_name=item,
        amount_cents=cents,
        category=category_name,
        tags=tags_csv
    )
    dollars = cents / 100
    suffix = f" · 🏷 {category_name}" if category_name else ""
    tags_suffix = f" · #{tags_csv.replace(',', ' #')}" if tags_csv else ""
    await message.answer(
        f"✅ Added: *{item}* — ${dollars:.2f}{suffix}{tags_suffix}\n`{exp.id}`",
        parse_mode="Markdown"
    )

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
        tags=tags_csv
    )
    dollars = cents / 100
    suffix = f" · 🏷 {category_name}" if category_name else ""
    tags_suffix = f" · #{tags_csv.replace(',', ' #')}" if tags_csv else ""
    await message.answer(
        f"✅ Added: *{item}* — ${dollars:.2f}{suffix}{tags_suffix}\n`{exp.id}`",
        parse_mode="Markdown"
    )
