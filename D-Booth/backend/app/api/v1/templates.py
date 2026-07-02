from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_active_user, check_team_member
from app.services.template_service import TemplateService
from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateResponse
from app.models.models import User

router = APIRouter()


class TemplateValidateRequest(BaseModel):
    template_data: dict


class TemplateValidateResponse(BaseModel):
    valid: bool
    message: str = ""


class TemplateDuplicateRequest(BaseModel):
    new_name: Optional[str] = Field(None, max_length=255)


@router.get("", response_model=List[TemplateResponse])
async def get_templates(
    team_id: UUID = Query(...),
    is_public: bool = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get templates for a team"""
    # Verify the user is a member of the requested team
    await check_team_member(team_id, current_user, db)

    template_service = TemplateService(db)

    templates = await template_service.get_templates(
        team_id=team_id,
        is_public=is_public,
        skip=skip,
        limit=limit
    )
    return templates


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_in: TemplateCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new template"""
    # IDOR guard: verify team membership
    await check_team_member(template_in.team_id, current_user, db)

    template_service = TemplateService(db)

    try:
        template = await template_service.create_template(template_in)
        return template
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get template by ID"""
    template_service = TemplateService(db)

    template = await template_service.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    await check_team_member(template.team_id, current_user, db)

    return template


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID,
    template_in: TemplateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update template"""
    template_service = TemplateService(db)

    existing = await template_service.get_template(template_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    await check_team_member(existing.team_id, current_user, db)

    template = await template_service.update_template(template_id, template_in)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete template"""
    template_service = TemplateService(db)

    existing = await template_service.get_template(template_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    await check_team_member(existing.team_id, current_user, db)

    success = await template_service.delete_template(template_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )


@router.post("/validate", response_model=TemplateValidateResponse)
async def validate_template(
    request: TemplateValidateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Validate template JSON structure"""
    template_service = TemplateService(db)
    valid = template_service.validate_template(request.template_data)
    return TemplateValidateResponse(
        valid=valid,
        message="Template is valid" if valid else "Template validation failed"
    )


@router.post("/{template_id}/duplicate", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_template(
    template_id: UUID,
    request: Optional[TemplateDuplicateRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Duplicate a template"""
    template_service = TemplateService(db)

    existing = await template_service.get_template(template_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    await check_team_member(existing.team_id, current_user, db)

    new_name = request.new_name if request else None
    try:
        new_template = await template_service.duplicate_template(template_id, new_name)
        return new_template
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{template_id}/preview")
async def get_template_preview(
    template_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate template preview image"""
    template_service = TemplateService(db)

    existing = await template_service.get_template(template_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    await check_team_member(existing.team_id, current_user, db)

    try:
        preview_bytes = await template_service.generate_preview(template_id)
        return Response(content=preview_bytes, media_type="image/png")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )