from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_team_member, get_current_active_user, get_db
from app.core.logging import logger
from app.models.models import TriggerConfig as TriggerConfigModel
from app.models.models import TriggerLog as TriggerLogModel
from app.models.models import User
from app.services.base_service import ValidationError
from app.services.event_service import EventService
from app.services.trigger_service import TriggerService

router = APIRouter()


@router.get("/{event_id}", response_model=List[dict])
async def get_trigger_configs(
    event_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all trigger configs for an event"""
    event_service = EventService(db)
    event = await event_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    await check_team_member(event.team_id, current_user, db)

    trigger_service = TriggerService(db)
    configs = await trigger_service.get_configs(event_id)
    return [
        {
            "id": str(c.id),
            "event_id": str(c.event_id),
            "event_type": (
                c.event_type.value if hasattr(c.event_type, "value") else str(c.event_type)
            ),
            "enabled": c.enabled,
            "action_type": (
                c.action_type.value if hasattr(c.action_type, "value") else str(c.action_type)
            ),
            "target": c.target,
            "payload_template": c.payload_template or {},
            "timeout": c.timeout,
            "retry": c.retry,
        }
        for c in configs
    ]


@router.put("/{event_id}", response_model=List[dict])
async def update_trigger_configs(
    event_id: UUID,
    configs: List[dict],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update trigger configs for an event (replaces all configs)"""
    event_service = EventService(db)
    event = await event_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    await check_team_member(event.team_id, current_user, db)

    # Validate configs
    valid_event_types = {
        "session_start",
        "countdown_start",
        "capture_start",
        "file_download",
        "processing_start",
        "sharing_screen",
        "session_end",
        "printing",
    }
    valid_actions = {"http_callback"}

    for cfg in configs:
        if cfg.get("event_type") not in valid_event_types:
            raise HTTPException(
                status_code=400, detail=f"Invalid event_type: {cfg.get('event_type')}"
            )
        if cfg.get("action_type") not in valid_actions:
            raise HTTPException(status_code=400, detail="Only HTTP callback triggers are supported")
        if not cfg.get("target"):
            raise HTTPException(status_code=400, detail="target is required")

    trigger_service = TriggerService(db)
    try:
        created = await trigger_service.update_config(event_id, configs)
        return [
            {
                "id": str(c.id),
                "event_id": str(c.event_id),
                "event_type": (
                    c.event_type.value if hasattr(c.event_type, "value") else str(c.event_type)
                ),
                "enabled": c.enabled if hasattr(c, "enabled") else bool(cfg.get("enabled", False)),
                "action_type": (
                    c.action_type.value if hasattr(c.action_type, "value") else str(c.action_type)
                ),
                "target": c.target,
                "payload_template": c.payload_template or {},
                "timeout": c.timeout,
                "retry": c.retry,
            }
            for c in created
        ]
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update trigger configs: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/test", response_model=dict)
async def test_trigger(
    config: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Test a single trigger configuration"""
    from app.models.models import TriggerAction, TriggerType

    trigger_service = TriggerService(db)

    try:
        event_id = UUID(config.get("event_id"))
        event_service = EventService(db)
        event = await event_service.get_event(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        await check_team_member(event.team_id, current_user, db)
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid event_id")

    try:
        event_type = TriggerType(config.get("event_type", "session_start"))
        action_type = TriggerAction(config.get("action_type", "http_callback"))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid trigger type")

    if action_type != TriggerAction.HTTP_CALLBACK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HTTP callback triggers are supported",
        )
    temp_config = TriggerConfigModel(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        event_id=event_id,
        event_type=event_type,
        enabled=True,
        action_type=action_type,
        target=config.get("target", "http://localhost:9999/test"),
        payload_template=config.get("payload_template", {}),
        timeout=config.get("timeout", 10),
        retry=1,
    )

    try:
        trigger_service._validate_http_callback_target(temp_config.target)
        log_entry = await trigger_service.test_trigger(temp_config)
        return {
            "success": log_entry.success,
            "response_status": log_entry.response_status,
            "response_data": log_entry.response_data,
            "duration_ms": log_entry.duration_ms,
            "attempt_count": log_entry.attempt_count,
        }
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Trigger test failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/logs/{event_id}", response_model=List[dict])
async def get_trigger_logs(
    event_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get trigger execution logs for an event"""
    event_service = EventService(db)
    event = await event_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    await check_team_member(event.team_id, current_user, db)

    trigger_service = TriggerService(db)
    logs = await trigger_service.get_logs(event_id, skip, limit)

    return [
        {
            "id": str(l.id),
            "trigger_id": str(l.trigger_id),
            "event_id": str(l.event_id),
            "event_type": (
                l.event_type.value if hasattr(l.event_type, "value") else str(l.event_type)
            ),
            "success": l.success,
            "response_status": l.response_status,
            "response_data": l.response_data,
            "duration_ms": l.duration_ms,
            "attempt_count": l.attempt_count,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]
