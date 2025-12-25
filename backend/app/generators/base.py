from abc import ABC, abstractmethod
from typing import List, Optional
from app.schemas.generate import GenerateRequest, GenerateResponse, VariantResponse


class BaseTweetGenerator(ABC):
    """
    Abstract base class for tweet generators.
    
    This interface allows swapping between different generator implementations:
    - RuleBasedGenerator: Deterministic, template-based (free, default)
    - LLMGenerator: AI-powered (paid, future implementation)
    """
    
    @property
    @abstractmethod
    def generator_name(self) -> str:
        """Return the name/version of this generator."""
        pass
    
    @abstractmethod
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """
        Generate tweet variants based on the request.
        
        Args:
            request: GenerateRequest with topic, constraints, etc.
            
        Returns:
            GenerateResponse with variants, recommended alt text, etc.
        """
        pass
    
    @abstractmethod
    def generate_alt_text(self, language: str, image_context: Optional[str]) -> str:
        """
        Generate alt text for images in the specified language.
        
        Args:
            language: Target language (tr, en, de)
            image_context: Optional context about the image
            
        Returns:
            Recommended alt text string
        """
        pass
    
    def validate_tweet(self, text: str, max_chars: int = 280) -> tuple[bool, List[str]]:
        """
        Validate a tweet against safety and length rules.
        
        Args:
            text: The tweet text to validate
            max_chars: Maximum character limit
            
        Returns:
            Tuple of (is_valid, list_of_safety_notes)
        """
        safety_notes = []
        
        # Check length
        if len(text) > max_chars:
            safety_notes.append(f"Tweet exceeds {max_chars} character limit")
        
        # Check for potentially problematic content
        problematic_patterns = [
            ("personal data patterns", self._contains_personal_data(text)),
        ]
        
        for description, contains in problematic_patterns:
            if contains:
                safety_notes.append(f"May contain {description}")
        
        return len(safety_notes) == 0, safety_notes
    
    def _contains_personal_data(self, text: str) -> bool:
        """Check if text may contain personal data like emails or phone numbers."""
        import re
        
        # Email pattern
        if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text):
            return True
        
        # Phone pattern (various formats)
        if re.search(r'(\+?[\d\s\-\(\)]{10,})', text):
            # Additional check to avoid false positives
            digits = re.sub(r'\D', '', text)
            if len(digits) >= 10:
                return True
        
        return False
