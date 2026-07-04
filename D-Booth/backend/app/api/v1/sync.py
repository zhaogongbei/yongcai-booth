from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_team_member, get_current_active_user, get_db
from app.models.models import Booth, User
from app.schemas.booth import SyncLogResponse, SyncPullResponse, SyncPushResponse, SyncStateResponse
from app.services.booth_service import BoothService
from app.services.sync_service import SyncService

router = APIRouter(prefix="/sync", tags=["Sync - 配置同步"])


async def _get_authorized_booth(
    db: AsyncSession,
    booth_id: UUID,
    team_id: UUID,
    current_user: User,
) -> Booth:
    await check_team_member(team_id, current_user, db)

    booth = await BoothService(db).get_booth(booth_id)
    if not booth or booth.team_id != team_id:
        raise HTTPException(status_code=404, detail="展位不存在或不属于该团队")

    return booth


@router.get("/state/{booth_id}", response_model=SyncStateResponse, summary="获取同步状态")
async def get_sync_state(
    booth_id: UUID,
    team_id: UUID = Query(..., description="团队ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_authorized_booth(db, booth_id, team_id, current_user)
    return await SyncService.get_sync_state(db, team_id, booth_id)


@router.post("/push/{booth_id}", response_model=SyncPushResponse, summary="推送配置到展位")
async def push_config(
    booth_id: UUID,
    team_id: UUID = Query(..., description="团队ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_authorized_booth(db, booth_id, team_id, current_user)
    return await SyncService.push_config(db, booth_id)


@router.post("/pull/{booth_id}", response_model=SyncPullResponse, summary="从展位拉取配置")
async def pull_config(
    booth_id: UUID,
    team_id: UUID = Query(..., description="团队ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_authorized_booth(db, booth_id, team_id, current_user)
    return await SyncService.pull_config(db, booth_id)


@router.get("/log/{team_id}", response_model=SyncLogResponse, summary="同步历史日志")
async def get_sync_log(
    team_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await check_team_member(team_id, current_user, db)
    return await SyncService.get_sync_log(db, team_id)
