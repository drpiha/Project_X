"""
Scheduler Worker

This worker runs every minute and:
1. Finds schedules with due times
2. Creates drafts for those times if not already created
3. Posts drafts if auto_post is enabled
4. Logs all actions to post_logs

Run with: python -m worker.scheduler
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
import pytz
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import async_session_maker
from app.db.models import Schedule, Draft, Campaign, PostLog, XAccount
from app.services.x_service import get_x_service
from app.core.config import get_settings
from app.core.security import decrypt_token

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("scheduler")

settings = get_settings()


async def get_due_schedules(db: AsyncSession) -> List[Schedule]:
    """Find all active schedules that have due times."""
    now = datetime.utcnow()
    
    query = select(Schedule).where(
        Schedule.is_active == True,
        Schedule.start_date <= now,
    )
    
    result = await db.execute(query)
    schedules = result.scalars().all()
    
    due_schedules = []
    for schedule in schedules:
        # Check end date
        if schedule.end_date and schedule.end_date < now:
            continue
        
        # Check if any time is due
        try:
            tz = pytz.timezone(schedule.timezone)
        except:
            tz = pytz.UTC
        
        local_now = datetime.now(tz)
        current_time_str = local_now.strftime("%H:%M")
        
        for time_str in schedule.times:
            if time_str == current_time_str:
                due_schedules.append(schedule)
                break
    
    return due_schedules


async def get_or_create_draft(
    db: AsyncSession, 
    schedule: Schedule,
    scheduled_for: datetime
) -> Draft:
    """Get existing draft or create one for the scheduled time."""
    # Check if draft already exists for this time
    query = select(Draft).where(
        Draft.schedule_id == schedule.id,
        Draft.scheduled_for == scheduled_for,
    )
    result = await db.execute(query)
    existing_draft = result.scalar_one_or_none()
    
    if existing_draft:
        return existing_draft
    
    # Get the selected variant from existing drafts
    variant_query = select(Draft).where(
        Draft.campaign_id == schedule.campaign_id,
        Draft.variant_index == schedule.selected_variant_index,
        Draft.schedule_id == None,  # Original generated draft
    )
    result = await db.execute(variant_query)
    source_draft = result.scalar_one_or_none()
    
    if not source_draft:
        # Fallback: get any draft
        fallback_query = select(Draft).where(
            Draft.campaign_id == schedule.campaign_id
        ).limit(1)
        result = await db.execute(fallback_query)
        source_draft = result.scalar_one_or_none()
    
    if not source_draft:
        logger.warning(f"No drafts found for campaign {schedule.campaign_id}")
        return None
    
    # Create new draft for this scheduled time
    draft = Draft(
        campaign_id=schedule.campaign_id,
        schedule_id=schedule.id,
        scheduled_for=scheduled_for,
        variant_index=source_draft.variant_index,
        text=source_draft.text,
        char_count=source_draft.char_count,
        hashtags_used=source_draft.hashtags_used,
        status="pending",
    )
    db.add(draft)
    await db.flush()
    await db.refresh(draft)
    
    logger.info(f"Created draft {draft.id} for schedule {schedule.id} at {scheduled_for}")
    return draft


async def post_draft(
    db: AsyncSession,
    draft: Draft,
    schedule: Schedule
) -> bool:
    """Post a draft to X (or mock)."""
    x_service = get_x_service()
    
    # Get campaign to find user
    campaign_query = select(Campaign).where(Campaign.id == draft.campaign_id)
    result = await db.execute(campaign_query)
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        logger.error(f"Campaign not found for draft {draft.id}")
        return False
    
    # Get X account
    x_account_query = select(XAccount).where(XAccount.user_id == campaign.user_id)
    result = await db.execute(x_account_query)
    x_account = result.scalar_one_or_none()
    
    if x_service.is_mock:
        # Mock posting
        logger.info(f"[MOCK POST] Draft {draft.id}: {draft.text[:50]}...")
        success = True
        message = "Mock post successful"
        tweet_id = f"mock_tweet_{draft.id}"
    elif not x_account or not x_account.access_token_encrypted:
        logger.warning(f"No X account connected for user {campaign.user_id}")
        success = False
        message = "X account not connected"
        tweet_id = None
    else:
        # Real posting
        try:
            access_token = decrypt_token(x_account.access_token_encrypted)
            success, message, tweet_id = await x_service.post_tweet(
                access_token, draft.text
            )
        except Exception as e:
            success = False
            message = str(e)
            tweet_id = None
    
    # Update draft status
    if success:
        draft.status = "posted"
        draft.x_post_id = tweet_id
        draft.posted_at = datetime.utcnow()
    else:
        draft.status = "failed"
        draft.last_error = message
    
    # Log the action
    log = PostLog(
        campaign_id=draft.campaign_id,
        draft_id=draft.id,
        action="posted" if success else "failed",
        details={
            "message": message,
            "tweet_id": tweet_id,
            "mock": x_service.is_mock,
        }
    )
    db.add(log)
    await db.flush()
    
    return success


async def process_schedule(db: AsyncSession, schedule: Schedule):
    """Process a single due schedule."""
    try:
        tz = pytz.timezone(schedule.timezone)
    except:
        tz = pytz.UTC
    
    now = datetime.now(tz)
    
    # Create scheduled_for timestamp
    for time_str in schedule.times:
        try:
            hour, minute = map(int, time_str.split(':'))
            scheduled_for = tz.localize(datetime(
                now.year, now.month, now.day, hour, minute
            ))
            
            # Only process if this time matches current time
            if scheduled_for.strftime("%H:%M") != now.strftime("%H:%M"):
                continue
            
            # Get or create draft
            draft = await get_or_create_draft(db, schedule, scheduled_for)
            if not draft:
                continue
            
            # Skip if already processed
            if draft.status in ["posted", "skipped"]:
                continue
            
            # Post if auto_post enabled
            if schedule.auto_post:
                await post_draft(db, draft, schedule)
            else:
                # Log that it's ready for manual posting
                log = PostLog(
                    campaign_id=schedule.campaign_id,
                    draft_id=draft.id,
                    action="scheduled",
                    details={"message": "Draft ready for manual posting"}
                )
                db.add(log)
                logger.info(f"Draft {draft.id} ready for manual posting")
            
        except ValueError as e:
            logger.error(f"Error parsing time {time_str}: {e}")
            continue


async def run_scheduler_cycle():
    """Run one cycle of the scheduler."""
    logger.info("Running scheduler cycle...")
    
    async with async_session_maker() as db:
        try:
            # Find due schedules
            due_schedules = await get_due_schedules(db)
            logger.info(f"Found {len(due_schedules)} due schedules")
            
            # Process each schedule
            for schedule in due_schedules:
                await process_schedule(db, schedule)
            
            await db.commit()
            
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            await db.rollback()
            raise


async def main():
    """Main scheduler loop."""
    logger.info("Starting scheduler worker...")
    logger.info(f"Interval: {settings.scheduler_interval_seconds} seconds")
    logger.info(f"X Posting: {'ENABLED' if settings.feature_x_posting else 'MOCK'}")
    
    while True:
        try:
            await run_scheduler_cycle()
        except Exception as e:
            logger.error(f"Scheduler cycle failed: {e}")
        
        logger.info(f"Sleeping for {settings.scheduler_interval_seconds} seconds...")
        await asyncio.sleep(settings.scheduler_interval_seconds)


if __name__ == "__main__":
    asyncio.run(main())
