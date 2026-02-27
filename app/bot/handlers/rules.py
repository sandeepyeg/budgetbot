from aiogram import Router, F
import contextlib
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.rule_service import RuleService
from app.bot.keyboards import main_menu_kb
from app.utils.text import short_ref

router = Router(name="rules")


class RuleFlow(StatesGroup):
    action = State()
    keyword = State()
    category = State()
    delete_ref = State()


def _rules_action_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Add Rule"), KeyboardButton(text="📋 List Rules")],
            [KeyboardButton(text="🗑 Delete Rule"), KeyboardButton(text="❌ Cancel")],
        ],
        resize_keyboard=True,
    )

@router.message(Command("rules"))
async def rules_help(message: Message, state: FSMContext):
    await state.set_state(RuleFlow.action)
    await message.answer(
        "Rule actions:\nChoose one below or use slash commands (/rules_add, /rules_list, /rules_delete).",
        reply_markup=_rules_action_kb(),
    )


@router.message(RuleFlow.action)
async def rules_action(message: Message, db: AsyncSession, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=main_menu_kb())
        return
    if text == "📋 List Rules":
        await state.clear()
        await rules_list(message, db)
        return
    if text == "➕ Add Rule":
        await state.set_state(RuleFlow.keyword)
        await message.answer("Enter keyword to match (e.g., uber)", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Cancel")]], resize_keyboard=True))
        return
    if text == "🗑 Delete Rule":
        await state.set_state(RuleFlow.delete_ref)
        await message.answer("Send rule ref (short id from list)", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Cancel")]], resize_keyboard=True))
        return
    await message.answer("Choose a valid action.")


@router.message(RuleFlow.keyword)
async def rules_keyword(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=main_menu_kb())
        return
    await state.update_data(keyword=text)
    await state.set_state(RuleFlow.category)
    await message.answer("Enter category for this keyword", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Cancel")]], resize_keyboard=True))


@router.message(RuleFlow.category)
async def rules_category(message: Message, db: AsyncSession, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=main_menu_kb())
        return
    data = await state.get_data()
    svc = RuleService(db)
    r = await svc.add_rule(message.from_user.id, data.get("keyword", ""), text)
    await state.clear()
    await message.answer(
        f"✅ Rule added: {r.keyword} → {r.category} (ref: `{short_ref(r.id)}`)",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(),
    )


@router.message(RuleFlow.delete_ref)
async def rules_delete_ref(message: Message, db: AsyncSession, state: FSMContext):
    text = (message.text or "").strip()
    if text == "❌ Cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=main_menu_kb())
        return
    svc = RuleService(db)
    r = await svc.delete_rule(message.from_user.id, text)
    await state.clear()
    await message.answer("✅ Deleted." if r else "❌ Not found or ambiguous ref.", reply_markup=main_menu_kb())

@router.message(Command("rules_list"))
async def rules_list(message: Message, db: AsyncSession):
    svc = RuleService(db)
    rules = await svc.list_rules(message.from_user.id)
    if not rules:
        await message.answer("No personal rules defined. Global defaults still apply.")
        return
    lines = ["📌 Your category rules:"]
    inline_rows: list[list[InlineKeyboardButton]] = []
    for r in rules:
        ref = short_ref(r.id)
        lines.append(f"- {r.keyword} → {r.category} (ref: {ref})")
        inline_rows.append([
            InlineKeyboardButton(text=f"🗑 Delete {ref}", callback_data=f"rule:delete:{ref}")
        ])
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_rows))


@router.callback_query(F.data.regexp(r"^rule:delete:[A-Za-z0-9]+$"))
async def rules_delete_quick(callback: CallbackQuery, db: AsyncSession):
    ref = callback.data.split(":", 2)[2]
    svc = RuleService(db)
    deleted = await svc.delete_rule(callback.from_user.id, ref)
    if deleted:
        with contextlib.suppress(Exception):
            await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer("✅ Rule deleted")
    else:
        await callback.answer("Rule not found", show_alert=True)

@router.message(Command("rules_add"))
async def rules_add(message: Message, db: AsyncSession):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /rules_add <keyword> <category>")
        return
    _, keyword, category = parts
    svc = RuleService(db)
    r = await svc.add_rule(message.from_user.id, keyword, category)
    await message.answer(f"✅ Rule added: {r.keyword} → {r.category} (ref: `{short_ref(r.id)}`)", parse_mode="Markdown")

@router.message(Command("rules_delete"))
async def rules_delete(message: Message, db: AsyncSession):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /rules_delete <ref>")
        return
    svc = RuleService(db)
    r = await svc.delete_rule(message.from_user.id, parts[1])
    await message.answer("✅ Deleted." if r else "❌ Not found or ambiguous ref.")
