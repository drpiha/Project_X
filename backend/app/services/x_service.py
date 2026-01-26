import uuid
import secrets
import hashlib
import base64
import logging
import asyncio
from typing import Optional, Dict
from datetime import datetime, timedelta
from urllib.parse import urlencode
import httpx
import aiofiles
import os

from app.core.config import get_settings
from app.core.security import encrypt_token, decrypt_token
from app.db.models import XAccount, Draft

settings = get_settings()
logger = logging.getLogger(__name__)


class XService:
    """
    Service for X (Twitter) API interactions.

    In local dev mode, operations are mocked.
    Real X posting requires FEATURE_X_POSTING=true and valid OAuth tokens.
    """

    # Minimum seconds between tweets to avoid spam detection
    MIN_TWEET_INTERVAL_SECONDS = 30

    def __init__(self):
        self.is_mock = not settings.feature_x_posting
        # Store PKCE code verifiers (in production, use Redis with TTL)
        self._code_verifiers: Dict[str, str] = {}
        # App-level rate limit tracking (shared across all users)
        self._last_rate_limit: Dict[str, Optional[str]] = {}
        # Per-user rate limit tracking: {user_id: {limit_info}}
        self._user_rate_limits: Dict[str, Dict[str, Optional[str]]] = {}
        # Per-user last tweet time: {user_id: datetime}
        self._user_last_tweet_time: Dict[str, datetime] = {}
        # Legacy tracking (for backwards compatibility)
        self._daily_tweet_count: int = 0
        self._tweet_count_reset_time: Optional[datetime] = None
        self._last_tweet_time: Optional[datetime] = None

    def generate_oauth_state(self) -> str:
        """Generate a random state for OAuth flow."""
        return secrets.token_urlsafe(32)

    def _generate_pkce_pair(self) -> tuple[str, str]:
        """
        Generate PKCE code_verifier and code_challenge using S256 method.

        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate cryptographically secure random verifier (43-128 chars)
        code_verifier = secrets.token_urlsafe(32)

        # Create S256 challenge: BASE64URL(SHA256(code_verifier))
        challenge_bytes = hashlib.sha256(code_verifier.encode('ascii')).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('ascii').rstrip('=')

        return code_verifier, code_challenge

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

        # Generate PKCE pair
        code_verifier, code_challenge = self._generate_pkce_pair()

        # Store code verifier for later use in token exchange
        self._code_verifiers[state] = code_verifier
        logger.debug(f"Stored PKCE verifier for state: {state[:8]}...")

        # Build redirect URI dynamically if base_url provided
        redirect_uri = settings.x_redirect_uri
        if base_url:
            redirect_uri = f"{base_url}/v1/x/oauth/callback"

        # Real X OAuth URL with proper PKCE
        params = {
            "response_type": "code",
            "client_id": settings.x_client_id,
            "redirect_uri": redirect_uri,
            "scope": "tweet.read tweet.write users.read offline.access media.write",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",  # Secure PKCE method
        }
        # Use urlencode for proper URL-safe encoding
        param_str = urlencode(params)
        return f"{settings.x_authorize_url}?{param_str}"

    def get_code_verifier(self, state: str) -> Optional[str]:
        """
        Get and remove the code verifier for a given state.

        Args:
            state: OAuth state parameter

        Returns:
            Code verifier if found, None otherwise
        """
        return self._code_verifiers.pop(state, None)

    def store_code_verifier(self, state: str, verifier: str):
        """Store a code verifier for a state (used when loading from DB)."""
        self._code_verifiers[state] = verifier

    async def exchange_code(
        self,
        code: str,
        state: str,
        code_verifier: Optional[str] = None,
        redirect_uri: Optional[str] = None
    ) -> tuple[str, str, datetime]:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback
            state: OAuth state parameter
            code_verifier: PKCE code verifier (required for real OAuth)
            redirect_uri: Redirect URI used in authorization

        Returns:
            Tuple of (access_token, refresh_token, expires_at)
        """
        if self.is_mock:
            # Mock tokens for local dev
            access_token = f"mock_access_token_{uuid.uuid4()}"
            refresh_token = f"mock_refresh_token_{uuid.uuid4()}"
            expires_at = datetime.utcnow().replace(year=datetime.utcnow().year + 1)
            return access_token, refresh_token, expires_at

        # Get code verifier from memory or parameter
        verifier = code_verifier or self.get_code_verifier(state)
        if not verifier:
            raise ValueError("PKCE code verifier not found for this state")

        # Use provided redirect_uri or default
        actual_redirect_uri = redirect_uri or settings.x_redirect_uri

        # Real X token exchange
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.x_token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": actual_redirect_uri,
                    "code_verifier": verifier,
                },
                auth=(settings.x_client_id, settings.x_client_secret),
            )

            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"Token exchange failed: {response.status_code} - {error_detail}")
                raise ValueError(f"Token exchange failed: {response.status_code}")

            data = response.json()

            access_token = data["access_token"]
            refresh_token = data.get("refresh_token", "")
            expires_in = data.get("expires_in", 7200)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            logger.info("Successfully exchanged code for tokens")
            return access_token, refresh_token, expires_at

    async def get_me(self, access_token: str) -> tuple[Optional[str], Optional[str]]:
        """Get current user info (id, username)."""
        if self.is_mock:
            return "mock_user_id", "MockXUser"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.x_api_base_url}/users/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if response.status_code != 200:
                    logger.warning(f"Failed to get user info: {response.status_code}")
                    return None, None

                data = response.json().get("data", {})
                return data.get("id"), data.get("username")
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None, None

    async def ensure_valid_token(
        self,
        x_account: "XAccount",
        db: "AsyncSession"
    ) -> str:
        """
        Ensure access token is valid, refresh if expired or expiring soon.

        Args:
            x_account: XAccount model instance
            db: Database session

        Returns:
            Valid access token
        """
        if self.is_mock:
            return decrypt_token(x_account.access_token_encrypted)

        # Check if token is expired or expiring within 5 minutes
        now = datetime.utcnow()
        buffer_time = timedelta(minutes=5)

        if x_account.token_expires_at and (x_account.token_expires_at - buffer_time) <= now:
            logger.info(f"Token expiring soon for account {x_account.id}, refreshing...")

            try:
                refresh_token = decrypt_token(x_account.refresh_token_encrypted)
                new_access, new_refresh, expires_at = await self.refresh_tokens(refresh_token)

                # Update tokens in database
                x_account.access_token_encrypted = encrypt_token(new_access)
                x_account.refresh_token_encrypted = encrypt_token(new_refresh)
                x_account.token_expires_at = expires_at

                await db.flush()
                logger.info(f"Token refreshed successfully for account {x_account.id}")

                return new_access

            except Exception as e:
                logger.error(f"Token refresh failed for account {x_account.id}: {e}")
                raise ValueError("Failed to refresh X token. Please reconnect your account.")

        # Token is still valid
        return decrypt_token(x_account.access_token_encrypted)

    async def upload_media(
        self,
        access_token: str,
        file_path: str,
        media_type: str,
        alt_text: Optional[str] = None
    ) -> tuple[bool, str, Optional[str]]:
        """
        Upload media to X (Twitter) API.

        IMPORTANT: X API v2 does NOT support direct media upload yet!
        We use the v1.1 media upload endpoint which works with OAuth 2.0 Bearer tokens
        for the media.write scope (as of 2024).

        For videos > 5MB, uses chunked upload.

        Args:
            access_token: User's OAuth access token
            file_path: Local path to media file
            media_type: 'image' or 'video'
            alt_text: Optional alt text for accessibility

        Returns:
            Tuple of (success, message, media_id)
        """
        if self.is_mock:
            mock_media_id = f"mock_media_{uuid.uuid4()}"
            logger.info(f"[MOCK X MEDIA] Uploaded: {file_path} | type: {media_type} | ID: {mock_media_id}")
            return True, "Mock media uploaded", mock_media_id

        try:
            # X API v1.1 media upload endpoint - this is the ONLY working endpoint for media upload
            # It works with OAuth 2.0 Bearer tokens when media.write scope is granted
            # Do NOT use api.x.com/2/media/upload - it doesn't exist!
            upload_url = "https://upload.twitter.com/1.1/media/upload.json"

            logger.info(f"Attempting to upload media: path={file_path}, type={media_type}")

            # Check file exists
            if not os.path.exists(file_path):
                logger.error(f"Media file not found: {file_path}")
                logger.error(f"Current working directory: {os.getcwd()}")
                return False, f"File not found: {file_path}", None

            # Read file
            async with aiofiles.open(file_path, 'rb') as f:
                file_data = await f.read()

            file_size = len(file_data)
            file_size_mb = file_size / (1024 * 1024)
            logger.info(f"Uploading media: {file_path} | type: {media_type} | size: {file_size_mb:.2f}MB")

            async with httpx.AsyncClient(timeout=120.0) as client:
                # For videos or large files (>5MB), use chunked upload
                if media_type == "video" or file_size > 5 * 1024 * 1024:
                    logger.info(f"Using chunked upload for {media_type}")
                    return await self._chunked_upload(
                        client, access_token, file_path, file_data, media_type, alt_text
                    )

                # Simple upload for images < 5MB using base64 encoding (v1.1 API)
                logger.info(f"Attempting base64 media upload: file={os.path.basename(file_path)}, size={file_size_mb:.2f}MB")

                # Determine MIME type
                ext = os.path.splitext(file_path)[1].lower()
                mime_types = {
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".gif": "image/gif",
                    ".webp": "image/webp",
                }
                mime_type = mime_types.get(ext, "image/jpeg")

                # v1.1 API uses base64 encoded media data
                media_base64 = base64.b64encode(file_data).decode('ascii')

                # Use form data with media_data parameter (base64)
                data = {
                    "media_data": media_base64,
                    "media_category": "tweet_image"
                }

                response = await client.post(
                    upload_url,
                    data=data,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )

                # Log full response for debugging
                logger.info(f"Media upload status: {response.status_code}")
                logger.info(f"Media upload headers: {dict(response.headers)}")

                response.raise_for_status()
                result_data = response.json()
                logger.info(f"Media upload response JSON: {result_data}")

                # v1.1 API returns media_id_string directly
                media_id = (
                    result_data.get("media_id_string") or
                    str(result_data.get("media_id", ""))
                )
                logger.info(f"Extracted media_id: {media_id}")

                # Add alt text using v1.1 metadata endpoint if provided
                if alt_text and media_id:
                    try:
                        alt_text_url = "https://upload.twitter.com/1.1/media/metadata/create.json"
                        alt_response = await client.post(
                            alt_text_url,
                            json={
                                "media_id": media_id,
                                "alt_text": {"text": alt_text[:1000]}  # X limit is 1000 chars
                            },
                            headers={"Authorization": f"Bearer {access_token}"},
                        )
                        if alt_response.status_code == 200:
                            logger.info(f"Alt text added for media {media_id}")
                        else:
                            logger.warning(f"Failed to add alt text: {alt_response.status_code}")
                    except Exception as e:
                        logger.warning(f"Alt text addition failed: {e}")

                logger.info(f"Media uploaded successfully: {media_id}")
                return True, "Media uploaded successfully", media_id

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text
            logger.error(f"Media upload HTTP error: {e.response.status_code}")
            logger.error(f"Media upload error detail: {error_detail}")
            logger.error(f"Media upload request headers: Authorization=Bearer {access_token[:20]}...")
            return False, f"HTTP error {e.response.status_code}: {error_detail}", None
        except Exception as e:
            logger.error(f"Media upload error: {e}")
            return False, f"Error uploading media: {str(e)}", None

    async def _chunked_upload(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        file_path: str,
        file_data: bytes,
        media_type: str,
        alt_text: Optional[str] = None
    ) -> tuple[bool, str, Optional[str]]:
        """
        Chunked upload for videos and large files.

        Uses X API v1.1 chunked upload with INIT, APPEND, FINALIZE commands.
        This is the ONLY working method for video upload.
        """
        # X API v1.1 chunked upload endpoint
        upload_url = "https://upload.twitter.com/1.1/media/upload.json"
        headers = {"Authorization": f"Bearer {access_token}"}

        # Determine media category
        media_category = "tweet_video" if media_type == "video" else "tweet_image"

        # Determine MIME type
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".webm": "video/webm",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
        }
        mime_type = mime_types.get(ext, "application/octet-stream")

        try:
            # Step 1: INIT command
            init_data = {
                "command": "INIT",
                "total_bytes": len(file_data),
                "media_type": mime_type,
                "media_category": media_category,
            }
            response = await client.post(upload_url, data=init_data, headers=headers)
            response.raise_for_status()
            init_result = response.json()
            media_id = init_result.get("media_id_string") or str(init_result.get("media_id", ""))
            logger.info(f"Chunked upload INIT: media_id={media_id}, response={init_result}")

            if not media_id:
                return False, "Failed to get media_id from INIT response", None

            # Step 2: APPEND command (in chunks of 5MB)
            chunk_size = 5 * 1024 * 1024  # 5MB
            for i, offset in enumerate(range(0, len(file_data), chunk_size)):
                chunk = file_data[offset:offset + chunk_size]
                chunk_base64 = base64.b64encode(chunk).decode('ascii')

                append_data = {
                    "command": "APPEND",
                    "media_id": media_id,
                    "media_data": chunk_base64,
                    "segment_index": i,
                }
                response = await client.post(upload_url, data=append_data, headers=headers)
                # APPEND returns 204 No Content on success (or sometimes 200 with empty body)
                if response.status_code not in (200, 204):
                    response.raise_for_status()
                logger.info(f"Chunked upload APPEND: segment {i}")

            # Step 3: FINALIZE command
            finalize_data = {
                "command": "FINALIZE",
                "media_id": media_id,
            }
            response = await client.post(upload_url, data=finalize_data, headers=headers)
            response.raise_for_status()
            finalize_result = response.json()
            logger.info(f"Chunked upload FINALIZE: {finalize_result}")

            # For videos, check processing status
            if media_type == "video":
                processing_info = finalize_result.get("processing_info")
                if processing_info:
                    state = processing_info.get("state")
                    check_after_secs = processing_info.get("check_after_secs", 5)

                    # Wait for processing to complete using STATUS command
                    while state in ("pending", "in_progress"):
                        logger.info(f"Video processing: {state}, waiting {check_after_secs}s...")
                        await asyncio.sleep(check_after_secs)

                        status_params = {
                            "command": "STATUS",
                            "media_id": media_id,
                        }
                        response = await client.get(upload_url, params=status_params, headers=headers)
                        response.raise_for_status()
                        status_result = response.json()
                        processing_info = status_result.get("processing_info", {})
                        state = processing_info.get("state", "succeeded")
                        check_after_secs = processing_info.get("check_after_secs", 5)

                    if state == "failed":
                        error = processing_info.get("error", {})
                        return False, f"Video processing failed: {error}", None

            # Add alt text using metadata endpoint
            if alt_text and media_id:
                try:
                    alt_text_url = "https://upload.twitter.com/1.1/media/metadata/create.json"
                    alt_response = await client.post(
                        alt_text_url,
                        json={
                            "media_id": media_id,
                            "alt_text": {"text": alt_text[:1000]}
                        },
                        headers=headers,
                    )
                    if alt_response.status_code == 200:
                        logger.info(f"Alt text added for media {media_id}")
                    else:
                        logger.warning(f"Failed to add alt text: {alt_response.status_code}")
                except Exception as e:
                    logger.warning(f"Alt text addition failed: {e}")

            logger.info(f"Chunked upload completed: {media_id}")
            return True, "Media uploaded successfully", media_id

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text
            logger.error(f"Chunked upload HTTP error: {e.response.status_code} - {error_detail}")
            return False, f"HTTP error {e.response.status_code}", None
        except Exception as e:
            logger.error(f"Chunked upload error: {e}")
            return False, f"Error in chunked upload: {str(e)}", None

    async def post_tweet(
        self,
        access_token: str,
        text: str,
        media_ids: Optional[list[str]] = None,
        user_id: Optional[str] = None
    ) -> tuple[bool, str, Optional[str]]:
        """
        Post a tweet to X.

        Args:
            access_token: User's access token
            text: Tweet text
            media_ids: Optional list of media IDs to attach
            user_id: Optional user ID for per-user rate limit tracking

        Returns:
            Tuple of (success, message, tweet_id)
        """
        if self.is_mock:
            mock_tweet_id = f"mock_tweet_{uuid.uuid4()}"
            media_info = f" with {len(media_ids)} media" if media_ids else ""
            logger.info(f"[MOCK X POST] Tweet: {text[:50]}...{media_info} | ID: {mock_tweet_id}")
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

                # Extract rate limit info from headers
                rate_limit_info = {
                    "app_limit": response.headers.get("x-app-limit-24hour-limit"),
                    "app_remaining": response.headers.get("x-app-limit-24hour-remaining"),
                    "app_reset": response.headers.get("x-app-limit-24hour-reset"),
                    "user_limit": response.headers.get("x-user-limit-24hour-limit"),
                    "user_remaining": response.headers.get("x-user-limit-24hour-remaining"),
                    "user_reset": response.headers.get("x-user-limit-24hour-reset"),
                }

                # Store app-level rate limit info
                self._last_rate_limit = rate_limit_info

                # Store per-user rate limit if user_id provided
                if user_id:
                    self._user_rate_limits[user_id] = {
                        "user_limit": rate_limit_info["user_limit"],
                        "user_remaining": rate_limit_info["user_remaining"],
                        "user_reset": rate_limit_info["user_reset"],
                    }
                    self._user_last_tweet_time[user_id] = datetime.utcnow()

                # Log rate limit status (both app and user)
                app_remaining = rate_limit_info["app_remaining"]
                user_remaining = rate_limit_info["user_remaining"]
                if app_remaining:
                    logger.info(f"App rate limit: {app_remaining}/{rate_limit_info['app_limit']} remaining")
                if user_remaining and user_id:
                    logger.info(f"User {user_id[:8]}... rate limit: {user_remaining}/{rate_limit_info['user_limit']} remaining")

                response.raise_for_status()
                data = response.json()

                tweet_id = data.get("data", {}).get("id")
                # Track last tweet time for anti-spam (global)
                self._last_tweet_time = datetime.utcnow()
                logger.info(f"Tweet posted successfully: {tweet_id}")
                return True, "Tweet posted successfully", tweet_id

        except httpx.HTTPStatusError as e:
            # Also capture rate limit info from error response
            rate_limit_info = {
                "app_limit": e.response.headers.get("x-app-limit-24hour-limit"),
                "app_remaining": e.response.headers.get("x-app-limit-24hour-remaining"),
                "app_reset": e.response.headers.get("x-app-limit-24hour-reset"),
            }
            self._last_rate_limit = rate_limit_info

            if e.response.status_code == 429:
                reset_time = rate_limit_info.get("app_reset", "unknown")
                logger.error(f"Rate limit exceeded! Resets at: {reset_time}")
                return False, f"Rate limit exceeded. Resets at {reset_time}", None

            logger.error(f"Tweet post HTTP error: {e.response.status_code}")
            return False, f"HTTP error: {e.response.status_code}", None
        except Exception as e:
            logger.error(f"Tweet post error: {e}")
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

            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                raise ValueError(f"Token refresh failed: {response.status_code}")

            data = response.json()

            access_token = data["access_token"]
            new_refresh_token = data.get("refresh_token", refresh_token)
            expires_in = data.get("expires_in", 7200)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            logger.info("Tokens refreshed successfully")
            return access_token, new_refresh_token, expires_at

    def get_rate_limit_info(self) -> Dict[str, Optional[str]]:
        """Get the last known rate limit info."""
        return self._last_rate_limit

    def can_post_tweet(self, safety_buffer: int = 2) -> tuple[bool, str]:
        """
        Check if we can safely post a tweet based on rate limits.

        Args:
            safety_buffer: Number of tweets to keep as safety margin

        Returns:
            Tuple of (can_post, reason)
        """
        if self.is_mock:
            return True, "Mock mode - no limits"

        remaining = self._last_rate_limit.get("app_remaining")
        if remaining is None:
            # No rate limit info yet, allow posting
            return True, "No rate limit info available"

        try:
            remaining_int = int(remaining)
            if remaining_int <= safety_buffer:
                reset_time = self._last_rate_limit.get("app_reset", "unknown")
                return False, f"Rate limit nearly exhausted ({remaining_int} remaining). Resets at {reset_time}"
            return True, f"{remaining_int} tweets remaining"
        except (ValueError, TypeError):
            return True, "Could not parse rate limit"

    def get_remaining_tweets(self) -> Optional[int]:
        """Get number of remaining tweets allowed."""
        remaining = self._last_rate_limit.get("app_remaining")
        if remaining:
            try:
                return int(remaining)
            except (ValueError, TypeError):
                pass
        return None

    def get_user_rate_limit(self, user_id: str) -> Dict[str, Optional[str]]:
        """Get rate limit info for a specific user."""
        return self._user_rate_limits.get(user_id, {})

    def can_user_post(self, user_id: str, safety_buffer: int = 2) -> tuple[bool, str]:
        """
        Check if a specific user can post based on their rate limit.

        Args:
            user_id: User ID to check
            safety_buffer: Number of tweets to keep as safety margin

        Returns:
            Tuple of (can_post, reason)
        """
        if self.is_mock:
            return True, "Mock mode - no limits"

        user_limit = self._user_rate_limits.get(user_id, {})
        remaining = user_limit.get("user_remaining")

        if remaining is None:
            return True, "No user rate limit info available"

        try:
            remaining_int = int(remaining)
            if remaining_int <= safety_buffer:
                reset_time = user_limit.get("user_reset", "unknown")
                return False, f"User rate limit nearly exhausted ({remaining_int} remaining). Resets at {reset_time}"
            return True, f"User has {remaining_int} tweets remaining"
        except (ValueError, TypeError):
            return True, "Could not parse user rate limit"

    def seconds_until_can_post(self) -> int:
        """
        Get seconds to wait before posting next tweet (anti-spam).

        Returns:
            0 if can post now, otherwise seconds to wait
        """
        if self.is_mock or self._last_tweet_time is None:
            return 0

        elapsed = (datetime.utcnow() - self._last_tweet_time).total_seconds()
        remaining = self.MIN_TWEET_INTERVAL_SECONDS - elapsed

        return max(0, int(remaining))

    def can_post_now(self) -> tuple[bool, int]:
        """
        Check if we can post now based on minimum interval.

        Returns:
            Tuple of (can_post, seconds_to_wait)
        """
        wait_seconds = self.seconds_until_can_post()
        return wait_seconds == 0, wait_seconds


# Singleton instance
_x_service: Optional[XService] = None


def get_x_service() -> XService:
    """Get the X service singleton."""
    global _x_service
    if _x_service is None:
        _x_service = XService()
    return _x_service
