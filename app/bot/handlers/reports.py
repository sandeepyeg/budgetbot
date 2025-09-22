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


@router.message(Command("year"))
async def year_report(message: Message, db: AsyncSession):
    """
    Usage:
      /year          → current year
      /year 2025     → specific year
    """
    parts = (message.text or "").split()
    if len(parts) == 1:
        now = datetime.now()
        year = now.year
    elif len(parts) == 2:
        try:
            year = int(parts[1])
        except ValueError:
            await message.answer("Usage: /year [YYYY]\nExample: /year 2025")
            return
    else:
        await message.answer("Usage: /year [YYYY]\nExample: /year 2025")
        return

    svc = ExpenseService(db)
    summary = await svc.yearly_summary(user_id=message.from_user.id, year=year)

    if summary["total_cents"] == 0:
        await message.answer(f"📊 No expenses found for {year}.")
        return

    total_dollars = summary["total_cents"] / 100
    lines = [f"📅 *{year}*"]
    lines.append(f"💰 Total: ${total_dollars:.2f}")

    # Category breakdown
    for cat, cents in summary["breakdown"].items():
        dollars = (cents or 0) / 100
        lines.append(f" - {cat}: ${dollars:.2f}")

    # Per-month subtotals
    if summary["per_month"]:
        lines.append("\n📆 *By Month*")
        for m in range(1, 13):
            if m in summary["per_month"]:
                dollars = summary["per_month"][m] / 100
                lines.append(f" - {year}-{m:02d}: ${dollars:.2f}")

    await message.answer("\n".join(lines), parse_mode="Markdown")

@router.message(Command("monthdetails"))
async def month_details(message: Message, db: AsyncSession):
    """
    Usage:
      /monthdetails item          → current month, grouped by item
      /monthdetails category      → current month, grouped by category
      /monthdetails 2025 9 item   → specific year/month
    """
    parts = (message.text or "").split()
    now = datetime.now()
    year, month, group_by = now.year, now.month, "item"

    if len(parts) == 2:
        group_by = parts[1].lower()
    elif len(parts) == 4:
        try:
            year, month = int(parts[1]), int(parts[2])
            group_by = parts[3].lower()
        except ValueError:
            await message.answer("Usage: /monthdetails [year month group_by]\nExample: /monthdetails 2025 9 category")
            return

    if group_by not in ["item", "category"]:
        await message.answer("Group by must be 'item' or 'category'")
        return

    svc = ExpenseService(db)
    rows = await svc.monthly_details(message.from_user.id, year, month, group_by)

    if not rows:
        await message.answer(f"No expenses found for {year}-{month:02d}.")
        return

    lines = [f"📅 *{year}-{month:02d}* — grouped by {group_by}"]
    for key, cents in rows:
        dollars = (cents or 0) / 100
        lines.append(f" - {key or 'Uncategorized'}: ${dollars:.2f}")

    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(Command("yeardetails"))
async def year_details(message: Message, db: AsyncSession):
    """
    Usage:
      /yeardetails item
      /yeardetails category
      /yeardetails 2025 item
    """
    parts = (message.text or "").split()
    now = datetime.now()
    year, group_by = now.year, "item"

    if len(parts) == 2:
        group_by = parts[1].lower()
    elif len(parts) == 3:
        try:
            year = int(parts[1])
            group_by = parts[2].lower()
        except ValueError:
            await message.answer("Usage: /yeardetails [year group_by]\nExample: /yeardetails 2025 category")
            return

    if group_by not in ["item", "category"]:
        await message.answer("Group by must be 'item' or 'category'")
        return

    svc = ExpenseService(db)
    rows = await svc.yearly_details(message.from_user.id, year, group_by)

    if not rows:
        await message.answer(f"No expenses found for {year}.")
        return

    lines = [f"📅 *{year}* — grouped by {group_by}"]
    for key, cents in rows:
        dollars = (cents or 0) / 100
        lines.append(f" - {key or 'Uncategorized'}: ${dollars:.2f}")

    await message.answer("\n".join(lines), parse_mode="Markdown")