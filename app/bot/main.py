import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.bot.handlers.expenses import router as expenses_router
from app.bot.handlers.categories import router as categories_router
from app.bot.handlers.reports import router as reports_router
from app.bot.handlers.receipts import router as receipts_router


logger = setup_logging()

async def db_session_middleware(handler, event, data):
    async with SessionLocal() as session:
        data["db"] = session  # inject AsyncSession into handlers
        return await handler(event, data)

async def on_startup(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command="add", description="Add expense: /add <item> <amount> [#category] [#tag]"),
        BotCommand(command="categories", description="List categories"),
        BotCommand(command="setcategory", description="Set category for an expense"),
        BotCommand(command="month", description="Monthly report: /month [year month]"),
        BotCommand(command="year", description="Yearly report: /year [year]"),
        BotCommand(command="monthdetails", description="Month details by item/category"),
        BotCommand(command="yeardetails", description="Year details by item/category"),
        BotCommand(command="search", description="Search expenses"),
        BotCommand(command="receipt", description="Get receipt by expense_id"),
        BotCommand(command="receipt", description="Get receipt by expense_id"),

    ])
    logger.info("Bot commands set.")

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    bot = Bot(settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.update.middleware(db_session_middleware)

    dp.include_router(expenses_router)
    dp.include_router(categories_router)
    dp.include_router(reports_router)
    dp.include_router(receipts_router)


    await on_startup(bot)
    logger.info("🚀 Bot starting (long polling)...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
