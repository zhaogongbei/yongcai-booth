from typing import List
from uuid import UUID, uuid4
import secrets

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from app.api.deps import get_db, get_current_active_user, check_team_member
from app.services.trigger_service import WebhookService
from app.models.models import User, Webhook as WebhookModel

router = APIRouter()


class WebhookCreate(BaseModel):
    url: str
    events: List[str] = []
    enabled: bool = True


class WebhookUpdate(BaseModel):
    url: str | None = None
    events: List[str] | None = None
    enabled: bool | None = None


class WebhookCreateResponse(BaseModel):
    id: str
    url: str
    events: List[str]
    enabled: bool
    secret: str


@router.post("", response_model=WebhookCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    data: WebhookCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new webhook for the user's team"""
    # For simplicity, create webhook for user's first team
    # In production, you'd have team selection
    from app.services.team_service import TeamService
    team_service = TeamService(db)
    teams = await team_service.get_user_teams(current_user.id)
    if not teams:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a team to create webhooks"
        )
    team_id = teams[0].id

    webhook_data = {
        "team_id": team_id,
        "url": data.url,
        "events": data.events,
        "enabled": data.enabled,
        "secret": secrets.token_hex(32),
    }

    webhook_service = WebhookService(db)
    webhook = await webhook_service.create_webhook(webhook_data)

    return WebhookCreateResponse(
        id=str(webhook.id),
        url=webhook.url,
        events=webhook.events or [],
        enabled=webhook.enabled,
        secret=webhook.secret,
    )


@router.get("", response_model=List[dict])
async def list_webhooks(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all webhooks for the user's teams"""
    from app.services.team_service import TeamService
    team_service = TeamService(db)
    teams = await team_service.get_user_teams(current_user.id)

    all_webhooks = []
    webhook_service = WebhookService(db)

    for team in teams:
        webhooks = await webhook_service.get_webhooks(team.id)
        all_webhooks.extend(webhooks)

    return [
        {
            "id": str(w.id),
            "team_id": str(w.team_id),
            "url": w.url,
            "events": w.events or [],
            "enabled": w.enabled,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        }
        for w in all_webhooks
    ]


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a webhook"""
    webhook_service = WebhookService(db)
    success = await webhook_service.delete_webhook(webhook_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )


@router.get("/{webhook_id}/logs", response_model=List[dict])
async def get_webhook_logs(
    webhook_id: UUID,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get webhook dispatch logs"""
    webhook_service = WebhookService(db)
    logs = await webhook_service.get_webhook_logs(webhook_id, skip, limit)

    return [
        {
            "id": str(l.id),
            "webhook_id": str(l.webhook_id),
            "event_type": l.event_type,
            "success": l.success,
            "response_status": l.response_status,
            "response_data": l.response_data,
            "duration_ms": l.duration_ms,
            "attempt_count": l.attempt_count,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]