import asyncio
import mimetypes
import re
from pathlib import Path
from typing import Optional
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import logger


class R2StorageService:
    """Cloudflare R2 (S3-compatible) storage service"""

    # Allowed folder prefixes to prevent path traversal
    ALLOWED_FOLDERS = {
        "photos",
        "templates",
        "uploads",
        "avatars",
        "exports",
        "props",
        "processed",
        "green-screen",
    }

    def __init__(self):
        self.client = None
        self.bucket_name = settings.R2_BUCKET_NAME

        # Only initialize if R2 credentials are configured
        if settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY:
            try:
                self.client = boto3.client(
                    "s3",
                    endpoint_url=settings.R2_ENDPOINT_URL,
                    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                    region_name=settings.R2_REGION,
                    config=Config(max_pool_connections=50),
                )
                logger.info("R2 storage client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize R2 client: {e}")
                self.client = None
        else:
            logger.warning("R2 credentials not configured, storage operations will be disabled")

    @staticmethod
    def _validate_folder(folder: str) -> str:
        """
        Validate and sanitize folder path to prevent path traversal.

        Args:
            folder: User-provided folder path

        Returns:
            Sanitized folder path

        Raises:
            ValueError: If path traversal is detected
        """
        # Remove leading/trailing slashes
        folder = folder.strip("/")

        # Check for path traversal attempts
        if ".." in folder or folder.startswith("/"):
            logger.warning(f"Path traversal attempt detected: {folder}")
            raise ValueError("Invalid folder path: path traversal detected")

        # Split path and validate each part
        parts = folder.split("/")
        if not parts or parts[0] not in R2StorageService.ALLOWED_FOLDERS:
            logger.warning(f"Invalid folder prefix: {folder}")
            raise ValueError(
                f"Invalid folder path: must start with one of {R2StorageService.ALLOWED_FOLDERS}"
            )

        # Sanitize each part (remove special chars)
        sanitized_parts = []
        for part in parts:
            safe_part = re.sub(r"[^\w\-]", "_", part)
            if safe_part and safe_part not in (".", ".."):
                sanitized_parts.append(safe_part)

        if not sanitized_parts:
            raise ValueError("Invalid folder path: empty after sanitization")

        return "/".join(sanitized_parts)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to remove dangerous characters.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove path components if present
        filename = Path(filename).name

        # Only keep alphanumeric, dots, hyphens, underscores
        safe_filename = re.sub(r"[^\w\-.]", "_", filename)

        # Prevent hidden files
        if safe_filename.startswith("."):
            safe_filename = "_" + safe_filename[1:]

        return safe_filename or "upload"

    def is_available(self) -> bool:
        """Check if R2 storage is configured and available"""
        return self.client is not None

    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        content_type: Optional[str] = None,
        folder: str = "uploads",
    ) -> str:
        """
        Upload file to R2 storage

        Args:
            file_data: File content as bytes
            filename: Original filename
            content_type: MIME type of the file
            folder: Folder path in bucket

        Returns:
            Public URL of uploaded file
        """
        if not self.is_available():
            raise RuntimeError("R2 storage is not configured")

        # Validate and sanitize folder path
        safe_folder = self._validate_folder(folder)

        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)

        # Generate unique filename
        file_ext = safe_filename.split(".")[-1] if "." in safe_filename else ""
        unique_filename = f"{uuid4()}.{file_ext}" if file_ext else str(uuid4())
        object_key = f"{safe_folder}/{unique_filename}"

        # Detect content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(safe_filename)
            content_type = content_type or "application/octet-stream"

        try:
            await asyncio.to_thread(
                self.client.put_object,
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file_data,
                ContentType=content_type,
                CacheControl="public, max-age=31536000",
            )

            # Generate public URL
            public_url = f"{settings.R2_ENDPOINT_URL}/{self.bucket_name}/{object_key}"

            logger.info(f"File uploaded successfully: {object_key}")
            return public_url

        except ClientError as e:
            logger.error(f"Failed to upload file to R2: {e}")
            raise RuntimeError(f"File upload failed: {str(e)}")

    async def delete_file(self, url: str) -> bool:
        """
        Delete file from R2 storage

        Args:
            url: Public URL of the file

        Returns:
            True if deleted successfully
        """
        if not self.is_available():
            return False

        try:
            # Extract object key from URL
            object_key = url.split(f"{self.bucket_name}/")[-1]

            await asyncio.to_thread(
                self.client.delete_object, Bucket=self.bucket_name, Key=object_key
            )

            logger.info(f"File deleted successfully: {object_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete file from R2: {e}")
            return False

    async def generate_presigned_url(
        self, filename: str, expires_in: int = 3600, folder: str = "uploads"
    ) -> dict:
        """
        Generate presigned URL for direct client upload

        Args:
            filename: Original filename
            expires_in: URL expiration time in seconds (default 1 hour)
            folder: Folder path in bucket

        Returns:
            Dict with upload_url and public_url
        """
        if not self.is_available():
            raise RuntimeError("R2 storage is not configured")

        # Validate and sanitize folder path
        safe_folder = self._validate_folder(folder)

        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)

        # Generate unique filename
        file_ext = safe_filename.split(".")[-1] if "." in safe_filename else ""
        unique_filename = f"{uuid4()}.{file_ext}" if file_ext else str(uuid4())
        object_key = f"{safe_folder}/{unique_filename}"

        try:
            # Generate presigned POST URL
            presigned_post = await asyncio.to_thread(
                self.client.generate_presigned_post,
                Bucket=self.bucket_name,
                Key=object_key,
                ExpiresIn=expires_in,
            )

            public_url = f"{settings.R2_ENDPOINT_URL}/{self.bucket_name}/{object_key}"

            return {
                "upload_url": presigned_post["url"],
                "fields": presigned_post["fields"],
                "public_url": public_url,
                "expires_in": expires_in,
            }

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise RuntimeError(f"Failed to generate upload URL: {str(e)}")


# Global instance
r2_storage = R2StorageService()
