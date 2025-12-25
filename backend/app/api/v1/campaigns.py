import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User, Campaign
from app.schemas.campaign import (
    CampaignCreate, CampaignResponse, CampaignListResponse, CampaignUpdate
)
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
