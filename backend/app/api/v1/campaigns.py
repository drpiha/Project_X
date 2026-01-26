import uuid
import random
from typing import List, Optional, Dict, Literal
from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.db.models import User, Campaign, Draft, DraftMediaAsset, MediaAsset, Schedule
from app.schemas.campaign import (
    CampaignCreate, CampaignResponse, CampaignListResponse, CampaignUpdate
)
from app.schemas.schedule import DraftResponse
from app.services.campaign_service import get_campaign_service
from app.services.media_service import get_media_service

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


async def get_current_user(
    x_user_id: str = Header(..., description="User ID from anonymous auth"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from header."""
    # Validate UUID format
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


@router.post("", response_model=CampaignResponse)
async def create_campaign(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    language: str = Form("tr"),
    hashtags: str = Form(""),  # Comma-separated
    tone: Optional[str] = Form(None),
    call_to_action: Optional[str] = Form(None),
    images: List[UploadFile] = File(default=[]),
    video: Optional[UploadFile] = File(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new campaign with optional media uploads.
    
    Accepts multipart/form-data with images (0-10) and video (0-1).
    """
    # Parse hashtags
    hashtag_list = [tag.strip() for tag in hashtags.split(",") if tag.strip()]
    
    # Validate limits
    if len(images) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images allowed")
    
    # Create campaign data object
    campaign_data = CampaignCreate(
        title=title,
        description=description,
        language=language,
        hashtags=hashtag_list,
        tone=tone,
        call_to_action=call_to_action,
    )
    
    campaign_service = get_campaign_service()
    media_service = get_media_service()
    
    # Create campaign
    campaign = await campaign_service.create_campaign(db, user.id, campaign_data)
    
    # Handle image uploads
    for image in images:
        if image.filename:
            try:
                path, original_name = await media_service.save_file(
                    image, str(campaign.id), "image"
                )
                await campaign_service.add_media_asset(
                    db, campaign.id, "image", path, original_name
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
    
    # Handle video upload
    if video and video.filename:
        try:
            path, original_name = await media_service.save_file(
                video, str(campaign.id), "video"
            )
            await campaign_service.add_media_asset(
                db, campaign.id, "video", path, original_name
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # Refresh to get media assets
    campaign = await campaign_service.get_campaign(db, campaign.id)
    
    # Log action
    await campaign_service.log_action(
        db, campaign.id, "generated",
        details={"action": "campaign_created", "title": title}
    )
    
    return campaign


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all campaigns for the current user."""
    campaign_service = get_campaign_service()
    campaigns, total = await campaign_service.list_campaigns(db, user.id, limit, offset)
    
    return CampaignListResponse(
        campaigns=[CampaignResponse.model_validate(c) for c in campaigns],
        total=total
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific campaign by ID."""
    campaign_service = get_campaign_service()
    campaign = await campaign_service.get_campaign(db, campaign_id, user.id)
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return campaign


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    update_data: CampaignUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a campaign."""
    campaign_service = get_campaign_service()
    campaign = await campaign_service.get_campaign(db, campaign_id, user.id)
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign = await campaign_service.update_campaign(db, campaign, update_data)
    return campaign


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a campaign."""
    campaign_service = get_campaign_service()
    campaign = await campaign_service.get_campaign(db, campaign_id, user.id)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    await campaign_service.delete_campaign(db, campaign)
    return {"status": "deleted", "campaign_id": str(campaign_id)}


# Schemas for new endpoints
class MediaDistributionRequest(BaseModel):
    draft_count: int = Field(..., ge=1, le=100)
    media_per_draft: int = Field(1, ge=1, le=4)
    distribution_strategy: Literal["random", "sequential"] = "random"


class MediaAssetResponse(BaseModel):
    id: str
    type: str
    path: str
    original_name: str
    alt_text: Optional[str] = None

    class Config:
        from_attributes = True


class DraftDetailResponse(BaseModel):
    id: str
    campaign_id: str
    scheduled_for: Optional[str] = None
    variant_index: int
    text: str
    char_count: int
    hashtags_used: List[str] = []
    status: str
    last_error: Optional[str] = None
    x_post_id: Optional[str] = None
    created_at: str
    posted_at: Optional[str] = None
    media_assets: List[MediaAssetResponse] = []
    x_post_url: Optional[str] = None

    class Config:
        from_attributes = True


class CampaignDetailResponse(BaseModel):
    campaign: CampaignResponse
    drafts: List[DraftDetailResponse]
    schedule: Optional[dict] = None
    stats: dict


@router.post("/{campaign_id}/media/distribute")
async def auto_distribute_media(
    campaign_id: str,
    request: MediaDistributionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Auto-distribute media across drafts.

    Args:
        draft_count: Number of drafts to distribute to
        media_per_draft: 1-4 media items per draft
        distribution_strategy: 'random' or 'sequential'

    Returns:
        Media assignment map: draft_index -> [media_asset_ids]
    """
    campaign_service = get_campaign_service()

    # Verify campaign exists
    campaign = await campaign_service.get_campaign(db, campaign_id, user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Get media assets
    media_query = select(MediaAsset).where(MediaAsset.campaign_id == campaign_id)
    result = await db.execute(media_query)
    media_assets = list(result.scalars().all())

    if not media_assets:
        raise HTTPException(status_code=400, detail="No media found")

    # Distribute media
    assignments = {}

    if request.distribution_strategy == "random":
        for draft_idx in range(request.draft_count):
            # Randomly select media_per_draft items
            selected = random.sample(
                media_assets,
                min(request.media_per_draft, len(media_assets))
            )
            assignments[str(draft_idx)] = [m.id for m in selected]
    else:  # sequential
        for draft_idx in range(request.draft_count):
            start_idx = (draft_idx * request.media_per_draft) % len(media_assets)
            selected = []
            for i in range(request.media_per_draft):
                media_idx = (start_idx + i) % len(media_assets)
                selected.append(media_assets[media_idx].id)
            assignments[str(draft_idx)] = selected

    return {"assignments": assignments}


@router.get("/{campaign_id}/detail", response_model=CampaignDetailResponse)
async def get_campaign_detail(
    campaign_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive campaign details including all scheduled drafts.

    Returns:
        - Campaign info
        - All drafts (original + scheduled)
        - Schedule info
        - Media assets
        - Stats (posted, pending, failed counts)
    """
    campaign_service = get_campaign_service()

    # Verify campaign exists
    campaign = await campaign_service.get_campaign(db, campaign_id, user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Get all drafts with media
    drafts_query = (
        select(Draft)
        .options(
            selectinload(Draft.draft_media_assets).selectinload(DraftMediaAsset.media_asset)
        )
        .where(Draft.campaign_id == campaign_id)
        .order_by(Draft.scheduled_for.nullslast(), Draft.variant_index)
    )
    result = await db.execute(drafts_query)
    drafts = result.scalars().all()

    # Get most recent schedule (there might be multiple)
    schedule_query = (
        select(Schedule)
        .where(Schedule.campaign_id == campaign_id)
        .order_by(Schedule.created_at.desc())
        .limit(1)
    )
    schedule_result = await db.execute(schedule_query)
    schedule = schedule_result.scalar_one_or_none()

    # Calculate stats
    stats = {
        "total": len(drafts),
        "posted": sum(1 for d in drafts if d.status == "posted"),
        "pending": sum(1 for d in drafts if d.status == "pending"),
        "failed": sum(1 for d in drafts if d.status == "failed"),
    }

    # Convert drafts to response format
    draft_responses = []
    for draft in drafts:
        media_assets = []
        if hasattr(draft, 'draft_media_assets'):
            for dm in sorted(draft.draft_media_assets, key=lambda x: x.order_index):
                media_assets.append(MediaAssetResponse.model_validate(dm.media_asset))

        x_post_url = None
        if draft.x_post_id and not draft.x_post_id.startswith("mock"):
            x_post_url = f"https://x.com/i/web/status/{draft.x_post_id}"

        draft_responses.append(DraftDetailResponse(
            id=str(draft.id),
            campaign_id=str(draft.campaign_id),
            scheduled_for=draft.scheduled_for.isoformat() if draft.scheduled_for else None,
            variant_index=draft.variant_index,
            text=draft.text,
            char_count=draft.char_count,
            hashtags_used=draft.hashtags_used,
            status=draft.status,
            last_error=draft.last_error,
            x_post_id=draft.x_post_id,
            created_at=draft.created_at.isoformat(),
            posted_at=draft.posted_at.isoformat() if draft.posted_at else None,
            media_assets=media_assets,
            x_post_url=x_post_url
        ))

    schedule_dict = None
    if schedule:
        schedule_dict = {
            "id": str(schedule.id),
            "timezone": schedule.timezone,
            "times": schedule.times,
            "recurrence": schedule.recurrence,
            "auto_post": schedule.auto_post
        }

    return CampaignDetailResponse(
        campaign=CampaignResponse.model_validate(campaign),
        drafts=draft_responses,
        schedule=schedule_dict,
        stats=stats
    )
