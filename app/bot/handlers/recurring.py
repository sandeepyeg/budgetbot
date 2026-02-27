from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.recurring_service import RecurringService
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
    )


@router.message(Command("recurring_list"))
async def recurring_list(message: Message, db: AsyncSession):
    svc = RecurringService(db)
    recs = await svc.list_all(message.from_user.id)
    if not recs:
        await message.answer("No recurring expenses.")
        return

    lines = ["📆 Recurring expenses:"]
    for r in recs:
        status = "⏸ Paused" if r.paused else ("✅ Active" if r.active else "❌ Cancelled")
        if r.frequency == "monthly":
            freq = f"monthly (day {r.day_of_month})"
        elif r.frequency == "weekly":
            freq = f"weekly (day {r.day_of_week})"
        else:
            freq = "daily"
        repeat = f" ×{r.remaining}" if r.remaining else (" ∞" if r.repeat_count is None else "")
        lines.append(
            f"- {r.item_name} ${r.amount_cents/100:.2f} "
            f"[{status}] — {freq}{repeat} (ref: {short_ref(r.id)})"
        )

    await message.answer("\n".join(lines))


@router.message(Command("recurring_cancel"))
async def recurring_cancel(message: Message, db: AsyncSession):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /recurring_cancel <ref>")
        return
    svc = RecurringService(db)
    rec = await svc.update_state(parts[1], message.from_user.id, active=False)
    await message.answer("❌ Cancelled." if rec else "Not found.")


@router.message(Command("recurring_pause"))
async def recurring_pause(message: Message, db: AsyncSession):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /recurring_pause <ref>")
        return
    svc = RecurringService(db)
    rec = await svc.update_state(parts[1], message.from_user.id, paused=True)
    await message.answer("⏸ Paused." if rec else "Not found.")


@router.message(Command("recurring_resume"))
async def recurring_resume(message: Message, db: AsyncSession):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /recurring_resume <ref>")
        return
    svc = RecurringService(db)
    rec = await svc.update_state(parts[1], message.from_user.id, paused=False)
    await message.answer("▶️ Resumed." if rec else "Not found.")
