import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/anonymous", response_model=UserResponse)
async def create_anonymous_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new anonymous user for local MVP.
    
    In production, this would be replaced with proper device-based
    authentication or X OAuth.
    """
    user = User(
        device_locale=user_data.device_locale,
        ui_language_override=user_data.device_locale,  # Default to device locale
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    
    return user


@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID."""
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user
