from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_team_member, get_current_active_user, get_db
from app.models.models import User
from app.schemas.print_job import PrintJobCreate, PrintJobResponse, PrintJobUpdate
from app.services.event_service import EventService
from app.services.photo_service import PhotoService
from app.services.print_service import PrintService

router = APIRouter()


async def _verify_photo_team_access(photo_id: Optional[UUID], current_user: User, db: AsyncSession):
    """Helper: verify the photo (and its event's team) belongs to the current user's team."""
    if not photo_id:
        return
    photo_service = PhotoService(db)
    photo = await photo_service.get_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    event_service = EventService(db)
    event = await event_service.get_event(photo.event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found for photo"
        )
    await check_team_member(event.team_id, current_user, db)


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
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new print job"""
    # IDOR guard: verify the photo belongs to user's team
    await _verify_photo_team_access(job_in.photo_id, current_user, db)

    print_service = PrintService(db)

    try:
        job = await print_service.create_print_job(job_in)
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
