import uuid
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User, Campaign, MediaAsset
from app.services.media_service import get_media_service
from app.services.campaign_service import get_campaign_service

router = APIRouter(prefix="/media", tags=["Media"])


async def get_current_user(
    x_user_id: str = Header(..., description="User ID from anonymous auth"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from header."""
    try:
        uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    query = select(User).where(User.id == x_user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.post("/upload")
async def upload_media(
    campaign_id: str = Form(...),
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload media file to a campaign.

    Accepts multipart/form-data with:
    - campaign_id: The campaign to attach the media to
    - file: The media file (image or video)
    - alt_text: Optional alt text for accessibility

    Returns the created media asset info.
    """
    # Validate campaign_id format
    try:
        uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")

    # Verify campaign exists and belongs to user
    campaign_query = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.user_id == user.id
    )
    result = await db.execute(campaign_query)
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Determine media type from file
    filename = file.filename or "upload"
    extension = filename.lower().split(".")[-1] if "." in filename else ""

    image_extensions = {"jpg", "jpeg", "png", "gif", "webp"}
    video_extensions = {"mp4", "mov", "avi", "webm"}

    if extension in image_extensions:
        media_type = "image"
    elif extension in video_extensions:
        media_type = "video"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {extension}"
        )

    # Save file
    media_service = get_media_service()
    campaign_service = get_campaign_service()

    try:
        path, original_name = await media_service.save_file(
            file, campaign_id, media_type
        )

        # Create media asset record
        media_asset = await campaign_service.add_media_asset(
            db, campaign_id, media_type, path, original_name, alt_text
        )

        await db.commit()

        return {
            "id": str(media_asset.id),
            "campaign_id": campaign_id,
            "type": media_type,
            "path": path,
            "original_name": original_name,
            "alt_text": alt_text,
            "url": f"/media/{campaign_id}/{os.path.basename(path)}"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{media_id}")
async def get_media(
    media_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get media asset info by ID."""
    try:
        uuid.UUID(media_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid media ID format")

    query = select(MediaAsset).where(MediaAsset.id == media_id)
    result = await db.execute(query)
    media = result.scalar_one_or_none()

    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Verify user owns the campaign
    campaign_query = select(Campaign).where(
        Campaign.id == media.campaign_id,
        Campaign.user_id == user.id
    )
    result = await db.execute(campaign_query)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Media not found")

    return {
        "id": str(media.id),
        "campaign_id": str(media.campaign_id),
        "type": media.type,
        "path": media.path,
        "original_name": media.original_name,
        "alt_text": media.alt_text,
    }


@router.delete("/{media_id}")
async def delete_media(
    media_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a media asset."""
    try:
        uuid.UUID(media_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid media ID format")

    query = select(MediaAsset).where(MediaAsset.id == media_id)
    result = await db.execute(query)
    media = result.scalar_one_or_none()

    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Verify user owns the campaign
    campaign_query = select(Campaign).where(
        Campaign.id == media.campaign_id,
        Campaign.user_id == user.id
    )
    result = await db.execute(campaign_query)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Media not found")

    # Delete file
    media_service = get_media_service()
    await media_service.delete_file(media.path)

    # Delete record
    await db.delete(media)
    await db.commit()

    return {"success": True, "deleted_id": media_id}
