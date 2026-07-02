from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from decimal import Decimal
from app.models.models import AITask
from app.repositories.base import BaseRepository


class AITaskRepository(BaseRepository[AITask]):
    """Repository for AITask model"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(AITask, db)
    
    async def get_by_team(
        self,
        team_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[AITask]:
        """Get all AI tasks for a team"""
        result = await self.db.execute(
            select(AITask)
            .where(AITask.team_id == team_id)
            .order_by(AITask.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_workflow(
        self,
        team_id: UUID,
        workflow: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AITask]:
        """Get tasks by workflow"""
        result = await self.db.execute(
            select(AITask)
            .where(
                AITask.team_id == team_id,
                AITask.workflow == workflow
            )
            .order_by(AITask.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_status(
        self,
        team_id: UUID,
        status: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AITask]:
        """Get tasks by status"""
        result = await self.db.execute(
            select(AITask)
            .where(
                AITask.team_id == team_id,
                AITask.status == status
            )
            .order_by(AITask.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_pending_tasks(self, limit: int = 50) -> List[AITask]:
        """Get pending AI tasks"""
        result = await self.db.execute(
            select(AITask)
            .where(AITask.status == "pending")
            .order_by(AITask.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def update_progress(
        self,
        task_id: UUID,
        progress: Decimal,
        status: Optional[str] = None
    ) -> Optional[AITask]:
        """Update task progress"""
        stmt = select(AITask).where(AITask.id == task_id)
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if task:
            task.progress = progress
            if status:
                task.status = status
            await self.db.commit()
            await self.db.refresh(task)
            return task
        return None
    
    async def complete_task(
        self,
        task_id: UUID,
        result_url: str,
        actual_cost: Optional[Decimal] = None
    ) -> Optional[AITask]:
        """Mark task as completed"""
        stmt = select(AITask).where(AITask.id == task_id)
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if task:
            task.status = "completed"
            task.progress = Decimal(100)
            task.result_url = result_url
            task.error_message = None
            if actual_cost is not None:
                task.actual_cost = actual_cost
            await self.db.commit()
            await self.db.refresh(task)
            return task
        return None
    
    async def fail_task(
        self,
        task_id: UUID,
        error_message: str
    ) -> Optional[AITask]:
        """Mark task as failed"""
        stmt = select(AITask).where(AITask.id == task_id)
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if task:
            task.status = "failed"
            task.error_message = error_message
            await self.db.commit()
            await self.db.refresh(task)
            return task
        return None
    
    async def get_total_cost(self, team_id: UUID) -> Decimal:
        """Get total AI cost for a team"""
        result = await self.db.execute(
            select(func.sum(AITask.actual_cost)).where(
                AITask.team_id == team_id
            )
        )
        return result.scalar_one() or Decimal(0)

    async def count_by_team_between(
        self,
        team_id: UUID,
        start_at: datetime,
        end_at: datetime
    ) -> int:
        """Count AI tasks for a team inside a billing period."""
        result = await self.db.execute(
            select(func.count())
            .select_from(AITask)
            .where(
                AITask.team_id == team_id,
                AITask.created_at >= start_at,
                AITask.created_at < end_at,
            )
        )
        return result.scalar_one()
    
    async def count_by_workflow(self, team_id: UUID) -> dict:
        """Count tasks by workflow"""
        result = await self.db.execute(
            select(AITask.workflow, func.count(AITask.id))
            .where(AITask.team_id == team_id)
            .group_by(AITask.workflow)
        )
        return {row[0]: row[1] for row in result.all()}
