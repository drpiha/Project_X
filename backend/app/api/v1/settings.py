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
