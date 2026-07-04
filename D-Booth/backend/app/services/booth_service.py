from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Booth, BoothStatus
from app.repositories.booth_repository import BoothRepository
from app.schemas.booth import BoothCreate, BoothUpdate
from app.services.base_service import BaseService, BusinessRuleError


class BoothService(BaseService[Booth, BoothCreate, BoothUpdate]):
    """Service for booth business logic."""

    def __init__(self, db: AsyncSession):
        repository = BoothRepository(db)
        super().__init__(repository, db)

    async def before_create(self, obj_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize booth defaults before creation."""
        obj_dict["status"] = BoothStatus.ONLINE
        obj_dict["last_heartbeat"] = datetime.now(timezone.utc)
        return obj_dict

    async def register_booth(self, booth_create: BoothCreate) -> Booth:
        """注册新展位 - 如果device_id已存在则更新"""
        # 检查device_id是否已存在
        existing_booth = await self.repository.get_by_device_id(booth_create.device_id)

        if existing_booth:
            # 更新现有展位信息
            update_data = BoothUpdate(
                name=booth_create.name,
                version=booth_create.version,
                ip_address=booth_create.ip_address,
                os_info=booth_create.os_info,
                status=BoothStatus.ONLINE,
                current_event_id=booth_create.current_event_id,
            )
            existing_booth.last_heartbeat = datetime.now(timezone.utc)
            updated = await self.update(existing_booth.id, update_data)
            return updated

        # 创建新展位
        return await self.create(booth_create)

    async def heartbeat(self, booth_id: UUID) -> Optional[Booth]:
        """更新展位心跳"""
        return await self.repository.update_heartbeat(booth_id)

    async def check_offline_booths(self) -> int:
        """检查超时展位，标记为离线（60秒无心跳）"""
        return await self.repository.mark_offline_booths(timeout_seconds=60)

    async def get_team_booths(self, team_id: UUID, skip: int = 0, limit: int = 100) -> List[Booth]:
        """获取团队所有展位"""
        return await self.repository.get_by_team(team_id, skip, limit)

    async def get_booth(self, booth_id: UUID) -> Optional[Booth]:
        """获取单个展位详情"""
        return await self.get(booth_id)

    async def update_booth(self, booth_id: UUID, booth_update: BoothUpdate) -> Optional[Booth]:
        """更新展位信息"""
        return await self.update(booth_id, booth_update)

    async def update_booth_config_hash(self, booth_id: UUID, config_hash: str) -> Optional[Booth]:
        """更新展位配置哈希"""
        return await self.repository.update_config_hash(booth_id, config_hash)

    async def deregister_booth(self, booth_id: UUID) -> bool:
        """注销展位"""
        return await self.delete(booth_id)
