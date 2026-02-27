import pytest
import pytest_asyncio
from datetime import date
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.base import Base
from app.db.models import Expense
from app.services.expense_service import ExpenseService
from app.services.budget_service import BudgetService


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
async def test_expense_short_ref_resolution(db_session: AsyncSession):
    svc = ExpenseService(db_session)
    exp = await svc.add_expense_text(user_id=1, item_name="Coffee", amount_cents=450)
    short = exp.id[:8]

    found = await svc.get_expense_by_ref(1, short)
    assert found is not None
    assert found.id == exp.id


@pytest.mark.asyncio
async def test_undo_delete_by_ref(db_session: AsyncSession):
    svc = ExpenseService(db_session)
    exp = await svc.add_expense_text(user_id=1, item_name="Lunch", amount_cents=1200)

    removed = await svc.delete_expense_by_ref(1, exp.id[:8])
    assert removed is not None

    should_be_none = await svc.get_expense(exp.id)
    assert should_be_none is None


@pytest.mark.asyncio
async def test_budget_rollover_progress(db_session: AsyncSession):
    user_id = 1
    db_session.add(
        Expense(
            user_id=user_id,
            item_name="Prev Month Spend",
            amount_cents=5000,
            currency="CAD",
            category="Food",
            tags=None,
            notes=None,
            receipt_path=None,
            local_date=date(2026, 1, 15),
            recurring_id=None,
        )
    )
    db_session.add(
        Expense(
            user_id=user_id,
            item_name="Current Spend",
            amount_cents=2000,
            currency="CAD",
            category="Food",
            tags=None,
            notes=None,
            receipt_path=None,
            local_date=date(2026, 2, 15),
            recurring_id=None,
        )
    )
    await db_session.commit()

    bsvc = BudgetService(db_session)
    budget = await bsvc.add_budget(
        user_id=user_id,
        scope_type="category",
        scope_value="Food",
        limit_cents=10000,
        period="month_rollover",
    )

    esvc = ExpenseService(db_session)
    progress = await bsvc.get_budget_progress(user_id, budget, esvc, 2026, 2)

    assert progress["effective_limit_cents"] == 15000
    assert progress["spent_cents"] == 2000


@pytest.mark.asyncio
async def test_budget_alerts_threshold_and_exceeded(db_session: AsyncSession):
    user_id = 1
    db_session.add(
        Expense(
            user_id=user_id,
            item_name="Food Spend",
            amount_cents=9000,
            currency="CAD",
            category="Food",
            tags=None,
            notes=None,
            receipt_path=None,
            local_date=date(2026, 2, 20),
            recurring_id=None,
        )
    )
    db_session.add(
        Expense(
            user_id=user_id,
            item_name="Rent",
            amount_cents=110000,
            currency="CAD",
            category="Bills",
            tags=None,
            notes=None,
            receipt_path=None,
            local_date=date(2026, 2, 1),
            recurring_id=None,
        )
    )
    await db_session.commit()

    bsvc = BudgetService(db_session)
    await bsvc.add_budget(user_id=user_id, scope_type="category", scope_value="Food", limit_cents=10000, period="month")
    await bsvc.add_budget(user_id=user_id, scope_type="overall", scope_value=None, limit_cents=100000, period="month")

    esvc = ExpenseService(db_session)
    alerts = await bsvc.check_alerts(user_id, esvc)

    assert any("Food budget at" in a for a in alerts)
    assert any("Overall budget exceeded" in a for a in alerts)
