from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.expense_service import ExpenseService
from app.core.storage import generate_receipt_path

router = Router(name="receipts")

@router.message(F.photo)
async def handle_receipt_photo(message: Message, db: AsyncSession):
    """
    User sends a photo with a caption like:
      /receipt <expense_id>
    The photo gets stored and linked to the expense.
    """
    if not message.caption or not message.caption.startswith("/receipt"):
        # Ignore photos that aren't for receipts
        return

    parts = message.caption.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: send photo with caption `/receipt <expense_id>`", parse_mode="Markdown")
        return

    expense_id = parts[1].strip()
    if not expense_id:
        await message.answer("Usage: /receipt <expense_id>")
        return

    photo = message.photo[-1]  # highest resolution
    file = await message.bot.get_file(photo.file_id)
    file_ext = ".jpg"
    local_path = generate_receipt_path(message.from_user.id, expense_id, file_ext)
    await message.bot.download_file(file.file_path, destination=local_path)

    svc = ExpenseService(db)
    updated = await svc.attach_receipt(expense_id, message.from_user.id, str(local_path))
    if not updated:
        await message.answer("❌ Expense not found or not yours.")
        return

    await message.answer(f"✅ Receipt saved for expense `{expense_id}`", parse_mode="Markdown")
