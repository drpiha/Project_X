# API v1 module
from fastapi import APIRouter
from app.api.v1 import auth, settings, campaigns, generate, schedule, logs, oauth, media

router = APIRouter(prefix="/v1")

router.include_router(auth.router)
router.include_router(settings.router)
router.include_router(campaigns.router)
router.include_router(generate.router)
router.include_router(schedule.router)
router.include_router(logs.router)
router.include_router(oauth.router)
router.include_router(media.router)
