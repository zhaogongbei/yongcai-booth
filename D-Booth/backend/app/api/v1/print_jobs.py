from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.api.deps import check_team_member, get_current_active_user, get_db
from app.core.database import get_session_maker
from app.models.models import Event, Photo, PrintJobStatus, Template, User
from app.schemas.print_job import PrintJobCreate, PrintJobResponse, PrintJobUpdate
from app.services.print_service import PrintService

router = APIRouter()


def _required_template_photo_count(template_layers: object) -> int:
    if not isinstance(template_layers, dict):
        return 0

    required = 0
    for element in template_layers.get("elements") or []:
        if not isinstance(element, dict):
            continue
        if element.get("type") != "photo" or element.get("visible") is False:
            continue
        props = element.get("props") or {}
        try:
            photo_number = int(props.get("photoNumber") or 1)
        except (TypeError, ValueError):
            photo_number = 1
        required = max(required, photo_number)
    return required


async def _get_photo_event(photo_id: UUID, db: AsyncSession) -> tuple[Photo, Event]:
    photo_result = await db.execute(select(Photo).where(Photo.id == photo_id).options(noload("*")))
    photo = photo_result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    event_result = await db.execute(
        select(Event).where(Event.id == photo.event_id).options(noload("*"))
    )
    event = event_result.scalar_one_or_none()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found for photo"
        )
    return photo, event


async def _verify_photo_team_access(photo_id: Optional[UUID], current_user: User, db: AsyncSession):
    """Helper: verify the photo (and its event's team) belongs to the current user's team."""
    if not photo_id:
        return
    _, event = await _get_photo_event(photo_id, db)
    await check_team_member(event.team_id, current_user, db)


async def _verify_template_matches_photo_team(
    template_id: Optional[UUID], photo_id: UUID, current_user: User, db: AsyncSession
) -> Optional[Template]:
    if not template_id:
        return None

    _, event = await _get_photo_event(photo_id, db)
    template_result = await db.execute(
        select(Template).where(Template.id == template_id).options(noload("*"))
    )
    template = template_result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    await check_team_member(template.team_id, current_user, db)
    if template.team_id != event.team_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template must belong to the same team as the photo event",
        )
    return template


async def _verify_template_photo_count(
    template: Optional[Template], photo_id: UUID, db: AsyncSession
):
    if not template:
        return

    required_count = _required_template_photo_count(template.layers)
    if required_count <= 1:
        return

    photo, _ = await _get_photo_event(photo_id, db)
    if not photo.session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template requires {required_count} photos, but the print photo has no session",
        )

    count_result = await db.execute(
        select(func.count()).select_from(Photo).where(Photo.session_id == photo.session_id)
    )
    session_photo_count = count_result.scalar_one()
    if session_photo_count < required_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template requires {required_count} photos, but session has {session_photo_count}",
        )


async def _execute_print_job_background(job_id: UUID) -> None:
    async with get_session_maker()() as db:
        print_service = PrintService(db)
        await print_service.execute_print_job(job_id)


@router.get("", response_model=List[PrintJobResponse])
async def get_print_jobs(
    photo_id: Optional[UUID] = Query(None),
    job_status: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get print jobs with optional filters"""
    print_service = PrintService(db)

    if photo_id:
        await _verify_photo_team_access(photo_id, current_user, db)
        return await print_service.get_print_jobs(photo_id=photo_id, skip=skip, limit=limit)

    # IMPORTANT: Always scope to user's teams (no global queries by status/channel alone)
    # Prevents cross-team data leakage
    return await print_service.get_print_jobs_visible_to_user(
        user_id=current_user.id, status=job_status, skip=skip, limit=limit
    )


@router.post("", response_model=PrintJobResponse, status_code=status.HTTP_201_CREATED)
async def create_print_job(
    job_in: PrintJobCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new print job"""
    # IDOR guard: verify the photo belongs to user's team
    await _verify_photo_team_access(job_in.photo_id, current_user, db)
    template = await _verify_template_matches_photo_team(
        job_in.template_id, job_in.photo_id, current_user, db
    )
    await _verify_template_photo_count(template, job_in.photo_id, db)

    print_service = PrintService(db)

    try:
        job = await print_service.create_print_job(job_in)
        queued_job = await print_service.update_print_job(
            job.id, PrintJobUpdate(status=PrintJobStatus.QUEUED)
        )
        background_tasks.add_task(_execute_print_job_background, job.id)
        if queued_job:
            return queued_job
        return job
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{job_id}", response_model=PrintJobResponse)
async def get_print_job(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get print job by ID"""
    print_service = PrintService(db)

    job = await print_service.get_print_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Print job not found")

    # Verify team membership via photo -> event -> team
    await _verify_photo_team_access(job.photo_id, current_user, db)

    return job


@router.patch("/{job_id}", response_model=PrintJobResponse)
async def update_print_job(
    job_id: UUID,
    job_in: PrintJobUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update print job status"""
    print_service = PrintService(db)

    existing_job = await print_service.get_print_job(job_id)
    if not existing_job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Print job not found")

    await _verify_photo_team_access(existing_job.photo_id, current_user, db)

    job = await print_service.update_print_job(job_id, job_in)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Print job not found")

    return job


@router.post("/{job_id}/retry", response_model=PrintJobResponse)
async def retry_print_job(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed print job"""
    print_service = PrintService(db)

    existing_job = await print_service.get_print_job(job_id)
    if not existing_job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Print job not found")

    await _verify_photo_team_access(existing_job.photo_id, current_user, db)

    try:
        job = await print_service.retry_print_job(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Print job not found")
        return job
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_print_job(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a print job"""
    print_service = PrintService(db)

    existing_job = await print_service.get_print_job(job_id)
    if not existing_job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Print job not found")

    await _verify_photo_team_access(existing_job.photo_id, current_user, db)

    success = await print_service.cancel_print_job(job_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Print job not found")
