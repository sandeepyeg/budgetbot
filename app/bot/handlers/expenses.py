from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.expense_service import ExpenseService
from app.utils.parser import parse_item_and_amount

router = Router(name="expenses")

@router.message(Command("add"))
async def add_cmd(message: Message, db: AsyncSession):
    """
    Usage: /add Pizza 12.50
    """
    text = message.text or ""
    payload = text.partition(" ")[2].strip()
    if not payload:
        await message.answer("Usage: /add <item> <amount>\nExample: /add Pizza 12.50")
        return

    parsed = parse_item_and_amount(payload)
    if not parsed:
        await message.answer("Couldn't parse amount. Try: /add Latte 4.25")
        return

    item, cents = parsed
    svc = ExpenseService(db)
    exp = await svc.add_expense_text(user_id=message.from_user.id, item_name=item, amount_cents=cents)
    dollars = cents / 100
    await message.answer(f"✅ Added: *{item}* — ${dollars:.2f} (id: `{exp.id}`)", parse_mode="Markdown")

@router.message(F.text & ~F.text.startswith("/"))
async def add_free_text(message: Message, db: AsyncSession):
    """
    Plain text: "Pizza 12.50"
    """
    parsed = parse_item_and_amount(message.text or "")
    if not parsed:
        return  # ignore non-expense messages for now
    item, cents = parsed
    svc = ExpenseService(db)
    exp = await svc.add_expense_text(user_id=message.from_user.id, item_name=item, amount_cents=cents)
    dollars = cents / 100
    await message.answer(f"✅ Added: *{item}* — ${dollars:.2f} (id: `{exp.id}`)", parse_mode="Markdown")
