import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, Boolean, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
import json as json_module

from app.db.base import Base


class LanguageEnum(str, enum.Enum):
    TR = "tr"
    EN = "en"
    DE = "de"


class MediaTypeEnum(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"


class RecurrenceEnum(str, enum.Enum):
    DAILY = "daily"
    ONCE = "once"


class DraftStatusEnum(str, enum.Enum):
    PENDING = "pending"
    POSTED = "posted"
    FAILED = "failed"
    SKIPPED = "skipped"


class PostLogActionEnum(str, enum.Enum):
    GENERATED = "generated"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    FAILED = "failed"
    SKIPPED = "skipped"


class User(Base):
    """User model for device-based anonymous authentication."""
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    device_locale: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    ui_language_override: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    auto_post_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_post_limit: Mapped[int] = mapped_column(Integer, default=10)
    
    # Relationships
    x_accounts: Mapped[List["XAccount"]] = relationship("XAccount", back_populates="user", cascade="all, delete-orphan")
    campaigns: Mapped[List["Campaign"]] = relationship("Campaign", back_populates="user", cascade="all, delete-orphan")


class XAccount(Base):
    """X (Twitter) OAuth account linked to a user."""
    __tablename__ = "x_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    oauth_state: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    oauth_state_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    oauth_state_used: Mapped[bool] = mapped_column(Boolean, default=False)
    oauth_code_verifier: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # PKCE verifier
    access_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    x_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    x_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="x_accounts")


class Campaign(Base):
    """Campaign containing tweets to be scheduled."""
    __tablename__ = "campaigns"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="tr")
    hashtags_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="[]")
    tone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    call_to_action: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="campaigns")
    media_assets: Mapped[List["MediaAsset"]] = relationship("MediaAsset", back_populates="campaign", cascade="all, delete-orphan")
    schedules: Mapped[List["Schedule"]] = relationship("Schedule", back_populates="campaign", cascade="all, delete-orphan")
    drafts: Mapped[List["Draft"]] = relationship("Draft", back_populates="campaign", cascade="all, delete-orphan")
    post_logs: Mapped[List["PostLog"]] = relationship("PostLog", back_populates="campaign", cascade="all, delete-orphan")

    @property
    def hashtags(self) -> List[str]:
        if self.hashtags_json:
            return json_module.loads(self.hashtags_json)
        return []
    
    @hashtags.setter
    def hashtags(self, value: List[str]):
        self.hashtags_json = json_module.dumps(value)


class MediaAsset(Base):
    """Media files (images/videos) attached to a campaign."""
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    alt_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    x_media_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="media_assets")
    draft_media_assets: Mapped[List["DraftMediaAsset"]] = relationship("DraftMediaAsset", back_populates="media_asset", cascade="all, delete-orphan")


class Schedule(Base):
    """Schedule configuration for a campaign."""
    __tablename__ = "schedules"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id"), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Istanbul")
    times_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="[]")
    recurrence: Mapped[str] = mapped_column(String(20), default="daily")
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_post: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_limit: Mapped[int] = mapped_column(Integer, default=10)
    selected_variant_index: Mapped[int] = mapped_column(Integer, default=0)
    post_interval_min: Mapped[int] = mapped_column(Integer, default=120)  # 2 minutes default
    post_interval_max: Mapped[int] = mapped_column(Integer, default=300)  # 5 minutes default
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="schedules")

    @property
    def times(self) -> List[str]:
        if self.times_json:
            return json_module.loads(self.times_json)
        return []
    
    @times.setter
    def times(self, value: List[str]):
        self.times_json = json_module.dumps(value)


class Draft(Base):
    """Generated tweet draft for a campaign."""
    __tablename__ = "drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id"), nullable=False)
    schedule_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("schedules.id"), nullable=True)
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    variant_index: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    hashtags_used_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    x_post_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="drafts")
    post_logs: Mapped[List["PostLog"]] = relationship("PostLog", back_populates="draft", cascade="all, delete-orphan")
    draft_media_assets: Mapped[List["DraftMediaAsset"]] = relationship("DraftMediaAsset", back_populates="draft", cascade="all, delete-orphan")

    @property
    def hashtags_used(self) -> List[str]:
        if self.hashtags_used_json:
            return json_module.loads(self.hashtags_used_json)
        return []
    
    @hashtags_used.setter
    def hashtags_used(self, value: List[str]):
        self.hashtags_used_json = json_module.dumps(value)


class DraftMediaAsset(Base):
    """Association table linking drafts to media assets."""
    __tablename__ = "draft_media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    draft_id: Mapped[str] = mapped_column(String(36), ForeignKey("drafts.id"), nullable=False)
    media_asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("media_assets.id"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    draft: Mapped["Draft"] = relationship("Draft", back_populates="draft_media_assets")
    media_asset: Mapped["MediaAsset"] = relationship("MediaAsset", back_populates="draft_media_assets")


class PostLog(Base):
    """Log of all posting actions and events."""
    __tablename__ = "post_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id"), nullable=False)
    draft_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("drafts.id"), nullable=True)
    run_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="post_logs")
    draft: Mapped[Optional["Draft"]] = relationship("Draft", back_populates="post_logs")
