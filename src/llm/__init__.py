"""
WorkMemEval: LLM Module

This module provides language model integrations for the WorkMemEval framework.
Includes factory functions and convenience methods for creating LLM providers.
"""

from ..core.llm_interfaces import (
    LLMInterface, LLMConfig, LLMResponse, LLMProvider, LLMUsageMetrics,
    LLMError, LLMRateLimitError, LLMAuthenticationError, 
    LLMTimeoutError, LLMInvalidResponseError
)

from .openai_provider import OpenAIProvider, create_openai_config
from .mock_provider import MockProvider


class LLMFactory:
    """Factory for creating LLM providers"""
    
    @staticmethod
    def create_provider(config: LLMConfig) -> LLMInterface:
        """Create LLM provider based on configuration"""
        if config.provider in [LLMProvider.OPENAI, LLMProvider.OPENROUTER]:
            return OpenAIProvider(config)
        elif config.provider == LLMProvider.MOCK:
            from .mock_provider import MockProvider
            return MockProvider(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")
    
    @staticmethod
    def create_openai(
        model: str = "gpt-4o-mini",
        api_key: str = None,
        **kwargs
    ) -> OpenAIProvider:
        """Convenience method to create OpenAI provider"""
        config = create_openai_config(
            model=model,
            api_key=api_key,
            provider=LLMProvider.OPENAI,
            **kwargs
        )
        return OpenAIProvider(config)
    
    @staticmethod
    def create_openrouter(
        model: str = "anthropic/claude-3-haiku",
        api_key: str = None,
        **kwargs
    ) -> OpenAIProvider:
        """Convenience method to create OpenRouter provider"""
        config = create_openai_config(
            model=model,
            api_key=api_key,
            provider=LLMProvider.OPENROUTER,
            **kwargs
        )
        return OpenAIProvider(config)


def get_recommended_models():
    """Get list of recommended models for different use cases"""
    return {
        "cost_effective": [
            "gpt-4o-mini",
            "anthropic/claude-3-haiku",
            "meta-llama/llama-3.1-8b-instruct"
        ],
        "balanced": [
            "gpt-4o",
            "anthropic/claude-3-sonnet",
            "meta-llama/llama-3.1-70b-instruct"
        ],
        "high_performance": [
            "gpt-4",
            "anthropic/claude-3-opus",
            "gpt-4-turbo"
        ]
    }


# Export main classes and functions
__all__ = [
    # Core interfaces
    'LLMInterface', 'LLMConfig', 'LLMResponse', 'LLMProvider', 'LLMUsageMetrics',
    
    # Exceptions
    'LLMError', 'LLMRateLimitError', 'LLMAuthenticationError', 
    'LLMTimeoutError', 'LLMInvalidResponseError',
    
    # Providers
    'OpenAIProvider', 'MockProvider',
    
    # Factory and utilities
    'LLMFactory', 'create_openai_config', 'get_recommended_models'
]
