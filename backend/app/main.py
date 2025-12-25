from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.v1 import router as api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Social Media Campaign API",
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
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

# Mount media files for serving
media_path = Path(settings.media_storage_path)
media_path.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_path)), name="media")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Social Media Campaign API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
