import asyncio
import contextlib
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from sqlalchemy import select
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.db.models import Expense, Budget, RecurringExpense
from app.bot.handlers.expenses import router as expenses_router
from app.bot.handlers.categories import router as categories_router
from app.bot.handlers.reports import router as reports_router
from app.bot.handlers.receipts import router as receipts_router
from app.bot.handlers.budgets import router as budgets_router
from app.bot.handlers.rules import router as rules_router
from app.bot.handlers.nlp import router as nlp_router
from app.bot.handlers.forecast import router as forecast_router
from app.bot.handlers.recurring import router as recurring_router
from app.bot.handlers.start import router as start_router
from app.services.recurring_service import RecurringService
from app.services.expense_service import ExpenseService
from app.services.budget_service import BudgetService
from app.utils.dates import local_date_for_now


logger = setup_logging()

_sent_weekly_digest: set[tuple[int, int, int]] = set()

async def db_session_middleware(handler, event, data):
    async with SessionLocal() as session:
        data["db"] = session  # inject AsyncSession into handlers
        return await handler(event, data)

async def on_startup(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command="start", description="Start and quick actions"),
        BotCommand(command="menu", description="Show main menu keyboard"),
        BotCommand(command="add", description="Add expense: /add <item> <amount> [#category] [#tag]"),
        BotCommand(command="split", description="Split expense: /split <item> <Cat:Amt,...> [pm:method]"),
        BotCommand(command="undo", description="Undo last expense"),
        BotCommand(command="edit_last", description="Edit last expense"),
        BotCommand(command="categories", description="List categories"),
        BotCommand(command="setcategory", description="Set category for an expense"),
        BotCommand(command="month", description="Monthly report: /month [year month]"),
        BotCommand(command="year", description="Yearly report: /year [year]"),
        BotCommand(command="monthdetails", description="Month details by item/category"),
        BotCommand(command="yeardetails", description="Year details by item/category"),
        BotCommand(command="search", description="Search expenses"),
        BotCommand(command="receipt", description="Get receipt by expense_id"),
        BotCommand(command="export", description="Export expenses as CSV/Excel"),
        BotCommand(command="recurring", description="Recurring help"),
        BotCommand(command="recurring_list", description="List recurring"),
        BotCommand(command="recurring_cancel", description="Cancel recurring"),
        BotCommand(command="recurring_pause", description="Pause recurring"),
        BotCommand(command="recurring_resume", description="Resume recurring"),
        BotCommand(command="compare", description="Compare expenses (month/year)"),
        BotCommand(command="chart", description="Charts: month, year, yeartrend"),
        BotCommand(command="budget", description="Budget help"),
        BotCommand(command="budget_add", description="Add a budget"),
        BotCommand(command="budget_list", description="List budgets"),
        BotCommand(command="budget_delete", description="Delete a budget"),
        BotCommand(command="rules", description="Rules help"),
        BotCommand(command="rules_list", description="List your rules"),
        BotCommand(command="rules_add", description="Add a keyword rule"),
        BotCommand(command="rules_delete", description="Delete a rule"),
        BotCommand(command="ask", description="Ask natural language queries"),
        BotCommand(command="forecast", description="Forecast next month’s expenses"),
    ])
    logger.info("Bot commands set.")


async def _all_user_ids(session) -> list[int]:
    users: set[int] = set()
    for model in (Expense, Budget, RecurringExpense):
        res = await session.execute(select(model.user_id).distinct())
        users.update([r for r in res.scalars().all() if r is not None])
    return list(users)


async def _background_worker(bot: Bot):
    while True:
        try:
            async with SessionLocal() as session:
                rsvc = RecurringService(session)
                created = await rsvc.generate_due_today()
                for exp in created:
                    try:
                        await bot.send_message(
                            exp.user_id,
                            f"🔁 Recurring expense added: {exp.item_name} ${exp.amount_cents/100:.2f}",
                        )
                    except Exception:
                        logger.exception("Failed to notify user for recurring expense")

                today = local_date_for_now()
                iso = today.isocalendar()
                if today.weekday() == 0:
                    user_ids = await _all_user_ids(session)
                    for uid in user_ids:
                        key = (uid, iso.year, iso.week)
                        if key in _sent_weekly_digest:
                            continue

                        es = ExpenseService(session)
                        summary = await es.week_summary(uid, iso.year, iso.week)
                        total = summary.get("total_cents", 0)
                        if total <= 0:
                            _sent_weekly_digest.add(key)
                            continue

                        lines = [f"📬 Weekly Digest (Week {iso.week}, {iso.year})"]
                        lines.append(f"💰 Total: ${total/100:.2f}")
                        for cat, cents in summary.get("breakdown", {}).items():
                            lines.append(f"- {cat}: ${((cents or 0)/100):.2f}")

                        bsvc = BudgetService(session)
                        alerts = await bsvc.check_alerts(uid, es)
                        if alerts:
                            lines.append("\nBudget Alerts:")
                            lines.extend(alerts)

                        try:
                            await bot.send_message(uid, "\n".join(lines))
                        except Exception:
                            logger.exception("Failed to send weekly digest")

                        _sent_weekly_digest.add(key)
        except Exception:
            logger.exception("Background worker error")

        await asyncio.sleep(60)

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    bot = Bot(settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.update.middleware(db_session_middleware)

    dp.include_router(start_router)
    dp.include_router(expenses_router)
    dp.include_router(categories_router)
    dp.include_router(reports_router)
    dp.include_router(receipts_router)
    dp.include_router(budgets_router)
    dp.include_router(nlp_router)
    dp.include_router(rules_router)
    dp.include_router(forecast_router)
    dp.include_router(recurring_router)


    await on_startup(bot)
    worker_task = asyncio.create_task(_background_worker(bot))
    logger.info("🚀 Bot starting (long polling)...")
    try:
        await dp.start_polling(bot)
    finally:
        worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker_task

if __name__ == "__main__":
    asyncio.run(main())
