from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime, date
import re
import logging

logger = logging.getLogger(__name__)

# Windows timezone to IANA mapping (common ones)
WINDOWS_TO_IANA = {
    "Turkey Standard Time": "Europe/Istanbul",
    "Turkey Daylight Time": "Europe/Istanbul",
    "GTB Standard Time": "Europe/Istanbul",
    "E. Europe Standard Time": "Europe/Istanbul",
    "Central European Standard Time": "Europe/Berlin",
    "W. Europe Standard Time": "Europe/Berlin",
    "Romance Standard Time": "Europe/Paris",
    "GMT Standard Time": "Europe/London",
    "UTC": "UTC",
    "Coordinated Universal Time": "UTC",
    "Pacific Standard Time": "America/Los_Angeles",
    "Eastern Standard Time": "America/New_York",
    "Central Standard Time": "America/Chicago",
    "Mountain Standard Time": "America/Denver",
}


def parse_date_flexible(v):
    """Parse date from various formats."""
    if v is None:
        return None
    if isinstance(v, date):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        # Handle ISO datetime string with T separator
        if 'T' in v:
            v = v.split('T')[0]
        # Handle datetime with space separator
        if ' ' in v:
            v = v.split(' ')[0]
        # Parse YYYY-MM-DD format
        try:
            return datetime.strptime(v, '%Y-%m-%d').date()
        except ValueError:
            pass
        # Parse DD.MM.YYYY format (European)
        try:
            return datetime.strptime(v, '%d.%m.%Y').date()
        except ValueError:
            pass
    raise ValueError(f"Cannot parse date: {v}")


class ScheduleRequest(BaseModel):
    """Request to schedule a campaign."""
    timezone: str = Field(..., max_length=100, description="IANA timezone name (e.g., Europe/Berlin)")
    recurrence: Literal["daily", "once"] = "daily"
    times: List[str] = Field(default=[], max_length=20)  # Legacy HH:MM format
    scheduled_times: List[str] = Field(default=[], max_length=100)  # Full ISO datetime strings (preferred)
    start_date: date
    end_date: Optional[date] = None
    auto_post: bool = False
    daily_limit: int = Field(10, ge=1, le=100)
    selected_variant_index: int = Field(0, ge=0, le=9)
    images_per_tweet: int = Field(0, ge=0, le=4)  # 0 means no images
    post_interval_min: int = Field(120, ge=30, le=3600, description="Minimum seconds between posts (default 2 min)")
    post_interval_max: int = Field(300, ge=60, le=7200, description="Maximum seconds between posts (default 5 min)")

    @field_validator('start_date', mode='before')
    @classmethod
    def parse_start_date(cls, v):
        return parse_date_flexible(v)

    @field_validator('end_date', mode='before')
    @classmethod
    def parse_end_date(cls, v):
        return parse_date_flexible(v)

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v):
        import pytz

        # First, try direct IANA lookup
        try:
            pytz.timezone(v)
            return v
        except pytz.UnknownTimeZoneError:
            pass

        # Try Windows timezone mapping
        if v in WINDOWS_TO_IANA:
            mapped = WINDOWS_TO_IANA[v]
            logger.info(f"Mapped Windows timezone '{v}' to IANA '{mapped}'")
            return mapped

        # Try case-insensitive lookup
        for win_tz, iana_tz in WINDOWS_TO_IANA.items():
            if win_tz.lower() == v.lower():
                logger.info(f"Mapped Windows timezone '{v}' to IANA '{iana_tz}' (case-insensitive)")
                return iana_tz

        # Fallback to UTC with warning
        logger.warning(f"Unknown timezone '{v}', falling back to Europe/Istanbul")
        return "Europe/Istanbul"
    
    @field_validator('times')
    @classmethod
    def validate_times(cls, v):
        pattern = re.compile(r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$')
        validated = []
        for time_str in v:
            time_str = time_str.strip()
            if not pattern.match(time_str):
                raise ValueError(f"Invalid time format: {time_str}. Use HH:MM format.")
            validated.append(time_str)
        return validated


class ScheduleResponse(BaseModel):
    """Response from schedule creation."""
    schedule_id: str
    next_runs: List[str] = []
    
    class Config:
        from_attributes = True


class DraftResponse(BaseModel):
    """Response model for a draft."""
    id: str
    campaign_id: str
    scheduled_for: Optional[datetime] = None
    variant_index: int
    text: str
    char_count: int
    hashtags_used: List[str] = []
    status: str
    last_error: Optional[str] = None
    created_at: datetime
    posted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PostLogResponse(BaseModel):
    """Response model for a post log entry."""
    id: str
    campaign_id: str
    draft_id: Optional[str] = None
    run_at: datetime
    action: str
    details: Optional[dict] = None
    
    class Config:
        from_attributes = True


class LogsListResponse(BaseModel):
    """List of post logs response."""
    logs: List[PostLogResponse]
    total: int


class AutoScheduleCalculateRequest(BaseModel):
    """Request to calculate auto-schedule times."""
    start_time: str = Field(..., pattern=r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$')
    interval_minutes: int = Field(..., ge=1, le=1440)
    tweet_count: int = Field(..., ge=1, le=100)
    timezone: str = Field(..., max_length=50, description="IANA timezone name")


class ScheduledTimeResponse(BaseModel):
    """A single calculated scheduled time."""
    index: int
    scheduled_for: str
    display_time: str


class AutoScheduleCalculateResponse(BaseModel):
    """Response from schedule calculation."""
    scheduled_times: List[ScheduledTimeResponse]


class AutoScheduleCreateRequest(BaseModel):
    """Request to create auto-schedule with calculated times."""
    scheduled_times: List[datetime]
    auto_post: bool = True
    selected_variant_indices: List[int] = Field(..., min_length=1)
    media_assignments: Optional[dict] = None
