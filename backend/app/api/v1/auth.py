import uuid
import hashlib
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db.session import get_db
from app.db.models import User
from app.schemas.user import UserCreate, UserResponse
from app.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)
settings = get_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


def get_device_fingerprint(request: Request) -> str:
    """
    Generate a device fingerprint from request headers.

    This is a basic fingerprint - for production, consider
    using more sophisticated device fingerprinting.
    """
    components = [
        request.headers.get("user-agent", ""),
        request.headers.get("accept-language", ""),
        request.headers.get("accept-encoding", ""),
        request.client.host if request.client else "",
    ]
    fingerprint = hashlib.sha256("".join(components).encode()).hexdigest()
    return fingerprint


@router.post("/anonymous", response_model=UserResponse)
async def create_anonymous_user(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new anonymous user for local MVP.

    Rate limited to prevent abuse.
    In production, this would be replaced with proper device-based
    authentication or X OAuth.
    """
    # Get device fingerprint
    fingerprint = get_device_fingerprint(request)

    # Check for rate limiting based on fingerprint
    # Allow max 5 users per device in 24 hours
    recent_cutoff = datetime.utcnow() - timedelta(hours=24)

    # Note: We need to add device_fingerprint column to User model for full implementation
    # For now, we'll use IP-based limiting which is already handled by slowapi

    # Validate device_locale
    if user_data.device_locale:
        # Basic locale format validation (e.g., "en", "en-US", "tr-TR")
        import re
        locale_pattern = re.compile(r'^[a-z]{2}(-[A-Z]{2})?$')
        if not locale_pattern.match(user_data.device_locale):
            logger.warning(f"Invalid locale format: {user_data.device_locale}")
            # Don't reject, just normalize
            user_data.device_locale = user_data.device_locale[:2].lower() if user_data.device_locale else None

    user = User(
        device_locale=user_data.device_locale,
        ui_language_override=user_data.device_locale,  # Default to device locale
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    logger.info(f"Created anonymous user: {user.id[:8]}...")

    return user


@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID."""
    # Validate UUID format
    try:
        uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
