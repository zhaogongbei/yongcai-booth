import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Booth, Event, Photo, Prop, Template


class SyncService:
    @staticmethod
    def _compute_hash(data: Any) -> str:
        """计算内容的SHA256哈希值"""
        content = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    async def get_sync_state(db: AsyncSession, team_id: uuid.UUID, booth_id: uuid.UUID) -> dict:
        """获取当前展位与云端配置的差异状态"""
        booth = await db.get(Booth, booth_id)
        if not booth:
            return {"error": "展位不存在"}

        # 获取团队模板
        templates_result = await db.execute(select(Template).where(Template.team_id == team_id))
        templates = templates_result.scalars().all()

        # 获取团队活动设置
        events_result = await db.execute(select(Event).where(Event.team_id == team_id))
        events = events_result.scalars().all()

        # 获取团队道具
        props_result = await db.execute(select(Prop).where(Prop.team_id == team_id))
        props = props_result.scalars().all()

        # 计算哈希
        templates_data = [{"id": str(t.id), "updated_at": str(t.updated_at)} for t in templates]
        settings_data = [
            {"id": str(e.id), "updated_at": str(e.updated_at), "settings": e.settings}
            for e in events
        ]
        props_data = [{"id": str(p.id), "updated_at": str(p.updated_at)} for p in props]

        templates_hash = SyncService._compute_hash(templates_data)
        settings_hash = SyncService._compute_hash(settings_data)
        props_hash = SyncService._compute_hash(props_data)

        # 合并云端哈希
        cloud_hash = SyncService._compute_hash(
            {"templates": templates_hash, "settings": settings_hash, "props": props_hash}
        )

        need_sync_templates = 0
        need_sync_settings = 0
        need_sync_props = 0

        if booth.config_hash != cloud_hash:
            need_sync_templates = len(templates)
            need_sync_settings = len(events)
            need_sync_props = len(props)

        return {
            "booth_id": str(booth_id),
            "team_id": str(team_id),
            "templates_hash": templates_hash,
            "settings_hash": settings_hash,
            "props_hash": props_hash,
            "cloud_hash": cloud_hash,
            "booth_config_hash": booth.config_hash,
            "need_sync_templates": need_sync_templates if booth.config_hash != cloud_hash else 0,
            "need_sync_settings": need_sync_settings if booth.config_hash != cloud_hash else 0,
            "need_sync_props": need_sync_props if booth.config_hash != cloud_hash else 0,
            "total_templates": len(templates),
            "total_events": len(events),
            "total_props": len(props),
            "is_synced": booth.config_hash == cloud_hash,
        }

    @staticmethod
    async def push_config(db: AsyncSession, booth_id: uuid.UUID) -> dict:
        """推送云端配置到展位"""
        booth = await db.get(Booth, booth_id)
        if not booth:
            return {"error": "展位不存在"}

        # 获取团队所有模板
        templates_result = await db.execute(
            select(Template).where(Template.team_id == booth.team_id)
        )
        templates = templates_result.scalars().all()

        # 获取团队所有活动
        events_result = await db.execute(select(Event).where(Event.team_id == booth.team_id))
        events = events_result.scalars().all()

        # 获取团队所有道具
        props_result = await db.execute(select(Prop).where(Prop.team_id == booth.team_id))
        props = props_result.scalars().all()

        # 计算新配置哈希
        templates_data = [{"id": str(t.id), "updated_at": str(t.updated_at)} for t in templates]
        settings_data = [
            {"id": str(e.id), "updated_at": str(e.updated_at), "settings": e.settings}
            for e in events
        ]
        props_data = [{"id": str(p.id), "updated_at": str(p.updated_at)} for p in props]

        new_hash = SyncService._compute_hash(
            {
                "templates": SyncService._compute_hash(templates_data),
                "settings": SyncService._compute_hash(settings_data),
                "props": SyncService._compute_hash(props_data),
            }
        )

        booth.config_hash = new_hash
        booth.status = booth.status  # 保持现有状态
        await db.commit()

        return {
            "booth_id": str(booth_id),
            "config_hash": new_hash,
            "pushed": {"templates": len(templates), "events": len(events), "props": len(props)},
        }

    @staticmethod
    async def pull_config(db: AsyncSession, booth_id: uuid.UUID) -> dict:
        """从展位拉取配置信息（此处返回展位当前状态）"""
        booth = await db.get(Booth, booth_id)
        if not booth:
            return {"error": "展位不存在"}

        return {
            "booth_id": str(booth_id),
            "name": booth.name,
            "status": booth.status.value if booth.status else "unknown",
            "version": booth.version,
            "config_hash": booth.config_hash,
            "last_heartbeat": str(booth.last_heartbeat) if booth.last_heartbeat else None,
            "ip_address": booth.ip_address,
            "os_info": booth.os_info,
            "current_event_id": str(booth.current_event_id) if booth.current_event_id else None,
        }

    @staticmethod
    async def get_sync_log(db: AsyncSession, team_id: uuid.UUID) -> dict:
        """获取团队同步历史日志（基于展位状态）"""
        booths_result = await db.execute(select(Booth).where(Booth.team_id == team_id))
        booths = booths_result.scalars().all()

        logs = []
        for booth in booths:
            logs.append(
                {
                    "booth_id": str(booth.id),
                    "booth_name": booth.name,
                    "status": booth.status.value if booth.status else "unknown",
                    "config_hash": booth.config_hash,
                    "last_heartbeat": str(booth.last_heartbeat) if booth.last_heartbeat else None,
                    "created_at": str(booth.created_at),
                    "updated_at": str(booth.updated_at),
                }
            )

        return {"team_id": str(team_id), "booths": logs, "total": len(booths)}
