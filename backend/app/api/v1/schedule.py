import uuid
from datetime import datetime, timedelta
from typing import List
import pytz
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User, Campaign, Schedule, Draft
from app.schemas.schedule import ScheduleRequest, ScheduleResponse, DraftResponse
from app.services.campaign_service import get_campaign_service

router = APIRouter(prefix="/campaigns", tags=["Scheduling"])


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


def calculate_next_runs(
    schedule: Schedule,
    count: int = 5
) -> List[str]:
    """
    Calculate the next scheduled run times.
    
    Args:
        schedule: Schedule object with times and timezone
        count: Number of next runs to return
        
    Returns:
        List of ISO formatted datetime strings
    """
    try:
        tz = pytz.timezone(schedule.timezone)
    except pytz.UnknownTimeZoneError:
        tz = pytz.UTC
    
    now = datetime.now(tz)
    start_date = schedule.start_date
    if start_date.tzinfo is None:
        start_date = tz.localize(datetime.combine(start_date.date(), datetime.min.time()))
    
    next_runs = []
    current_date = start_date.date() if start_date <= now else start_date.date()
    
    # If start_date is in the past, start from today
    if datetime.combine(current_date, datetime.min.time()) < now.replace(tzinfo=None):
        current_date = now.date()
    
    max_iterations = 365  # Prevent infinite loop
    iterations = 0
    
    while len(next_runs) < count and iterations < max_iterations:
        for time_str in sorted(schedule.times):
            try:
                hour, minute = map(int, time_str.split(':'))
                run_time = tz.localize(datetime(
                    current_date.year, 
                    current_date.month, 
                    current_date.day,
                    hour, 
                    minute
                ))
                
                # Check if this run is in the future
                if run_time > now:
                    # Check end date
                    if schedule.end_date:
                        end = schedule.end_date
                        if end.tzinfo is None:
                            end = tz.localize(datetime.combine(end.date(), datetime.max.time()))
                        if run_time > end:
                            continue
                    
                    next_runs.append(run_time.isoformat())
                    
                    if len(next_runs) >= count:
                        break
                        
            except ValueError:
                continue
        
        # Move to next day
        if schedule.recurrence == "once":
            break
        current_date += timedelta(days=1)
        iterations += 1
    
    return next_runs


@router.post("/{campaign_id}/schedule", response_model=ScheduleResponse)
async def schedule_campaign(
    campaign_id: str,
    request: ScheduleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a schedule for a campaign.
    
    The schedule defines when drafts should be posted.
    Returns the schedule ID and next run times.
    """
    campaign_service = get_campaign_service()
    
    # Verify campaign exists and belongs to user
    campaign = await campaign_service.get_campaign(db, campaign_id, user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Verify drafts exist
    drafts = await campaign_service.get_drafts(db, campaign_id)
    if not drafts:
        raise HTTPException(
            status_code=400, 
            detail="No drafts found. Generate drafts first."
        )
    
    # Create schedule
    tz = pytz.timezone(request.timezone)
    
    # Convert start date to UTC
    start_local = tz.localize(datetime.combine(request.start_date, datetime.min.time()))
    start_datetime = start_local.astimezone(pytz.UTC).replace(tzinfo=None)
    
    end_datetime = None
    if request.end_date:
        end_local = tz.localize(datetime.combine(request.end_date, datetime.max.time()))
        end_datetime = end_local.astimezone(pytz.UTC).replace(tzinfo=None)
    
    schedule = Schedule(
        campaign_id=campaign_id,
        timezone=request.timezone,
        times=request.times,
        recurrence=request.recurrence,
        start_date=start_datetime,
        end_date=end_datetime,
        is_active=True,
        auto_post=request.auto_post,
        daily_limit=request.daily_limit,
        selected_variant_index=request.selected_variant_index,
    )
    db.add(schedule)
    await db.flush()
    await db.refresh(schedule)
    
    # Calculate next runs
    next_runs = calculate_next_runs(schedule)
    
    # Log scheduling
    await campaign_service.log_action(
        db, campaign_id, "scheduled",
        details={
            "schedule_id": str(schedule.id),
            "times": request.times,
            "recurrence": request.recurrence,
            "auto_post": request.auto_post,
        }
    )
    
    return ScheduleResponse(
        schedule_id=schedule.id,
        next_runs=next_runs,
    )


@router.get("/{campaign_id}/drafts", response_model=List[DraftResponse])
async def get_campaign_drafts(
    campaign_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all drafts for a campaign."""
    campaign_service = get_campaign_service()
    
    # Verify campaign exists and belongs to user
    campaign = await campaign_service.get_campaign(db, campaign_id, user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    drafts = await campaign_service.get_drafts(db, campaign_id)
    return [DraftResponse.model_validate(d) for d in drafts]
