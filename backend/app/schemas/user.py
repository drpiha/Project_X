from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """Request to create an anonymous user."""
    device_locale: Optional[str] = Field(None, max_length=10)


class UserResponse(BaseModel):
    """User response model."""
    id: str
    created_at: datetime
    device_locale: Optional[str] = None
    ui_language_override: Optional[str] = None
    auto_post_enabled: bool = False
    daily_post_limit: int = 10
    is_x_connected: bool = False
    x_username: Optional[str] = None
    
    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    """Request to update user settings."""
    ui_language_override: Optional[str] = Field(None, max_length=10)
    auto_post_enabled: Optional[bool] = None
    daily_post_limit: Optional[int] = Field(None, ge=1, le=100)


class SettingsResponse(BaseModel):
    """User settings response."""
    ui_language_override: Optional[str] = None
    auto_post_enabled: bool = False
    daily_post_limit: int = 10
    is_x_connected: bool = False
    x_username: Optional[str] = None
    
    class Config:
        from_attributes = True
