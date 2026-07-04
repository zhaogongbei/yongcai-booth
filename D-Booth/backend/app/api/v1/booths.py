from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.api.deps import check_team_member, get_current_active_user, get_db
from app.models.models import Booth, Event, User
from app.schemas.booth import BoothCreate, BoothResponse, BoothUpdate, HeartbeatResponse
from app.services.booth_service import BoothService

router = APIRouter(prefix="/booths", tags=["Booths - 展位管理"])


async def _get_authorized_booth(
    db: AsyncSession,
    booth_id: UUID,
    current_user: User,
) -> Booth:
    result = await db.execute(
        select(Booth)
        .options(noload(Booth.team), noload(Booth.current_event))
        .where(Booth.id == booth_id)
    )
    booth = result.scalar_one_or_none()
    if not booth:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="展位不存在")

    await check_team_member(booth.team_id, current_user, db)
    return booth


async def _ensure_event_belongs_to_team(
    db: AsyncSession,
    event_id: UUID | None,
    team_id: UUID,
) -> None:
    if event_id is None:
        return

    result = await db.execute(select(Event.team_id).where(Event.id == event_id))
    event_team_id = result.scalar_one_or_none()
    if event_team_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动不存在")
    if event_team_id != team_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="活动不属于该团队",
        )


@router.post("/register", response_model=BoothResponse, summary="注册新展位")
async def register_booth(
    booth_create: BoothCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await check_team_member(booth_create.team_id, current_user, db)
    await _ensure_event_belongs_to_team(db, booth_create.current_event_id, booth_create.team_id)

    service = BoothService(db)
    existing = await service.repository.get_by_device_id(booth_create.device_id)
    if existing and existing.team_id != booth_create.team_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="设备已注册到其他团队",
        )

    return await service.register_booth(booth_create)


@router.post(
    "/{booth_id}/heartbeat", response_model=HeartbeatResponse, summary="展位心跳（30秒间隔）"
)
async def booth_heartbeat(
    booth_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_authorized_booth(db, booth_id, current_user)
    booth = await BoothService(db).heartbeat(booth_id)
    return HeartbeatResponse(
        booth_id=booth_id,
        status=booth.status,
        last_heartbeat=booth.last_heartbeat,
        message="心跳已接收",
    )


@router.get("", response_model=List[BoothResponse], summary="团队所有展位状态")
async def list_booths(
    team_id: UUID = Query(..., description="团队ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await check_team_member(team_id, current_user, db)
    return await BoothService(db).get_team_booths(team_id)


@router.get("/{booth_id}", response_model=BoothResponse, summary="展位详情")
async def get_booth(
    booth_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_authorized_booth(db, booth_id, current_user)


@router.put("/{booth_id}", response_model=BoothResponse, summary="更新展位配置")
async def update_booth(
    booth_id: UUID,
    booth_update: BoothUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await _get_authorized_booth(db, booth_id, current_user)
    await _ensure_event_belongs_to_team(db, booth_update.current_event_id, existing.team_id)

    booth = await BoothService(db).update_booth(booth_id, booth_update)
    return booth


@router.delete("/{booth_id}", summary="注销展位")
async def deregister_booth(
    booth_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_authorized_booth(db, booth_id, current_user)
    success = await BoothService(db).deregister_booth(booth_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="展位不存在")
    return {"message": "展位已注销", "booth_id": str(booth_id)}
