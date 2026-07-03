import json
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_team, get_current_user
from app.core.database import get_db
from app.models.models import PropCategory, Team, User
from app.schemas.prop import AppliedPropRequest, PropCreate, PropResponse
from app.services.base_service import BusinessRuleError
from app.services.props_service import PropsService
from app.services.storage_service import r2_storage

router = APIRouter(tags=["props"])


@router.get("", response_model=dict)
async def get_props(
    category: Optional[PropCategory] = Query(None, description="Filter by category"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=200, description="Maximum number of items to return"),
    current_team: Team = Depends(get_current_team),
    db: AsyncSession = Depends(get_db),
):
    """Get props list (team private + public props)"""
    props_service = PropsService(db)

    props, total = await props_service.get_props(
        team_id=str(current_team.id), category=category, skip=skip, limit=limit
    )

    return {
        "data": [PropResponse.from_orm(prop) for prop in props],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.post("", response_model=PropResponse, status_code=status.HTTP_201_CREATED)
async def upload_prop(
    name: str = Query(..., description="Prop name"),
    category: PropCategory = Query(..., description="Prop category"),
    tags: Optional[List[str]] = Query(None, description="Prop tags"),
    file: UploadFile = File(..., description="PNG image file"),
    current_team: Team = Depends(get_current_team),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload custom prop (transparent PNG only)"""
    props_service = PropsService(db)

    try:
        prop = await props_service.upload_prop(
            team_id=str(current_team.id), file=file, name=name, category=category, tags=tags
        )
    except BusinessRuleError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PropResponse.from_orm(prop)


@router.delete("/{prop_id}", response_model=dict)
async def delete_prop(
    prop_id: UUID,
    current_team: Team = Depends(get_current_team),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a prop"""
    props_service = PropsService(db)

    try:
        success = await props_service.delete_prop(str(prop_id))
    except BusinessRuleError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not success:
        raise HTTPException(status_code=404, detail="Prop not found")

    return {"success": True}


@router.get("/categories", response_model=dict)
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Get all prop categories"""
    props_service = PropsService(db)

    categories = await props_service.get_categories()

    return {"data": categories}


@router.post("/apply", response_model=dict)
async def apply_props(
    image_file: UploadFile = File(..., description="Base image file"),
    applied_props: str = Form(..., description="JSON array of props to apply"),
    current_team: Team = Depends(get_current_team),
    db: AsyncSession = Depends(get_db),
):
    """Apply props to an image"""
    props_service = PropsService(db)

    # Read image bytes
    image_bytes = await image_file.read()

    # Convert request to AppliedProp objects
    from app.services.props_service import AppliedProp

    try:
        parsed_props = [
            AppliedPropRequest.model_validate(item) for item in json.loads(applied_props)
        ]
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid applied_props payload: {exc}")

    props = [
        AppliedProp(
            prop_id=str(p.prop_id),
            x=p.x,
            y=p.y,
            scale=p.scale,
            rotation=p.rotation,
            flip_h=p.flip_h,
            flip_v=p.flip_v,
            opacity=p.opacity,
        )
        for p in parsed_props
    ]

    # Apply props
    result_bytes = await props_service.apply_props(image_bytes, props)

    # Upload result
    import uuid

    file_id = str(uuid.uuid4())
    filename = f"processed/{file_id}_with_props.png"

    from io import BytesIO

    result_io = BytesIO(result_bytes)
    result_url = await r2_storage.upload_file(
        result_io.getvalue(), filename, content_type="image/png"
    )

    return {"result_url": result_url}
