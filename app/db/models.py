from sqlalchemy import String, Integer, DateTime, Date, BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone, date
import uuid
from app.db.base import Base

class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)            # Telegram numeric user id
    item_name: Mapped[str] = mapped_column(String(200))
    amount_cents: Mapped[int] = mapped_column(Integer)                      # store money safely as cents
    currency: Mapped[str] = mapped_column(String(10), default="CAD")
    category: Mapped[str | None] = mapped_column(String(50), nullable=True) # manual for now
    tags: Mapped[str | None] = mapped_column(String(200), nullable=True)    # comma-separated (upgrade later)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                     default=lambda: datetime.now(timezone.utc))
    local_date: Mapped[date] = mapped_column(Date, index=True)              # denormalized for fast month filters
