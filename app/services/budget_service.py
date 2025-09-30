from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid

from app.db.models import Budget
from app.services.expense_service import ExpenseService

class BudgetService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_budget(self, user_id: int, scope_type: str, scope_value: str | None,
                         limit_cents: int, period: str) -> Budget:
        b = Budget(
            id=str(uuid.uuid4()),
            user_id=user_id,
            scope_type=scope_type,
            scope_value=scope_value,
            limit_cents=limit_cents,
            period=period,
            active=True,
        )
        self.db.add(b)
        await self.db.commit()
        await self.db.refresh(b)
        return b

    async def list_budgets(self, user_id: int):
        q = select(Budget).where(Budget.user_id == user_id, Budget.active == True)
        res = await self.db.execute(q)
        return list(res.scalars().all())

    async def delete_budget(self, budget_id: str, user_id: int):
        q = select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
        res = await self.db.execute(q)
        b = res.scalar_one_or_none()
        if not b:
            return None
        b.active = False
        await self.db.commit()
        return b

    async def check_alerts(self, user_id: int, expense_service: ExpenseService):
        """
        Check if any budgets are exceeded or near threshold.
        Returns list of alert strings.
        """
        now = datetime.now()
        year, month = now.year, now.month
        alerts = []

        budgets = await self.list_budgets(user_id)
        for b in budgets:
            if b.period == "month":
                totals = await expense_service.monthly_summary(user_id, year, month)
                total = totals["total_cents"] if b.scope_type == "overall" else totals["breakdown"].get(b.scope_value, 0)
            else:  # yearly
                totals = await expense_service.yearly_summary(user_id, year)
                total = totals["total_cents"] if b.scope_type == "overall" else totals["breakdown"].get(b.scope_value, 0)

            pct = (total / b.limit_cents * 100) if b.limit_cents > 0 else None
            if pct and 80 <= pct < 100:
                alerts.append(f"⚠️ {b.scope_value or 'Overall'} budget at {pct:.0f}% (${total/100:.2f}/${b.limit_cents/100:.2f})")
            elif pct and pct >= 100:
                alerts.append(f"🚨 {b.scope_value or 'Overall'} budget exceeded! (${total/100:.2f}/${b.limit_cents/100:.2f})")

        return alerts
