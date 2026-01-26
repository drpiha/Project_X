import uuid
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User
from app.schemas.user import SettingsUpdate, SettingsResponse

router = APIRouter(prefix="/settings", tags=["Settings"])


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


@router.get("", response_model=SettingsResponse)
async def get_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user settings."""
    from app.db.models import XAccount
    query = select(XAccount).where(XAccount.user_id == user.id)
    result = await db.execute(query)
    x_account = result.scalar_one_or_none()

    is_x_connected = x_account is not None and x_account.access_token_encrypted is not None
    x_username = x_account.x_username if x_account else None

    return SettingsResponse(
        ui_language_override=user.ui_language_override,
        auto_post_enabled=user.auto_post_enabled,
        daily_post_limit=user.daily_post_limit,
        is_x_connected=is_x_connected,
        x_username=x_username,
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(
    settings_data: SettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user settings."""
    update_dict = settings_data.model_dump(exclude_unset=True)

    for field, value in update_dict.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)

    from app.db.models import XAccount
    query = select(XAccount).where(XAccount.user_id == user.id)
    result = await db.execute(query)
    x_account = result.scalar_one_or_none()

    is_x_connected = x_account is not None and x_account.access_token_encrypted is not None
    x_username = x_account.x_username if x_account else None

    return SettingsResponse(
        ui_language_override=user.ui_language_override,
        auto_post_enabled=user.auto_post_enabled,
        daily_post_limit=user.daily_post_limit,
        is_x_connected=is_x_connected,
        x_username=x_username,
    )


@router.get("/rate-limit")
async def get_rate_limit_info(
    user: User = Depends(get_current_user),
):
    """
    Get current X API rate limit information.

    Returns both app-level and user-level rate limits.
    """
    from app.services.x_service import get_x_service
    from datetime import datetime

    x_service = get_x_service()
    rate_limit = x_service.get_rate_limit_info()
    remaining = x_service.get_remaining_tweets()
    can_post_app, app_reason = x_service.can_post_tweet()
    can_post_user, user_reason = x_service.can_user_post(str(user.id))
    can_post_now, wait_seconds = x_service.can_post_now()

    # Get per-user rate limit
    user_rate_limit = x_service.get_user_rate_limit(str(user.id))

    # Parse app reset time
    app_reset_timestamp = rate_limit.get("app_reset")
    app_reset_time_str = None
    if app_reset_timestamp:
        try:
            app_reset_time = datetime.fromtimestamp(int(app_reset_timestamp))
            app_reset_time_str = app_reset_time.isoformat()
        except (ValueError, TypeError):
            pass

    # Parse user reset time
    user_reset_timestamp = user_rate_limit.get("user_reset")
    user_reset_time_str = None
    if user_reset_timestamp:
        try:
            user_reset_time = datetime.fromtimestamp(int(user_reset_timestamp))
            user_reset_time_str = user_reset_time.isoformat()
        except (ValueError, TypeError):
            pass

    return {
        "is_mock": x_service.is_mock,
        # App-level limits (shared across ALL users)
        "app_limit": rate_limit.get("app_limit"),
        "app_remaining": remaining,
        "app_reset_time": app_reset_time_str,
        "can_post_app": can_post_app,
        "app_reason": app_reason,
        # User-level limits (per user)
        "user_limit": user_rate_limit.get("user_limit"),
        "user_remaining": user_rate_limit.get("user_remaining"),
        "user_reset_time": user_reset_time_str,
        "can_post_user": can_post_user,
        "user_reason": user_reason,
        # Combined status
        "can_post": can_post_app and can_post_user,
        "can_post_now": can_post_now,
        "wait_seconds": wait_seconds,
        "min_interval_seconds": x_service.MIN_TWEET_INTERVAL_SECONDS,
    }
