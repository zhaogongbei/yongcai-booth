from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.schemas.booth import SyncStateResponse, SyncPushResponse, SyncPullResponse, SyncLogResponse
from app.services.sync_service import SyncService
from app.services.booth_service import BoothService

router = APIRouter(prefix="/sync", tags=["Sync - 配置同步"])


@router.get("/state/{booth_id}", response_model=SyncStateResponse, summary="获取同步状态")
async def get_sync_state(
    booth_id: UUID,
    team_id: UUID = Query(..., description="团队ID"),
    db: AsyncSession = Depends(get_db)
):
    # 验证展位是否存在且属于该团队
    booth = await BoothService.get_booth(db, booth_id)
    if not booth or booth.team_id != team_id:
        raise HTTPException(status_code=404, detail="展位不存在或不属于该团队")

    return await SyncService.get_sync_state(db, team_id, booth_id)


@router.post("/push/{booth_id}", response_model=SyncPushResponse, summary="推送配置到展位")
async def push_config(
    booth_id: UUID,
    team_id: UUID = Query(..., description="团队ID"),
    db: AsyncSession = Depends(get_db)
):
    # 验证展位是否存在且属于该团队
    booth = await BoothService.get_booth(db, booth_id)
    if not booth or booth.team_id != team_id:
        raise HTTPException(status_code=404, detail="展位不存在或不属于该团队")

    return await SyncService.push_config(db, booth_id)


@router.post("/pull/{booth_id}", response_model=SyncPullResponse, summary="从展位拉取配置")
async def pull_config(
    booth_id: UUID,
    team_id: UUID = Query(..., description="团队ID"),
    db: AsyncSession = Depends(get_db)
):
    # 验证展位是否存在且属于该团队
    booth = await BoothService.get_booth(db, booth_id)
    if not booth or booth.team_id != team_id:
        raise HTTPException(status_code=404, detail="展位不存在或不属于该团队")

    return await SyncService.pull_config(db, booth_id)


@router.get("/log/{team_id}", response_model=SyncLogResponse, summary="同步历史日志")
async def get_sync_log(
    team_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    return await SyncService.get_sync_log(db, team_id)
