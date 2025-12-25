import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User, PostLog
from app.schemas.schedule import PostLogResponse, LogsListResponse

router = APIRouter(prefix="/logs", tags=["Logs"])


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


@router.get("", response_model=LogsListResponse)
async def get_logs(
    campaign_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get post logs, optionally filtered by campaign.
    
    Returns a paginated list of log entries with total count.
    """
    from app.db.models import Campaign
    
    # Build base query
    query = select(PostLog)
    
    if campaign_id:
        # Verify campaign belongs to user
        campaign_query = select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.user_id == user.id
        )
        result = await db.execute(campaign_query)
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        query = query.where(PostLog.campaign_id == campaign_id)
    else:
        # Get logs for all user's campaigns
        campaign_ids_query = select(Campaign.id).where(Campaign.user_id == user.id)
        result = await db.execute(campaign_ids_query)
        user_campaign_ids = [row[0] for row in result.fetchall()]
        
        if user_campaign_ids:
            query = query.where(PostLog.campaign_id.in_(user_campaign_ids))
        else:
            return LogsListResponse(logs=[], total=0)
    
    # Get total count
    count_result = await db.execute(query)
    total = len(count_result.scalars().all())
    
    # Get paginated results
    query = query.order_by(PostLog.run_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return LogsListResponse(
        logs=[PostLogResponse.model_validate(log) for log in logs],
        total=total
    )
