from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.budget_service import BudgetService
from app.services.expense_service import ExpenseService

router = Router(name="budgets")

@router.message(Command("budget"))
async def budget_help(message: Message):
    await message.answer("Usage:\n"
                         "/budget_add <scope> <limit> <period>\n"
                         "  scope = overall OR category:<name>\n"
                         "  limit = number in dollars\n"
                         "  period = month|year\n"
                         "Example: /budget_add overall 2000 month\n"
                         "Example: /budget_add category:Food 500 month\n"
                         "/budget_list\n"
                         "/budget_delete <id>")

@router.message(Command("budget_list"))
async def budget_list(message: Message, db: AsyncSession):
    svc = BudgetService(db)
    budgets = await svc.list_budgets(message.from_user.id)
    if not budgets:
        await message.answer("No budgets set.")
        return
    lines = ["📊 Active budgets:"]
    for b in budgets:
        scope = b.scope_value if b.scope_type == "category" else "Overall"
        lines.append(f"- {scope}: ${b.limit_cents/100:.2f} per {b.period} (id: {b.id})")
    await message.answer("\n".join(lines))

@router.message(Command("budget_add"))
async def budget_add(message: Message, db: AsyncSession):
    parts = message.text.split()
    if len(parts) != 4:
        await message.answer("Usage: /budget_add <scope> <limit> <period>")
        return
    _, scope, limit_str, period = parts
    try:
        limit_cents = int(float(limit_str) * 100)
    except ValueError:
        await message.answer("Invalid limit amount.")
        return
    if scope.lower() == "overall":
        scope_type, scope_value = "overall", None
    elif scope.lower().startswith("category:"):
        scope_type, scope_value = "category", scope.split(":", 1)[1]
    else:
        await message.answer("Scope must be 'overall' or 'category:<name>'")
        return
    if period.lower() not in ("month", "year"):
        await message.answer("Period must be month or year.")
        return

    svc = BudgetService(db)
    b = await svc.add_budget(message.from_user.id, scope_type, scope_value, limit_cents, period.lower())
    scope_disp = scope_value or "Overall"
    await message.answer(f"✅ Budget set: {scope_disp} ${limit_cents/100:.2f}/{period}")

@router.message(Command("budget_delete"))
async def budget_delete(message: Message, db: AsyncSession):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /budget_delete <id>")
        return
    svc = BudgetService(db)
    b = await svc.delete_budget(parts[1], message.from_user.id)
    await message.answer("✅ Deleted." if b else "❌ Not found.")
