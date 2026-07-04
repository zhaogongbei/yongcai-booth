import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_team_member, get_current_active_user
from app.core.database import get_db
from app.core.logging import logger
from app.models.models import Disclaimer, DisclaimerAcceptance, Event, PhotoSession, User
from app.schemas.disclaimer import (
    DisclaimerAcceptanceCreate,
    DisclaimerAcceptanceResponse,
    DisclaimerResponse,
    DisclaimerUpdate,
)

router = APIRouter(prefix="/disclaimers", tags=["disclaimers"])


async def _ensure_event_access(
    db: AsyncSession,
    event_id: UUID,
    current_user: User,
) -> None:
    result = await db.execute(select(Event.team_id).where(Event.id == event_id))
    team_id = result.scalar_one_or_none()
    if team_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    await check_team_member(team_id, current_user, db)


async def _ensure_session_belongs_to_event(
    db: AsyncSession,
    event_id: UUID,
    session_id: UUID,
) -> None:
    result = await db.execute(
        select(PhotoSession.id)
        .where(PhotoSession.id == session_id)
        .where(PhotoSession.event_id == event_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")


@router.get("/event/{event_id}", response_model=DisclaimerResponse)
async def get_event_disclaimer(event_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取事件的免责声明"""
    result = await db.execute(select(Disclaimer).where(Disclaimer.event_id == event_id))
    disclaimer = result.scalar_one_or_none()

    if not disclaimer:
        # 创建默认免责声明
        disclaimer = Disclaimer(
            id=uuid.uuid4(),
            event_id=event_id,
            enabled=False,
            title="免责声明",
            text="请仔细阅读本免责声明...",
            require_signature=False,
        )
        db.add(disclaimer)
        await db.commit()
        await db.refresh(disclaimer)

    return disclaimer


@router.put("/event/{event_id}", response_model=DisclaimerResponse)
async def update_event_disclaimer(
    event_id: UUID,
    disclaimer_data: DisclaimerUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """更新事件的免责声明"""
    await _ensure_event_access(db, event_id, current_user)

    try:
        result = await db.execute(
            select(Disclaimer).where(Disclaimer.event_id == event_id)
        )
        disclaimer = result.scalar_one_or_none()

        if not disclaimer:
            disclaimer = Disclaimer(
                id=uuid.uuid4(), event_id=event_id, **disclaimer_data.model_dump()
            )
            db.add(disclaimer)
        else:
            for field, value in disclaimer_data.model_dump().items():
                setattr(disclaimer, field, value)

        await db.commit()
        await db.refresh(disclaimer)
        return disclaimer

    except Exception as e:
        logger.error(f"更新免责声明失败: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="更新免责声明失败")


@router.post("/accept", response_model=DisclaimerAcceptanceResponse)
async def accept_disclaimer(
    acceptance_data: DisclaimerAcceptanceCreate, db: AsyncSession = Depends(get_db)
):
    """记录来宾确认免责声明"""
    try:
        disclaimer_result = await db.execute(
            select(Disclaimer.id).where(Disclaimer.event_id == acceptance_data.event_id)
        )
        disclaimer_id = disclaimer_result.scalar_one_or_none()
        if not disclaimer_id:
            raise HTTPException(status_code=404, detail="免责声明不存在")

        await _ensure_session_belongs_to_event(
            db, acceptance_data.event_id, acceptance_data.session_id
        )

        # 检查是否已经接受过
        existing = await db.execute(
            select(DisclaimerAcceptance.id)
            .where(DisclaimerAcceptance.event_id == acceptance_data.event_id)
            .where(DisclaimerAcceptance.session_id == acceptance_data.session_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="已经接受过免责声明")

        acceptance = DisclaimerAcceptance(
            id=uuid.uuid4(),
            event_id=acceptance_data.event_id,
            session_id=acceptance_data.session_id,
            disclaimer_id=disclaimer_id,
        )

        db.add(acceptance)
        await db.commit()
        return acceptance

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"记录免责声明接受失败: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="提交失败")
