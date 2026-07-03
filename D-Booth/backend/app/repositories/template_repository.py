from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Template
from app.repositories.base import BaseRepository


class TemplateRepository(BaseRepository[Template]):
    """Repository for Template model"""

    def __init__(self, db: AsyncSession):
        super().__init__(Template, db)

    async def get_by_team(self, team_id: UUID, skip: int = 0, limit: int = 100) -> List[Template]:
        """Get all templates for a team"""
        result = await self.db.execute(
            select(Template)
            .where(Template.team_id == team_id)
            .order_by(Template.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_public_templates(self, skip: int = 0, limit: int = 100) -> List[Template]:
        """Get all public templates"""
        result = await self.db.execute(
            select(Template)
            .where(Template.is_public == True)
            .order_by(Template.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_size(
        self, team_id: UUID, size: str, skip: int = 0, limit: int = 100
    ) -> List[Template]:
        """Get templates by size"""
        result = await self.db.execute(
            select(Template)
            .where(Template.team_id == team_id, Template.size == size)
            .order_by(Template.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_team(self, team_id: UUID) -> int:
        """Count templates for a team"""
        result = await self.db.execute(
            select(func.count()).select_from(Template).where(Template.team_id == team_id)
        )
        return result.scalar_one()
