from typing import Optional
from app.generators.base import BaseTweetGenerator
from app.generators.rule_based import RuleBasedGenerator
from app.generators.llm_generator import LLMGenerator
from app.core.config import get_settings

def get_generator(generator_type: str = "rule_based") -> BaseTweetGenerator:
    """
    Factory function to get the appropriate generator.
    
    Args:
        generator_type: Type of generator ("rule_based" or "llm")
        
    Returns:
        BaseTweetGenerator instance
    """
    settings = get_settings()
    
    if generator_type == "llm":
        if settings.openrouter_api_key:
            return LLMGenerator()
        else:
            # Fallback if key missing
            return RuleBasedGenerator()
            
    return RuleBasedGenerator()

__all__ = [
    "BaseTweetGenerator",
    "RuleBasedGenerator",
    "LLMGenerator",
    "get_generator",
]
