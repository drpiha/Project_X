from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Campaign, MediaAsset, User, Draft, PostLog, Schedule, DraftMediaAsset
from app.schemas.campaign import CampaignCreate, CampaignUpdate


class CampaignService:
    """Service for campaign CRUD operations."""
    
    async def create_campaign(
        self,
        db: AsyncSession,
        user_id: str,
        campaign_data: CampaignCreate
    ) -> Campaign:
        """Create a new campaign."""
        campaign = Campaign(
            user_id=user_id,
            title=campaign_data.title,
            description=campaign_data.description,
            language=campaign_data.language,
            tone=campaign_data.tone,
            call_to_action=campaign_data.call_to_action,
        )
        # Set hashtags using the property (converts to JSON)
        campaign.hashtags = campaign_data.hashtags or []
        
        db.add(campaign)
        await db.flush()
        await db.refresh(campaign)
        return campaign
    
    async def get_campaign(
        self,
        db: AsyncSession,
        campaign_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Campaign]:
        """Get a campaign by ID, optionally filtered by user."""
        query = select(Campaign).options(
            selectinload(Campaign.media_assets)
        ).where(Campaign.id == campaign_id)
        
        if user_id:
            query = query.where(Campaign.user_id == user_id)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_campaigns(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Campaign], int]:
        """List campaigns for a user."""
        # Get count
        count_query = select(Campaign).where(Campaign.user_id == user_id)
        count_result = await db.execute(count_query)
        total = len(count_result.scalars().all())
        
        # Get campaigns
        query = (
            select(Campaign)
            .options(selectinload(Campaign.media_assets))
            .where(Campaign.user_id == user_id)
            .order_by(Campaign.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        campaigns = result.scalars().all()
        
        return list(campaigns), total
    
    async def update_campaign(
        self,
        db: AsyncSession,
        campaign: Campaign,
        update_data: CampaignUpdate
    ) -> Campaign:
        """Update a campaign."""
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            if field == 'hashtags':
                campaign.hashtags = value
            else:
                setattr(campaign, field, value)
        
        campaign.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(campaign)
        return campaign
    
    async def delete_campaign(
        self,
        db: AsyncSession,
        campaign: Campaign
    ) -> bool:
        """Delete a campaign and its associated data.

        Explicitly deletes children in correct order to avoid FK constraint errors
        with async SQLAlchemy where lazy loading is not available.
        """
        cid = campaign.id

        # 1. DraftMediaAssets (references both drafts and media_assets)
        await db.execute(
            delete(DraftMediaAsset).where(
                DraftMediaAsset.draft_id.in_(
                    select(Draft.id).where(Draft.campaign_id == cid)
                )
            )
        )

        # 2. PostLogs (references drafts and campaigns)
        await db.execute(
            delete(PostLog).where(PostLog.campaign_id == cid)
        )

        # 3. Drafts (references campaigns and schedules)
        await db.execute(
            delete(Draft).where(Draft.campaign_id == cid)
        )

        # 4. MediaAssets (references campaigns)
        await db.execute(
            delete(MediaAsset).where(MediaAsset.campaign_id == cid)
        )

        # 5. Schedules (references campaigns)
        await db.execute(
            delete(Schedule).where(Schedule.campaign_id == cid)
        )

        # 6. Campaign itself
        await db.delete(campaign)
        await db.flush()
        return True
    
    async def add_media_asset(
        self,
        db: AsyncSession,
        campaign_id: str,
        media_type: str,
        path: str,
        original_name: str,
        alt_text: Optional[str] = None
    ) -> MediaAsset:
        """Add a media asset to a campaign."""
        asset = MediaAsset(
            campaign_id=campaign_id,
            type=media_type,
            path=path,
            original_name=original_name,
            alt_text=alt_text,
        )
        db.add(asset)
        await db.flush()
        await db.refresh(asset)
        return asset
    
    async def get_drafts(
        self,
        db: AsyncSession,
        campaign_id: str
    ) -> List[Draft]:
        """Get all drafts for a campaign."""
        query = (
            select(Draft)
            .where(Draft.campaign_id == campaign_id)
            .order_by(Draft.variant_index)
        )
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def create_draft(
        self,
        db: AsyncSession,
        campaign_id: str,
        variant_index: int,
        text: str,
        char_count: int,
        hashtags_used: List[str],
        scheduled_for: Optional[datetime] = None,
        schedule_id: Optional[str] = None
    ) -> Draft:
        """Create a draft for a campaign."""
        draft = Draft(
            campaign_id=campaign_id,
            schedule_id=schedule_id,
            scheduled_for=scheduled_for,
            variant_index=variant_index,
            text=text,
            char_count=char_count,
            status="pending",
        )
        # Set hashtags using property
        draft.hashtags_used = hashtags_used
        
        db.add(draft)
        await db.flush()
        await db.refresh(draft)
        return draft
    
    async def log_action(
        self,
        db: AsyncSession,
        campaign_id: str,
        action: str,
        draft_id: Optional[str] = None,
        details: Optional[dict] = None
    ) -> PostLog:
        """Log an action for a campaign."""
        log = PostLog(
            campaign_id=campaign_id,
            draft_id=draft_id,
            action=action,
            details=details or {},
        )
        db.add(log)
        await db.flush()
        await db.refresh(log)
        return log


# Singleton instance
_campaign_service: Optional[CampaignService] = None


def get_campaign_service() -> CampaignService:
    """Get the campaign service singleton."""
    global _campaign_service
    if _campaign_service is None:
        _campaign_service = CampaignService()
    return _campaign_service
