from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.utils.nlp_parser import parse_query
from app.services.expense_service import ExpenseService

router = Router(name="nlp")

@router.message(Command("ask"))
async def ask_query(message: Message, db: AsyncSession):
    """
    Usage:
      /ask how much did I spend on food last March?
    """
    query_text = message.text[len("/ask "):].strip()
    parsed = parse_query(query_text)
    if not parsed:
        await message.answer("🤔 Sorry, I didn’t understand. Try using keywords like 'food', 'transport', 'March', '2024'.")
        return

    category, year, month, period_type = parsed
    svc = ExpenseService(db)

    summary = None
    if period_type == "week":
        week_num = datetime.now().isocalendar()[1]
        summary = await svc.week_summary(message.from_user.id, year, week_num)
    elif period_type == "month":
        summary = await svc.monthly_summary(message.from_user.id, year, month)
    elif period_type == "year":
        summary = await svc.yearly_summary(message.from_user.id, year)

    if not summary or summary["total_cents"] == 0:
        await message.answer("No expenses found for that period.")
        return

    if category:
        amt = summary["breakdown"].get(category, 0) or 0
        await message.answer(f"📊 {category} in {year}{('-' + str(month)) if month else ''}: ${amt/100:.2f}")
    else:
        await message.answer(f"📊 Total in {year}{('-' + str(month)) if month else ''}: ${summary['total_cents']/100:.2f}")
