import os
import uuid
import logging
import aiofiles
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile
from io import BytesIO

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# File signatures (magic bytes) for validation
FILE_SIGNATURES = {
    # Images
    b'\xff\xd8\xff': 'image/jpeg',  # JPEG
    b'\x89PNG\r\n\x1a\n': 'image/png',  # PNG
    b'GIF87a': 'image/gif',  # GIF87a
    b'GIF89a': 'image/gif',  # GIF89a
    b'RIFF': 'image/webp',  # WebP (partial, needs WEBP check)
    # Videos
    b'\x00\x00\x00\x18ftypmp42': 'video/mp4',  # MP4 (one variant)
    b'\x00\x00\x00\x1cftypmp42': 'video/mp4',  # MP4 (another variant)
    b'\x00\x00\x00\x20ftypisom': 'video/mp4',  # MP4 (isom)
    b'\x00\x00\x00': 'video/mp4',  # Generic MP4 start (will check ftyp later)
    b'RIFF....AVI': 'video/avi',  # AVI
    b'\x1aE\xdf\xa3': 'video/webm',  # WebM
}

# Allowed MIME types
ALLOWED_IMAGE_MIMES = {
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
}

ALLOWED_VIDEO_MIMES = {
    'video/mp4',
    'video/quicktime',
    'video/x-msvideo',
    'video/webm',
}


def detect_mime_type(content: bytes) -> Optional[str]:
    """
    Detect MIME type from file content using magic bytes.

    Args:
        content: File content bytes

    Returns:
        Detected MIME type or None
    """
    if len(content) < 12:
        return None

    # Check JPEG
    if content[:3] == b'\xff\xd8\xff':
        return 'image/jpeg'

    # Check PNG
    if content[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'

    # Check GIF
    if content[:6] in (b'GIF87a', b'GIF89a'):
        return 'image/gif'

    # Check WebP (RIFF....WEBP)
    if content[:4] == b'RIFF' and content[8:12] == b'WEBP':
        return 'image/webp'

    # Check MP4/MOV (ftyp box)
    if content[4:8] == b'ftyp':
        ftyp_brand = content[8:12]
        if ftyp_brand in (b'mp41', b'mp42', b'isom', b'avc1', b'M4V ', b'M4A '):
            return 'video/mp4'
        if ftyp_brand == b'qt  ':
            return 'video/quicktime'

    # Check WebM
    if content[:4] == b'\x1aE\xdf\xa3':
        return 'video/webm'

    # Check AVI
    if content[:4] == b'RIFF' and content[8:12] == b'AVI ':
        return 'video/x-msvideo'

    return None


def validate_image_content(content: bytes) -> bool:
    """
    Validate image content by checking magic bytes and basic structure.

    Args:
        content: Image file content

    Returns:
        True if valid image
    """
    mime = detect_mime_type(content)
    if mime not in ALLOWED_IMAGE_MIMES:
        return False

    # Additional validation with PIL if available
    try:
        from PIL import Image
        img = Image.open(BytesIO(content))
        img.verify()

        # Check dimensions (max 10000x10000)
        img = Image.open(BytesIO(content))  # Need to reopen after verify
        if img.size[0] > 10000 or img.size[1] > 10000:
            logger.warning(f"Image too large: {img.size}")
            return False

        return True
    except ImportError:
        # PIL not available, just use magic bytes check
        logger.debug("PIL not available, using magic bytes only")
        return True
    except Exception as e:
        logger.warning(f"Image validation failed: {e}")
        return False


def validate_video_content(content: bytes) -> bool:
    """
    Validate video content by checking magic bytes.

    Args:
        content: Video file content

    Returns:
        True if valid video
    """
    mime = detect_mime_type(content)
    return mime in ALLOWED_VIDEO_MIMES


class MediaService:
    """
    Service for handling media file storage.

    Currently stores files locally, but designed with an abstraction
    layer for future S3-compatible storage integration.
    """

    def __init__(self, storage_path: Optional[str] = None):
        # Convert relative path to absolute path based on backend directory
        storage_path_str = storage_path or settings.media_storage_path
        storage_path_obj = Path(storage_path_str)

        # If relative path, make it absolute relative to backend directory
        if not storage_path_obj.is_absolute():
            # Get the backend directory (parent of app directory)
            backend_dir = Path(__file__).parent.parent.parent
            storage_path_obj = backend_dir / storage_path_obj

        self.storage_path = storage_path_obj.resolve()  # Get canonical absolute path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"MediaService initialized with storage path: {self.storage_path}")

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to prevent path traversal and other attacks.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        if not filename:
            return "upload"

        # Remove directory components
        filename = os.path.basename(filename)

        # Remove dangerous characters
        safe_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-')
        sanitized = ''.join(c if c in safe_chars else '_' for c in filename)

        # Ensure it doesn't start with a dot (hidden file)
        if sanitized.startswith('.'):
            sanitized = '_' + sanitized[1:]

        return sanitized or "upload"

    async def save_file(
        self,
        file: UploadFile,
        campaign_id: str,
        media_type: str
    ) -> tuple[str, str]:
        """
        Save an uploaded file with security validation.

        Args:
            file: The uploaded file
            campaign_id: ID of the campaign this file belongs to
            media_type: 'image' or 'video'

        Returns:
            Tuple of (stored_path, original_name)

        Raises:
            ValueError: If file validation fails
        """
        # Validate campaign_id format (prevent path traversal)
        try:
            uuid.UUID(campaign_id)
        except ValueError:
            raise ValueError("Invalid campaign ID format")

        # Sanitize filename
        original_name = self._sanitize_filename(file.filename or "upload")
        file_ext = Path(original_name).suffix.lower()

        # Validate extension first
        if media_type == "image":
            if file_ext not in settings.allowed_image_extensions:
                raise ValueError(f"Invalid image extension: {file_ext}")
        elif media_type == "video":
            if file_ext not in settings.allowed_video_extensions:
                raise ValueError(f"Invalid video extension: {file_ext}")
        else:
            raise ValueError(f"Invalid media type: {media_type}")

        # Read file content
        content = await file.read()

        # Check file size
        size_mb = len(content) / (1024 * 1024)
        if size_mb > settings.max_file_size_mb:
            raise ValueError(f"File too large: {size_mb:.1f}MB (max {settings.max_file_size_mb}MB)")

        # Validate content using magic bytes
        detected_mime = detect_mime_type(content)
        if detected_mime is None:
            raise ValueError("Unable to detect file type - invalid or corrupted file")

        if media_type == "image":
            if detected_mime not in ALLOWED_IMAGE_MIMES:
                raise ValueError(f"File content doesn't match image type. Detected: {detected_mime}")
            if not validate_image_content(content):
                raise ValueError("Invalid or corrupted image file")
        elif media_type == "video":
            if detected_mime not in ALLOWED_VIDEO_MIMES:
                raise ValueError(f"File content doesn't match video type. Detected: {detected_mime}")
            if not validate_video_content(content):
                raise ValueError("Invalid or corrupted video file")

        # Create campaign directory
        campaign_dir = self.storage_path / campaign_id
        campaign_dir.mkdir(parents=True, exist_ok=True)

        # Verify we're still in storage path (extra protection)
        if not str(campaign_dir.resolve()).startswith(str(self.storage_path.resolve())):
            raise ValueError("Invalid storage path detected")

        # Generate unique filename
        unique_name = f"{uuid.uuid4()}{file_ext}"
        file_path = campaign_dir / unique_name

        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        logger.info(f"Saved {media_type} file: {file_path} ({size_mb:.2f}MB)")

        return str(file_path), original_name

    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            file_path: Path to the file to delete

        Returns:
            True if deleted, False if file didn't exist
        """
        path = Path(file_path)

        # Security check - ensure we're in storage path
        try:
            if not str(path.resolve()).startswith(str(self.storage_path.resolve())):
                logger.warning(f"Attempted to delete file outside storage: {file_path}")
                return False
        except Exception:
            return False

        if path.exists():
            path.unlink()
            logger.info(f"Deleted file: {file_path}")
            return True
        return False

    async def get_file_path(self, relative_path: str) -> Optional[Path]:
        """
        Get the full path to a stored file.

        Args:
            relative_path: Relative path within storage

        Returns:
            Full path if exists, None otherwise
        """
        path = self.storage_path / relative_path

        # Security check
        try:
            if not str(path.resolve()).startswith(str(self.storage_path.resolve())):
                return None
        except Exception:
            return None

        if path.exists():
            return path
        return None

    def get_file_url(self, file_path: str) -> str:
        """
        Get a URL for accessing a stored file.

        For local dev, returns a relative path.
        For S3, would return a presigned URL.

        Args:
            file_path: Stored file path

        Returns:
            URL string
        """
        # Extract campaign_id and filename from path
        path = Path(file_path)
        if len(path.parts) >= 2:
            campaign_id = path.parts[-2]
            filename = path.parts[-1]
            return f"/media/{campaign_id}/{filename}"
        return f"/media/{path.name}"


# Singleton instance
_media_service: Optional[MediaService] = None


def get_media_service() -> MediaService:
    """Get the media service singleton."""
    global _media_service
    if _media_service is None:
        _media_service = MediaService()
    return _media_service
