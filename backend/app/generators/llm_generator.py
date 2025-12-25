from typing import Optional, List
import json
from openai import AsyncOpenAI
from app.generators.base import BaseTweetGenerator
from app.schemas.generate import GenerateRequest, GenerateResponse, VariantResponse
from app.core.config import get_settings

class LLMGenerator(BaseTweetGenerator):
    """
    Tweet generator using LLMs via OpenRouter (OpenAI-compatible API).
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=self.settings.openrouter_api_key,
            base_url=self.settings.openrouter_base_url,
        )
        self.model = self.settings.openrouter_model

    @property
    def generator_name(self) -> str:
        return f"llm_{self.model}"
    
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate tweet variants using LLM."""
        
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(request)
        
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                response_format={"type": "json_object"},
            )
            
            content = completion.choices[0].message.content
            data = json.loads(content)
            
            variants = []
            for i, item in enumerate(data.get("variants", [])):
                text = item.get("text", "")
                hashtags = item.get("hashtags", [])
                
                # Basic validation
                char_count = len(text)
                
                variants.append(VariantResponse(
                    variant_index=i,
                    text=text,
                    char_count=char_count,
                    hashtags_used=hashtags,
                    safety_notes=[]
                ))
            
            # Ensure we respect the requested number of variants
            variants = variants[:request.output.variants]
            
            return GenerateResponse(
                campaign_id=request.campaign_id,
                language=request.language,
                variants=variants,
                recommended_alt_text=data.get("alt_text", ""),
                generator=self.generator_name
            )
            
        except Exception as e:
            # Fallback or re-raise? For now re-raise to see errors
            print(f"LLM Generation Error: {e}")
            raise

    def generate_alt_text(self, language: str, image_context: Optional[str]) -> str:
        # Implementation for standalone alt text if needed
        return "Generated alt text placeholder"

    def _build_system_prompt(self) -> str:
        return """You are an expert social media manager and copywriter.
You specialize in creating engaging, viral, and high-impact tweets for X (Twitter).
Your output must be a valid JSON object with the following structure:
{
  "variants": [
    {
      "text": "Tweet text here...",
      "hashtags": ["#tag1", "#tag2"]
    }
  ],
  "alt_text": "Recommended alt text for media..."
}
Ensure strictly valid JSON output."""

    def _build_user_prompt(self, request: GenerateRequest) -> str:
        prompt = f"""Generate {request.output.variants} unique tweet variants for a campaign.

**Topic & Context:**
{request.topic_summary}

**Language:** {request.language}
**Tone:** {request.tone}
**Constraints:**
- Max characters: {request.constraints.max_chars}
- Target characters: {request.constraints.target_chars}
- Include Emojis: {request.constraints.include_emojis}
"""

        if request.hashtags:
            prompt += f"**Required Hashtags:** {', '.join(request.hashtags)}\n"
            
        if request.call_to_action:
            prompt += f"**Call to Action:** {request.call_to_action}\n"
            
        if request.anti_repeat.avoid_phrases:
            prompt += f"**Avoid Phrases:** {', '.join(request.anti_repeat.avoid_phrases)}\n"
            
        return prompt
