import uuid
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.db.session import get_db
from app.db.models import User, XAccount, Draft
from app.services.x_service import get_x_service
from app.services.campaign_service import get_campaign_service
from app.core.security import encrypt_token, decrypt_token

router = APIRouter(prefix="/x", tags=["X OAuth"])


class OAuthStartResponse(BaseModel):
    authorize_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str


class OAuthCallbackResponse(BaseModel):
    success: bool
    message: str
    x_username: Optional[str] = None


class PostRequest(BaseModel):
    draft_id: str


class PostResponse(BaseModel):
    success: bool
    message: str
    tweet_id: Optional[str] = None


async def get_current_user(
    x_user_id: str = Header(..., description="User ID from anonymous auth"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from header."""
    # Validate UUID format
    try:
        uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    query = select(User).where(User.id == x_user_id)
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
    # Build base URL from request for correct redirect on any host
    base_url = str(request.base_url).rstrip("/")
    authorize_url = x_service.get_authorize_url(state, base_url)
    
    # Store or update X account with state
    query = select(XAccount).where(XAccount.user_id == user.id)
    result = await db.execute(query)
    x_account = result.scalar_one_or_none()
    
    if x_account:
        x_account.oauth_state = state
    else:
        x_account = XAccount(
            user_id=user.id,
            oauth_state=state,
        )
        db.add(x_account)
    
    await db.flush()
    
    return OAuthStartResponse(
        authorize_url=authorize_url,
        state=state,
    )


@router.get("/oauth/callback")
async def oauth_callback_get(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle OAuth callback redirect from X (GET request).
    """
    from fastapi.responses import HTMLResponse
    
    # Find X account with matching state
    query = select(XAccount).where(XAccount.oauth_state == state)
    result = await db.execute(query)
    x_account = result.scalar_one_or_none()
    
    if not x_account:
        return HTMLResponse(
            content="<h1>❌ Error</h1><p>Invalid state or session expired.</p>", 
            status_code=400
        )
    
    # Exchange code for tokens
    x_service = get_x_service()
    try:
        # If mock mode, we simulate the exchange logic if needed, 
        # but usually exchange_code handles it based on is_mock flag.
        access_token, refresh_token, expires_at = await x_service.exchange_code(
            code, state
        )
        
        # Store encrypted tokens
        x_account.access_token_encrypted = encrypt_token(access_token)
        x_account.refresh_token_encrypted = encrypt_token(refresh_token)
        x_account.token_expires_at = expires_at
        x_account.oauth_state = None  # Clear used state
        
        # For mock, set a mock username info if missing
        if x_service.is_mock and not x_account.x_username:
             x_account.x_username = "MockXUser"
        
        await db.commit()
        
        return HTMLResponse(
            content="""
            <html>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: #22C55E;">✅ Successfully connected to X!</h1>
                    <p>You can close this window and return to the app.</p>
                </body>
            </html>
            """
        )
        
    except Exception as e:
        return HTMLResponse(
            content=f"<h1>❌ Error connecting to X</h1><p>{str(e)}</p>", 
            status_code=500
        )


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
    
    # Exchange code for tokens
    x_service = get_x_service()
    try:
        access_token, refresh_token, expires_at = await x_service.exchange_code(
            request.code, request.state
        )
        
        # Store encrypted tokens
        x_account.access_token_encrypted = encrypt_token(access_token)
        x_account.refresh_token_encrypted = encrypt_token(refresh_token)
        x_account.token_expires_at = expires_at
        x_account.oauth_state = None  # Clear used state
        
        # For mock, set a mock username
        if x_service.is_mock:
            x_account.x_user_id = f"mock_user_{user.id}"
            x_account.x_username = "MockXUser"
        
        await db.flush()
        
        return OAuthCallbackResponse(
            success=True,
            message="Successfully connected to X",
            x_username=x_account.x_username,
        )
        
    except Exception as e:
        return OAuthCallbackResponse(
            success=False,
            message=f"OAuth error: {str(e)}",
        )


@router.get("/oauth/mock")
async def mock_oauth_redirect(state: str, request: Request):
    """
    Mock OAuth redirect for local development.
    
    Directly redirects to the callback to simulate user approval.
    """
    from fastapi.responses import RedirectResponse
    
    code = f"mock_code_{state}"
    # Use request base URL for callback to work on any host
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
    
    # Decrypt token and post
    x_service = get_x_service()
    access_token = decrypt_token(x_account.access_token_encrypted)
    
    success, message, tweet_id = await x_service.post_tweet(
        access_token, 
        draft.text
    )
    
    if success:
        from datetime import datetime
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
    else:
        draft.status = "failed"
        draft.last_error = message
        
        campaign_service = get_campaign_service()
        await campaign_service.log_action(
            db, draft.campaign_id, "failed",
            draft_id=draft.id,
            details={"error": message}
        )
    
    await db.flush()
    
    return PostResponse(
        success=success,
        message=message,
        tweet_id=tweet_id,
    )
