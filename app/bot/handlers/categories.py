from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.category_service import CategoryService
from app.services.expense_service import ExpenseService

router = Router(name="categories")

@router.message(Command("categories"))
async def list_categories(message: Message, db: AsyncSession):
    cs = CategoryService(db)
    cats = await cs.list_all()
    if not cats:
        await message.answer("No categories yet. Add one by tagging: #food (on /add).")
        return
    names = ", ".join([c.name for c in cats])
    await message.answer(f"📚 *Categories*:\n{names}", parse_mode="Markdown")

@router.message(Command("setcategory"))
async def set_category(message: Message, db: AsyncSession):
    """
    Usage: /setcategory <expense_id> <category>
    """
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /setcategory <expense_id> <category>\nExample: /setcategory abcd-1234 Food")
        return

    _, expense_id, cat_name = parts
    cs = CategoryService(db)
    cat = await cs.get_or_create(cat_name)
    es = ExpenseService(db)
    updated = await es.update_category(expense_id=expense_id, user_id=message.from_user.id, category_name=cat.name)
    if not updated:
        await message.answer("Expense not found or not yours.")
        return

    await message.answer(f"✅ Category set to *{cat.name}* for `{expense_id}`", parse_mode="Markdown")
