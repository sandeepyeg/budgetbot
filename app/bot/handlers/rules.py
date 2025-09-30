from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.rule_service import RuleService

router = Router(name="rules")

@router.message(Command("rules"))
async def rules_help(message: Message):
    await message.answer("Usage:\n"
                         "/rules_list – show your rules\n"
                         "/rules_add <keyword> <category> – add a rule\n"
                         "/rules_delete <id> – delete a rule")

@router.message(Command("rules_list"))
async def rules_list(message: Message, db: AsyncSession):
    svc = RuleService(db)
    rules = await svc.list_rules(message.from_user.id)
    if not rules:
        await message.answer("No personal rules defined. Global defaults still apply.")
        return
    lines = ["📌 Your category rules:"]
    for r in rules:
        lines.append(f"- {r.keyword} → {r.category} (id: {r.id})")
    await message.answer("\n".join(lines))

@router.message(Command("rules_add"))
async def rules_add(message: Message, db: AsyncSession):
    parts = message.text.split(maxsplit=3)
    if len(parts) < 3:
        await message.answer("Usage: /rules_add <keyword> <category>")
        return
    _, _, keyword, category = parts
    svc = RuleService(db)
    r = await svc.add_rule(message.from_user.id, keyword, category)
    await message.answer(f"✅ Rule added: {r.keyword} → {r.category} (id: {r.id})")

@router.message(Command("rules_delete"))
async def rules_delete(message: Message, db: AsyncSession):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /rules_delete <id>")
        return
    svc = RuleService(db)
    r = await svc.delete_rule(message.from_user.id, parts[1])
    await message.answer("✅ Deleted." if r else "❌ Not found.")
