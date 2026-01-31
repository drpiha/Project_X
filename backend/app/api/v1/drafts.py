import uuid
import logging
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User, Campaign, Draft
from app.generators import get_generator
from app.schemas.generate import GenerateRequest, GenerateOutput

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/drafts", tags=["Drafts"])


async def get_current_user(
    x_user_id: str = Header(..., description="User ID from anonymous auth"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from header."""
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


async def get_draft_with_auth(
    draft_id: str, user: User, db: AsyncSession
) -> Draft:
    """Get a draft and verify the user owns it via the campaign."""
    try:
        uuid.UUID(draft_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid draft ID format")

    query = select(Draft).where(Draft.id == draft_id)
    result = await db.execute(query)
    draft = result.scalar_one_or_none()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Verify user owns the campaign
    campaign_query = select(Campaign).where(
        Campaign.id == draft.campaign_id,
        Campaign.user_id == user.id
    )
    result = await db.execute(campaign_query)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Draft not found")

    return draft


class UpdateDraftRequest(BaseModel):
    text: Optional[str] = None
    scheduled_for: Optional[str] = None
    status: Optional[str] = None


@router.put("/{draft_id}")
async def update_draft(
    draft_id: str,
    request: UpdateDraftRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a draft's text, scheduled time, or status."""
    draft = await get_draft_with_auth(draft_id, user, db)

    if request.text is not None:
        draft.text = request.text
        draft.char_count = len(request.text)

    if request.scheduled_for is not None:
        try:
            parsed_dt = datetime.fromisoformat(
                request.scheduled_for.replace('Z', '+00:00')
            )
            # Store as naive UTC
            if parsed_dt.tzinfo is not None:
                import pytz
                scheduled_utc = parsed_dt.astimezone(pytz.UTC).replace(tzinfo=None)
            else:
                scheduled_utc = parsed_dt
            draft.scheduled_for = scheduled_utc
            logger.info(f"Draft {draft_id} rescheduled to {scheduled_utc}")
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid datetime format: {e}"
            )

    if request.status is not None:
        draft.status = request.status

    await db.commit()
    await db.refresh(draft)

    return {
        "id": str(draft.id),
        "campaign_id": str(draft.campaign_id),
        "text": draft.text,
        "char_count": draft.char_count,
        "scheduled_for": draft.scheduled_for.isoformat() if draft.scheduled_for else None,
        "status": draft.status,
        "variant_index": draft.variant_index,
    }


@router.post("/{draft_id}/regenerate")
async def regenerate_draft(
    draft_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Regenerate a single draft's text using AI."""
    draft = await get_draft_with_auth(draft_id, user, db)

    # Get the campaign for context
    campaign_query = select(Campaign).where(Campaign.id == draft.campaign_id)
    result = await db.execute(campaign_query)
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    try:
        generator = get_generator("llm")

        topic = campaign.title
        if campaign.description:
            topic = f"{campaign.title}: {campaign.description}"

        gen_request = GenerateRequest(
            campaign_id=campaign.id,
            topic_summary=topic,
            language=campaign.language,
            hashtags=campaign.hashtags,
            tone=campaign.tone or "informative",
            call_to_action=campaign.call_to_action,
            output=GenerateOutput(variants=1),
        )

        response = await generator.generate(gen_request)

        if response.variants:
            new_text = response.variants[0].text
            new_char_count = response.variants[0].char_count

            draft.text = new_text
            draft.char_count = new_char_count
            await db.commit()

            return {
                "id": str(draft.id),
                "text": new_text,
                "char_count": new_char_count,
                "variant_index": draft.variant_index,
            }
        else:
            raise HTTPException(
                status_code=500, detail="AI generation returned no variants"
            )

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Regeneration error for draft {draft_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to regenerate: {str(e)}"
        )


@router.delete("/{draft_id}")
async def delete_draft(
    draft_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a draft."""
    draft = await get_draft_with_auth(draft_id, user, db)

    await db.delete(draft)
    await db.commit()

    return {"success": True, "deleted_id": draft_id}
