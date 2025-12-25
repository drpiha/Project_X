import uuid
import secrets
from typing import Optional
from datetime import datetime
import httpx

from app.core.config import get_settings
from app.core.security import encrypt_token, decrypt_token
from app.db.models import XAccount, Draft

settings = get_settings()


class XService:
    """
    Service for X (Twitter) API interactions.
    
    In local dev mode, operations are mocked.
    Real X posting requires FEATURE_X_POSTING=true and valid OAuth tokens.
    """
    
    def __init__(self):
        self.is_mock = not settings.feature_x_posting
    
    def generate_oauth_state(self) -> str:
        """Generate a random state for OAuth flow."""
        return secrets.token_urlsafe(32)
    
    def get_authorize_url(self, state: str, base_url: str | None = None) -> str:
        """
        Get the X OAuth authorization URL.
        
        Args:
            state: OAuth state parameter
            base_url: Optional base URL to use (for dynamic host detection)
            
        Returns:
            Authorization URL string
        """
        if self.is_mock:
            # Use provided base_url or fall back to redirect_uri
            if base_url is None:
                base_url = settings.x_redirect_uri.split("/v1/")[0]
            return f"{base_url}/v1/x/oauth/mock?state={state}"
        
        # Real X OAuth URL
        params = {
            "response_type": "code",
            "client_id": settings.x_client_id,
            "redirect_uri": settings.x_redirect_uri,
            "scope": "tweet.read tweet.write users.read offline.access",
            "state": state,
            "code_challenge": "challenge",  # In production, use real S256 PKCE
            "code_challenge_method": "plain",
        }
        param_str = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{settings.x_authorize_url}?{param_str}"
    
    async def exchange_code(
        self,
        code: str,
        state: str
    ) -> tuple[str, str, datetime]:
        """
        Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from callback
            state: OAuth state parameter
            
        Returns:
            Tuple of (access_token, refresh_token, expires_at)
        """
        if self.is_mock:
            # Mock tokens for local dev
            access_token = f"mock_access_token_{uuid.uuid4()}"
            refresh_token = f"mock_refresh_token_{uuid.uuid4()}"
            expires_at = datetime.utcnow().replace(year=datetime.utcnow().year + 1)
            return access_token, refresh_token, expires_at
        
        # Real X token exchange
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.x_token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.x_redirect_uri,
                    "code_verifier": "challenge",
                },
                auth=(settings.x_client_id, settings.x_client_secret),
            )
            response.raise_for_status()
            data = response.json()
            
            access_token = data["access_token"]
            refresh_token = data.get("refresh_token", "")
            expires_in = data.get("expires_in", 7200)
            expires_at = datetime.utcnow().replace(
                second=datetime.utcnow().second + expires_in
            )
            
            return access_token, refresh_token, expires_at
    
    async def post_tweet(
        self,
        access_token: str,
        text: str,
        media_ids: Optional[list[str]] = None
    ) -> tuple[bool, str, Optional[str]]:
        """
        Post a tweet to X.
        
        Args:
            access_token: User's access token
            text: Tweet text
            media_ids: Optional list of media IDs to attach
            
        Returns:
            Tuple of (success, message, tweet_id)
        """
        if self.is_mock:
            # Mock posting - just log and return success
            mock_tweet_id = f"mock_tweet_{uuid.uuid4()}"
            print(f"[MOCK X POST] Tweet: {text[:50]}... | ID: {mock_tweet_id}")
            return True, "Mock tweet posted successfully", mock_tweet_id
        
        # Real X posting
        try:
            async with httpx.AsyncClient() as client:
                payload = {"text": text}
                if media_ids:
                    payload["media"] = {"media_ids": media_ids}
                
                response = await client.post(
                    f"{settings.x_api_base_url}/tweets",
                    json=payload,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                data = response.json()
                
                tweet_id = data.get("data", {}).get("id")
                return True, "Tweet posted successfully", tweet_id
                
        except httpx.HTTPStatusError as e:
            return False, f"HTTP error: {e.response.status_code}", None
        except Exception as e:
            return False, f"Error posting tweet: {str(e)}", None
    
    async def refresh_tokens(
        self,
        refresh_token: str
    ) -> tuple[str, str, datetime]:
        """
        Refresh access tokens.
        
        Args:
            refresh_token: Current refresh token
            
        Returns:
            Tuple of (new_access_token, new_refresh_token, expires_at)
        """
        if self.is_mock:
            access_token = f"mock_access_token_{uuid.uuid4()}"
            new_refresh_token = f"mock_refresh_token_{uuid.uuid4()}"
            expires_at = datetime.utcnow().replace(year=datetime.utcnow().year + 1)
            return access_token, new_refresh_token, expires_at
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.x_token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
                auth=(settings.x_client_id, settings.x_client_secret),
            )
            response.raise_for_status()
            data = response.json()
            
            access_token = data["access_token"]
            new_refresh_token = data.get("refresh_token", refresh_token)
            expires_in = data.get("expires_in", 7200)
            expires_at = datetime.utcnow().replace(
                second=datetime.utcnow().second + expires_in
            )
            
            return access_token, new_refresh_token, expires_at


# Singleton instance
_x_service: Optional[XService] = None


def get_x_service() -> XService:
    """Get the X service singleton."""
    global _x_service
    if _x_service is None:
        _x_service = XService()
    return _x_service
