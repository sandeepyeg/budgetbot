import pytest
import pytest_asyncio
from datetime import date
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.base import Base
from app.services.recurring_service import RecurringService


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_recurring_create_sets_defaults_from_today(monkeypatch, db_session: AsyncSession):
    import app.services.recurring_service as recurring_module

    monkeypatch.setattr(recurring_module, "local_date_for_now", lambda: date(2026, 2, 27))

    svc = RecurringService(db_session)
    monthly = await svc.create(user_id=1, item_name="Rent", amount_cents=100000, frequency="monthly")
    weekly = await svc.create(user_id=1, item_name="Gym", amount_cents=3000, frequency="weekly")

    assert monthly.day_of_month == 27
    assert weekly.day_of_week == 4


@pytest.mark.asyncio
async def test_generate_due_today_is_idempotent(monkeypatch, db_session: AsyncSession):
    import app.services.recurring_service as recurring_module

    monkeypatch.setattr(recurring_module, "local_date_for_now", lambda: date(2026, 2, 27))

    svc = RecurringService(db_session)
    await svc.create(user_id=1, item_name="Coffee Sub", amount_cents=999, frequency="daily")

    first = await svc.generate_due_today()
    second = await svc.generate_due_today()

    assert len(first) == 1
    assert len(second) == 0


@pytest.mark.asyncio
async def test_update_state_works_with_short_ref(db_session: AsyncSession):
    svc = RecurringService(db_session)
    rec = await svc.create(user_id=1, item_name="Netflix", amount_cents=1599, frequency="monthly")

    updated = await svc.update_state(rec.id[:8], 1, paused=True)
    assert updated is not None
    assert updated.paused is True
