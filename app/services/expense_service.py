from datetime import datetime, timezone
from sqlalchemy import select, update
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
