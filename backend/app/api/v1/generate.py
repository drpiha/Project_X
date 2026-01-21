import uuid
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User, Campaign
from app.schemas.generate import GenerateRequest, GenerateResponse
from app.generators import get_generator
from app.services.campaign_service import get_campaign_service

router = APIRouter(prefix="/campaigns", tags=["Generation"])


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


@router.post("/{campaign_id}/generate", response_model=GenerateResponse)
async def generate_drafts(
    campaign_id: str,
    request: GenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate tweet variants for a campaign using AI.

    Requires OpenRouter API key to be configured.
    Returns unique, original AI-generated tweet variants.
    """
    campaign_service = get_campaign_service()

    # Verify campaign exists and belongs to user
    campaign = await campaign_service.get_campaign(db, campaign_id, user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Validate campaign_id in request matches URL
    if request.campaign_id != campaign_id:
        raise HTTPException(
            status_code=400,
            detail="Campaign ID in request body must match URL"
        )

    # Check if AI API key is configured (Groq or OpenRouter)
    from app.core.config import get_settings
    settings = get_settings()
    has_groq = settings.groq_api_key and len(settings.groq_api_key) > 0
    has_openrouter = settings.openrouter_api_key and len(settings.openrouter_api_key) > 0
    if not has_groq and not has_openrouter:
        raise HTTPException(
            status_code=503,
            detail="AI tweet generation is not configured. Please set GROQ_API_KEY or OPENROUTER_API_KEY."
        )

    # Use LLM generator only - no fallback
    generator = get_generator("llm")

    # Generate variants with AI
    try:
        response = await generator.generate(request)
    except Exception as e:
        print(f"AI Generation Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI tweet generation failed: {str(e)}"
        )

    # Save drafts to database
    for variant in response.variants:
        await campaign_service.create_draft(
            db=db,
            campaign_id=campaign_id,
            variant_index=variant.variant_index,
            text=variant.text,
            char_count=variant.char_count,
            hashtags_used=variant.hashtags_used,
        )

    # Log generation
    await campaign_service.log_action(
        db, campaign_id, "generated",
        details={
            "variants_count": len(response.variants),
            "generator": response.generator,
            "language": response.language,
        }
    )

    return response
