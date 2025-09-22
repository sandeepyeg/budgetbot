from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Category
from app.utils.text import slugify

DEFAULT_GLOBAL_CATEGORIES = [
    "Food", "Groceries", "Transport", "Shopping", "Bills", "Entertainment",
    "Health", "Education", "Travel", "Utilities", "Rent", "Household",
    "Kids", "Gifts", "Taxes", "Fees", "Savings", "Other"
]

class CategoryService:
    def __init__(self, db: AsyncSession, user_id: int | None = None):
        self.db = db
        self.user_id = user_id  # keep None for global categories

    async def get_by_slug(self, slug: str) -> Category | None:
        q = select(Category).where(Category.slug == slug, Category.user_id.is_(None))
        res = await self.db.execute(q)
        return res.scalar_one_or_none()

    async def get_or_create(self, name: str) -> Category:
        slug = slugify(name)
        existing = await self.get_by_slug(slug)
        if existing:
            return existing
        cat = Category(user_id=None, name=name.strip()[:50], slug=slug)
        self.db.add(cat)
        await self.db.commit()
        await self.db.refresh(cat)
        return cat

    async def list_all(self) -> list[Category]:
        q = select(Category).where(Category.user_id.is_(None)).order_by(Category.name.asc())
        res = await self.db.execute(q)
        return list(res.scalars().all())

    async def seed_defaults(self):
        for n in DEFAULT_GLOBAL_CATEGORIES:
            await self.get_or_create(n)
