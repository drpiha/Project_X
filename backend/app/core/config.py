import os
import secrets
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    environment: str = Field(default="development", description="development, staging, or production")
    debug: bool = Field(default=True, description="Enable debug mode")

    # Database - SQLite for local dev, PostgreSQL for production
    # Render provides DATABASE_URL in postgres:// format, we convert to asyncpg
    database_url: str = "sqlite+aiosqlite:///./campaign.db"

    @field_validator('database_url')
    @classmethod
    def convert_database_url(cls, v: str) -> str:
        """Convert postgres:// URL to postgresql+asyncpg:// for async support."""
        if v.startswith('postgres://'):
            return v.replace('postgres://', 'postgresql+asyncpg://', 1)
        if v.startswith('postgresql://') and '+asyncpg' not in v:
            return v.replace('postgresql://', 'postgresql+asyncpg://', 1)
        return v

    # Media Storage
    media_storage_path: str = "./media"
    max_images_per_campaign: int = 10
    max_video_per_campaign: int = 1
    allowed_image_extensions: list[str] = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    allowed_video_extensions: list[str] = [".mp4", ".mov", ".avi", ".webm"]
    max_file_size_mb: int = 50

    # Security
    secret_key: str = Field(
        default_factory=lambda: secrets.token_hex(32),
        description="Secret key for JWT and encryption - MUST be set in production"
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 30  # 30 days

    # CORS - Allowed origins (comma-separated in env)
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080,http://localhost:8000",
        description="Comma-separated list of allowed CORS origins"
    )

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 60
    rate_limit_requests_per_hour: int = 500

    # X (Twitter) OAuth
    x_client_id: str = "mock_client_id"
    x_client_secret: str = "mock_client_secret"
    x_redirect_uri: str = "http://localhost:8000/v1/x/oauth/callback"
    x_authorize_url: str = "https://twitter.com/i/oauth2/authorize"
    x_token_url: str = "https://api.twitter.com/2/oauth2/token"
    x_api_base_url: str = "https://api.twitter.com/2"

    # OAuth State TTL (in minutes)
    oauth_state_ttl_minutes: int = 10

    # Feature Flags
    feature_x_posting: bool = True

    # Scheduler - Run every 30 seconds for better timing accuracy
    # This ensures scheduled posts are caught within ~30 seconds of their scheduled time
    scheduler_interval_seconds: int = 30

    # Generator
    default_target_chars: int = 268
    max_tweet_chars: int = 280

    # AI Provider Selection: "groq" (recommended - no daily limit) or "openrouter"
    ai_provider: str = "groq"

    # Groq (Recommended - NO daily limit, 30 req/min)
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # OpenRouter (Fallback - 50 req/day free limit)
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "google/gemini-2.0-flash-exp:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure secret key is strong enough."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        # Warn about default development key
        if v.startswith("dev-secret-key"):
            import logging
            logging.warning("Using development secret key - NOT suitable for production!")
        return v

    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse allowed origins into a list."""
        if not self.allowed_origins:
            return []
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
