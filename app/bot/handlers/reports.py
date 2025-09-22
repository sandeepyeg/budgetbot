from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.services.expense_service import ExpenseService

router = Router(name="reports")

@router.message(Command("month"))
async def month_report(message: Message, db: AsyncSession):
    """
    Usage:
      /month                → current month
      /month 2025 9         → year + month (YYYY M)
    """
    parts = (message.text or "").split()
    year, month = None, None
    if len(parts) == 1:
        now = datetime.now()
        year, month = now.year, now.month
    elif len(parts) >= 3:
        try:
            year, month = int(parts[1]), int(parts[2])
        except ValueError:
            await message.answer("Usage: /month [year month]\nExample: /month 2025 9")
            return
    else:
        await message.answer("Usage: /month [year month]\nExample: /month 2025 9")
        return

    svc = ExpenseService(db)
    summary = await svc.monthly_summary(user_id=message.from_user.id, year=year, month=month)

    if summary["total_cents"] == 0:
        await message.answer(f"📊 No expenses found for {year}-{month:02d}.")
        return

    total_dollars = summary["total_cents"] / 100
    lines = [f"📅 *{year}-{month:02d}*"]
    lines.append(f"💰 Total: ${total_dollars:.2f}")

    for cat, cents in summary["breakdown"].items():
        dollars = (cents or 0) / 100
        lines.append(f" - {cat}: ${dollars:.2f}")

    await message.answer("\n".join(lines), parse_mode="Markdown")
