import uuid
import logging
import re
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db.session import get_db
from app.db.models import User, XAccount, Draft
from app.services.x_service import get_x_service
from app.services.campaign_service import get_campaign_service
from app.core.security import encrypt_token, decrypt_token
from app.core.config import get_settings

router = APIRouter(prefix="/x", tags=["X OAuth"])
logger = logging.getLogger(__name__)
settings = get_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# UUID regex pattern for strict validation
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)


class OAuthStartResponse(BaseModel):
    authorize_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=500)
    state: str = Field(..., min_length=1, max_length=100)

    @field_validator('code', 'state')
    @classmethod
    def validate_no_injection(cls, v: str) -> str:
        """Prevent injection attacks."""
        # Basic sanitization - no HTML/script tags
        if '<' in v or '>' in v:
            raise ValueError("Invalid characters in input")
        return v


class OAuthCallbackResponse(BaseModel):
    success: bool
    message: str
    x_username: Optional[str] = None


class PostRequest(BaseModel):
    draft_id: str = Field(..., min_length=36, max_length=36)

    @field_validator('draft_id')
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        if not UUID_PATTERN.match(v):
            raise ValueError("Invalid draft ID format")
        return v


class PostResponse(BaseModel):
    success: bool
    message: str
    tweet_id: Optional[str] = None


def validate_uuid_strict(value: str) -> str:
    """Strict UUID validation."""
    if not UUID_PATTERN.match(value):
        raise ValueError("Invalid UUID format")
    # Double-check with uuid.UUID
    try:
        uuid.UUID(value)
    except (ValueError, AttributeError):
        raise ValueError("Invalid UUID format")
    return value.lower()


async def get_current_user(
    x_user_id: str = Header(..., description="User ID from anonymous auth"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from header with strict validation."""
    # Strict UUID validation
    try:
        user_id = validate_uuid_strict(x_user_id)
    except ValueError:
        logger.warning(f"Invalid user ID format: {x_user_id[:20]}...")
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.post("/oauth/start", response_model=OAuthStartResponse)
async def start_oauth(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start the X OAuth flow.

    Returns an authorization URL and state for the OAuth dance.
    In local dev, this returns a mock URL.
    """
    x_service = get_x_service()
    state = x_service.generate_oauth_state()
    base_url = str(request.base_url).rstrip("/")
    authorize_url = x_service.get_authorize_url(state, base_url)

    # Calculate state expiration
    expires_at = datetime.utcnow() + timedelta(minutes=settings.oauth_state_ttl_minutes)

    # Get PKCE code verifier if not mock mode
    # Use peek instead of pop - verifier should stay in memory until callback
    # But more importantly, we store it in DB for persistence across server restarts
    code_verifier = None
    if not x_service.is_mock:
        # Access directly without removing - verifier needs to stay for callback
        code_verifier = x_service._code_verifiers.get(state)

    # Store or update X account with state
    query = select(XAccount).where(XAccount.user_id == user.id)
    result = await db.execute(query)
    x_account = result.scalar_one_or_none()

    if x_account:
        x_account.oauth_state = state
        x_account.oauth_state_expires_at = expires_at
        x_account.oauth_state_used = False
        x_account.oauth_code_verifier = code_verifier
    else:
        x_account = XAccount(
            user_id=user.id,
            oauth_state=state,
            oauth_state_expires_at=expires_at,
            oauth_state_used=False,
            oauth_code_verifier=code_verifier,
        )
        db.add(x_account)

    await db.flush()

    logger.info(f"OAuth started for user {user.id[:8]}...")

    return OAuthStartResponse(
        authorize_url=authorize_url,
        state=state,
    )


def _create_app_redirect_html(params: str, is_success: bool = False, username: str = None) -> str:
    """Create HTML page that redirects to app with multiple strategies.
    Works for both mobile (deep links) and web (close tab message).
    """
    custom_scheme_link = f"campaignapp://oauth?{params}"
    intent_link = f"intent://oauth?{params}#Intent;scheme=campaignapp;package=com.campaignapp.social;S.browser_fallback_url=https%3A%2F%2Fplay.google.com%2Fstore;end"

    if is_success:
        bg_gradient = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
        icon = "✓"
        title = f"@{username} bağlandı!" if username else "Bağlantı Başarılı!"
        btn_color = "#667eea"
        subtitle = "Hesabınız başarıyla bağlandı"
        web_message = "Bu sekmeyi kapatıp uygulamaya dönebilirsiniz."
    else:
        bg_gradient = "linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)"
        icon = "✗"
        title = "Bir Hata Oluştu"
        btn_color = "#e74c3c"
        subtitle = "Lütfen tekrar deneyin"
        web_message = "Lütfen bu sekmeyi kapatıp tekrar deneyin."

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
        <title>Campaign App - OAuth</title>
        <style>
            * {{ box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex; justify-content: center; align-items: center;
                min-height: 100vh; margin: 0; padding: 20px;
                background: {bg_gradient}; color: white; text-align: center;
            }}
            .container {{ max-width: 400px; width: 100%; }}
            .icon {{ font-size: 80px; margin-bottom: 24px; animation: pulse 2s infinite; }}
            @keyframes pulse {{ 0%, 100% {{ transform: scale(1); }} 50% {{ transform: scale(1.1); }} }}
            h1 {{ font-size: 28px; margin: 0 0 8px 0; font-weight: 700; }}
            .subtitle {{ font-size: 16px; opacity: 0.9; margin-bottom: 32px; }}
            .btn {{
                display: block; width: 100%; background: white; color: {btn_color};
                padding: 18px 32px; border-radius: 16px; text-decoration: none;
                font-weight: 700; font-size: 18px; box-shadow: 0 8px 30px rgba(0,0,0,0.3);
                border: none; cursor: pointer; margin-bottom: 16px;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .btn:active {{ transform: scale(0.97); box-shadow: 0 4px 15px rgba(0,0,0,0.2); }}
            .btn-close {{
                background: rgba(255,255,255,0.2); color: white;
                border: 2px solid white;
            }}
            .hint {{ font-size: 14px; opacity: 0.8; margin-top: 24px; line-height: 1.5; }}
            .mobile-only {{ display: none; }}
            .desktop-only {{ display: block; }}
            @media (max-width: 768px) and (hover: none) {{
                .mobile-only {{ display: block; }}
                .desktop-only {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">{icon}</div>
            <h1>{title}</h1>
            <p class="subtitle">{subtitle}</p>

            <!-- Desktop/Web message -->
            <div class="desktop-only">
                <button class="btn btn-close" onclick="window.close()">
                    ✕ Sekmeyi Kapat
                </button>
                <p class="hint">{web_message}</p>
            </div>

            <!-- Mobile buttons -->
            <div class="mobile-only">
                <a href="{custom_scheme_link}" class="btn" id="openBtn" onclick="handleClick()">
                    📱 Uygulamayı Aç
                </a>
                <p class="hint" id="hint">
                    Butona tıkladıktan sonra uygulama açılacak.<br>
                    Açılmazsa bu sayfayı kapatıp uygulamaya dönün.
                </p>
            </div>
        </div>

        <script>
            var customUrl = "{custom_scheme_link}";
            var intentUrl = "{intent_link}";
            var clicked = false;

            // Detect if mobile
            var isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

            function handleClick() {{
                if (clicked) return;
                clicked = true;

                var hint = document.getElementById('hint');
                if (hint) hint.innerHTML = 'Uygulama açılıyor...<br>Açılmazsa bu sayfayı kapatın.';

                // Try intent URL for Android (more reliable)
                setTimeout(function() {{
                    window.location.href = intentUrl;
                }}, 100);
            }}

            // Auto-try on page load for mobile only
            window.onload = function() {{
                if (!isMobile) return; // Skip for desktop
                // Small delay then try intent
                setTimeout(function() {{
                    // Create invisible link and click it
                    var link = document.createElement('a');
                    link.href = intentUrl;
                    link.style.display = 'none';
                    document.body.appendChild(link);

                    // Simulate user click (some browsers allow this)
                    try {{
                        link.click();
                    }} catch(e) {{
                        console.log('Auto-click failed:', e);
                    }}
                }}, 300);

                // Fallback: try direct navigation
                setTimeout(function() {{
                    try {{
                        window.location.href = customUrl;
                    }} catch(e) {{
                        console.log('Direct navigation failed:', e);
                    }}
                }}, 800);
            }};

            // Detect if page is still visible after 3 seconds (app didn't open)
            setTimeout(function() {{
                if (document.visibilityState === 'visible') {{
                    document.getElementById('hint').innerHTML =
                        '<strong>Butona tıklayın</strong> veya<br>bu sayfayı kapatıp uygulamaya dönün.';
                }}
            }}, 3000);
        </script>
    </body>
    </html>
    """


@router.get("/oauth/callback")
async def oauth_callback_get(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle OAuth callback redirect from X (GET request).
    Supports both web and mobile deep linking.
    """
    base_url = str(request.base_url).rstrip("/")

    # Basic input validation
    if len(code) > 500 or len(state) > 100:
        logger.warning("OAuth callback with oversized parameters")
        return HTMLResponse(content=_create_app_redirect_html("error=invalid_request"))

    # Find X account with matching state
    query = select(XAccount).where(XAccount.oauth_state == state)
    result = await db.execute(query)
    x_account = result.scalar_one_or_none()

    if not x_account:
        logger.warning(f"OAuth callback with invalid state: {state[:20]}...")
        return HTMLResponse(content=_create_app_redirect_html("error=invalid_state"))

    # Check if state has expired
    now = datetime.utcnow()
    if x_account.oauth_state_expires_at and x_account.oauth_state_expires_at < now:
        logger.warning(f"OAuth callback with expired state for account {x_account.id}")
        x_account.oauth_state = None
        x_account.oauth_code_verifier = None
        await db.commit()
        return HTMLResponse(content=_create_app_redirect_html("error=state_expired"))

    # Check if state has already been used (replay protection)
    if x_account.oauth_state_used:
        logger.warning(f"OAuth callback with already-used state for account {x_account.id}")
        return HTMLResponse(content=_create_app_redirect_html("error=state_already_used"))

    # Mark state as used immediately
    x_account.oauth_state_used = True

    # Exchange code for tokens
    x_service = get_x_service()
    try:
        # Build redirect URI dynamically
        redirect_uri = f"{base_url}/v1/x/oauth/callback"

        access_token, refresh_token, expires_at = await x_service.exchange_code(
            code,
            state,
            code_verifier=x_account.oauth_code_verifier,
            redirect_uri=redirect_uri
        )

        # Store encrypted tokens
        x_account.access_token_encrypted = encrypt_token(access_token)
        x_account.refresh_token_encrypted = encrypt_token(refresh_token)
        x_account.token_expires_at = expires_at

        # Clear OAuth state data
        x_account.oauth_state = None
        x_account.oauth_state_expires_at = None
        x_account.oauth_code_verifier = None

        # Get user info from X
        x_user_id, x_username = await x_service.get_me(access_token)
        if x_user_id and x_username:
            x_account.x_user_id = x_user_id
            x_account.x_username = x_username

        # For mock, set a mock username info if missing
        if x_service.is_mock and not x_account.x_username:
            x_account.x_username = "MockXUser"

        await db.commit()

        logger.info(f"OAuth completed successfully for account {x_account.id}")

        username = x_account.x_username or 'user'
        return HTMLResponse(content=_create_app_redirect_html(
            f"success=true&username={username}",
            is_success=True,
            username=username
        ))

    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        return HTMLResponse(content=_create_app_redirect_html("error=oauth_failed"))


@router.post("/oauth/callback", response_model=OAuthCallbackResponse)
async def oauth_callback(
    request: OAuthCallbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle OAuth callback from X.

    Exchanges the authorization code for tokens.
    In local dev, uses mock tokens.
    """
    # Find X account with matching state
    query = select(XAccount).where(
        XAccount.user_id == user.id,
        XAccount.oauth_state == request.state
    )
    result = await db.execute(query)
    x_account = result.scalar_one_or_none()

    if not x_account:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    # Check state expiration
    now = datetime.utcnow()
    if x_account.oauth_state_expires_at and x_account.oauth_state_expires_at < now:
        x_account.oauth_state = None
        x_account.oauth_code_verifier = None
        await db.flush()
        raise HTTPException(status_code=400, detail="OAuth state expired")

    # Check if already used
    if x_account.oauth_state_used:
        raise HTTPException(status_code=400, detail="OAuth state already used")

    # Mark as used
    x_account.oauth_state_used = True

    # Exchange code for tokens
    x_service = get_x_service()
    try:
        access_token, refresh_token, expires_at = await x_service.exchange_code(
            request.code,
            request.state,
            code_verifier=x_account.oauth_code_verifier
        )

        # Store encrypted tokens
        x_account.access_token_encrypted = encrypt_token(access_token)
        x_account.refresh_token_encrypted = encrypt_token(refresh_token)
        x_account.token_expires_at = expires_at

        # Clear state
        x_account.oauth_state = None
        x_account.oauth_state_expires_at = None
        x_account.oauth_code_verifier = None

        # Get user info from X
        x_user_id, x_username = await x_service.get_me(access_token)
        if x_user_id and x_username:
            x_account.x_user_id = x_user_id
            x_account.x_username = x_username

        # For mock, set a mock username
        if x_service.is_mock:
            x_account.x_user_id = f"mock_user_{user.id}"
            x_account.x_username = "MockXUser"

        await db.flush()

        logger.info(f"OAuth completed for user {user.id[:8]}...")

        return OAuthCallbackResponse(
            success=True,
            message="Successfully connected to X",
            x_username=x_account.x_username,
        )

    except Exception as e:
        logger.error(f"OAuth callback error for user {user.id[:8]}: {str(e)}")
        return OAuthCallbackResponse(
            success=False,
            message="OAuth failed. Please try again.",
        )


@router.get("/oauth/mock")
async def mock_oauth_redirect(state: str, request: Request):
    """
    Mock OAuth redirect for local development.

    Directly redirects to the callback to simulate user approval.
    """
    from fastapi.responses import RedirectResponse

    # Validate state length
    if len(state) > 100:
        raise HTTPException(status_code=400, detail="Invalid state")

    code = f"mock_code_{state}"
    base_url = str(request.base_url).rstrip("/")
    redirect_url = f"{base_url}/v1/x/oauth/callback?code={code}&state={state}"
    return RedirectResponse(url=redirect_url)


@router.post("/post", response_model=PostResponse)
async def post_tweet(
    request: PostRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Post a draft to X.

    Requires the user to have connected their X account.
    In local dev with mocked X, this simulates posting.
    """
    # Get draft
    query = select(Draft).where(Draft.id == request.draft_id)
    result = await db.execute(query)
    draft = result.scalar_one_or_none()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Get X account
    query = select(XAccount).where(XAccount.user_id == user.id)
    result = await db.execute(query)
    x_account = result.scalar_one_or_none()

    if not x_account or not x_account.access_token_encrypted:
        raise HTTPException(
            status_code=400,
            detail="X account not connected. Start OAuth flow first."
        )

    # Get valid token (auto-refresh if needed)
    x_service = get_x_service()
    try:
        access_token = await x_service.ensure_valid_token(x_account, db)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    success, message, tweet_id = await x_service.post_tweet(
        access_token,
        draft.text
    )

    if success:
        draft.status = "posted"
        draft.x_post_id = tweet_id
        draft.posted_at = datetime.utcnow()

        # Log the post
        campaign_service = get_campaign_service()
        await campaign_service.log_action(
            db, draft.campaign_id, "posted",
            draft_id=draft.id,
            details={"tweet_id": tweet_id, "mock": x_service.is_mock}
        )

        logger.info(f"Tweet posted successfully: {tweet_id}")
    else:
        draft.status = "failed"
        draft.last_error = message

        campaign_service = get_campaign_service()
        await campaign_service.log_action(
            db, draft.campaign_id, "failed",
            draft_id=draft.id,
            details={"error": message}
        )

        logger.warning(f"Tweet post failed: {message}")

    await db.flush()

    return PostResponse(
        success=success,
        message=message,
        tweet_id=tweet_id,
    )
