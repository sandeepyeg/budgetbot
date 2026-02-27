from datetime import datetime, timezone
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Expense
from app.utils.dates import local_date_for_now
import pandas as pd

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
                extract("year", Expense.local_date) == year,
                extract("month", Expense.local_date) == month,
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
    
    async def yearly_summary(self, user_id: int, year: int):
        """
        Returns yearly total + breakdown by category + per-month totals.
        """
        # Category breakdown
        q_cat = (
            select(
                Expense.category,
                func.sum(Expense.amount_cents).label("cat_total_cents"),
            )
            .where(extract("year", Expense.local_date) == year,
                   Expense.user_id == user_id)
            .group_by(Expense.category)
        )
        res_cat = await self.db.execute(q_cat)
        cat_rows = res_cat.all()

        breakdown = {row.category or "Uncategorized": row.cat_total_cents for row in cat_rows}
        total = sum([row.cat_total_cents or 0 for row in cat_rows])

        # Per-month totals
        q_months = (
            select(
                extract("month", Expense.local_date).label("month"),
                func.sum(Expense.amount_cents).label("month_total_cents"),
            )
            .where(extract("year", Expense.local_date) == year,
                   Expense.user_id == user_id)
            .group_by("month")
            .order_by("month")
        )
        res_months = await self.db.execute(q_months)
        month_rows = res_months.all()
        per_month = {int(row.month): row.month_total_cents for row in month_rows}

        return {
            "year": year,
            "total_cents": total,
            "breakdown": breakdown,
            "per_month": per_month,
        }
    
    async def monthly_details(self, user_id: int, year: int, month: int, group_by: str = "item"):
        """
        Return detailed breakdown for a month.
        group_by = "item" → group by item_name
        group_by = "category" → group by category
        """
        col = Expense.item_name if group_by == "item" else Expense.category
        q = (
            select(col.label("key"), func.sum(Expense.amount_cents).label("total_cents"))
            .where(
                extract("year", Expense.local_date) == year,
                extract("month", Expense.local_date) == month,
                Expense.user_id == user_id,
            )
            .group_by(col)
            .order_by(func.sum(Expense.amount_cents).desc())
        )
        res = await self.db.execute(q)
        rows = res.all()
        return rows

    async def yearly_details(self, user_id: int, year: int, group_by: str = "item"):
        col = Expense.item_name if group_by == "item" else Expense.category
        q = (
            select(col.label("key"), func.sum(Expense.amount_cents).label("total_cents"))
            .where(
                extract("year", Expense.local_date) == year,
                Expense.user_id == user_id,
            )
            .group_by(col)
            .order_by(func.sum(Expense.amount_cents).desc())
        )
        res = await self.db.execute(q)
        rows = res.all()
        return rows
    
    async def search_expenses(self, user_id: int, query: str, limit: int = 10):
        """
        Simple keyword search across item_name, category, tags, and notes.
        Returns up to `limit` results sorted by most recent.
        """
        pattern = f"%{query.lower()}%"
        q = (
            select(Expense)
            .where(
                Expense.user_id == user_id,
                (
                    func.lower(Expense.item_name).like(pattern) |
                    func.lower(Expense.category).like(pattern) |
                    func.lower(Expense.tags).like(pattern) |
                    func.lower(Expense.notes).like(pattern)
                )
            )
            .order_by(Expense.created_at_utc.desc())
            .limit(limit)
        )
        res = await self.db.execute(q)
        return list(res.scalars().all())
    
    async def attach_receipt(self, expense_id: str, user_id: int, file_path: str):
        """
        Attach a receipt (file path) to an existing expense.
        """
        q = select(Expense).where(Expense.id == expense_id, Expense.user_id == user_id)
        res = await self.db.execute(q)
        exp = res.scalar_one_or_none()
        if not exp:
            return None

        exp.receipt_path = file_path
        await self.db.commit()
        await self.db.refresh(exp)
        return exp
    
    async def update_tags(self, *, expense_id: str, user_id: int, tags: str):
        q = select(Expense).where(Expense.id == expense_id, Expense.user_id == user_id)
        res = await self.db.execute(q)
        exp = res.scalar_one_or_none()
        if not exp:
            return None
        exp.tags = tags
        await self.db.commit()
        await self.db.refresh(exp)
        return exp

    async def update_note(self, *, expense_id: str, user_id: int, note: str):
        q = select(Expense).where(Expense.id == expense_id, Expense.user_id == user_id)
        res = await self.db.execute(q)
        exp = res.scalar_one_or_none()
        if not exp:
            return None
        exp.notes = note
        await self.db.commit()
        await self.db.refresh(exp)
        return exp
    
    async def export_expenses(self, user_id: int, year: int | None = None, month: int | None = None):
        """
        Return a Pandas DataFrame of expenses for export.
        """
        q = select(Expense).where(Expense.user_id == user_id)
        if year:
            q = q.where(extract("year", Expense.local_date) == year)
        if month:
            q = q.where(extract("month", Expense.local_date) == month)

        q = q.order_by(Expense.local_date.asc())
        res = await self.db.execute(q)
        rows = res.scalars().all()

        if not rows:
            return None

        data = []
        for e in rows:
            data.append({
                "ID": e.id,
                "Date": e.local_date.isoformat(),
                "Item": e.item_name,
                "Amount": f"{e.amount_cents/100:.2f} {e.currency}",
                "Category": e.category or "",
                "Tags": e.tags or "",
                "Notes": e.notes or "",
                "Receipt": e.receipt_path or "",
            })
        df = pd.DataFrame(data)
        return df
    
    async def totals_for_period(self, user_id: int, year: int, month: int | None = None):
        """
        Return total + breakdown for a given period (month OR year).
        """
        q = select(
            func.sum(Expense.amount_cents).label("total_cents"),
            Expense.category,
            func.sum(Expense.amount_cents).label("cat_total_cents"),
        ).where(Expense.user_id == user_id)

        if month:
            q = q.where(
                extract("year", Expense.local_date) == year,
                extract("month", Expense.local_date) == month
            )
        else:
            q = q.where(extract("year", Expense.local_date) == year)

        q = q.group_by(Expense.category)
        res = await self.db.execute(q)
        rows = res.all()

        total = sum([r.cat_total_cents or 0 for r in rows]) if rows else 0
        breakdown = {r.category or "Uncategorized": r.cat_total_cents for r in rows}
        return {"total": total, "breakdown": breakdown}
    
    def compare_periods(self, current: dict, previous: dict):
        """
        Compare two periods (both dicts from totals_for_period).
        Returns difference totals and per-category changes.
        """
        result = {}
        cur_total, prev_total = current["total"], previous["total"]
        result["total"] = {
            "current": cur_total,
            "previous": prev_total,
            "diff": cur_total - prev_total,
            "pct": ((cur_total - prev_total) / prev_total * 100) if prev_total > 0 else None,
        }

        categories = set(current["breakdown"].keys()) | set(previous["breakdown"].keys())
        cat_changes = {}
        for cat in categories:
            cur_val = current["breakdown"].get(cat, 0) or 0
            prev_val = previous["breakdown"].get(cat, 0) or 0
            diff = cur_val - prev_val
            pct = ((diff) / prev_val * 100) if prev_val > 0 else None
            cat_changes[cat] = {
                "current": cur_val,
                "previous": prev_val,
                "diff": diff,
                "pct": pct,
            }
        result["categories"] = cat_changes
        return result

    async def week_summary(self, user_id: int, year: int, week: int):
        """
        Returns total + breakdown for a given ISO week.
        """
        q = select(
            func.sum(Expense.amount_cents).label("total_cents"),
            Expense.category,
            func.sum(Expense.amount_cents).label("cat_total_cents"),
        ).where(Expense.user_id == user_id,
                extract("year", Expense.local_date) == year,
                extract("week", Expense.local_date) == week
        ).group_by(Expense.category)

        res = await self.db.execute(q)
        rows = res.all()
        total = sum([r.cat_total_cents or 0 for r in rows]) if rows else 0
        breakdown = {r.category or "Uncategorized": r.cat_total_cents for r in rows}
        return {"year": year, "week": week, "total_cents": total, "breakdown": breakdown}
