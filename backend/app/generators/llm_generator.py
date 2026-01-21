from typing import Optional, List
import json
import re
from openai import AsyncOpenAI
from app.generators.base import BaseTweetGenerator
from app.schemas.generate import GenerateRequest, GenerateResponse, VariantResponse
from app.core.config import get_settings


class LLMGenerator(BaseTweetGenerator):
    """
    Tweet generator using LLMs via Groq or OpenRouter (OpenAI-compatible APIs).
    Groq is preferred - NO daily limit, just 30 req/min.
    """

    def __init__(self):
        self.settings = get_settings()
        self.provider = self.settings.ai_provider.lower()

        # Try Groq first (recommended - no daily limit)
        if self.provider == "groq" and self.settings.groq_api_key:
            self.client = AsyncOpenAI(
                api_key=self.settings.groq_api_key,
                base_url=self.settings.groq_base_url,
            )
            self.model = self.settings.groq_model
            self.provider_name = "groq"
        # Fallback to OpenRouter
        elif self.settings.openrouter_api_key:
            self.client = AsyncOpenAI(
                api_key=self.settings.openrouter_api_key,
                base_url=self.settings.openrouter_base_url,
            )
            self.model = self.settings.openrouter_model
            self.provider_name = "openrouter"
        else:
            raise ValueError("No AI API key configured. Set GROQ_API_KEY or OPENROUTER_API_KEY.")

    @property
    def generator_name(self) -> str:
        return f"llm_{self.model}"

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate tweet variants using LLM."""

        system_prompt = self._build_system_prompt(request)
        user_prompt = self._build_user_prompt(request)

        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,  # Balanced - creative but not random
                max_tokens=2000,
            )

            content = completion.choices[0].message.content

            # Try to extract JSON from the response
            data = self._parse_json_response(content)

            variants = []
            for i, item in enumerate(data.get("variants", [])):
                text = item.get("text", "").strip()

                # Quality control: Skip empty or too short tweets
                if not text or len(text) < 20:
                    print(f"Skipping variant {i}: too short or empty")
                    continue

                # Quality control: Skip tweets that are just hashtags
                if text.startswith('#') and len(text.split()) < 3:
                    print(f"Skipping variant {i}: only hashtags")
                    continue

                # Append user-provided hashtags/tags to the end if not already present
                if request.hashtags:
                    text = self._append_hashtags(text, request.hashtags)

                # Enforce character limit
                if len(text) > request.constraints.max_chars:
                    text = self._truncate_text(text, request.constraints.max_chars)

                char_count = len(text)

                # Quality control: Skip if text became too short after truncation
                if char_count < 30:
                    print(f"Skipping variant {i}: too short after processing")
                    continue

                variants.append(VariantResponse(
                    variant_index=i,
                    text=text,
                    char_count=char_count,
                    hashtags_used=request.hashtags or [],
                    safety_notes=[]
                ))

            # Ensure we have at least some variants
            if len(variants) == 0:
                raise ValueError("No valid variants generated. AI output was low quality.")

            # Return what we have (may be less than requested if quality filtering removed some)
            variants = variants[:request.output.variants]

            return GenerateResponse(
                campaign_id=request.campaign_id,
                language=request.language,
                variants=variants,
                recommended_alt_text=data.get("alt_text", ""),
                generator=self.generator_name
            )

        except Exception as e:
            print(f"LLM Generation Error: {e}")
            raise RuntimeError(f"AI tweet generation failed: {str(e)}")

    def _parse_json_response(self, content: str) -> dict:
        """Parse JSON from LLM response, handling various formats."""
        # Try direct JSON parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find raw JSON object
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse JSON from LLM response: {content[:200]}")

    def _append_hashtags(self, text: str, hashtags: List[str]) -> str:
        """Append hashtags to tweet if not already present."""
        hashtags_to_add = []
        for tag in hashtags:
            tag_text = tag.strip()
            if tag_text.lower() not in text.lower():
                hashtags_to_add.append(tag_text)

        if hashtags_to_add:
            separator = " " if text and not text.endswith(" ") else ""
            text = text + separator + " ".join(hashtags_to_add)

        return text

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncate text to max characters while preserving meaning."""
        if len(text) <= max_chars:
            return text

        # Try to cut at a sentence boundary
        truncated = text[:max_chars - 3]
        last_period = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))
        if last_period > max_chars // 2:
            return text[:last_period + 1]

        # Otherwise cut at word boundary
        last_space = truncated.rfind(' ')
        if last_space > max_chars // 2:
            return truncated[:last_space] + "..."

        return truncated + "..."

    def generate_alt_text(self, language: str, image_context: Optional[str]) -> str:
        return "AI generated tweet image"

    def _build_system_prompt(self, request: GenerateRequest) -> str:
        """Build a comprehensive system prompt for high-quality tweet generation."""

        language_instructions = {
            "tr": """Sen profesyonel bir Türkçe sosyal medya içerik uzmanısın.
Görevin, verilen konu hakkında kaliteli, etkili ve alakalı tweet'ler üretmek.
Türkçe dilbilgisine dikkat et, doğal ve akıcı cümleler kur.""",
            "en": """You are a professional English social media content expert.
Your task is to create high-quality, effective, and relevant tweets about the given topic.
Pay attention to grammar and write natural, fluent sentences.""",
            "de": """Du bist ein professioneller deutscher Social-Media-Content-Experte.
Deine Aufgabe ist es, qualitativ hochwertige, effektive und relevante Tweets zu erstellen.
Achte auf Grammatik und schreibe natürliche, fließende Sätze."""
        }

        tone_instructions = {
            "informative": """Bilgilendirici Ton:
- Konuyu net ve anlaşılır şekilde açıkla
- Önemli bilgileri, istatistikleri veya gerçekleri vurgula
- Nesnel ve güvenilir bir üslup kullan
- Okuyucuyu eğitmeyi ve bilgilendirmeyi hedefle
- Abartısız, sade bir dil kullan""",

            "emotional": """Duygusal Ton:
- İnsan hikayeleri ve deneyimlerine odaklan
- Empati kuran, samimi bir dil kullan
- Okuyucunun duygularına hitap et
- Gerçek ve özgün ifadeler kullan
- Kalbe dokunan, etkileyici anlatım yap""",

            "formal": """Resmi Ton:
- Profesyonel ve kurumsal bir dil kullan
- Saygılı ve ciddi bir üslup benimse
- Resmi iletişim standartlarına uy
- Net, anlaşılır ama resmi ifadeler kullan
- Güvenilir ve otoriter bir tutum sergile""",

            "hopeful": """Umut Verici Ton:
- Pozitif ve iyimser bir bakış açısı sun
- Geleceğe dair umut veren mesajlar ver
- Motivasyon ve ilham kaynağı ol
- Zorlukları fırsata dönüştürmeyi vurgula
- İyimser ama gerçekçi bir yaklaşım kullan""",

            "call_to_action": """Eylem Çağrısı Tonu:
- Okuyucuyu harekete geçmeye teşvik et
- Net ve doğrudan çağrılarda bulun
- Aciliyet hissi yaratarak motive et
- Somut adımlar öner
- Kararlı ve inandırıcı bir dil kullan"""
        }

        lang = request.language
        tone = request.tone

        tone_name_map = {
            "informative": "BİLGİLENDİRİCİ",
            "emotional": "DUYGUSAL",
            "formal": "RESMİ",
            "hopeful": "UMUT VERİCİ",
            "call_to_action": "EYLEM ÇAĞRISI"
        }
        tone_display = tone_name_map.get(tone, tone.upper())

        return f"""{language_instructions.get(lang, language_instructions["en"])}

========================================
ÇOK ÖNEMLİ: SEÇİLİ TON = {tone_display}
========================================

{tone_instructions.get(tone, tone_instructions["informative"])}

UYARI: SADECE {tone_display} TONUNDA TWEET ÜRET!
Diğer tonları kullanma, karıştırma veya değiştirme.

KALİTE KURALLARI:
1. Her tweet verilen konuyla DOĞRUDAN alakalı olmalı
2. Mantıklı, gerçekçi ve anlamlı içerik üret
3. Saçma, alakasız veya yanlış bilgi ASLA üretme
4. Her tweet özgün ve farklı bir perspektif sunmalı
5. Doğal, akıcı Türkçe/dil kullan - yapay veya zorlama ifadelerden kaçın
6. Tweet uzunluğu: maksimum {request.constraints.max_chars}, hedef {request.constraints.target_chars} karakter
7. {"Doğal ve az emoji kullan (1-2 adet)" if request.constraints.include_emojis else "Emoji kullanma"}

ÇIKTI FORMATI:
Sadece JSON formatında yanıt ver, başka açıklama ekleme:
{{
  "variants": [
    {{"text": "İlk tweet metni..."}},
    {{"text": "İkinci tweet metni..."}},
    {{"text": "Üçüncü tweet metni..."}}
  ],
  "alt_text": "Görsel için kısa açıklama"
}}

ÖNEMLİ: Yalnızca geçerli JSON döndür."""

    def _build_user_prompt(self, request: GenerateRequest) -> str:
        """Build the user prompt with campaign details."""

        tone_name_map = {
            "informative": "BİLGİLENDİRİCİ",
            "emotional": "DUYGUSAL",
            "formal": "RESMİ",
            "hopeful": "UMUT VERİCİ",
            "call_to_action": "EYLEM ÇAĞRISI"
        }
        tone_display = tone_name_map.get(request.tone, request.tone.upper())

        prompt = f"""Konu: {request.topic_summary}

Gereksinimler:
- Üretilecek tweet sayısı: {request.output.variants}
- Dil: {request.language}
- TON: {tone_display} (ÇOK ÖNEMLİ!)"""

        if request.hashtags:
            prompt += f"\n- Hashtag'ler (tweet sonuna ekle): {', '.join(request.hashtags)}"

        if request.call_to_action:
            prompt += f"\n- Eylem çağrısı: {request.call_to_action}"

        if request.anti_repeat.avoid_phrases:
            prompt += f"\n- Bu ifadelerden kaçın: {', '.join(request.anti_repeat.avoid_phrases)}"

        prompt += f"""

HATIRLATMA: SADECE {tone_display} TONUNDA TWEET ÜRET!
- Informative ise: Nesnel, bilgilendirici, eğitici dil kullan
- Emotional ise: Duygusal, empati kuran, hikaye anlatan dil kullan
- Formal ise: Resmi, kurumsal, profesyonel dil kullan
- Hopeful ise: Pozitif, umut verici, iyimser dil kullan
- Call to action ise: Harekete geçirici, doğrudan, acil dil kullan

Lütfen bu konu hakkında {request.output.variants} farklı tweet üret.
Her tweet MUTLAKA:
- {tone_display} tonunda olmalı (başka ton kullanma!)
- Konuyla doğrudan alakalı
- Özgün ve anlamlı
- {request.constraints.target_chars} karakter civarında

JSON formatında yanıtla."""

        return prompt
