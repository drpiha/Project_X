import pytest
import uuid
from app.generators.rule_based import RuleBasedGenerator
from app.schemas.generate import (
    GenerateRequest, GenerateConstraints, GenerateAssets, 
    GenerateAntiRepeat, GenerateOutput
)


class TestRuleBasedGenerator:
    """Tests for the rule-based tweet generator."""
    
    @pytest.fixture
    def generator(self):
        return RuleBasedGenerator()
    
    @pytest.fixture
    def campaign_id(self):
        return str(uuid.uuid4())
    
    @pytest.mark.asyncio
    async def test_generate_rule_based_tr(self, generator, campaign_id):
        """
        Test Turkish tweet generation.
        
        Ensures:
        - 6 variants are generated
        - Each variant has <= 280 characters
        - Hashtags are included
        - char_count matches actual length
        """
        request = GenerateRequest(
            campaign_id=campaign_id,
            language="tr",
            topic_summary="çevre koruma ve sürdürülebilirlik",
            hashtags=["#ÇevreBilinci", "#DoğayıKoru"],
            tone="hopeful",
            call_to_action="Bugün harekete geç!",
            constraints=GenerateConstraints(
                max_chars=280,
                target_chars=268,
                include_emojis=True,
                emoji_density="low",
            ),
            assets=GenerateAssets(image_count=2),
            anti_repeat=GenerateAntiRepeat(),
            output=GenerateOutput(variants=6),
        )
        
        response = await generator.generate(request)
        
        # Check we got 6 variants
        assert len(response.variants) == 6
        
        # Check each variant
        for variant in response.variants:
            # Character count must not exceed 280
            assert variant.char_count <= 280, f"Variant {variant.variant_index} exceeds 280 chars"
            
            # char_count must match actual length
            assert variant.char_count == len(variant.text), \
                f"Variant {variant.variant_index}: char_count mismatch"
            
            # Variant index should be correct
            assert 0 <= variant.variant_index <= 5
            
            # Text should not be empty
            assert len(variant.text) > 0
        
        # Check generator name
        assert response.generator == "rule_based_v1"
        
        # Check language
        assert response.language == "tr"
        
        # Check campaign_id
        assert response.campaign_id == campaign_id
        
        # Check alt text is generated
        assert len(response.recommended_alt_text) > 0
    
    @pytest.mark.asyncio
    async def test_generate_rule_based_en(self, generator, campaign_id):
        """Test English tweet generation."""
        request = GenerateRequest(
            campaign_id=campaign_id,
            language="en",
            topic_summary="environmental protection and sustainability",
            hashtags=["#Environment", "#Sustainability"],
            tone="informative",
            call_to_action="Take action today!",
            constraints=GenerateConstraints(max_chars=280, target_chars=268),
            output=GenerateOutput(variants=6),
        )
        
        response = await generator.generate(request)
        
        assert len(response.variants) == 6
        for variant in response.variants:
            assert variant.char_count <= 280
            assert variant.char_count == len(variant.text)
    
    @pytest.mark.asyncio
    async def test_generate_rule_based_de(self, generator, campaign_id):
        """Test German tweet generation."""
        request = GenerateRequest(
            campaign_id=campaign_id,
            language="de",
            topic_summary="Umweltschutz und Nachhaltigkeit",
            hashtags=["#Umweltschutz"],
            tone="formal",
            constraints=GenerateConstraints(max_chars=280, target_chars=268),
            output=GenerateOutput(variants=6),
        )
        
        response = await generator.generate(request)
        
        assert len(response.variants) == 6
        for variant in response.variants:
            assert variant.char_count <= 280
    
    @pytest.mark.asyncio
    async def test_generate_without_emojis(self, generator, campaign_id):
        """Test generation with emojis disabled."""
        request = GenerateRequest(
            campaign_id=campaign_id,
            language="tr",
            topic_summary="test topic",
            hashtags=["#Test"],
            tone="formal",
            constraints=GenerateConstraints(
                include_emojis=False,
                emoji_density="none",
            ),
            output=GenerateOutput(variants=3),
        )
        
        response = await generator.generate(request)
        
        assert len(response.variants) == 3
    
    @pytest.mark.asyncio
    async def test_generate_handles_long_topic(self, generator, campaign_id):
        """Test that long topics are handled gracefully."""
        long_topic = "Bu çok uzun bir konu özeti " * 20  # Very long topic
        
        request = GenerateRequest(
            campaign_id=campaign_id,
            language="tr",
            topic_summary=long_topic[:500],  # Max 500 chars
            hashtags=["#Test", "#Long", "#Topic"],
            constraints=GenerateConstraints(max_chars=280),
            output=GenerateOutput(variants=6),
        )
        
        response = await generator.generate(request)
        
        # All variants should still be under 280 chars
        for variant in response.variants:
            assert variant.char_count <= 280
    
    def test_alt_text_generation_tr(self, generator):
        """Test Turkish alt text generation."""
        alt_text = generator.generate_alt_text("tr", "çevre koruma görseli")
        
        assert len(alt_text) > 0
        assert "Görsel" in alt_text or "görsel" in alt_text.lower()
    
    def test_alt_text_generation_en(self, generator):
        """Test English alt text generation."""
        alt_text = generator.generate_alt_text("en", "environmental image")
        
        assert len(alt_text) > 0
        assert "Image" in alt_text or "image" in alt_text.lower()
    
    def test_alt_text_generation_default(self, generator):
        """Test default alt text when no context provided."""
        alt_text = generator.generate_alt_text("tr", None)
        
        assert len(alt_text) > 0
    
    def test_validate_tweet_valid(self, generator):
        """Test tweet validation with valid content."""
        is_valid, notes = generator.validate_tweet("This is a valid tweet #test", 280)
        
        assert is_valid is True
        assert len(notes) == 0
    
    def test_validate_tweet_too_long(self, generator):
        """Test tweet validation with too-long content."""
        long_tweet = "x" * 300
        is_valid, notes = generator.validate_tweet(long_tweet, 280)
        
        assert is_valid is False
        assert len(notes) > 0
