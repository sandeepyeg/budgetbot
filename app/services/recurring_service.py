from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import RecurringExpense, Expense
from app.utils.dates import local_date_for_now
from datetime import datetime, timezone, date
import uuid

class RecurringService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_recurring_id(self, user_id: int, recurring_ref: str) -> str | None:
        ref = (recurring_ref or "").strip()
        if not ref:
            return None
        if len(ref) >= 36:
            q = select(RecurringExpense.id).where(RecurringExpense.id == ref, RecurringExpense.user_id == user_id)
            res = await self.db.execute(q)
            return res.scalar_one_or_none()

        q = (
            select(RecurringExpense.id)
            .where(RecurringExpense.user_id == user_id, RecurringExpense.id.like(f"{ref}%"))
            .order_by(RecurringExpense.created_at_utc.desc())
            .limit(2)
        )
        res = await self.db.execute(q)
        rows = res.scalars().all()
        if len(rows) != 1:
            return None
        return rows[0]

    async def create(self, user_id: int, item_name: str, amount_cents: int, *,
                     currency="CAD", category=None, tags=None, notes=None,
                     frequency="monthly", day_of_month=None, day_of_week=None,
                     repeat_count=None) -> RecurringExpense:
        today = local_date_for_now()
        if frequency == "monthly" and day_of_month is None:
            day_of_month = today.day
        if frequency == "weekly" and day_of_week is None:
            day_of_week = today.weekday()

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

    def _is_due_today(self, rec: RecurringExpense, today: date) -> bool:
        if not rec.active or rec.paused:
            return False
        if rec.frequency == "daily":
            return True
        if rec.frequency == "weekly":
            due_weekday = rec.day_of_week if rec.day_of_week is not None else today.weekday()
            return today.weekday() == due_weekday
        if rec.frequency == "monthly":
            due_day = rec.day_of_month if rec.day_of_month is not None else today.day
            return today.day == due_day
        return False

    async def list_all(self, user_id: int):
        q = select(RecurringExpense).where(
            RecurringExpense.user_id == user_id
        ).order_by(RecurringExpense.created_at_utc.desc())
        res = await self.db.execute(q)
        return list(res.scalars().all())

    async def update_state(self, recurring_id: str, user_id: int, *, active=None, paused=None):
        resolved_id = await self.resolve_recurring_id(user_id, recurring_id)
        if not resolved_id:
            return None
        q = select(RecurringExpense).where(
            RecurringExpense.id == resolved_id,
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

    async def generate_due_today(self) -> list[Expense]:
        today = local_date_for_now()
        q = select(RecurringExpense).where(
            RecurringExpense.active == True,
            RecurringExpense.paused == False,
        )
        res = await self.db.execute(q)
        recs = list(res.scalars().all())

        created: list[Expense] = []
        for rec in recs:
            if not self._is_due_today(rec, today):
                continue

            exists_q = select(Expense.id).where(
                Expense.recurring_id == rec.id,
                Expense.local_date == today,
            )
            exists_res = await self.db.execute(exists_q)
            if exists_res.scalar_one_or_none():
                continue

            exp = await self.generate_expense(rec)
            created.append(exp)

        return created
