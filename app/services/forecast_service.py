import numpy as np
from sqlalchemy import func, select, extract
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.db.models import Expense

class ForecastService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_monthly_totals(self, user_id: int, category: str | None = None):
        q = (
            select(
                extract("year", Expense.local_date).label("year"),
                extract("month", Expense.local_date).label("month"),
                func.sum(Expense.amount_cents).label("total_cents")
            )
            .where(Expense.user_id == user_id)
            .group_by("year", "month")
            .order_by("year", "month")
        )
        if category:
            q = q.where(Expense.category == category)

        res = await self.db.execute(q)
        rows = res.all()
        return [(int(r.year), int(r.month), r.total_cents) for r in rows]

    async def forecast_next_month(self, user_id: int, category: str | None = None):
        history = await self.get_monthly_totals(user_id, category)
        if len(history) < 3:
            return None  # not enough data

        # x = month index, y = totals
        y = np.array([v for (_, _, v) in history], dtype=float)
        x = np.arange(len(y))

        # simple linear regression (1st degree polyfit)
        slope, intercept = np.polyfit(x, y, 1)

        # forecast next point
        next_idx = len(y)
        forecast_cents = slope * next_idx + intercept

        trend = "📈 Increasing" if slope > 0 else ("📉 Decreasing" if slope < 0 else "➡️ Flat")

        # next period info
        last_year, last_month, _ = history[-1]
        next_year, next_month = (last_year + 1, 1) if last_month == 12 else (last_year, last_month + 1)

        return {
            "forecast_cents": max(0, int(forecast_cents)),
            "trend": trend,
            "next_year": next_year,
            "next_month": next_month,
            "history": history,
        }
