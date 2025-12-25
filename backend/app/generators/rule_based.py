import random
from typing import List, Optional, Dict
from app.generators.base import BaseTweetGenerator
from app.schemas.generate import GenerateRequest, GenerateResponse, VariantResponse


class RuleBasedGenerator(BaseTweetGenerator):
    """
    Deterministic, rule-based tweet generator.
    
    Generates 6 distinct tweet variants by combining:
    - Angle rotation templates (human_story, facts, solution, international, solidarity)
    - Synonyms list per language
    - Optional emojis based on density settings
    - Natural hashtag placement
    - Character limit enforcement
    """
    
    # Templates by language and angle
    TEMPLATES: Dict[str, Dict[str, List[str]]] = {
        "tr": {
            "human_story": [
                "{topic} hakkında düşündükçe, insan hikayelerinin gücünü görüyoruz. {cta}",
                "Gerçek insanların {topic} ile yaşadığı deneyimler bize ilham veriyor. {cta}",
                "Her birimizin {topic} konusunda bir hikayesi var. {cta}",
            ],
            "facts": [
                "{topic} konusunda bilmeniz gereken gerçekler var. {cta}",
                "Araştırmalar {topic} hakkında önemli sonuçlar ortaya koyuyor. {cta}",
                "{topic} ile ilgili veriler dikkat çekici. {cta}",
            ],
            "solution": [
                "{topic} için somut çözümler üretebiliriz. {cta}",
                "Birlikte {topic} konusunda değişim yaratabiliriz. {cta}",
                "{topic} sorununa pratik yaklaşımlar mümkün. {cta}",
            ],
            "international_awareness": [
                "Dünya genelinde {topic} konusu giderek daha fazla gündemde. {cta}",
                "Uluslararası arenada {topic} tartışılıyor. {cta}",
                "Global perspektiften {topic} değerlendirmesi. {cta}",
            ],
            "solidarity": [
                "{topic} konusunda dayanışma şart. {cta}",
                "Birlik ve beraberlikle {topic} için ses çıkarıyoruz. {cta}",
                "Omuz omuza {topic} için mücadele ediyoruz. {cta}",
            ],
        },
        "en": {
            "human_story": [
                "Thinking about {topic}, we see the power of human stories. {cta}",
                "Real experiences with {topic} inspire us all. {cta}",
                "Each of us has a story about {topic}. {cta}",
            ],
            "facts": [
                "Here are facts you need to know about {topic}. {cta}",
                "Research reveals important findings about {topic}. {cta}",
                "The data on {topic} is striking. {cta}",
            ],
            "solution": [
                "We can create concrete solutions for {topic}. {cta}",
                "Together, we can drive change on {topic}. {cta}",
                "Practical approaches to {topic} are possible. {cta}",
            ],
            "international_awareness": [
                "Globally, {topic} is increasingly in the spotlight. {cta}",
                "{topic} is being discussed on the international stage. {cta}",
                "A global perspective on {topic}. {cta}",
            ],
            "solidarity": [
                "Solidarity is essential for {topic}. {cta}",
                "United, we raise our voice for {topic}. {cta}",
                "Standing together for {topic}. {cta}",
            ],
        },
        "de": {
            "human_story": [
                "Wenn wir über {topic} nachdenken, sehen wir die Kraft menschlicher Geschichten. {cta}",
                "Echte Erfahrungen mit {topic} inspirieren uns alle. {cta}",
                "Jeder von uns hat eine Geschichte über {topic}. {cta}",
            ],
            "facts": [
                "Hier sind Fakten, die Sie über {topic} wissen sollten. {cta}",
                "Forschungen zeigen wichtige Erkenntnisse über {topic}. {cta}",
                "Die Daten zu {topic} sind bemerkenswert. {cta}",
            ],
            "solution": [
                "Wir können konkrete Lösungen für {topic} schaffen. {cta}",
                "Gemeinsam können wir bei {topic} Veränderungen bewirken. {cta}",
                "Praktische Ansätze für {topic} sind möglich. {cta}",
            ],
            "international_awareness": [
                "Weltweit steht {topic} zunehmend im Fokus. {cta}",
                "{topic} wird auf internationaler Ebene diskutiert. {cta}",
                "Eine globale Perspektive auf {topic}. {cta}",
            ],
            "solidarity": [
                "Solidarität ist für {topic} unerlässlich. {cta}",
                "Vereint erheben wir unsere Stimme für {topic}. {cta}",
                "Gemeinsam stehen wir für {topic} ein. {cta}",
            ],
        },
    }
    
    # Tone modifiers by language
    TONE_PREFIXES: Dict[str, Dict[str, List[str]]] = {
        "tr": {
            "informative": ["📊", "ℹ️", "📌"],
            "emotional": ["💔", "🥺", "😢", "❤️"],
            "formal": [""],
            "hopeful": ["🌟", "✨", "🌈", "💪"],
            "call_to_action": ["🚨", "⚡", "📢"],
        },
        "en": {
            "informative": ["📊", "ℹ️", "📌"],
            "emotional": ["💔", "🥺", "😢", "❤️"],
            "formal": [""],
            "hopeful": ["🌟", "✨", "🌈", "💪"],
            "call_to_action": ["🚨", "⚡", "📢"],
        },
        "de": {
            "informative": ["📊", "ℹ️", "📌"],
            "emotional": ["💔", "🥺", "😢", "❤️"],
            "formal": [""],
            "hopeful": ["🌟", "✨", "🌈", "💪"],
            "call_to_action": ["🚨", "⚡", "📢"],
        },
    }
    
    # Alt text templates
    ALT_TEXT_TEMPLATES: Dict[str, str] = {
        "tr": "Görsel: {context}. Sosyal medya kampanyası için hazırlanmış içerik.",
        "en": "Image: {context}. Content prepared for social media campaign.",
        "de": "Bild: {context}. Inhalt für Social-Media-Kampagne vorbereitet.",
    }
    
    ALT_TEXT_DEFAULT: Dict[str, str] = {
        "tr": "Kampanya görseli - sosyal farkındalık içeriği",
        "en": "Campaign image - social awareness content",
        "de": "Kampagnenbild - Inhalte zur sozialen Sensibilisierung",
    }
    
    @property
    def generator_name(self) -> str:
        return "rule_based_v1"
    
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate tweet variants using rule-based templates."""
        language = request.language
        variants: List[VariantResponse] = []
        
        # Get angles to rotate through
        angles = request.anti_repeat.rotate_angles or [
            "human_story", "facts", "solution", "international_awareness", "solidarity"
        ]
        
        # Generate requested number of variants
        for i in range(request.output.variants):
            # Rotate through angles
            angle = angles[i % len(angles)]
            
            # Get templates for this angle
            templates = self.TEMPLATES.get(language, self.TEMPLATES["en"]).get(
                angle, self.TEMPLATES["en"]["human_story"]
            )
            
            # Pick a template (rotate through available ones)
            template = templates[i % len(templates)]
            
            # Prepare CTA
            cta = request.call_to_action or ""
            
            # Generate base text
            text = template.format(topic=request.topic_summary, cta=cta)
            
            # Add emoji if enabled
            if request.constraints.include_emojis and request.constraints.emoji_density != "none":
                emoji = self._get_emoji(language, request.tone, request.constraints.emoji_density)
                if emoji:
                    text = f"{emoji} {text}"
            
            # Insert hashtags naturally
            text, hashtags_used = self._insert_hashtags(text, request.hashtags, request.constraints.target_chars)
            
            # Enforce character limit
            text = self._enforce_char_limit(text, request.constraints.max_chars, hashtags_used)
            
            # Check for phrases to avoid
            for phrase in request.anti_repeat.avoid_phrases:
                if phrase.lower() in text.lower():
                    # Try to rephrase or skip this variant
                    text = text.replace(phrase, "")
            
            # Clean up text
            text = self._clean_text(text)
            
            # Validate
            is_valid, safety_notes = self.validate_tweet(text, request.constraints.max_chars)
            
            variant = VariantResponse(
                variant_index=i,
                text=text,
                char_count=len(text),
                hashtags_used=hashtags_used,
                safety_notes=safety_notes,
            )
            variants.append(variant)
        
        # Determine best variant (shortest that includes all hashtags and is under limit)
        best_index = self._find_best_variant(variants, request.hashtags, request.constraints.target_chars)
        
        # Generate alt text
        alt_text = self.generate_alt_text(language, request.assets.image_context)
        
        return GenerateResponse(
            campaign_id=request.campaign_id,
            language=language,
            variants=variants,
            best_variant_index=best_index,
            recommended_alt_text=alt_text,
            generator=self.generator_name,
        )
    
    def generate_alt_text(self, language: str, image_context: Optional[str]) -> str:
        """Generate alt text for images."""
        if image_context:
            template = self.ALT_TEXT_TEMPLATES.get(language, self.ALT_TEXT_TEMPLATES["en"])
            return template.format(context=image_context)
        return self.ALT_TEXT_DEFAULT.get(language, self.ALT_TEXT_DEFAULT["en"])
    
    def _get_emoji(self, language: str, tone: str, density: str) -> str:
        """Get appropriate emoji based on tone and density."""
        emojis = self.TONE_PREFIXES.get(language, self.TONE_PREFIXES["en"]).get(
            tone, [""]
        )
        if not emojis or emojis == [""]:
            return ""
        
        if density == "low":
            return random.choice(emojis) if random.random() > 0.5 else ""
        elif density == "medium":
            return random.choice(emojis)
        return ""
    
    def _insert_hashtags(self, text: str, hashtags: List[str], target_chars: int) -> tuple[str, List[str]]:
        """Insert hashtags naturally into the text or at the end."""
        if not hashtags:
            return text, []
        
        hashtags_used = []
        remaining_chars = target_chars - len(text)
        
        # Try to fit hashtags
        for tag in hashtags:
            tag_with_space = f" {tag}"
            if remaining_chars >= len(tag_with_space):
                remaining_chars -= len(tag_with_space)
                hashtags_used.append(tag)
        
        # Add hashtags at the end with proper spacing
        if hashtags_used:
            hashtag_str = " ".join(hashtags_used)
            text = f"{text.rstrip()} {hashtag_str}"
        
        return text, hashtags_used
    
    def _enforce_char_limit(self, text: str, max_chars: int, hashtags: List[str]) -> str:
        """Ensure text fits within character limit."""
        if len(text) <= max_chars:
            return text
        
        # Calculate space needed for hashtags
        hashtag_space = sum(len(tag) + 1 for tag in hashtags)
        
        # Truncate main text while preserving hashtags
        available = max_chars - hashtag_space - 3  # -3 for "..."
        
        # Find main text (before hashtags)
        main_text = text
        for tag in hashtags:
            main_text = main_text.replace(tag, "").strip()
        
        if len(main_text) > available:
            # Truncate at word boundary
            truncated = main_text[:available]
            last_space = truncated.rfind(' ')
            if last_space > available // 2:
                truncated = truncated[:last_space]
            truncated = truncated.rstrip('.,!? ') + "..."
            
            # Reconstruct with hashtags
            if hashtags:
                text = f"{truncated} {' '.join(hashtags)}"
            else:
                text = truncated
        
        return text
    
    def _clean_text(self, text: str) -> str:
        """Clean up text formatting."""
        # Remove double spaces
        while "  " in text:
            text = text.replace("  ", " ")
        
        # Trim
        text = text.strip()
        
        return text
    
    def _find_best_variant(self, variants: List[VariantResponse], target_hashtags: List[str], target_chars: int) -> int:
        """Find the best variant based on criteria."""
        best_index = 0
        best_score = -1
        
        for variant in variants:
            score = 0
            
            # Prefer variants with more hashtags used
            score += len(variant.hashtags_used) * 10
            
            # Prefer variants close to target length
            diff = abs(variant.char_count - target_chars)
            score += max(0, 50 - diff)
            
            # Penalize safety notes
            score -= len(variant.safety_notes) * 20
            
            # Penalize being over limit
            if variant.char_count > 280:
                score -= 100
            
            if score > best_score:
                best_score = score
                best_index = variant.variant_index
        
        return best_index



