from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.filters.state import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from decimal import Decimal, InvalidOperation
from app.services.budget_service import BudgetService
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.expense_service import ExpenseService
from app.services.category_service import CategoryService
from app.services.recurring_service import RecurringService
from app.bot.keyboards import main_menu_kb
from app.utils.parser import parse_item_and_amount, extract_hashtags, extract_note, parse_recurring_from_tags
from app.utils.text import short_ref, normalize_merchant

router = Router(name="expenses")


class AddExpenseFlow(StatesGroup):
    item = State()
    amount = State()
    category = State()
    payment_method = State()
    tags = State()
    note = State()


class EditLastFlow(StatesGroup):
    field = State()
    value = State()


def _cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Cancel")]],
        resize_keyboard=True,
    )


def _skip_cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⏭ Skip"), KeyboardButton(text="❌ Cancel")]],
        resize_keyboard=True,
    )


def _category_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Food"), KeyboardButton(text="Transport")],
            [KeyboardButton(text="Shopping"), KeyboardButton(text="Bills")],
            [KeyboardButton(text="Health"), KeyboardButton(text="Entertainment")],
            [KeyboardButton(text="⏭ Skip"), KeyboardButton(text="❌ Cancel")],
        ],
        resize_keyboard=True,
    )


def _payment_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="card"), KeyboardButton(text="cash")],
            [KeyboardButton(text="transfer"), KeyboardButton(text="upi")],
            [KeyboardButton(text="⏭ Skip"), KeyboardButton(text="❌ Cancel")],
        ],
        resize_keyboard=True,
    )


def _edit_field_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Item"), KeyboardButton(text="Amount")],
            [KeyboardButton(text="Category"), KeyboardButton(text="Tags")],
            [KeyboardButton(text="Note"), KeyboardButton(text="❌ Cancel")],
        ],
        resize_keyboard=True,
    )


async def _save_expense(
    message: Message,
    db: AsyncSession,
    item: str,
    cents: int,
    category_name: str | None,
    tags_csv: str | None,
    note: str | None,
    hashtags_for_recurring: list[str],
    payment_method: str | None = None,
):
    merchant = normalize_merchant(item)
    normalized_note = note.strip() if note else ""
    if payment_method:
        normalized_note = (normalized_note + " | " if normalized_note else "") + f"pm:{payment_method.strip()}"
    normalized_note = (normalized_note + " | " if normalized_note else "") + f"merchant:{merchant}"

    svc = ExpenseService(db)
    exp = await svc.add_expense_text(
        user_id=message.from_user.id,
        item_name=item,
        amount_cents=cents,
        category=category_name,
        tags=tags_csv,
        notes=normalized_note,
    )

    bsvc = BudgetService(db)
    alerts = await bsvc.check_alerts(message.from_user.id, svc)
    for alert in alerts:
        await message.answer(alert)

    dollars = cents / 100
    msg = f"✅ Added: *{item}* — ${dollars:.2f} · Ref: `{short_ref(exp.id)}`"
    if category_name:
        msg += f" · 🏷 {category_name}"
    if tags_csv:
        msg += f" · #{tags_csv.replace(',', ' #')}"
    if payment_method:
        msg += f" · 💳 {payment_method}"
    msg += f" · 🏪 {merchant}"

    rec_cfg = parse_recurring_from_tags(hashtags_for_recurring)
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

    await message.answer(msg, parse_mode="Markdown", reply_markup=main_menu_kb())

def _split_category_and_tags(hashtags: list[str]) -> tuple[str | None, str | None]:
    if not hashtags:
        return None, None
    cat = hashtags[0]
    others = hashtags[1:]
    tags_csv = ",".join(others) if others else None
    return cat, tags_csv


def _extract_payment_method(hashtags: list[str]) -> tuple[str | None, list[str]]:
    cleaned: list[str] = []
    payment = None
    for h in hashtags:
        h_low = h.lower()
        if h_low.startswith("pm_"):
            payment = h.split("_", 1)[1]
            continue
        if h_low.startswith("pay_"):
            payment = h.split("_", 1)[1]
            continue
        cleaned.append(h)
    return payment, cleaned

@router.message(Command("add"))
async def add_cmd(message: Message, db: AsyncSession, state: FSMContext):
    text = message.text or ""
    payload = text.partition(" ")[2].strip()
    if not payload:
        await state.set_state(AddExpenseFlow.item)
        await message.answer(
            "Let’s add an expense. What did you buy?",
            reply_markup=_cancel_kb(),
        )
        return

    parsed = parse_item_and_amount(payload)
    if not parsed:
        await message.answer("Couldn't parse amount.")
        return

    item, cents = parsed
    hashtags = extract_hashtags(payload)
    payment_method, hashtags = _extract_payment_method(hashtags)
    note = extract_note(payload)
    cat_token, tags_csv = _split_category_and_tags(hashtags)

    category_name = None
    if cat_token:
        cs = CategoryService(db)
        cat = await cs.get_or_create(cat_token)
        category_name = cat.name
    if not category_name:
        from app.services.rule_service import RuleService
        rsvc = RuleService(db)
        suggested = await rsvc.suggest_category(message.from_user.id, item)
        if suggested:
            cs = CategoryService(db)
            cat = await cs.get_or_create(suggested)
            category_name = cat.name
    await _save_expense(message, db, item, cents, category_name, tags_csv, note, hashtags, payment_method)


@router.message(AddExpenseFlow.item, F.text)
async def add_flow_item(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=main_menu_kb())
        return
    await state.update_data(item=text)
    await state.set_state(AddExpenseFlow.amount)
    await message.answer("Enter amount (e.g., 12.50)", reply_markup=_cancel_kb())


@router.message(AddExpenseFlow.amount, F.text)
async def add_flow_amount(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=main_menu_kb())
        return
    try:
        amount = Decimal(text.replace(",", "."))
        cents = int((amount * 100).quantize(Decimal("1")))
    except (InvalidOperation, ValueError):
        await message.answer("Invalid amount. Try like 12.50")
        return
    await state.update_data(cents=cents)
    await state.set_state(AddExpenseFlow.category)
    await message.answer("Category? Choose one below or skip.", reply_markup=_category_kb())


@router.message(AddExpenseFlow.category, F.text)
async def add_flow_category(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=main_menu_kb())
        return
    category = None if text == "⏭ Skip" else text
    await state.update_data(category=category)
    await state.set_state(AddExpenseFlow.payment_method)
    await message.answer("Payment method? Choose below or skip.", reply_markup=_payment_kb())


@router.message(AddExpenseFlow.payment_method, F.text)
async def add_flow_payment_method(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=main_menu_kb())
        return
    payment_method = None if text == "⏭ Skip" else text
    await state.update_data(payment_method=payment_method)
    await state.set_state(AddExpenseFlow.tags)
    await message.answer("Tags? comma-separated (or Skip)", reply_markup=_skip_cancel_kb())


@router.message(AddExpenseFlow.tags, F.text)
async def add_flow_tags(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=main_menu_kb())
        return
    tags = None if text == "⏭ Skip" else ",".join([t.strip() for t in text.split(",") if t.strip()])
    await state.update_data(tags=tags)
    await state.set_state(AddExpenseFlow.note)
    await message.answer("Any note? (or Skip)", reply_markup=_skip_cancel_kb())


@router.message(AddExpenseFlow.note, F.text)
async def add_flow_note(message: Message, db: AsyncSession, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=main_menu_kb())
        return

    note = None if text == "⏭ Skip" else text
    data = await state.get_data()
    await state.clear()

    category_name = None
    if data.get("category"):
        cs = CategoryService(db)
        cat = await cs.get_or_create(data["category"])
        category_name = cat.name

    await _save_expense(
        message,
        db,
        data.get("item", "Unknown"),
        data.get("cents", 0),
        category_name,
        data.get("tags"),
        note,
        [],
        data.get("payment_method"),
    )


@router.message(Command("undo"))
async def undo_last(message: Message, db: AsyncSession):
    svc = ExpenseService(db)
    last = await svc.get_last_expense(message.from_user.id)
    if not last:
        await message.answer("No expense to undo.")
        return
    removed = await svc.delete_expense_by_ref(message.from_user.id, last.id)
    if not removed:
        await message.answer("Could not undo last expense.")
        return
    await message.answer(
        f"↩️ Undone: *{removed.item_name}* ${removed.amount_cents/100:.2f} · Ref: `{short_ref(removed.id)}`",
        parse_mode="Markdown",
    )


@router.message(Command("edit_last"))
async def edit_last(message: Message, db: AsyncSession, state: FSMContext):
    svc = ExpenseService(db)
    last = await svc.get_last_expense(message.from_user.id)
    if not last:
        await message.answer("No recent expense to edit.")
        return

    await state.set_state(EditLastFlow.field)
    await state.update_data(expense_id=last.id)
    await message.answer(
        f"Editing last expense: *{last.item_name}* ${last.amount_cents/100:.2f} · Ref: `{short_ref(last.id)}`\nChoose field:",
        parse_mode="Markdown",
        reply_markup=_edit_field_kb(),
    )


@router.message(EditLastFlow.field, F.text)
async def edit_last_choose_field(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Cancel":
        await state.clear()
        await message.answer("Edit cancelled.", reply_markup=main_menu_kb())
        return
    allowed = {"Item", "Amount", "Category", "Tags", "Note"}
    if text not in allowed:
        await message.answer("Choose one of: Item, Amount, Category, Tags, Note")
        return

    await state.update_data(field=text.lower())
    await state.set_state(EditLastFlow.value)
    if text in {"Category", "Tags", "Note"}:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🧹 Clear"), KeyboardButton(text="❌ Cancel")]],
            resize_keyboard=True,
        )
    else:
        kb = _cancel_kb()
    await message.answer(f"Send new {text.lower()} value:", reply_markup=kb)


@router.message(EditLastFlow.value, F.text)
async def edit_last_apply(message: Message, db: AsyncSession, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Cancel":
        await state.clear()
        await message.answer("Edit cancelled.", reply_markup=main_menu_kb())
        return

    data = await state.get_data()
    expense_id = data.get("expense_id")
    field = data.get("field")
    svc = ExpenseService(db)
    updated = None

    if field == "item":
        updated = await svc.update_item(expense_id=expense_id, user_id=message.from_user.id, item_name=text)
    elif field == "amount":
        try:
            amount = Decimal(text.replace(",", "."))
            cents = int((amount * 100).quantize(Decimal("1")))
        except (InvalidOperation, ValueError):
            await message.answer("Invalid amount. Try like 12.50")
            return
        updated = await svc.update_amount(expense_id=expense_id, user_id=message.from_user.id, amount_cents=cents)
    elif field == "category":
        if text == "🧹 Clear":
            updated = await svc.update_category(expense_id=expense_id, user_id=message.from_user.id, category_name=None)
        else:
            cs = CategoryService(db)
            cat = await cs.get_or_create(text)
            updated = await svc.update_category(expense_id=expense_id, user_id=message.from_user.id, category_name=cat.name)
    elif field == "tags":
        tags_val = "" if text == "🧹 Clear" else text
        updated = await svc.update_tags(expense_id=expense_id, user_id=message.from_user.id, tags=tags_val)
    elif field == "note":
        note_val = "" if text == "🧹 Clear" else text
        updated = await svc.update_note(expense_id=expense_id, user_id=message.from_user.id, note=note_val)

    await state.clear()
    if not updated:
        await message.answer("Could not update the last expense.", reply_markup=main_menu_kb())
        return
    await message.answer(
        f"✅ Updated last expense · Ref: `{short_ref(updated.id)}`",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(),
    )

@router.message(StateFilter(None), F.text & ~F.text.startswith("/"))
async def add_free_text(message: Message, db: AsyncSession):
    """
    Plain text: "Pizza 12.50 #food #lunch"
    """
    parsed = parse_item_and_amount(message.text or "")
    if not parsed:
        return  # ignore non-expense messages for now

    item, cents = parsed
    hashtags = extract_hashtags(message.text or "")
    payment_method, hashtags = _extract_payment_method(hashtags)
    note = extract_note(message.text or "")
    cat_token, tags_csv = _split_category_and_tags(hashtags)

    category_name = None
    if cat_token:
        cs = CategoryService(db)
        cat = await cs.get_or_create(cat_token)
        category_name = cat.name
    if not category_name:
        from app.services.rule_service import RuleService
        rsvc = RuleService(db)
        suggested = await rsvc.suggest_category(message.from_user.id, item)
        if suggested:
            cs = CategoryService(db)
            cat = await cs.get_or_create(suggested)
            category_name = cat.name

    await _save_expense(message, db, item, cents, category_name, tags_csv, note, hashtags, payment_method)


@router.message(Command("split"))
async def split_expense(message: Message, db: AsyncSession):
    """
    Usage:
      /split Dinner Food:20,Transport:10 [pm:card]
    """
    payload = (message.text or "").partition(" ")[2].strip()
    if not payload:
        await message.answer("Usage: /split <item> <Category:Amount,Category:Amount> [pm:<method>]")
        return

    payment_method = None
    if " pm:" in payload:
        payload, payment_method = payload.rsplit(" pm:", 1)
        payment_method = payment_method.strip()

    parts = payload.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Usage: /split <item> <Category:Amount,Category:Amount> [pm:<method>]")
        return

    item, split_blob = parts
    entries = [x.strip() for x in split_blob.split(",") if x.strip()]
    if not entries:
        await message.answer("No split entries found.")
        return

    cs = CategoryService(db)
    created_refs = []
    for entry in entries:
        if ":" not in entry:
            await message.answer(f"Invalid split entry: {entry}")
            return
        cat_name, amount_text = entry.split(":", 1)
        try:
            cents = int((Decimal(amount_text.strip().replace(",", ".")) * 100).quantize(Decimal("1")))
        except (InvalidOperation, ValueError):
            await message.answer(f"Invalid amount in entry: {entry}")
            return

        cat = await cs.get_or_create(cat_name.strip())
        merchant = normalize_merchant(item)
        note = f"split:{item} | merchant:{merchant}"
        if payment_method:
            note += f" | pm:{payment_method}"

        svc = ExpenseService(db)
        exp = await svc.add_expense_text(
            user_id=message.from_user.id,
            item_name=item,
            amount_cents=cents,
            category=cat.name,
            tags="split",
            notes=note,
        )
        created_refs.append(short_ref(exp.id))

    await message.answer(
        f"✅ Split expense created ({len(created_refs)} entries). Refs: {', '.join(created_refs)}",
    )

@router.message(Command("settags"))
async def set_tags(message: Message, db: AsyncSession):
    """
    Usage: /settags <ref> tag1,tag2,tag3
    """
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /settags <ref> <tag1,tag2,...>")
        return

    _, expense_id, tags = parts
    svc = ExpenseService(db)
    updated = await svc.update_tags(expense_id=expense_id, user_id=message.from_user.id, tags=tags)
    if not updated:
        await message.answer("❌ Expense not found or not yours.")
        return

    await message.answer(f"✅ Tags updated for `{short_ref(updated.id)}` → {tags}", parse_mode="Markdown")


@router.message(Command("setnote"))
async def set_note(message: Message, db: AsyncSession):
    """
    Usage: /setnote <ref> some note text
    """
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /setnote <ref> <note text>")
        return

    _, expense_id, note = parts
    svc = ExpenseService(db)
    updated = await svc.update_note(expense_id=expense_id, user_id=message.from_user.id, note=note)
    if not updated:
        await message.answer("❌ Expense not found or not yours.")
        return

    await message.answer(f"✅ Note updated for `{short_ref(updated.id)}` → {note}", parse_mode="Markdown")