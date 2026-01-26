import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.v1 import router as api_router
from app.core.config import get_settings
from app.db.session import get_db
from app.db.models import Campaign

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Background scheduler task
scheduler_task = None


async def run_scheduler_loop():
    """Background scheduler loop that runs within the FastAPI app."""
    from worker.scheduler import run_scheduler_cycle

    logger.info("🚀 Scheduler started as background task")
    logger.info(f"📅 Interval: {settings.scheduler_interval_seconds} seconds")

    while True:
        try:
            await run_scheduler_cycle()
        except Exception as e:
            logger.error(f"Scheduler cycle error: {e}")

        await asyncio.sleep(settings.scheduler_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifespan - start/stop scheduler."""
    global scheduler_task

    # Startup: Start scheduler
    logger.info("Starting application...")
    scheduler_task = asyncio.create_task(run_scheduler_loop())
    logger.info("✅ Scheduler background task created")

    yield

    # Shutdown: Cancel scheduler
    logger.info("Shutting down application...")
    if scheduler_task:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            logger.info("Scheduler task cancelled")


app = FastAPI(
    title="Social Media Campaign API",
    lifespan=lifespan,  # Enable scheduler on startup
    description="""
    API for creating and scheduling social media campaign posts to X (Twitter).

    ## Features
    - Anonymous user authentication
    - Campaign creation with media uploads
    - Rule-based tweet generation (6 variants)
    - Scheduling with timezone support
    - Mock X posting for local development

    ## Authentication
    All endpoints (except /v1/auth/anonymous) require the `X-User-Id` header
    with a valid user UUID from the anonymous auth endpoint.
    """,
    version="1.0.0",
    docs_url="/docs" if settings.is_development else None,  # Disable docs in production
    redoc_url="/redoc" if settings.is_development else None,
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware with proper configuration
allowed_origins = settings.allowed_origins_list

# In development, also allow any localhost origin
if settings.is_development:
    # Add wildcard for development convenience but log a warning
    logger.warning("Development mode: CORS is permissive. Do not use in production!")
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True if allowed_origins != ["*"] else False,  # Can't use credentials with wildcard
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-User-Id", "X-Request-ID"],
    max_age=600,  # Cache preflight for 10 minutes
)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # HSTS only in production with HTTPS
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # Remove server header
    if "server" in response.headers:
        del response.headers["server"]

    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s - "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )

    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.exception(f"Unhandled exception: {str(exc)}")

    # In development, show error details
    if settings.is_development:
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "type": type(exc).__name__}
        )

    # In production, include error type for debugging
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {str(exc)}"}
    )


# Include API routes
app.include_router(api_router)


# Secure media endpoint with authorization
@app.get("/media/{campaign_id}/{filename}")
async def get_media_file(
    campaign_id: str,
    filename: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Serve media files with authorization check.
    Requires X-User-Id header to verify ownership.
    """
    import uuid as uuid_module
    from fastapi import Header
    from app.db.models import User

    # Get user ID from header (optional for media, but verify if provided)
    x_user_id = request.headers.get("X-User-Id")

    # Validate campaign_id format
    try:
        uuid_module.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid campaign ID")

    # Verify campaign exists and optionally check ownership
    query = select(Campaign).where(Campaign.id == campaign_id)
    result = await db.execute(query)
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # If user ID provided, verify ownership
    if x_user_id:
        try:
            uuid_module.UUID(x_user_id)
            if str(campaign.user_id) != x_user_id:
                raise HTTPException(status_code=403, detail="Access denied")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user ID")

    # Validate filename (prevent path traversal)
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Build path
    media_path = Path(settings.media_storage_path) / campaign_id / filename

    # Ensure we're still within media directory (extra path traversal protection)
    try:
        media_path = media_path.resolve()
        base_path = Path(settings.media_storage_path).resolve()
        if not str(media_path).startswith(str(base_path)):
            raise HTTPException(status_code=400, detail="Invalid path")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    if not media_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Determine content type
    suffix = media_path.suffix.lower()
    content_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".webm": "video/webm",
    }
    content_type = content_types.get(suffix, "application/octet-stream")

    return FileResponse(
        media_path,
        media_type=content_type,
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        }
    )


# Mount static files (for OAuth callback page only)
static_path = Path(__file__).parent / "static"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.environment,
        "scheduler": "running" if scheduler_task and not scheduler_task.done() else "stopped",
    }


@app.get("/debug/scheduled-drafts")
async def debug_scheduled_drafts(db: AsyncSession = Depends(get_db)):
    """Debug endpoint to see all scheduled drafts and their status."""
    # SECURITY: Only allow in development mode
    if not settings.is_development:
        raise HTTPException(status_code=404, detail="Not found")

    from datetime import datetime
    from app.db.models import Draft, Schedule

    now_utc = datetime.utcnow()

    # Get all pending drafts with scheduled_for
    query = select(Draft).where(
        Draft.status == "pending",
        Draft.scheduled_for != None
    ).order_by(Draft.scheduled_for)

    result = await db.execute(query)
    drafts = result.scalars().all()

    draft_info = []
    for d in drafts:
        # Check if schedule has auto_post
        auto_post = False
        if d.schedule_id:
            schedule_query = select(Schedule).where(Schedule.id == d.schedule_id)
            schedule_result = await db.execute(schedule_query)
            schedule = schedule_result.scalar_one_or_none()
            if schedule:
                auto_post = schedule.auto_post

        time_diff = (d.scheduled_for - now_utc).total_seconds() if d.scheduled_for else None

        draft_info.append({
            "id": str(d.id),
            "campaign_id": str(d.campaign_id),
            "scheduled_for_utc": d.scheduled_for.isoformat() if d.scheduled_for else None,
            "status": d.status,
            "auto_post": auto_post,
            "seconds_until_due": time_diff,
            "is_due": time_diff <= 0 if time_diff is not None else False,
            "text_preview": d.text[:50] + "..." if d.text and len(d.text) > 50 else d.text,
        })

    return {
        "server_time_utc": now_utc.isoformat(),
        "pending_drafts_count": len(draft_info),
        "drafts": draft_info,
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Social Media Campaign API",
        "version": "1.0.0",
        "docs": "/docs" if settings.is_development else None,
        "health": "/health",
    }
