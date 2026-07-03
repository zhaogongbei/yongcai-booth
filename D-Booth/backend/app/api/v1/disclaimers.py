import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.models.models import Disclaimer, DisclaimerAcceptance
from app.schemas.disclaimer import (
    DisclaimerAcceptanceCreate,
    DisclaimerAcceptanceResponse,
    DisclaimerResponse,
    DisclaimerUpdate,
)

router = APIRouter(prefix="/disclaimers", tags=["disclaimers"])


@router.get("/event/{event_id}", response_model=DisclaimerResponse)
async def get_event_disclaimer(event_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取事件的免责声明"""
    result = await db.execute(Disclaimer.__table__.select().where(Disclaimer.event_id == event_id))
    disclaimer = result.first()

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
    event_id: UUID, disclaimer_data: DisclaimerUpdate, db: AsyncSession = Depends(get_db)
):
    """更新事件的免责声明"""
    try:
        result = await db.execute(
            Disclaimer.__table__.select().where(Disclaimer.event_id == event_id)
        )
        disclaimer = result.first()

        if not disclaimer:
            disclaimer = Disclaimer(id=uuid.uuid4(), event_id=event_id, **disclaimer_data.dict())
            db.add(disclaimer)
        else:
            for field, value in disclaimer_data.dict().items():
                setattr(disclaimer, field, value)

        await db.commit()
        await db.refresh(disclaimer)
        return disclaimer

    except Exception as e:
        logger.error(f"更新免责声明失败: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新免责声明失败: {str(e)}")


@router.post("/accept", response_model=DisclaimerAcceptanceResponse)
async def accept_disclaimer(
    acceptance_data: DisclaimerAcceptanceCreate, db: AsyncSession = Depends(get_db)
):
    """记录来宾确认免责声明"""
    try:
        # 检查是否已经接受过
        existing = await db.execute(
            DisclaimerAcceptance.__table__.select()
            .where(DisclaimerAcceptance.event_id == acceptance_data.event_id)
            .where(DisclaimerAcceptance.session_id == acceptance_data.session_id)
        )
        if existing.first():
            raise HTTPException(status_code=400, detail="已经接受过免责声明")

        acceptance = DisclaimerAcceptance(
            id=uuid.uuid4(),
            event_id=acceptance_data.event_id,
            session_id=acceptance_data.session_id,
        )

        db.add(acceptance)
        await db.commit()
        await db.refresh(acceptance)
        return acceptance

    except Exception as e:
        logger.error(f"记录免责声明接受失败: {str(e)}")
        await db.rollback()
        if "已经接受过免责声明" in str(e):
            raise
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")
