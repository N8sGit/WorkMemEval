"""
Unit tests for OpenRouterProvider integration.

Tests both mock scenarios and real API integration when credentials are available.
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm import (
    LLMConfig,
    LLMFactory,
    LLMProvider,
    OpenRouterProvider,
    resolve_model_name,
)
from src.llm.openrouter_provider import OpenRouterError


class TestOpenRouterProvider:
    """Test OpenRouterProvider functionality"""

    def test_resolve_model_name(self):
        """Test model name resolution shortcuts"""
        assert resolve_model_name("gpt-4") == "openai/gpt-4"
        assert resolve_model_name("claude-3.5-sonnet") == "anthropic/claude-3.5-sonnet"
        assert (
            resolve_model_name("llama-3.1-70b") == "meta-llama/llama-3.1-70b-instruct"
        )

        # Unknown models should pass through unchanged
        assert resolve_model_name("custom/model") == "custom/model"
        assert resolve_model_name("unknown-model") == "unknown-model"

    def test_openrouter_provider_creation_without_api_key(self):
        """Test that OpenRouterProvider requires API key"""
        config = LLMConfig(provider=LLMProvider.OPENROUTER, model="gpt-3.5-turbo")

        # Should raise error when no API key is provided
        with pytest.raises(ValueError, match="OpenRouter API key is required"):
            OpenRouterProvider(config)


if __name__ == "__main__":
    # Run simple tests manually
    test = TestOpenRouterProvider()
    test.test_resolve_model_name()
    print("✅ Model name resolution works")
