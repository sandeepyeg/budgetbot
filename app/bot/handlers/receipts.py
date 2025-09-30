from aiogram import Router, F
from aiogram.types import Message
from app.services.budget_service import BudgetService
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.expense_service import ExpenseService
from app.services.category_service import CategoryService
from app.utils.parser import parse_item_and_amount, extract_hashtags
from app.core.storage import generate_receipt_path, optimize_and_save
import tempfile
import os
from pathlib import Path

router = Router(name="receipts")

@router.message(F.photo)
async def add_expense_with_receipt(message: Message, db: AsyncSession):
    """
    User sends a photo with caption like:
      "Pizza 12.50 #food #lunch"
    → bot adds expense + stores optimized receipt
    """
    if not message.caption:
        await message.answer("Please add a caption with item and amount, e.g.: 'Pizza 12.50 #food'")
        return

    parsed = parse_item_and_amount(message.caption)
    if not parsed:
        await message.answer("Couldn't parse caption. Use: '<item> <amount> [#category] [#tags]'")
        return

    item, cents = parsed
    hashtags = extract_hashtags(message.caption)
    cat_token = hashtags[0] if hashtags else None
    tags_csv = ",".join(hashtags[1:]) if len(hashtags) > 1 else None

    category_name = None
    if cat_token:
        cs = CategoryService(db)
        cat = await cs.get_or_create(cat_token)
        category_name = cat.name

    svc = ExpenseService(db)
    exp = await svc.add_expense_text(
        user_id=message.from_user.id,
        item_name=item,
        amount_cents=cents,
        category=category_name,
        tags=tags_csv
    )
    bsvc = BudgetService(db)
    alerts = await bsvc.check_alerts(message.from_user.id, svc)
    for alert in alerts:
        await message.answer(alert)

    # --- Receipt handling ---
    photo = message.photo[-1]  # highest resolution
    file = await message.bot.get_file(photo.file_id)

    # Download temp file first
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    await message.bot.download_file(file.file_path, destination=tmp_file.name)

    # Optimize + save to final path
    final_path = generate_receipt_path(message.from_user.id, exp.id, ".jpg")
    optimize_and_save(Path(tmp_file.name), final_path)
    os.unlink(tmp_file.name)  # clean temp

    # Attach to expense
    await svc.attach_receipt(exp.id, message.from_user.id, str(final_path))

    dollars = cents / 100
    suffix = f" · 🏷 {category_name}" if category_name else ""
    tags_suffix = f" · #{tags_csv.replace(',', ' #')}" if tags_csv else ""
    await message.answer(
        f"✅ Added: *{item}* — ${dollars:.2f}{suffix}{tags_suffix}\n📎 Receipt saved\n`{exp.id}`",
        parse_mode="Markdown"
    )
