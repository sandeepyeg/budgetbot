from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import CategoryRule
from app.services.global_rules import GLOBAL_RULES
import uuid

class RuleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_rules(self, user_id: int):
        q = select(CategoryRule).where(CategoryRule.user_id == user_id).order_by(CategoryRule.created_at_utc)
        res = await self.db.execute(q)
        return list(res.scalars().all())

    async def add_rule(self, user_id: int, keyword: str, category: str) -> CategoryRule:
        r = CategoryRule(
            id=str(uuid.uuid4()),
            user_id=user_id,
            keyword=keyword.lower(),
            category=category,
        )
        self.db.add(r)
        await self.db.commit()
        await self.db.refresh(r)
        return r

    async def delete_rule(self, user_id: int, rule_id: str):
        q = select(CategoryRule).where(CategoryRule.id == rule_id, CategoryRule.user_id == user_id)
        res = await self.db.execute(q)
        r = res.scalar_one_or_none()
        if not r:
            return None
        await self.db.delete(r)
        await self.db.commit()
        return r

    async def suggest_category(self, user_id: int, text: str) -> str | None:
        """
        1. Check user rules.
        2. Fallback to global defaults.
        """
        text_lower = text.lower()

        # user rules
        q = select(CategoryRule).where(CategoryRule.user_id == user_id)
        res = await self.db.execute(q)
        rules = res.scalars().all()
        for rule in rules:
            if rule.keyword in text_lower:
                return rule.category

        # global defaults
        for keyword, category in GLOBAL_RULES.items():
            if keyword in text_lower:
                return category

        return None
