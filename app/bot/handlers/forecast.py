from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.forecast_service import ForecastService

router = Router(name="forecast")

@router.message(Command("forecast"))
async def forecast_expenses(message: Message, db: AsyncSession):
    """
    Usage:
      /forecast           → overall forecast
      /forecast Food      → forecast for category
    """
    parts = message.text.split(maxsplit=1)
    category = parts[1] if len(parts) == 2 else None

    svc = ForecastService(db)
    result = await svc.forecast_next_month(message.from_user.id, category)

    if not result:
        await message.answer("Not enough data for forecasting (need at least 3 months).")
        return

    dollars = result["forecast_cents"] / 100
    cat_label = f" in {category}" if category else ""
    await message.answer(
        f"🔮 Forecast for {result['next_year']}-{result['next_month']:02d}{cat_label}:\n"
        f"≈ ${dollars:.2f}\n"
        f"Trend: {result['trend']}"
    )
