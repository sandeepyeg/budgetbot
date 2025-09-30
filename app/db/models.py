from sqlalchemy import String, Integer, DateTime, Date, BigInteger, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone, date
import uuid
from app.db.base import Base

class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    item_name: Mapped[str] = mapped_column(String(200))
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(10), default="CAD")
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tags: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    local_date: Mapped[date] = mapped_column(Date, index=True)
    recurring_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


class RecurringExpense(Base):
    __tablename__ = "recurring_expenses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)

    # template
    item_name: Mapped[str] = mapped_column(String(200))
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(10), default="CAD")
    category: Mapped[str | None] = mapped_column(String(50))
    tags: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)

    # recurrence config
    frequency: Mapped[str] = mapped_column(String(20))  # daily | weekly | monthly
    day_of_month: Mapped[int | None] = mapped_column(Integer)
    day_of_week: Mapped[int | None] = mapped_column(Integer)  # 0=Mon … 6=Sun
    repeat_count: Mapped[int | None] = mapped_column(Integer)  # None = infinite
    remaining: Mapped[int | None] = mapped_column(Integer)

    # state
    active: Mapped[bool] = mapped_column(default=True)
    paused: Mapped[bool] = mapped_column(default=False)

    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("slug", name="uq_categories_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Optional: per-user categories in future; keep column now (nullable) for flexibility
    user_id: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)

    name: Mapped[str] = mapped_column(String(50))    # canonical display name, e.g., "Food"
    slug: Mapped[str] = mapped_column(String(60), index=True)  # e.g., "food"
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

class CategoryRule(Base):
    __tablename__ = "category_rules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    keyword: Mapped[str] = mapped_column(String(50), index=True)
    category: Mapped[str] = mapped_column(String(50))
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )