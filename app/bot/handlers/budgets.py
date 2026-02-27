from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.budget_service import BudgetService
from app.services.expense_service import ExpenseService
from app.utils.text import short_ref

router = Router(name="budgets")


class BudgetFlow(StatesGroup):
    action = State()
    scope = State()
    category = State()
    limit = State()
    period = State()
    delete_ref = State()


def _budget_action_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Add Budget"), KeyboardButton(text="📋 List Budgets")],
            [KeyboardButton(text="🗑 Delete Budget"), KeyboardButton(text="❌ Cancel")],
        ],
        resize_keyboard=True,
    )


def _budget_scope_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="overall"), KeyboardButton(text="category")],
            [KeyboardButton(text="❌ Cancel")],
        ],
        resize_keyboard=True,
    )


def _budget_period_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="month"), KeyboardButton(text="year")],
            [KeyboardButton(text="❌ Cancel")],
        ],
        resize_keyboard=True,
    )

@router.message(Command("budget"))
async def budget_help(message: Message, state: FSMContext):
    await state.set_state(BudgetFlow.action)
    await message.answer(
        "Budget actions:\nChoose one below or use slash commands (/budget_add, /budget_list, /budget_delete).",
        reply_markup=_budget_action_kb(),
    )


@router.message(BudgetFlow.action)
async def budget_action(message: Message, db: AsyncSession, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=ReplyKeyboardRemove())
        return
    if text == "📋 List Budgets":
        await state.clear()
        await budget_list(message, db)
        return
    if text == "➕ Add Budget":
        await state.set_state(BudgetFlow.scope)
        await message.answer("Choose scope", reply_markup=_budget_scope_kb())
        return
    if text == "🗑 Delete Budget":
        await state.set_state(BudgetFlow.delete_ref)
        await message.answer("Send budget ref (short id from list)", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Cancel")]], resize_keyboard=True))
        return
    await message.answer("Choose a valid action.")


@router.message(BudgetFlow.scope)
async def budget_scope(message: Message, state: FSMContext):
    text = (message.text or "").strip().lower()
    if text == "❌ cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=ReplyKeyboardRemove())
        return
    if text == "overall":
        await state.update_data(scope_type="overall", scope_value=None)
        await state.set_state(BudgetFlow.limit)
        await message.answer("Enter limit in dollars (e.g., 500)", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Cancel")]], resize_keyboard=True))
        return
    if text == "category":
        await state.set_state(BudgetFlow.category)
        await message.answer("Enter category name (e.g., Food)", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Cancel")]], resize_keyboard=True))
        return
    await message.answer("Choose 'overall' or 'category'.")


@router.message(BudgetFlow.category)
async def budget_category(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=ReplyKeyboardRemove())
        return
    await state.update_data(scope_type="category", scope_value=text)
    await state.set_state(BudgetFlow.limit)
    await message.answer("Enter limit in dollars (e.g., 500)", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Cancel")]], resize_keyboard=True))


@router.message(BudgetFlow.limit)
async def budget_limit(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=ReplyKeyboardRemove())
        return
    try:
        limit_cents = int(float(text) * 100)
    except ValueError:
        await message.answer("Invalid amount. Try again.")
        return
    await state.update_data(limit_cents=limit_cents)
    await state.set_state(BudgetFlow.period)
    await message.answer("Choose period", reply_markup=_budget_period_kb())


@router.message(BudgetFlow.period)
async def budget_period(message: Message, db: AsyncSession, state: FSMContext):
    text = (message.text or "").strip().lower()
    if text == "❌ cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=ReplyKeyboardRemove())
        return
    if text not in ("month", "year"):
        await message.answer("Choose 'month' or 'year'.")
        return

    data = await state.get_data()
    await state.clear()

    svc = BudgetService(db)
    b = await svc.add_budget(
        message.from_user.id,
        data["scope_type"],
        data["scope_value"],
        data["limit_cents"],
        text,
    )
    scope_disp = data["scope_value"] or "Overall"
    await message.answer(
        f"✅ Budget set: {scope_disp} ${data['limit_cents']/100:.2f}/{text} · Ref: `{short_ref(b.id)}`",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(BudgetFlow.delete_ref)
async def budget_delete_ref(message: Message, db: AsyncSession, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=ReplyKeyboardRemove())
        return
    svc = BudgetService(db)
    b = await svc.delete_budget(text, message.from_user.id)
    await state.clear()
    await message.answer("✅ Deleted." if b else "❌ Not found or ambiguous ref.", reply_markup=ReplyKeyboardRemove())

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
        lines.append(f"- {scope}: ${b.limit_cents/100:.2f} per {b.period} (ref: {short_ref(b.id)})")
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
    await message.answer(f"✅ Budget set: {scope_disp} ${limit_cents/100:.2f}/{period} · Ref: `{short_ref(b.id)}`", parse_mode="Markdown")

@router.message(Command("budget_delete"))
async def budget_delete(message: Message, db: AsyncSession):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /budget_delete <ref>")
        return
    svc = BudgetService(db)
    b = await svc.delete_budget(parts[1], message.from_user.id)
    await message.answer("✅ Deleted." if b else "❌ Not found or ambiguous ref.")
