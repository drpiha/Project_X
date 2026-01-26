from typing import Optional
from app.generators.base import BaseTweetGenerator
from app.generators.rule_based import RuleBasedGenerator
from app.generators.llm_generator import LLMGenerator
from app.core.config import get_settings

def get_generator(generator_type: str = "llm") -> BaseTweetGenerator:
    """
    Factory function to get the appropriate generator.

    Args:
        generator_type: Type of generator ("llm" only - rule_based is deprecated)

    Returns:
        LLMGenerator instance

    Raises:
        ValueError: If OpenRouter API key is not configured
    """
    settings = get_settings()

    if generator_type == "llm":
        if not settings.openrouter_api_key:
            raise ValueError("OpenRouter API key is required for AI tweet generation. Set OPENROUTER_API_KEY in environment.")
        return LLMGenerator()

    # Rule-based generator is deprecated - always use LLM
    raise ValueError(f"Invalid generator type: {generator_type}. Only 'llm' is supported.")

__all__ = [
    "BaseTweetGenerator",
    "RuleBasedGenerator",
    "LLMGenerator",
    "get_generator",
]
