import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Booth, BoothStatus
from app.schemas.booth import BoothCreate, BoothUpdate


class BoothService:
    @staticmethod
    async def register_booth(db: AsyncSession, booth_create: BoothCreate) -> Booth:
        """注册新展位"""
        # 检查device_id是否已存在
        existing_booth = await db.execute(
            select(Booth).where(Booth.device_id == booth_create.device_id)
        )
        existing_booth = existing_booth.scalar_one_or_none()

        if existing_booth:
            # 更新现有展位信息
            existing_booth.name = booth_create.name
            existing_booth.version = booth_create.version
            existing_booth.ip_address = booth_create.ip_address
            existing_booth.os_info = booth_create.os_info
            existing_booth.status = BoothStatus.ONLINE
            existing_booth.last_heartbeat = datetime.utcnow()
            await db.commit()
            await db.refresh(existing_booth)
            return existing_booth

        # 创建新展位
        booth = Booth(
            id=uuid.uuid4(),
            team_id=booth_create.team_id,
            name=booth_create.name,
            device_id=booth_create.device_id,
            status=BoothStatus.ONLINE,
            version=booth_create.version,
            last_heartbeat=datetime.utcnow(),
            ip_address=booth_create.ip_address,
            os_info=booth_create.os_info,
            current_event_id=booth_create.current_event_id
        )

        db.add(booth)
        await db.commit()
        await db.refresh(booth)
        return booth

    @staticmethod
    async def heartbeat(db: AsyncSession, booth_id: uuid.UUID) -> Optional[Booth]:
        """更新展位心跳"""
        booth = await db.get(Booth, booth_id)
        if not booth:
            return None

        booth.last_heartbeat = datetime.utcnow()
        booth.status = BoothStatus.ONLINE
        await db.commit()
        await db.refresh(booth)
        return booth

    @staticmethod
    async def check_offline_booths(db: AsyncSession) -> int:
        """检查超时展位，标记为离线（60秒无心跳）"""
        cutoff_time = datetime.utcnow() - timedelta(seconds=60)
        result = await db.execute(
            update(Booth)
            .where(Booth.last_heartbeat < cutoff_time)
            .where(Booth.status != BoothStatus.OFFLINE)
            .values(status=BoothStatus.OFFLINE)
        )
        await db.commit()
        return result.rowcount

    @staticmethod
    async def get_team_booths(db: AsyncSession, team_id: uuid.UUID) -> List[Booth]:
        """获取团队所有展位"""
        result = await db.execute(
            select(Booth).where(Booth.team_id == team_id).order_by(Booth.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_booth(db: AsyncSession, booth_id: uuid.UUID) -> Optional[Booth]:
        """获取单个展位详情"""
        return await db.get(Booth, booth_id)

    @staticmethod
    async def update_booth(
        db: AsyncSession,
        booth_id: uuid.UUID,
        booth_update: BoothUpdate
    ) -> Optional[Booth]:
        """更新展位信息"""
        booth = await db.get(Booth, booth_id)
        if not booth:
            return None

        update_data = booth_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(booth, field, value)

        await db.commit()
        await db.refresh(booth)
        return booth

    @staticmethod
    async def update_booth_config_hash(
        db: AsyncSession,
        booth_id: uuid.UUID,
        config_hash: str
    ) -> Optional[Booth]:
        """更新展位配置哈希"""
        booth = await db.get(Booth, booth_id)
        if not booth:
            return None

        booth.config_hash = config_hash
        await db.commit()
        await db.refresh(booth)
        return booth

    @staticmethod
    async def deregister_booth(db: AsyncSession, booth_id: uuid.UUID) -> bool:
        """注销展位"""
        booth = await db.get(Booth, booth_id)
        if not booth:
            return False

        await db.delete(booth)
        await db.commit()
        return True
