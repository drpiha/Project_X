import uuid
import logging
from datetime import datetime, timedelta
from typing import List
import pytz
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User, Campaign, Schedule, Draft, DraftMediaAsset, MediaAsset
from app.schemas.schedule import (
    ScheduleRequest, ScheduleResponse, DraftResponse,
    AutoScheduleCalculateRequest, AutoScheduleCalculateResponse, ScheduledTimeResponse,
    AutoScheduleCreateRequest
)
from app.services.campaign_service import get_campaign_service
import random

logger = logging.getLogger(__name__)
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
    # Log incoming request for debugging
    logger.info(f"=== SCHEDULE REQUEST ===")
    logger.info(f"Campaign ID: {campaign_id}")
    logger.info(f"User ID: {user.id}")
    logger.info(f"Request data: timezone={request.timezone}, start_date={request.start_date}")
    logger.info(f"  times={request.times}, scheduled_times={len(request.scheduled_times)} items")
    logger.info(f"  images_per_tweet={request.images_per_tweet}, auto_post={request.auto_post}")
    logger.info(f"  intervals: {request.post_interval_min}-{request.post_interval_max}s")

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

    # Debug logging for timezone conversion
    logger.info(f"=== SCHEDULE DEBUG ===")
    logger.info(f"Received timezone: {request.timezone}")
    logger.info(f"Received start_date: {request.start_date}")
    logger.info(f"Received times (legacy): {request.times}")
    logger.info(f"Received scheduled_times (new): {request.scheduled_times}")
    logger.info(f"Received images_per_tweet: {request.images_per_tweet}")
    logger.info(f"Server UTC now: {datetime.utcnow()}")

    # Determine if using new scheduled_times format or legacy times format
    use_scheduled_times = len(request.scheduled_times) > 0

    # Convert start date to UTC
    start_local = tz.localize(datetime.combine(request.start_date, datetime.min.time()))
    start_datetime = start_local.astimezone(pytz.UTC).replace(tzinfo=None)

    logger.info(f"start_local (midnight in user tz): {start_local}")
    logger.info(f"Using {'scheduled_times' if use_scheduled_times else 'times'} format")
    
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
        post_interval_min=request.post_interval_min,
        post_interval_max=request.post_interval_max,
    )
    db.add(schedule)
    await db.flush()
    await db.refresh(schedule)

    # Get media assets for the campaign if images_per_tweet > 0
    image_assets = []
    video_assets = []
    if request.images_per_tweet > 0:
        media_query = select(MediaAsset).where(MediaAsset.campaign_id == campaign_id)
        result = await db.execute(media_query)
        all_media = list(result.scalars().all())

        # Separate images and videos (X only allows images OR video, not both)
        for ma in all_media:
            if ma.type == "video":
                video_assets.append(ma)
            else:
                image_assets.append(ma)

        logger.info(f"=== MEDIA ASSETS DEBUG ===")
        logger.info(f"Campaign {campaign_id}: Found {len(image_assets)} images, {len(video_assets)} videos")
        for ma in all_media:
            logger.info(f"  - Media: {ma.id} | type: {ma.type} | path: {ma.path}")

    # Create scheduled drafts for each time slot with media attachments
    # Get all unscheduled drafts (original generated variants) sorted by variant_index
    unscheduled_drafts = sorted(
        [d for d in drafts if d.scheduled_for is None],
        key=lambda d: d.variant_index
    )

    if not unscheduled_drafts:
        # Fallback: use all drafts if none are unscheduled
        unscheduled_drafts = sorted(drafts, key=lambda d: d.variant_index)

    logger.info(f"Found {len(unscheduled_drafts)} unscheduled draft variants to cycle through")

    if unscheduled_drafts:
        # Determine which times list to use
        if use_scheduled_times:
            # NEW FORMAT: Full ISO datetime strings from client (local time)
            for idx, datetime_str in enumerate(request.scheduled_times):
                try:
                    # Parse the ISO datetime string
                    # Replace 'Z' with '+00:00' for proper parsing
                    parsed_dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))

                    logger.info(f"Draft {idx}: datetime_str={datetime_str}")
                    logger.info(f"  parsed_dt={parsed_dt}, tzinfo={parsed_dt.tzinfo}")

                    # Convert to UTC for storage
                    if parsed_dt.tzinfo is None:
                        # Naive datetime - treat as user's local timezone
                        scheduled_dt = tz.localize(parsed_dt)
                        scheduled_utc = scheduled_dt.astimezone(pytz.UTC).replace(tzinfo=None)
                        logger.info(f"  Naive -> localized to {tz} -> UTC: {scheduled_utc}")
                    else:
                        # Timezone-aware datetime - convert directly to UTC
                        scheduled_utc = parsed_dt.astimezone(pytz.UTC).replace(tzinfo=None)
                        logger.info(f"  Timezone-aware -> UTC: {scheduled_utc}")

                    # Cycle through available variants (wrap around if more times than variants)
                    source_draft = unscheduled_drafts[idx % len(unscheduled_drafts)]
                    logger.info(f"  Using variant {source_draft.variant_index} for scheduled slot {idx}")

                    # UPDATE existing draft instead of creating a copy (if within bounds)
                    if idx < len(unscheduled_drafts):
                        # Update the existing draft directly
                        draft = unscheduled_drafts[idx]
                        draft.schedule_id = schedule.id
                        draft.scheduled_for = scheduled_utc
                        draft.status = "pending"
                        logger.info(f"  Updated existing draft {draft.id} with scheduled time")
                    else:
                        # Create a copy only if we need more scheduled times than available drafts
                        draft = Draft(
                            campaign_id=campaign_id,
                            schedule_id=schedule.id,
                            scheduled_for=scheduled_utc,
                            variant_index=source_draft.variant_index,
                            text=source_draft.text,
                            char_count=source_draft.char_count,
                            status="pending",
                        )
                        draft.hashtags_used = source_draft.hashtags_used
                        db.add(draft)
                        logger.info(f"  Created new draft copy for extra scheduled slot")

                    await db.flush()
                    await db.refresh(draft)

                    # Attach media if available and images_per_tweet > 0
                    # X allows either images (up to 4) OR video (1), not both
                    if request.images_per_tweet > 0:
                        selected_media = []
                        if video_assets:
                            # If video exists, use video (only 1 allowed per tweet)
                            selected_media = [video_assets[0]]
                            logger.info(f"Using video for draft {draft.id}")
                        elif image_assets:
                            # Use images (up to 4 per tweet for X)
                            max_images = min(request.images_per_tweet, 4, len(image_assets))
                            selected_media = random.sample(image_assets, max_images)
                            logger.info(f"Using {len(selected_media)} images for draft {draft.id}")

                        if selected_media:
                            for order, media in enumerate(selected_media):
                                assoc = DraftMediaAsset(
                                    draft_id=draft.id,
                                    media_asset_id=media.id,
                                    order_index=order
                                )
                                db.add(assoc)
                                logger.info(f"  - Attached media {media.id} (type={media.type}) at order {order}")
                        else:
                            logger.info(f"No media found for campaign {campaign_id}")
                    else:
                        logger.info(f"images_per_tweet=0, skipping media attachment")
                except Exception as e:
                    logger.error(f"Error parsing scheduled_time {datetime_str}: {e}")
                    continue
        else:
            # LEGACY FORMAT: HH:MM time strings (all on same start_date)
            for idx, time_str in enumerate(request.times):
                try:
                    hour, minute = map(int, time_str.split(':'))
                    scheduled_dt = tz.localize(datetime(
                        start_local.year, start_local.month, start_local.day, hour, minute
                    ))
                    # Convert to UTC
                    scheduled_utc = scheduled_dt.astimezone(pytz.UTC).replace(tzinfo=None)

                    logger.info(f"Draft {idx}: time_str={time_str} -> local={scheduled_dt} -> UTC={scheduled_utc}")

                    # Cycle through available variants (wrap around if more times than variants)
                    source_draft = unscheduled_drafts[idx % len(unscheduled_drafts)]
                    logger.info(f"  Using variant {source_draft.variant_index} for scheduled slot {idx}")

                    # UPDATE existing draft instead of creating a copy (if within bounds)
                    if idx < len(unscheduled_drafts):
                        # Update the existing draft directly
                        draft = unscheduled_drafts[idx]
                        draft.schedule_id = schedule.id
                        draft.scheduled_for = scheduled_utc
                        draft.status = "pending"
                        logger.info(f"  Updated existing draft {draft.id} with scheduled time")
                    else:
                        # Create a copy only if we need more scheduled times than available drafts
                        draft = Draft(
                            campaign_id=campaign_id,
                            schedule_id=schedule.id,
                            scheduled_for=scheduled_utc,
                            variant_index=source_draft.variant_index,
                            text=source_draft.text,
                            char_count=source_draft.char_count,
                            status="pending",
                        )
                        draft.hashtags_used = source_draft.hashtags_used
                        db.add(draft)
                        logger.info(f"  Created new draft copy for extra scheduled slot")

                    await db.flush()
                    await db.refresh(draft)

                    # Attach media if available and images_per_tweet > 0
                    # X allows either images (up to 4) OR video (1), not both
                    if request.images_per_tweet > 0:
                        selected_media = []
                        if video_assets:
                            # If video exists, use video (only 1 allowed per tweet)
                            selected_media = [video_assets[0]]
                            logger.info(f"Using video for draft {draft.id}")
                        elif image_assets:
                            # Use images (up to 4 per tweet for X)
                            max_images = min(request.images_per_tweet, 4, len(image_assets))
                            selected_media = random.sample(image_assets, max_images)
                            logger.info(f"Using {len(selected_media)} images for draft {draft.id}")

                        if selected_media:
                            for order, media in enumerate(selected_media):
                                assoc = DraftMediaAsset(
                                    draft_id=draft.id,
                                    media_asset_id=media.id,
                                    order_index=order
                                )
                                db.add(assoc)
                                logger.info(f"  - Attached media {media.id} (type={media.type}) at order {order}")
                        else:
                            logger.info(f"No media found for campaign {campaign_id}")
                    else:
                        logger.info(f"images_per_tweet=0, skipping media attachment")
                except ValueError as e:
                    logger.error(f"Error parsing time {time_str}: {e}")
                    continue

        await db.commit()

    # Calculate next runs
    next_runs = calculate_next_runs(schedule)

    # Log scheduling
    await campaign_service.log_action(
        db, campaign_id, "scheduled",
        details={
            "schedule_id": str(schedule.id),
            "times_count": len(request.scheduled_times) if use_scheduled_times else len(request.times),
            "recurrence": request.recurrence,
            "auto_post": request.auto_post,
            "images_per_tweet": request.images_per_tweet,
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


@router.post("/{campaign_id}/schedule/calculate", response_model=AutoScheduleCalculateResponse)
async def calculate_schedule_times(
    campaign_id: str,
    request: AutoScheduleCalculateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate all tweet times for auto-scheduling.

    Args:
        start_time: First tweet time (HH:MM)
        interval_minutes: Minutes between tweets
        tweet_count: Total number of tweets
        timezone: User's timezone

    Returns:
        List of calculated times as ISO datetime strings
    """
    campaign_service = get_campaign_service()

    # Verify campaign exists
    campaign = await campaign_service.get_campaign(db, campaign_id, user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    try:
        # Parse start time
        tz = pytz.timezone(request.timezone)
        hour, minute = map(int, request.start_time.split(':'))

        # Start from today or tomorrow if time passed
        now = datetime.now(tz)
        start_date = now.date()
        start_dt = tz.localize(datetime(
            start_date.year, start_date.month, start_date.day, hour, minute
        ))

        # If start time is in past, use tomorrow
        if start_dt <= now:
            start_dt += timedelta(days=1)

        # Calculate all times
        scheduled_times = []
        current_time = start_dt

        for i in range(request.tweet_count):
            scheduled_times.append(ScheduledTimeResponse(
                index=i,
                scheduled_for=current_time.isoformat(),
                display_time=current_time.strftime("%Y-%m-%d %H:%M"),
            ))
            current_time += timedelta(minutes=request.interval_minutes)

        return AutoScheduleCalculateResponse(scheduled_times=scheduled_times)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{campaign_id}/schedule/auto", response_model=dict)
async def create_auto_schedule(
    campaign_id: str,
    request: AutoScheduleCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create schedule with auto-calculated times and media assignments.

    Creates one Draft per scheduled time with assigned media.
    """
    campaign_service = get_campaign_service()

    # Verify campaign exists
    campaign = await campaign_service.get_campaign(db, campaign_id, user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Get source drafts (templates)
    source_drafts = await campaign_service.get_drafts(db, campaign_id)
    if not source_drafts:
        raise HTTPException(status_code=400, detail="No drafts found. Generate drafts first.")

    # Create schedule (placeholder for grouping)
    schedule = Schedule(
        campaign_id=campaign_id,
        timezone="UTC",
        times=[],  # Times stored in individual drafts
        recurrence="once",
        start_date=datetime.utcnow(),
        is_active=True,
        auto_post=request.auto_post,
    )
    db.add(schedule)
    await db.flush()

    # Create draft for each scheduled time
    created_drafts = []
    for idx, scheduled_time in enumerate(request.scheduled_times):
        variant_index = request.selected_variant_indices[idx % len(request.selected_variant_indices)]

        # Find source draft by variant_index
        source_draft = next(
            (d for d in source_drafts if d.variant_index == variant_index),
            source_drafts[0]
        )

        # Parse scheduled time and convert to naive UTC datetime
        if isinstance(scheduled_time, str):
            scheduled_dt = datetime.fromisoformat(scheduled_time)
        else:
            scheduled_dt = scheduled_time

        # Remove timezone info (convert to naive UTC)
        if scheduled_dt.tzinfo is not None:
            scheduled_dt = scheduled_dt.astimezone(pytz.UTC).replace(tzinfo=None)

        # Create scheduled draft
        draft = Draft(
            campaign_id=campaign_id,
            schedule_id=schedule.id,
            scheduled_for=scheduled_dt,
            variant_index=variant_index,
            text=source_draft.text,
            char_count=source_draft.char_count,
            status="pending",
        )
        draft.hashtags_used = source_draft.hashtags_used
        db.add(draft)
        await db.flush()
        await db.refresh(draft)

        # Assign media if provided
        if request.media_assignments:
            # Convert string keys to int if needed
            media_ids = request.media_assignments.get(str(idx), [])
            for order, media_id in enumerate(media_ids):
                assoc = DraftMediaAsset(
                    draft_id=draft.id,
                    media_asset_id=media_id,
                    order_index=order
                )
                db.add(assoc)

        created_drafts.append(draft)

    await db.commit()

    return {
        "schedule_id": str(schedule.id),
        "drafts_created": len(created_drafts),
        "draft_ids": [str(d.id) for d in created_drafts]
    }
