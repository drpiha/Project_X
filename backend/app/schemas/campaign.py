from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class CampaignCreate(BaseModel):
    """Request to create a new campaign."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    language: str = Field("tr", pattern="^(tr|en|de)$")
    hashtags: List[str] = Field(default_factory=list)
    tone: Optional[str] = Field(None, pattern="^(informative|emotional|formal|hopeful|call_to_action)$")
    call_to_action: Optional[str] = Field(None, max_length=100)
    
    @field_validator('hashtags')
    @classmethod
    def validate_hashtags(cls, v):
        """Validate hashtags - preserve exact user formatting including spaces."""
        validated = []
        for tag in v:
            # Only strip leading/trailing whitespace, preserve internal spaces
            tag = tag.strip()
            if len(tag) >= 1:
                validated.append(tag)
        return validated


class CampaignUpdate(BaseModel):
    """Request to update an existing campaign."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    language: Optional[str] = Field(None, pattern="^(tr|en|de)$")
    hashtags: Optional[List[str]] = None
    tone: Optional[str] = Field(None, pattern="^(informative|emotional|formal|hopeful|call_to_action)$")
    call_to_action: Optional[str] = Field(None, max_length=100)


class MediaAssetResponse(BaseModel):
    """Media asset response model."""
    id: str
    type: str
    path: str
    original_name: str
    alt_text: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class CampaignResponse(BaseModel):
    """Campaign response model."""
    id: str
    user_id: str
    title: str
    description: Optional[str] = None
    language: str
    hashtags: List[str] = []
    tone: Optional[str] = None
    call_to_action: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    media_assets: List[MediaAssetResponse] = []
    
    class Config:
        from_attributes = True


class CampaignListResponse(BaseModel):
    """List of campaigns response."""
    campaigns: List[CampaignResponse]
    total: int
