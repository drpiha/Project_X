from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql+asyncpg://campaign_user:campaign_pass@localhost:5432/campaign_db"
    
    # Media Storage
    media_storage_path: str = "./media"
    max_images_per_campaign: int = 10
    max_video_per_campaign: int = 1
    allowed_image_extensions: list[str] = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    allowed_video_extensions: list[str] = [".mp4", ".mov", ".avi", ".webm"]
    max_file_size_mb: int = 50
    
    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 30  # 30 days
    
    # X (Twitter) OAuth
    x_client_id: str = "mock_client_id"
    x_client_secret: str = "mock_client_secret"
    x_redirect_uri: str = "http://localhost:8000/v1/x/oauth/callback"
    x_authorize_url: str = "https://twitter.com/i/oauth2/authorize"
    x_token_url: str = "https://api.twitter.com/2/oauth2/token"
    x_api_base_url: str = "https://api.twitter.com/2"
    
    # Feature Flags
    feature_x_posting: bool = False
    
    # Scheduler
    scheduler_interval_seconds: int = 60
    
    # Generator
    default_target_chars: int = 268
    max_tweet_chars: int = 280
    
    # AI (OpenRouter)
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "google/gemini-2.0-flash-exp:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
