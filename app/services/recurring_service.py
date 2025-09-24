from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import RecurringExpense, Expense
from app.utils.dates import local_date_for_now
from datetime import datetime, timezone
import uuid

class RecurringService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, item_name: str, amount_cents: int, *,
                     currency="CAD", category=None, tags=None, notes=None,
                     frequency="monthly", day_of_month=None, day_of_week=None,
                     repeat_count=None) -> RecurringExpense:
        rec = RecurringExpense(
            id=str(uuid.uuid4()),
            user_id=user_id,
            item_name=item_name,
            amount_cents=amount_cents,
            currency=currency,
            category=category,
            tags=tags,
            notes=notes,
            frequency=frequency,
            day_of_month=day_of_month,
            day_of_week=day_of_week,
            repeat_count=repeat_count,
            remaining=repeat_count,
            active=True,
            paused=False,
        )
        self.db.add(rec)
        await self.db.commit()
        await self.db.refresh(rec)
        return rec

    async def list_all(self, user_id: int):
        q = select(RecurringExpense).where(
            RecurringExpense.user_id == user_id
        ).order_by(RecurringExpense.created_at_utc.desc())
        res = await self.db.execute(q)
        return list(res.scalars().all())

    async def update_state(self, recurring_id: str, user_id: int, *, active=None, paused=None):
        q = select(RecurringExpense).where(
            RecurringExpense.id == recurring_id,
            RecurringExpense.user_id == user_id
        )
        res = await self.db.execute(q)
        rec = res.scalar_one_or_none()
        if not rec:
            return None
        if active is not None:
            rec.active = active
        if paused is not None:
            rec.paused = paused
        await self.db.commit()
        await self.db.refresh(rec)
        return rec

    async def generate_expense(self, rec: RecurringExpense) -> Expense:
        exp = Expense(
            user_id=rec.user_id,
            item_name=rec.item_name,
            amount_cents=rec.amount_cents,
            currency=rec.currency,
            category=rec.category,
            tags=rec.tags,
            notes=rec.notes,
            created_at_utc=datetime.now(timezone.utc),
            local_date=local_date_for_now(),
            recurring_id=rec.id,
        )
        self.db.add(exp)

        if rec.remaining is not None and rec.remaining > 0:
            rec.remaining -= 1
            if rec.remaining == 0:
                rec.active = False

        await self.db.commit()
        await self.db.refresh(exp)
        return exp
