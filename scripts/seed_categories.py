import asyncio
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.services.category_service import CategoryService

async def run():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        cs = CategoryService(session)
        await cs.seed_defaults()
        print("✅ Categories seeded")

if __name__ == "__main__":
    asyncio.run(run())
