import os
import uuid
import aiofiles
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile

from app.core.config import get_settings

settings = get_settings()


class MediaService:
    """
    Service for handling media file storage.
    
    Currently stores files locally, but designed with an abstraction
    layer for future S3-compatible storage integration.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or settings.media_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def save_file(
        self, 
        file: UploadFile, 
        campaign_id: str,
        media_type: str
    ) -> tuple[str, str]:
        """
        Save an uploaded file.
        
        Args:
            file: The uploaded file
            campaign_id: ID of the campaign this file belongs to
            media_type: 'image' or 'video'
            
        Returns:
            Tuple of (stored_path, original_name)
        """
        # Create campaign directory
        campaign_dir = self.storage_path / campaign_id
        campaign_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_ext = Path(file.filename or "").suffix.lower()
        unique_name = f"{uuid.uuid4()}{file_ext}"
        file_path = campaign_dir / unique_name
        
        # Validate extension
        if media_type == "image":
            if file_ext not in settings.allowed_image_extensions:
                raise ValueError(f"Invalid image extension: {file_ext}")
        elif media_type == "video":
            if file_ext not in settings.allowed_video_extensions:
                raise ValueError(f"Invalid video extension: {file_ext}")
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            
            # Check file size
            size_mb = len(content) / (1024 * 1024)
            if size_mb > settings.max_file_size_mb:
                raise ValueError(f"File too large: {size_mb:.1f}MB (max {settings.max_file_size_mb}MB)")
            
            await f.write(content)
        
        return str(file_path), file.filename or unique_name
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if deleted, False if file didn't exist
        """
        path = Path(file_path)
        if path.exists():
            path.unlink()
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
        # In local dev, return relative path for serving via API
        return f"/media/{file_path}"


# Singleton instance
_media_service: Optional[MediaService] = None


def get_media_service() -> MediaService:
    """Get the media service singleton."""
    global _media_service
    if _media_service is None:
        _media_service = MediaService()
    return _media_service
