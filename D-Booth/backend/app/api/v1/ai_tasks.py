from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_team_member, get_current_active_user, get_db
from app.models.models import User
from app.schemas.ai_task import AITaskCreate, AITaskResponse
from app.services.ai_service import AIService

router = APIRouter()


@router.get("", response_model=List[AITaskResponse])
async def get_ai_tasks(
    team_id: Optional[UUID] = Query(None),
    workflow: Optional[str] = Query(None),
    job_status: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI tasks with optional filters"""
    # If team_id provided, verify membership; otherwise scope to user's teams
    team_ids: Optional[List[UUID]] = None
    if team_id:
        await check_team_member(team_id, current_user, db)
    else:
        from app.services.team_service import TeamService

        team_service = TeamService(db)
        user_teams = await team_service.get_user_teams(current_user.id)
        if not user_teams:
            return []
        team_ids = [t.id for t in user_teams]

    ai_service = AIService(db)

    tasks = await ai_service.get_tasks(
        team_id=team_id,
        workflow=workflow,
        status=job_status,
        team_ids=team_ids,
        skip=skip,
        limit=limit,
    )
    return tasks


@router.post("", response_model=AITaskResponse, status_code=status.HTTP_201_CREATED)
async def create_ai_task(
    task_in: AITaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new AI task"""
    # Verify the caller is a member of the task's team (IDOR guard)
    await check_team_member(task_in.team_id, current_user, db)

    ai_service = AIService(db)

    try:
        task = await ai_service.create_task(task_in)
        return task
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{task_id}", response_model=AITaskResponse)
async def get_ai_task(
    task_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI task by ID"""
    ai_service = AIService(db)

    task = await ai_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI task not found")

    await check_team_member(task.team_id, current_user, db)

    return task


@router.post("/{task_id}/cancel", response_model=AITaskResponse)
async def cancel_ai_task(
    task_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an AI task"""
    ai_service = AIService(db)

    task = await ai_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI task not found")

    await check_team_member(task.team_id, current_user, db)

    try:
        task = await ai_service.cancel_task(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI task not found")
        return task
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_task(
    task_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete AI task"""
    ai_service = AIService(db)

    task = await ai_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI task not found")

    await check_team_member(task.team_id, current_user, db)

    success = await ai_service.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI task not found")
