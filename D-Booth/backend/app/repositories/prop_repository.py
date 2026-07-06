"""
Prop repository for data access operations.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Prop, PropCategory
from app.repositories.base import BaseRepository


class PropRepository(BaseRepository[Prop]):
    """Repository for Prop data access."""

    def __init__(self, db: AsyncSession):
        super().__init__(Prop, db)

    async def get_accessible_props(
        self,
        team_id: Optional[UUID] = None,
        category: Optional[PropCategory] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Prop]:
        """Get props accessible to team (public + team-owned)."""
        query = select(Prop).where(or_(Prop.is_public == True, Prop.team_id == team_id))

        if category:
            query = query.where(Prop.category == category)

        # Sort: default props first, then by creation time
        query = (
            query.order_by(Prop.is_default.desc(), Prop.created_at.desc()).offset(skip).limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_accessible_props(
        self, team_id: Optional[UUID] = None, category: Optional[PropCategory] = None
    ) -> int:
        """Count props accessible to team."""
        query = select(func.count(Prop.id)).where(
            or_(Prop.is_public == True, Prop.team_id == team_id)
        )

        if category:
            query = query.where(Prop.category == category)

        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_by_team(self, team_id: UUID, skip: int = 0, limit: int = 100) -> List[Prop]:
        """Get props owned by specific team."""
        result = await self.db.execute(
            select(Prop)
            .where(Prop.team_id == team_id)
            .order_by(Prop.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
