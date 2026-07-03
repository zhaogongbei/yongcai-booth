from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_team_member, get_current_active_user, get_db
from app.models.models import User
from app.schemas.booth import BoothCreate, BoothResponse, BoothUpdate, HeartbeatResponse
from app.services.booth_service import BoothService

router = APIRouter(prefix="/booths", tags=["Booths - 展位管理"])


@router.post("/register", response_model=BoothResponse, summary="注册新展位")
async def register_booth(
    booth_create: BoothCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await BoothService.register_booth(db, booth_create)


@router.post(
    "/{booth_id}/heartbeat", response_model=HeartbeatResponse, summary="展位心跳（30秒间隔）"
)
async def booth_heartbeat(
    booth_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    booth = await BoothService.heartbeat(db, booth_id)
    if not booth:
        raise HTTPException(status_code=404, detail="展位不存在")
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
    return await BoothService.get_team_booths(db, team_id)


@router.get("/{booth_id}", response_model=BoothResponse, summary="展位详情")
async def get_booth(
    booth_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    booth = await BoothService.get_booth(db, booth_id)
    if not booth:
        raise HTTPException(status_code=404, detail="展位不存在")
    return booth


@router.put("/{booth_id}", response_model=BoothResponse, summary="更新展位配置")
async def update_booth(
    booth_id: UUID,
    booth_update: BoothUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    booth = await BoothService.update_booth(db, booth_id, booth_update)
    if not booth:
        raise HTTPException(status_code=404, detail="展位不存在")
    return booth


@router.delete("/{booth_id}", summary="注销展位")
async def deregister_booth(
    booth_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    success = await BoothService.deregister_booth(db, booth_id)
    if not success:
        raise HTTPException(status_code=404, detail="展位不存在")
    return {"message": "展位已注销", "booth_id": str(booth_id)}
