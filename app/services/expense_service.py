from datetime import datetime, timezone
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Expense
from app.utils.dates import local_date_for_now

class ExpenseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_expense_text(self, *, user_id: int, item_name: str, amount_cents: int,
                               currency: str = "CAD", category: str | None = None,
                               tags: str | None = None, notes: str | None = None) -> Expense:
        exp = Expense(
            user_id=user_id,
            item_name=item_name[:200],
            amount_cents=amount_cents,
            currency=currency,
            category=category,
            tags=tags,
            notes=notes,
            created_at_utc=datetime.now(timezone.utc),
            local_date=local_date_for_now(),
        )
        self.db.add(exp)
        await self.db.commit()
        await self.db.refresh(exp)
        return exp

    async def get_expense(self, expense_id: str) -> Expense | None:
        q = select(Expense).where(Expense.id == expense_id)
        res = await self.db.execute(q)
        return res.scalar_one_or_none()

    async def update_category(self, *, expense_id: str, user_id: int, category_name: str | None):
        # Ensure ownership
        q = select(Expense).where(Expense.id == expense_id, Expense.user_id == user_id)
        res = await self.db.execute(q)
        exp = res.scalar_one_or_none()
        if not exp:
            return None

        exp.category = category_name
        await self.db.commit()
        await self.db.refresh(exp)
        return exp

    async def monthly_summary(self, user_id: int, year: int, month: int):
        """
        Returns total + breakdown by category for given user, year, month.
        """
        q = (
            select(
                func.sum(Expense.amount_cents).label("total_cents"),
                Expense.category,
                func.sum(Expense.amount_cents).label("cat_total_cents"),
            )
            .where(
                Expense.user_id == user_id,
                func.strftime("%Y", Expense.local_date) == str(year),
                func.strftime("%m", Expense.local_date) == f"{month:02d}",
            )
            .group_by(Expense.category)
        )
        res = await self.db.execute(q)
        rows = res.all()

        total = sum([row.cat_total_cents or 0 for row in rows]) if rows else 0
        breakdown = {row.category or "Uncategorized": row.cat_total_cents for row in rows}

        return {
            "year": year,
            "month": month,
            "total_cents": total,
            "breakdown": breakdown,
        }