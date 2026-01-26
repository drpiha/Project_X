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
    
    # Templates by language and TONE (not angle)
    TEMPLATES: Dict[str, Dict[str, List[str]]] = {
        "tr": {
            "informative": [
                "Biliyor muydunuz? {topic} hakkında önemli veriler mevcut. {cta}",
                "Araştırmalar gösteriyor ki {topic} konusunda dikkat çekici sonuçlar var. {cta}",
                "{topic} ile ilgili bilmeniz gereken gerçekler bunlar. {cta}",
                "Veriler açık: {topic} konusu giderek önem kazanıyor. {cta}",
                "İstatistikler {topic} hakkında önemli bilgiler ortaya koyuyor. {cta}",
                "Uzmanlar {topic} konusunda şunları söylüyor. {cta}",
            ],
            "emotional": [
                "{topic} hakkında düşündükçe, insan hikayelerinin gücünü görüyoruz. {cta}",
                "Gerçek insanların {topic} ile yaşadığı deneyimler yürek burkuyor. {cta}",
                "Her birimizin {topic} konusunda bir hikayesi var. {cta}",
                "{topic} konusu hepimizi derinden etkiliyor. {cta}",
                "Kalbimiz {topic} için atıyor. {cta}",
                "{topic} hakkında hissettiklerimizi paylaşmak istiyoruz. {cta}",
            ],
            "formal": [
                "{topic} konusunda resmi açıklama yapılması gerekmektedir. {cta}",
                "Bu bağlamda {topic} değerlendirilmelidir. {cta}",
                "{topic} hakkında profesyonel bir yaklaşım benimsenmektedir. {cta}",
                "Kurumsal perspektiften {topic} ele alınmalıdır. {cta}",
                "{topic} konusunda stratejik adımlar atılmaktadır. {cta}",
                "Resmi kaynaklara göre {topic} öncelikli konular arasındadır. {cta}",
            ],
            "hopeful": [
                "{topic} için umut dolu bir gelecek mümkün. {cta}",
                "Birlikte {topic} konusunda değişim yaratabiliriz. {cta}",
                "{topic} için olumlu adımlar atılıyor. {cta}",
                "Yarın {topic} için daha iyi olacak. {cta}",
                "{topic} konusunda iyimseriz çünkü birlikte güçlüyüz. {cta}",
                "Umut var: {topic} için çözümler üretiliyor. {cta}",
            ],
            "call_to_action": [
                "Hemen harekete geçin! {topic} için destek olun. {cta}",
                "{topic} konusunda sesinizi yükseltin! {cta}",
                "Şimdi {topic} için bir şeyler yapma zamanı! {cta}",
                "Bize katılın! {topic} için birlikte mücadele edelim. {cta}",
                "{topic} için harekete geçme zamanı geldi! {cta}",
                "Eyleme geç! {topic} senin de desteğine ihtiyaç duyuyor. {cta}",
            ],
        },
        "en": {
            "informative": [
                "Did you know? Important data about {topic} is available. {cta}",
                "Research shows significant findings about {topic}. {cta}",
                "Here are the facts you need to know about {topic}. {cta}",
                "The data is clear: {topic} is gaining importance. {cta}",
                "Statistics reveal important insights about {topic}. {cta}",
                "Experts say this about {topic}. {cta}",
            ],
            "emotional": [
                "Thinking about {topic}, we see the power of human stories. {cta}",
                "Real experiences with {topic} are heartbreaking. {cta}",
                "Each of us has a story about {topic}. {cta}",
                "{topic} deeply affects us all. {cta}",
                "Our hearts beat for {topic}. {cta}",
                "We want to share what we feel about {topic}. {cta}",
            ],
            "formal": [
                "An official statement regarding {topic} is warranted. {cta}",
                "In this context, {topic} must be evaluated. {cta}",
                "A professional approach to {topic} is being adopted. {cta}",
                "From a corporate perspective, {topic} should be addressed. {cta}",
                "Strategic steps are being taken regarding {topic}. {cta}",
                "According to official sources, {topic} is among priority issues. {cta}",
            ],
            "hopeful": [
                "A hopeful future for {topic} is possible. {cta}",
                "Together, we can create change for {topic}. {cta}",
                "Positive steps are being taken for {topic}. {cta}",
                "Tomorrow will be better for {topic}. {cta}",
                "We are optimistic about {topic} because together we are strong. {cta}",
                "There is hope: solutions for {topic} are being developed. {cta}",
            ],
            "call_to_action": [
                "Take action now! Support {topic}. {cta}",
                "Raise your voice for {topic}! {cta}",
                "Now is the time to do something for {topic}! {cta}",
                "Join us! Let's fight together for {topic}. {cta}",
                "It's time to take action for {topic}! {cta}",
                "Act now! {topic} needs your support. {cta}",
            ],
        },
        "de": {
            "informative": [
                "Wussten Sie? Wichtige Daten über {topic} sind verfügbar. {cta}",
                "Forschungen zeigen bedeutende Erkenntnisse über {topic}. {cta}",
                "Hier sind die Fakten, die Sie über {topic} wissen müssen. {cta}",
                "Die Daten sind klar: {topic} gewinnt an Bedeutung. {cta}",
                "Statistiken zeigen wichtige Einblicke über {topic}. {cta}",
                "Experten sagen dies über {topic}. {cta}",
            ],
            "emotional": [
                "Wenn wir über {topic} nachdenken, sehen wir die Kraft menschlicher Geschichten. {cta}",
                "Echte Erfahrungen mit {topic} sind herzzerreißend. {cta}",
                "Jeder von uns hat eine Geschichte über {topic}. {cta}",
                "{topic} betrifft uns alle tief. {cta}",
                "Unsere Herzen schlagen für {topic}. {cta}",
                "Wir möchten teilen, was wir über {topic} fühlen. {cta}",
            ],
            "formal": [
                "Eine offizielle Erklärung zu {topic} ist erforderlich. {cta}",
                "In diesem Zusammenhang muss {topic} bewertet werden. {cta}",
                "Ein professioneller Ansatz zu {topic} wird verfolgt. {cta}",
                "Aus unternehmerischer Sicht sollte {topic} angegangen werden. {cta}",
                "Strategische Schritte werden bezüglich {topic} unternommen. {cta}",
                "Laut offiziellen Quellen gehört {topic} zu den Prioritäten. {cta}",
            ],
            "hopeful": [
                "Eine hoffnungsvolle Zukunft für {topic} ist möglich. {cta}",
                "Gemeinsam können wir Veränderungen für {topic} schaffen. {cta}",
                "Positive Schritte werden für {topic} unternommen. {cta}",
                "Morgen wird besser für {topic} sein. {cta}",
                "Wir sind optimistisch bezüglich {topic}, denn gemeinsam sind wir stark. {cta}",
                "Es gibt Hoffnung: Lösungen für {topic} werden entwickelt. {cta}",
            ],
            "call_to_action": [
                "Handeln Sie jetzt! Unterstützen Sie {topic}. {cta}",
                "Erheben Sie Ihre Stimme für {topic}! {cta}",
                "Jetzt ist die Zeit, etwas für {topic} zu tun! {cta}",
                "Schließen Sie sich uns an! Kämpfen wir gemeinsam für {topic}. {cta}",
                "Es ist Zeit, für {topic} zu handeln! {cta}",
                "Werden Sie aktiv! {topic} braucht Ihre Unterstützung. {cta}",
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

        # Use the tone from the request to select templates
        tone = request.tone or "informative"

        # Generate requested number of variants
        for i in range(request.output.variants):
            # Get templates for this tone
            templates = self.TEMPLATES.get(language, self.TEMPLATES["en"]).get(
                tone, self.TEMPLATES["en"]["informative"]
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
        """Insert hashtags at the end of the text.

        User-provided hashtags are ALWAYS appended to the tweet as-is.
        User may or may not include # character - we preserve exactly what they entered.
        """
        if not hashtags:
            return text, []

        # ALWAYS add all hashtags at the end - they are user-provided and must appear
        hashtags_used = list(hashtags)  # Use all hashtags

        # Add hashtags at the end with proper spacing
        hashtag_str = " ".join(tag.strip() for tag in hashtags_used)
        text = f"{text.rstrip()} {hashtag_str}"

        return text, hashtags_used
    
    def _enforce_char_limit(self, text: str, max_chars: int, hashtags: List[str]) -> str:
        """Ensure text fits within character limit while preserving hashtags.

        Hashtags are always preserved - main text is truncated if needed.
        """
        if len(text) <= max_chars:
            return text

        # Calculate space needed for hashtags (they must be preserved)
        hashtag_str = " ".join(tag.strip() for tag in hashtags)
        hashtag_space = len(hashtag_str) + 1 if hashtags else 0  # +1 for space before

        # Truncate main text while preserving hashtags
        available = max_chars - hashtag_space - 4  # -4 for "... "

        # Find main text (before hashtags)
        main_text = text
        for tag in hashtags:
            main_text = main_text.replace(tag, "").strip()

        if len(main_text) > available and available > 20:
            # Truncate at word boundary
            truncated = main_text[:available]
            last_space = truncated.rfind(' ')
            if last_space > available // 2:
                truncated = truncated[:last_space]
            truncated = truncated.rstrip('.,!? ') + "..."

            # Reconstruct with hashtags
            if hashtags:
                text = f"{truncated} {hashtag_str}"
            else:
                text = truncated
        elif hashtags:
            # If text is too short to truncate, just append hashtags
            text = f"{main_text.rstrip()} {hashtag_str}"

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



