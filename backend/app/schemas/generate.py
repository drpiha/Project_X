from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class GenerateConstraints(BaseModel):
    """Constraints for tweet generation."""
    max_chars: int = Field(280, ge=100, le=280)
    target_chars: int = Field(268, ge=100, le=280)
    include_emojis: bool = True
    emoji_density: Literal["none", "low", "medium"] = "low"


class GenerateAssets(BaseModel):
    """Asset information for generation context."""
    image_count: int = Field(0, ge=0, le=10)
    video_present: bool = False
    image_context: Optional[str] = Field(None, max_length=200)


class GenerateAntiRepeat(BaseModel):
    """Anti-repetition settings."""
    avoid_phrases: List[str] = Field(default_factory=list)
    rotate_angles: List[str] = Field(
        default_factory=lambda: ["human_story", "facts", "solution", "international_awareness", "solidarity"]
    )


class GenerateOutput(BaseModel):
    """Output configuration."""
    variants: int = Field(6, ge=1, le=10)


class GenerateRequest(BaseModel):
    """Request to generate tweet variants."""
    campaign_id: str
    language: Literal["tr", "en", "de"] = "tr"
    topic_summary: str = Field(..., min_length=1, max_length=500)
    hashtags: List[str] = Field(default_factory=list)
    tone: Literal["informative", "emotional", "formal", "hopeful", "call_to_action"] = "informative"
    call_to_action: Optional[str] = Field(None, max_length=80)
    constraints: GenerateConstraints = Field(default_factory=GenerateConstraints)
    assets: GenerateAssets = Field(default_factory=GenerateAssets)
    anti_repeat: GenerateAntiRepeat = Field(default_factory=GenerateAntiRepeat)
    output: GenerateOutput = Field(default_factory=GenerateOutput)


class VariantResponse(BaseModel):
    """A single generated tweet variant."""
    variant_index: int
    text: str
    char_count: int
    hashtags_used: List[str] = []
    safety_notes: List[str] = []


class GenerateResponse(BaseModel):
    """Response from tweet generation."""
    campaign_id: str
    language: str
    variants: List[VariantResponse]
    best_variant_index: int = 0
    recommended_alt_text: str = ""
    generator: str = "rule_based_v1"
