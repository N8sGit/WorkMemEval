"""
WorkMemEval: LLM Module

Production LLM integration for WorkMemEval with support for multiple providers.
Currently supports OpenRouter (200+ models) with extensible architecture.
"""

from ..core.llm_interfaces import LLMConfig, LLMInterface, LLMProvider, LLMResponse
from .openrouter_provider import OpenRouterProvider, resolve_model_name


class UnsupportedProviderError(Exception):
    """Raised when an unsupported LLM provider is requested"""

    pass


class LLMFactory:
    """Factory for creating LLM providers"""

    @staticmethod
    def create_provider(config: LLMConfig) -> LLMInterface:
        """Create LLM provider based on configuration

        Args:
            config: LLM configuration specifying provider and parameters

        Returns:
            Configured LLM provider instance

        Raises:
            UnsupportedProviderError: If the requested provider is not supported
        """
        if config.provider == LLMProvider.OPENROUTER:
            # Resolve model shortcuts to full OpenRouter model names
            resolved_config = LLMConfig(
                provider=config.provider,
                model=resolve_model_name(config.model),
                api_key=config.api_key,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                timeout_seconds=config.timeout_seconds,
                provider_config=config.provider_config,
            )
            return OpenRouterProvider(resolved_config)
        else:
            # No fallback - raise error for unsupported providers
            supported_providers = [provider.value for provider in LLMProvider]
            raise UnsupportedProviderError(
                f"Unsupported LLM provider: {config.provider.value if hasattr(config.provider, 'value') else config.provider}. "
                f"Supported providers: {', '.join(supported_providers)}"
            )


# Export main classes
__all__ = [
    "LLMInterface",
    "LLMConfig",
    "LLMResponse",
    "LLMProvider",
    "OpenRouterProvider",
    "LLMFactory",
    "resolve_model_name",
    "UnsupportedProviderError",
]
