from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.recurring_service import RecurringService
from app.bot.keyboards import main_menu_kb
from app.utils.text import short_ref

router = Router(name="recurring")

@router.message(Command("recurring"))
async def recurring_help(message: Message):
    await message.answer(
        "Recurring expense commands:\n"
        "/recurring_list → list active recurring\n"
        "/recurring_cancel <ref> → cancel permanently\n"
        "/recurring_pause <ref> → pause temporarily\n"
        "/recurring_resume <ref> → resume paused"
    , reply_markup=main_menu_kb())


@router.message(Command("recurring_list"))
async def recurring_list(message: Message, db: AsyncSession):
    svc = RecurringService(db)
    recs = await svc.list_all(message.from_user.id)
    if not recs:
        await message.answer("No recurring expenses.")
        return

    lines = ["📆 Recurring expenses:"]
    inline_rows: list[list[InlineKeyboardButton]] = []
    for r in recs:
        status = "⏸ Paused" if r.paused else ("✅ Active" if r.active else "❌ Cancelled")
        if r.frequency == "monthly":
            freq = f"monthly (day {r.day_of_month})"
        elif r.frequency == "weekly":
            freq = f"weekly (day {r.day_of_week})"
        else:
            freq = "daily"
        repeat = f" ×{r.remaining}" if r.remaining else (" ∞" if r.repeat_count is None else "")
        ref = short_ref(r.id)
        lines.append(
            f"- {r.item_name} ${r.amount_cents/100:.2f} "
            f"[{status}] — {freq}{repeat} (ref: {ref})"
        )
        row: list[InlineKeyboardButton] = []
        if r.active and not r.paused:
            row.append(InlineKeyboardButton(text=f"⏸ Pause {ref}", callback_data=f"recurring:pause:{ref}"))
        if r.active and r.paused:
            row.append(InlineKeyboardButton(text=f"▶️ Resume {ref}", callback_data=f"recurring:resume:{ref}"))
        row.append(InlineKeyboardButton(text=f"❌ Cancel {ref}", callback_data=f"recurring:cancel:{ref}"))
        inline_rows.append(row)

    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_rows))


@router.callback_query(F.data.regexp(r"^recurring:(pause|resume|cancel):[A-Za-z0-9]+$"))
async def recurring_quick_action(callback: CallbackQuery, db: AsyncSession):
    _, action, ref = callback.data.split(":", 2)
    svc = RecurringService(db)

    if action == "pause":
        rec = await svc.update_state(ref, callback.from_user.id, paused=True)
        if rec:
            await callback.answer("Paused")
            await callback.message.answer("⏸ Recurring expense paused.", reply_markup=main_menu_kb())
        else:
            await callback.answer("Not found", show_alert=True)
        return

    if action == "resume":
        rec = await svc.update_state(ref, callback.from_user.id, paused=False)
        if rec:
            await callback.answer("Resumed")
            await callback.message.answer("▶️ Recurring expense resumed.", reply_markup=main_menu_kb())
        else:
            await callback.answer("Not found", show_alert=True)
        return

    rec = await svc.update_state(ref, callback.from_user.id, active=False)
    if rec:
        await callback.answer("Cancelled")
        await callback.message.answer("❌ Recurring expense cancelled.", reply_markup=main_menu_kb())
    else:
        await callback.answer("Not found", show_alert=True)


@router.message(Command("recurring_cancel"))
async def recurring_cancel(message: Message, db: AsyncSession):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /recurring_cancel <ref>")
        return
    svc = RecurringService(db)
    rec = await svc.update_state(parts[1], message.from_user.id, active=False)
    await message.answer("❌ Cancelled." if rec else "Not found.", reply_markup=main_menu_kb())


@router.message(Command("recurring_pause"))
async def recurring_pause(message: Message, db: AsyncSession):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /recurring_pause <ref>")
        return
    svc = RecurringService(db)
    rec = await svc.update_state(parts[1], message.from_user.id, paused=True)
    await message.answer("⏸ Paused." if rec else "Not found.", reply_markup=main_menu_kb())


@router.message(Command("recurring_resume"))
async def recurring_resume(message: Message, db: AsyncSession):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /recurring_resume <ref>")
        return
    svc = RecurringService(db)
    rec = await svc.update_state(parts[1], message.from_user.id, paused=False)
    await message.answer("▶️ Resumed." if rec else "Not found.", reply_markup=main_menu_kb())
