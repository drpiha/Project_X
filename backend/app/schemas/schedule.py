from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime, date
import re


class ScheduleRequest(BaseModel):
    """Request to schedule a campaign."""
    timezone: str = Field("Europe/Istanbul", max_length=50)
    recurrence: Literal["daily", "once"] = "daily"
    times: List[str] = Field(..., min_length=1, max_length=20)
    start_date: date
    end_date: Optional[date] = None
    auto_post: bool = False
    daily_limit: int = Field(10, ge=1, le=100)
    selected_variant_index: int = Field(0, ge=0, le=9)
    
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
