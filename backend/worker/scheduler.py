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
import sys
import os
import random
import tempfile
from datetime import datetime, timedelta
from typing import List

import pytz
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get backend directory for resolving relative media paths
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import async_session_maker
from app.db.models import Schedule, Draft, Campaign, PostLog, XAccount, DraftMediaAsset, MediaAsset
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

# Track consecutive failures
consecutive_failures = 0
MAX_CONSECUTIVE_FAILURES = 10


def resolve_media_path(path: str) -> str:
    """
    Resolve media path to absolute path.
    Handles various path formats:
    - Absolute paths: C:/... or /...
    - Relative with ./: ./media/...
    - Relative without ./: media/... or media\\...
    """
    # Normalize path separators first
    normalized_path = path.replace('\\', '/')

    # If already absolute, return as-is
    if os.path.isabs(normalized_path):
        return os.path.normpath(normalized_path)

    # Remove leading ./ if present
    if normalized_path.startswith('./'):
        normalized_path = normalized_path[2:]

    # Resolve relative to backend directory
    resolved = os.path.normpath(os.path.join(BACKEND_DIR, normalized_path))

    # If still not found, try in media subdirectory
    if not os.path.exists(resolved) and not normalized_path.startswith('media'):
        media_path = os.path.normpath(os.path.join(BACKEND_DIR, 'media', normalized_path))
        if os.path.exists(media_path):
            return media_path

    return resolved


async def get_due_schedules(db: AsyncSession) -> List[Schedule]:
    """Find all active schedules that have due times.

    Uses a 2-minute window to catch scheduled times, preventing missed posts
    if scheduler runs at odd seconds (e.g., 10:30:45 might miss 10:30:00).
    """
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
        except pytz.UnknownTimeZoneError:
            logger.warning(f"Invalid timezone for schedule {schedule.id}: {schedule.timezone}")
            tz = pytz.UTC

        local_now = datetime.now(tz)
        current_minute = local_now.hour * 60 + local_now.minute

        for time_str in schedule.times:
            try:
                hour, minute = map(int, time_str.split(':'))
                scheduled_minute = hour * 60 + minute

                # Allow a 2-minute window: current minute or 1 minute ago
                # This prevents missing posts if scheduler runs at :30 or :45 seconds
                if current_minute == scheduled_minute or current_minute == scheduled_minute + 1:
                    due_schedules.append(schedule)
                    logger.info(f"Schedule {schedule.id} is due: time={time_str}, local_now={local_now.strftime('%H:%M:%S')}")
                    break
            except ValueError:
                logger.warning(f"Invalid time format in schedule {schedule.id}: {time_str}")
                continue

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
    """Post a draft to X (or mock) with media attachments."""
    logger.info(f"=== POST DRAFT DEBUG ===")
    logger.info(f"Draft ID: {draft.id}")
    logger.info(f"Draft scheduled_for: {draft.scheduled_for}")
    logger.info(f"Draft text: {draft.text[:50]}...")

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

    # Load draft with media relationships
    logger.info(f"Loading draft with media relationships...")
    draft_query = (
        select(Draft)
        .options(
            selectinload(Draft.draft_media_assets).selectinload(DraftMediaAsset.media_asset)
        )
        .where(Draft.id == draft.id)
    )
    result = await db.execute(draft_query)
    draft = result.scalar_one_or_none()

    media_ids = []

    # Debug: Check what we got
    logger.info(f"Draft loaded: {draft is not None}")
    if draft:
        has_attr = hasattr(draft, 'draft_media_assets')
        logger.info(f"Has draft_media_assets attr: {has_attr}")
        if has_attr:
            logger.info(f"draft_media_assets count: {len(draft.draft_media_assets) if draft.draft_media_assets else 0}")
            if draft.draft_media_assets:
                for dma in draft.draft_media_assets:
                    logger.info(f"  - DraftMediaAsset: draft_id={dma.draft_id}, media_id={dma.media_asset_id}, order={dma.order_index}")
                    if dma.media_asset:
                        logger.info(f"    -> MediaAsset: path={dma.media_asset.path}, type={dma.media_asset.type}")

    # Upload media files if attached to draft
    media_upload_errors = []
    expected_media_count = 0

    if draft and hasattr(draft, 'draft_media_assets') and draft.draft_media_assets:
        expected_media_count = len(draft.draft_media_assets)
        logger.info(f"Processing {expected_media_count} media attachments for draft {draft.id}")

        for draft_media in sorted(draft.draft_media_assets, key=lambda x: x.order_index):
            media_asset = draft_media.media_asset

            if not media_asset:
                logger.error(f"DraftMediaAsset {draft_media.id} has no media_asset!")
                media_upload_errors.append("Missing media asset reference")
                continue

            # Check if already uploaded to X
            if media_asset.x_media_id:
                media_ids.append(media_asset.x_media_id)
                logger.info(f"Using cached X media ID: {media_asset.x_media_id}")
                continue

            # Resolve media path (handle relative paths)
            resolved_path = resolve_media_path(media_asset.path)
            logger.info(f"Media path: original={media_asset.path}, resolved={resolved_path}")
            temp_file_path = None

            # Verify file exists on disk, if not try DB fallback
            if not os.path.exists(resolved_path):
                logger.warning(f"Media file not on disk: {resolved_path}")
                # DB fallback: restore file from file_data stored in database
                if media_asset.file_data:
                    try:
                        ext = os.path.splitext(media_asset.path)[1] or '.jpg'
                        fd, temp_file_path = tempfile.mkstemp(suffix=ext)
                        with os.fdopen(fd, 'wb') as f:
                            f.write(media_asset.file_data)
                        resolved_path = temp_file_path
                        logger.info(f"Restored media from DB to temp file: {temp_file_path} ({len(media_asset.file_data)} bytes)")
                    except Exception as e:
                        logger.error(f"Failed to restore media from DB: {e}")
                        media_upload_errors.append(f"DB restore failed: {e}")
                        continue
                else:
                    error_msg = f"Media file not found on disk or in DB: {resolved_path}"
                    logger.error(error_msg)
                    media_upload_errors.append(error_msg)
                    continue

            # Upload to X
            if not x_service.is_mock and x_account and x_account.access_token_encrypted:
                try:
                    access_token = decrypt_token(x_account.access_token_encrypted)
                    success, msg, x_media_id = await x_service.upload_media(
                        access_token,
                        resolved_path,  # Use resolved path
                        media_asset.type,
                        media_asset.alt_text
                    )

                    if success and x_media_id:
                        media_asset.x_media_id = x_media_id
                        media_ids.append(x_media_id)
                        logger.info(f"Uploaded media {media_asset.id} to X: {x_media_id}")
                    else:
                        error_msg = f"Media upload failed for {media_asset.id}: {msg}"
                        logger.error(error_msg)
                        media_upload_errors.append(error_msg)
                except Exception as e:
                    error_msg = f"Error uploading media {media_asset.id}: {str(e)}"
                    logger.error(error_msg)
                    media_upload_errors.append(error_msg)
            elif x_service.is_mock:
                # Mock mode - verify file exists then generate fake media ID
                if os.path.exists(resolved_path):
                    mock_media_id = f"mock_media_{media_asset.id}"
                    media_asset.x_media_id = mock_media_id
                    media_ids.append(mock_media_id)
                    logger.info(f"[MOCK] Media {media_asset.id}: {mock_media_id} (file: {resolved_path})")
                else:
                    error_msg = f"[MOCK] Media file not found: {resolved_path} (original: {media_asset.path})"
                    logger.error(error_msg)
                    media_upload_errors.append(error_msg)

            # Clean up temp file if we created one from DB
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass

        # Log summary
        if media_upload_errors:
            logger.warning(f"Media upload issues for draft {draft.id}: {len(media_upload_errors)} errors, {len(media_ids)} successful")
        else:
            logger.info(f"All {len(media_ids)} media uploaded successfully for draft {draft.id}")

    if x_service.is_mock:
        # Mock posting
        media_info = f" with {len(media_ids)} media" if media_ids else ""
        logger.info(f"[MOCK POST] Draft {draft.id}: {draft.text[:50]}...{media_info}")
        success = True
        message = "Mock post successful"
        tweet_id = f"mock_tweet_{draft.id}"
    elif not x_account or not x_account.access_token_encrypted:
        logger.warning(f"No X account connected for user {campaign.user_id}")
        success = False
        message = "X account not connected"
        tweet_id = None
    else:
        # Check anti-spam interval before posting
        can_post_now, wait_seconds = x_service.can_post_now()
        if not can_post_now:
            logger.info(f"Anti-spam delay: waiting {wait_seconds}s before posting")
            await asyncio.sleep(wait_seconds)

        # Check APP rate limit before posting (shared across all users)
        can_post_app, app_reason = x_service.can_post_tweet(safety_buffer=2)
        if not can_post_app:
            logger.warning(f"App rate limit check failed: {app_reason}")
            success = False
            message = f"App rate limit: {app_reason}"
            tweet_id = None
        else:
            # Check USER rate limit (per-user)
            can_post_user, user_reason = x_service.can_user_post(str(campaign.user_id), safety_buffer=2)
            if not can_post_user:
                logger.warning(f"User rate limit check failed: {user_reason}")
                success = False
                message = f"User rate limit: {user_reason}"
                tweet_id = None
            else:
                # Real posting with media
                try:
                    # Try to refresh token if needed
                    access_token = await x_service.ensure_valid_token(x_account, db)

                    success, message, tweet_id = await x_service.post_tweet(
                        access_token,
                        draft.text,
                        media_ids=media_ids if media_ids else None,
                        user_id=str(campaign.user_id)  # Track per-user rate limits
                    )

                    # Log remaining tweets after posting
                    remaining = x_service.get_remaining_tweets()
                    if remaining is not None:
                        logger.info(f"App remaining tweet quota: {remaining}")

                except ValueError as e:
                    success = False
                    message = str(e)
                    tweet_id = None
                    logger.error(f"Token error for user {campaign.user_id}: {e}")
                except Exception as e:
                    success = False
                    message = str(e)
                    tweet_id = None
                    logger.error(f"Posting error: {e}")

    # Update draft status
    if success:
        draft.status = "posted"
        draft.x_post_id = tweet_id
        draft.posted_at = datetime.utcnow()
    else:
        draft.status = "failed"
        draft.last_error = message

    # Log the action with media info
    log_details = {
        "message": message,
        "tweet_id": tweet_id,
        "mock": x_service.is_mock,
        "media_count": len(media_ids),
        "expected_media_count": expected_media_count,
    }

    # Add media errors if any
    if media_upload_errors:
        log_details["media_errors"] = media_upload_errors

    log = PostLog(
        campaign_id=draft.campaign_id,
        draft_id=draft.id,
        action="posted" if success else "failed",
        details=log_details
    )
    db.add(log)
    await db.flush()

    return success


async def process_schedule(db: AsyncSession, schedule: Schedule):
    """Process a single due schedule."""
    try:
        tz = pytz.timezone(schedule.timezone)
    except pytz.UnknownTimeZoneError:
        logger.warning(f"Invalid timezone {schedule.timezone}, using UTC")
        tz = pytz.UTC

    now = datetime.now(tz)

    # Create scheduled_for timestamp
    for time_str in schedule.times:
        try:
            hour, minute = map(int, time_str.split(':'))
            scheduled_local = tz.localize(datetime(
                now.year, now.month, now.day, hour, minute
            ))

            # Only process if this time matches current time
            if scheduled_local.strftime("%H:%M") != now.strftime("%H:%M"):
                continue

            # Convert to UTC for storage and comparison (CRITICAL!)
            scheduled_for = scheduled_local.astimezone(pytz.UTC).replace(tzinfo=None)
            logger.info(f"Schedule {schedule.id}: {time_str} local ({tz}) -> {scheduled_for} UTC")

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


async def get_due_drafts(db: AsyncSession, max_drafts: int = 5) -> List[Draft]:
    """Find pending drafts that are due to be posted (including past due).

    Returns up to max_drafts drafts that have scheduled_for <= now + 30 seconds.
    The 30-second buffer ensures drafts scheduled for the current minute are caught
    even if the scheduler runs a few seconds early.

    This ensures missed tweets are eventually sent, but with rate limiting.
    """
    now = datetime.utcnow()
    # Add 30 second buffer to catch drafts scheduled for "right now"
    # This prevents edge cases where scheduler runs at :58 and misses :00 scheduled draft
    now_with_buffer = now + timedelta(seconds=30)

    logger.info(f"=== GET DUE DRAFTS DEBUG ===")
    logger.info(f"Server UTC now: {now.isoformat()}")
    logger.info(f"Checking for drafts scheduled before: {now_with_buffer.isoformat()}")

    # Query ALL pending drafts that are due (scheduled_for <= now + buffer)
    # Limit to max_drafts per cycle to avoid overwhelming the API
    # Order by scheduled_for so oldest are processed first
    query = select(Draft).where(
        Draft.status == "pending",
        Draft.scheduled_for != None,
        Draft.scheduled_for <= now_with_buffer
    ).order_by(Draft.scheduled_for).limit(max_drafts)

    result = await db.execute(query)
    drafts = result.scalars().all()

    logger.info(f"Found {len(drafts)} due drafts")
    for d in drafts:
        time_diff = (now - d.scheduled_for).total_seconds() if d.scheduled_for else 0
        status = "OVERDUE" if time_diff > 0 else f"in {abs(time_diff):.0f}s"
        logger.info(f"  - Draft {d.id}: scheduled_for={d.scheduled_for.isoformat() if d.scheduled_for else 'None'}, {status}")

    return drafts


async def run_scheduler_cycle():
    """Run one cycle of the scheduler with proper error handling."""
    global consecutive_failures
    now_utc = datetime.utcnow()
    logger.info(f"=== SCHEDULER CYCLE START === UTC: {now_utc.isoformat()}")

    async with async_session_maker() as db:
        try:
            # Debug: Show ALL pending drafts for visibility
            all_pending_query = select(Draft).where(
                Draft.status == "pending",
                Draft.scheduled_for != None
            ).order_by(Draft.scheduled_for).limit(10)
            all_pending_result = await db.execute(all_pending_query)
            all_pending = all_pending_result.scalars().all()
            logger.info(f"=== ALL PENDING DRAFTS (max 10) ===")
            for d in all_pending:
                if d.scheduled_for:
                    diff = (d.scheduled_for - now_utc).total_seconds()
                    status = "DUE" if diff <= 0 else f"in {diff:.0f}s"
                    logger.info(f"  - {d.id}: scheduled_for={d.scheduled_for.isoformat()} ({status})")

            # Method 1: Process old-style schedules (with times array)
            due_schedules = await get_due_schedules(db)
            logger.info(f"Found {len(due_schedules)} due schedules (old-style)")

            for schedule in due_schedules:
                try:
                    await process_schedule(db, schedule)
                except Exception as e:
                    logger.error(f"Error processing schedule {schedule.id}: {e}")
                    # Continue with other schedules

            # Method 2: Process new-style direct scheduled drafts
            due_drafts = await get_due_drafts(db)
            logger.info(f"Found {len(due_drafts)} due drafts (new-style)")

            for idx, draft in enumerate(due_drafts):
                try:
                    # Get the schedule to check auto_post and interval settings
                    schedule = None
                    if draft.schedule_id:
                        schedule_query = select(Schedule).where(Schedule.id == draft.schedule_id)
                        schedule_result = await db.execute(schedule_query)
                        schedule = schedule_result.scalar_one_or_none()

                    # Add random delay between multiple posts
                    if idx > 0:
                        # Use schedule's interval settings or defaults (2-5 minutes)
                        interval_min = schedule.post_interval_min if schedule else 120
                        interval_max = schedule.post_interval_max if schedule else 300
                        delay_seconds = random.randint(interval_min, interval_max)
                        logger.info(f"Waiting {delay_seconds}s (random {interval_min}-{interval_max}s) before next post...")
                        await asyncio.sleep(delay_seconds)

                    if schedule and schedule.auto_post:
                        logger.info(f"Processing draft {draft.id} (scheduled for {draft.scheduled_for})")
                        await post_draft(db, draft, schedule)
                    elif schedule:
                        logger.info(f"Draft {draft.id} ready for manual posting")
                    else:
                        logger.warning(f"Draft {draft.id} has no schedule_id")
                except Exception as e:
                    logger.error(f"Error processing draft {draft.id}: {e}")
                    # Continue with other drafts

            await db.commit()

            # Reset failure counter on success
            consecutive_failures = 0

        except SQLAlchemyError as e:
            logger.error(f"Database error in scheduler: {e}")
            await db.rollback()
            consecutive_failures += 1

        except httpx.HTTPError as e:
            logger.error(f"HTTP error in scheduler (X API): {e}")
            consecutive_failures += 1

        except Exception as e:
            logger.exception(f"Unexpected error in scheduler: {e}")
            await db.rollback()
            consecutive_failures += 1


async def main():
    """Main scheduler loop with health monitoring."""
    global consecutive_failures

    logger.info("Starting scheduler worker...")
    logger.info(f"Interval: {settings.scheduler_interval_seconds} seconds")
    logger.info(f"X Posting: {'ENABLED' if settings.feature_x_posting else 'MOCK'}")
    logger.info(f"Max consecutive failures before exit: {MAX_CONSECUTIVE_FAILURES}")

    while True:
        try:
            await run_scheduler_cycle()

            # Check if we've had too many consecutive failures
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                logger.critical(
                    f"Too many consecutive failures ({consecutive_failures}), "
                    "scheduler is unhealthy. Exiting..."
                )
                # In production, this would trigger a restart via process manager
                sys.exit(1)

        except Exception as e:
            logger.exception(f"Scheduler cycle failed: {e}")
            consecutive_failures += 1

            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                logger.critical("Critical failure threshold reached. Exiting...")
                sys.exit(1)

        logger.info(f"Sleeping for {settings.scheduler_interval_seconds} seconds...")
        await asyncio.sleep(settings.scheduler_interval_seconds)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.critical(f"Scheduler crashed: {e}")
        sys.exit(1)
