from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from app.api.deps import get_current_active_user
from app.models.models import User

router = APIRouter()

UPLOADS_DIR = Path("uploads")

@router.get("/{file_path:path}")
async def serve_media(
    file_path: str,
    current_user: User = Depends(get_current_active_user),
):
    """Serve uploaded media files (authenticated users only)."""
    # Prevent path traversal
    safe_path = (UPLOADS_DIR / file_path).resolve()
    if not str(safe_path).startswith(str(UPLOADS_DIR.resolve())):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if not safe_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileResponse(safe_path)
