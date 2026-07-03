from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.deps import get_current_active_user
from app.models.models import User

router = APIRouter()

UPLOADS_DIR = Path("uploads")


def _ensure_within_uploads(path: Path) -> None:
    try:
        path.relative_to(UPLOADS_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get("/{file_path:path}")
async def serve_media(
    file_path: str,
    current_user: User = Depends(get_current_active_user),
):
    """Serve uploaded media files (authenticated users only)."""
    safe_path = (UPLOADS_DIR / file_path).resolve()
    _ensure_within_uploads(safe_path)
    if not safe_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileResponse(safe_path)
