from typing import Optional, List
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile
from PIL import Image, ImageOps
import io
import re
from pathlib import Path

from app.repositories.photo_repository import PhotoRepository, PhotoSessionRepository
from app.schemas.photo import PhotoCreate, PhotoUpdate, PhotoSessionCreate
from app.models.models import Photo, PhotoSession
from app.services.storage_service import r2_storage
from app.services.beauty_service import BeautyParams, beauty_processor
from app.core.logging import logger


class PhotoService:
    """Service for photo and session business logic"""
    
    ALLOWED_TYPES = {'image/jpeg', 'image/png', 'image/jpg', 'image/webp', 'image/gif'}
    IMAGE_FORMAT_TYPES = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
        "GIF": "image/gif",
    }
    CONTENT_TYPE_EXTENSIONS = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    MAX_FILE_SIZE_MB = 10
    MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
    MAX_IMAGE_PIXELS = 24_000_000

    THUMBNAIL_SIZES = {
        'micro': (48, 48),       # 极缩略图(列表快速预览)
        'thumb': (200, 200),     # 缩略图(网格列表)
        'medium': (600, 600),    # 中图(详情预览)
        'large': (1200, 1200),   # 大图(全屏预览)
    }

    WEBP_QUALITY = 80
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.photo_repo = PhotoRepository(db)
        self.session_repo = PhotoSessionRepository(db)
    
    async def get_photo(self, photo_id: UUID) -> Optional[Photo]:
        """Get photo by ID"""
        return await self.photo_repo.get(photo_id)
    
    async def get_photos(
        self,
        event_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Photo]:
        """Get photos with filters"""
        if event_id:
            return await self.photo_repo.get_by_event(event_id, skip, limit)
        elif session_id:
            return await self.photo_repo.get_by_session(session_id, skip, limit)
        else:
            return await self.photo_repo.get_all(skip, limit)
    
    async def create_photo(self, photo_in: PhotoCreate) -> Photo:
        """Create a new photo record"""
        if photo_in.session_id:
            session = await self.session_repo.get(photo_in.session_id)
            if not session:
                raise ValueError("Photo session not found")
            if session.event_id != photo_in.event_id:
                raise ValueError("Photo session does not belong to this event")

        photo_data = photo_in.model_dump()
        if "metadata" in photo_data:
            photo_data["metadata_"] = photo_data.pop("metadata")
        return await self.photo_repo.create(photo_data)
    
    async def upload_photo(
        self,
        file: UploadFile,
        event_id: UUID,
        session_id: Optional[UUID] = None,
        beauty_params: Optional[BeautyParams] = None,
    ) -> Photo:
        """Upload photo file, optionally apply built-in AI beauty, and create record."""
        
        declared_content_type = (file.content_type or "").lower()
        if declared_content_type and declared_content_type not in self.ALLOWED_TYPES | {"application/octet-stream"}:
            raise ValueError(f"File type {file.content_type} not allowed. Allowed types: {self.ALLOWED_TYPES}")

        if session_id:
            session = await self.session_repo.get(session_id)
            if not session:
                raise ValueError("Photo session not found")
            if session.event_id != event_id:
                raise ValueError("Photo session does not belong to this event")

        # Read file
        file_data = await file.read()
        if not file_data:
            raise ValueError("Uploaded file is empty")
        
        # Validate file size
        if len(file_data) > self.MAX_FILE_SIZE:
            raise ValueError(f"File size exceeds maximum allowed size of {self.MAX_FILE_SIZE_MB}MB")
        
        # Validate it's a valid image - verify FIRST, then open
        try:
            img_verify = Image.open(io.BytesIO(file_data))
            img_verify.verify()  # Verify first without decoding pixel data

            # Re-open to normalize orientation and get dimensions (verify() invalidates the image object)
            img_source = Image.open(io.BytesIO(file_data))
            detected_content_type = self.IMAGE_FORMAT_TYPES.get(img_source.format or "")
            if detected_content_type not in self.ALLOWED_TYPES:
                raise ValueError("File content is not an allowed image type")
            img_open = ImageOps.exif_transpose(img_source)
            width, height = img_open.size
            if width * height > self.MAX_IMAGE_PIXELS:
                raise ValueError("Image dimensions exceed maximum allowed pixel count")
            storage_data = self._encode_for_storage(img_open, detected_content_type)
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Invalid image file: {str(e)}")
        
        # Preserve the submitted name only as metadata. Storage names are server-generated
        # to avoid overwrites and extension/content mismatches.
        safe_original_filename = re.sub(r'[^\w\-.]', '_', file.filename or 'upload') if file.filename else 'upload'
        safe_filename = f"{uuid4().hex}{self.CONTENT_TYPE_EXTENSIONS[detected_content_type]}"

        # Upload to R2 storage
        try:
            if r2_storage.is_available():
                original_url = await r2_storage.upload_file(
                    file_data=storage_data,
                    filename=safe_filename,
                    content_type=detected_content_type,
                    folder=f"photos/{event_id}"
                )

                # Generate all thumbnails and WebP versions
                thumbnail_urls = await self._generate_all_thumbnails(storage_data, safe_filename, event_id, detected_content_type)
                webp_url = await self._transcode_to_webp(storage_data, safe_filename, event_id)
            else:
                # Fallback: save locally (for development)
                logger.warning("R2 storage not configured, using local storage")
                original_url = self._save_local_file(
                    storage_data,
                    safe_filename,
                    folder=f"photos/{event_id}",
                )
                thumbnail_urls = await self._generate_all_thumbnails(
                    storage_data,
                    safe_filename,
                    event_id,
                    detected_content_type,
                )
                webp_url = await self._transcode_to_webp(storage_data, safe_filename, event_id)
                
        except Exception as e:
            logger.error(f"Failed to upload photo: {e}")
            raise ValueError(f"Failed to upload photo: {str(e)}")

        # ── Built-in AI beauty processing ──────────────────────
        processed_url = None
        if beauty_params is not None and any(
            getattr(beauty_params, f, 0) > 0 for f in BeautyParams.model_fields
        ):
            try:
                beauty_bytes = beauty_processor.process_image(
                    file_data, beauty_params, quality="full"
                )
                beauty_name = f"beauty_{safe_filename}"
                if r2_storage.is_available():
                    processed_url = await r2_storage.upload_file(
                        file_data=beauty_bytes,
                        filename=beauty_name,
                        content_type="image/jpeg",
                        folder=f"photos/{event_id}/beauty",
                    )
                else:
                    processed_url = self._save_local_file(
                        beauty_bytes,
                        beauty_name,
                        folder=f"photos/{event_id}/beauty",
                    )
                logger.info(f"Beauty processing applied to {safe_filename}")
            except Exception as e:
                logger.warning(f"Beauty processing skipped (non-fatal): {e}")
                processed_url = None

        # Create photo record
        photo_data = PhotoCreate(
            event_id=event_id,
            session_id=session_id,
            original_url=original_url,
            processed_url=processed_url,
            thumbnail_url=thumbnail_urls.get('thumb'),
            thumbnail_urls=thumbnail_urls,
            webp_url=webp_url,
            file_size=len(file_data),
            width=width,
            height=height,
            metadata={
                "original_filename": safe_original_filename,
                "stored_filename": safe_filename,
                "declared_content_type": declared_content_type or None,
                "detected_content_type": detected_content_type,
            }
        )

        return await self.create_photo(photo_data)

    async def _fire_trigger(self, event_id: UUID, trigger_type: str, extra_context: dict = None):
        """Fire a trigger, never let it break the main flow."""
        try:
            from app.services.trigger_service import TriggerService
            context = {"event_id": str(event_id)}
            if extra_context:
                context.update(extra_context)
            await TriggerService(self.db).execute_triggers(trigger_type, context)
        except Exception:
            pass

    @staticmethod
    def _encode_for_storage(image: Image.Image, content_type: str) -> bytes:
        """Encode an already-validated image after EXIF orientation normalization."""
        output = io.BytesIO()
        if content_type == "image/png":
            image.save(output, format="PNG", optimize=True)
        elif content_type == "image/webp":
            image.save(output, format="WEBP", quality=90, method=6)
        elif content_type == "image/gif":
            # Preserve original frame behavior as much as possible by not converting animated GIFs.
            image.save(output, format="GIF")
        else:
            image.convert("RGB").save(output, format="JPEG", quality=92, optimize=True)
        return output.getvalue()

    @staticmethod
    def _save_local_file(file_data: bytes, filename: str, folder: str) -> str:
        """Save a file under the local uploads directory and return its public path."""
        safe_folder = folder.strip("/").replace("\\", "/")
        target_dir = Path("uploads") / safe_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename
        target_path.write_bytes(file_data)
        return f"/uploads/{safe_folder}/{filename}"
    
    async def _generate_all_thumbnails(
        self,
        file_data: bytes,
        filename: str,
        event_id: UUID,
        content_type: str
    ) -> dict:
        """Generate all thumbnail sizes and upload"""
        thumbnails = {}
        base_filename = Path(filename).stem

        try:
            image = Image.open(io.BytesIO(file_data)).convert("RGB")

            for size_name, (target_width, target_height) in self.THUMBNAIL_SIZES.items():
                # Create copy of original image for resizing
                img = image.copy()

                # Resize and crop to exact dimensions
                img.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)

                # Center crop if aspect ratio differs
                width, height = img.size
                left = (width - target_width) / 2
                top = (height - target_height) / 2
                right = (width + target_width) / 2
                bottom = (height + target_height) / 2
                img = img.crop((left, top, right, bottom))

                # Save thumbnail to bytes
                thumb_io = io.BytesIO()
                img.save(thumb_io, format='JPEG', quality=85)
                thumb_data = thumb_io.getvalue()

                # Upload thumbnail
                thumb_filename = f"{base_filename}_{size_name}.jpg"
                folder = f"thumbnails/{event_id}"

                if r2_storage.is_available():
                    thumb_url = await r2_storage.upload_file(
                        file_data=thumb_data,
                        filename=thumb_filename,
                        content_type='image/jpeg',
                        folder=folder
                    )
                else:
                    thumb_url = self._save_local_file(
                        thumb_data,
                        thumb_filename,
                        folder=folder,
                    )

                thumbnails[size_name] = thumb_url

            return thumbnails

        except Exception as e:
            logger.error(f"Failed to generate thumbnails: {e}")
            return {}

    async def _transcode_to_webp(
        self,
        file_data: bytes,
        filename: str,
        event_id: UUID
    ) -> Optional[str]:
        """Transcode image to WebP format"""
        try:
            image = Image.open(io.BytesIO(file_data)).convert("RGB")

            # Save as WebP
            webp_io = io.BytesIO()
            image.save(webp_io, format="WEBP", quality=self.WEBP_QUALITY, method=6)
            webp_data = webp_io.getvalue()

            webp_filename = f"{Path(filename).stem}.webp"
            folder = f"photos/webp/{event_id}"

            if r2_storage.is_available():
                return await r2_storage.upload_file(
                    file_data=webp_data,
                    filename=webp_filename,
                    content_type='image/webp',
                    folder=folder
                )
            else:
                return self._save_local_file(
                    webp_data,
                    webp_filename,
                    folder=folder,
                )

        except Exception as e:
            logger.error(f"Failed to transcode to WebP: {e}")
            return None

    async def _generate_thumbnail(
        self,
        file_data: bytes,
        filename: str,
        event_id: UUID,
        thumbnail_size: tuple = (300, 300)
    ) -> str:
        """Generate and upload thumbnail (legacy method)"""
        try:
            image = Image.open(io.BytesIO(file_data)).convert("RGB")
            image.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)

            # Save thumbnail to bytes
            thumb_io = io.BytesIO()
            image.save(thumb_io, format='JPEG', quality=85)
            thumb_data = thumb_io.getvalue()

            # Upload thumbnail
            if r2_storage.is_available():
                thumb_filename = f"thumb_{filename}"
                thumbnail_url = await r2_storage.upload_file(
                    file_data=thumb_data,
                    filename=thumb_filename,
                    content_type='image/jpeg',
                    folder=f"photos/{event_id}/thumbnails"
                )
                return thumbnail_url
            else:
                thumb_name = f"thumb_{Path(filename).stem}.jpg"
                return self._save_local_file(
                    thumb_data,
                    thumb_name,
                    folder=f"photos/{event_id}/thumbnails",
                )

        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            return None
    
    async def update_photo(
        self,
        photo_id: UUID,
        photo_in: PhotoUpdate
    ) -> Optional[Photo]:
        """Update photo metadata"""
        update_data = photo_in.model_dump(exclude_unset=True)
        if "metadata" in update_data:
            update_data["metadata_"] = update_data.pop("metadata")
        return await self.photo_repo.update(photo_id, update_data)
    
    async def delete_photo(self, photo_id: UUID) -> bool:
        """Delete a photo and its files"""
        photo = await self.get_photo(photo_id)
        if not photo:
            return False
        
        # Delete from storage
        if r2_storage.is_available():
            try:
                await r2_storage.delete_file(photo.original_url)
                if photo.thumbnail_url:
                    await r2_storage.delete_file(photo.thumbnail_url)
            except Exception as e:
                logger.error(f"Failed to delete photo files: {e}")
        
        # Delete database record
        return await self.photo_repo.delete(photo_id)
    
    async def create_session(
        self,
        session_in: PhotoSessionCreate
    ) -> PhotoSession:
        """Create a new photo session"""
        session_data = session_in.model_dump()
        return await self.session_repo.create(session_data)
    
    async def get_session(self, session_id: UUID) -> Optional[PhotoSession]:
        """Get session by ID"""
        return await self.session_repo.get(session_id)

    async def get_sessions(
        self,
        event_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[PhotoSession]:
        """Get photo sessions for an event."""
        return await self.session_repo.get_by_event(event_id, skip, limit)
    
    async def complete_session(self, session_id: UUID) -> Optional[PhotoSession]:
        """Mark session as completed"""
        return await self.session_repo.complete_session(session_id)
    
    async def generate_upload_url(
        self,
        event_id: UUID,
        filename: str
    ) -> dict:
        """Generate presigned URL for photo upload to R2"""
        if not r2_storage.is_available():
            raise RuntimeError("R2 storage is not configured")

        # Sanitize filename - only keep alphanumeric, dots, hyphens, underscores
        safe_filename = re.sub(r'[^\w\-.]', '_', filename or 'upload')

        return await r2_storage.generate_presigned_url(
            filename=safe_filename,
            folder=f"photos/{event_id}",
            expires_in=3600
        )
