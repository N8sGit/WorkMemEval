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

    def test_openrouter_provider_creation_with_api_key(self):
        """Test OpenRouterProvider creation with API key"""
        config = LLMConfig(
            provider=LLMProvider.OPENROUTER,
            model="gpt-3.5-turbo",
            api_key="neutral-mock-key-for-testing"  # pragma: allowlist secret
        )

        provider = OpenRouterProvider(config)
        assert provider.config.model == "gpt-3.5-turbo"
        assert provider.api_key == "neutral-mock-key-for-testing"
        assert provider.call_count == 0

    def test_llm_factory_creates_openrouter_provider(self):
        """Test that LLMFactory creates OpenRouterProvider correctly"""
        config = LLMConfig(
            provider=LLMProvider.OPENROUTER,
            model="gpt-4",  # Should resolve to openai/gpt-4
            api_key="neutral-mock-key-for-testing"  # pragma: allowlist secret
        )

        provider = LLMFactory.create_provider(config)
        assert isinstance(provider, OpenRouterProvider)
        assert provider.config.model == "openai/gpt-4"  # Should be resolved

    @patch("httpx.AsyncClient")
    async def test_successful_api_call(self, mock_client_class):
        """Test successful API call to OpenRouter"""
        # Mock the HTTP client and response
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {"content": "Test response from OpenRouter"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "openai/gpt-3.5-turbo",
            "id": "test-id-123",
            "cost": 0.000025,
        }

        mock_client.post.return_value = mock_response

        # Create provider and test
        config = LLMConfig(
            provider=LLMProvider.OPENROUTER,
            model="gpt-3.5-turbo",
            api_key="neutral-mock-key-for-testing"  # pragma: allowlist secret
        )

        provider = OpenRouterProvider(config)
        response = await provider.generate_response("Test prompt")

        # Verify response
        assert response.content == "Test response from OpenRouter"
        assert response.model == "openai/gpt-3.5-turbo"
        assert response.usage["total_tokens"] == 15
        assert response.cost_usd == 0.000025
        assert response.metadata["openrouter_id"] == "test-id-123"

        # Verify API call was made correctly
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/chat/completions" in call_args[0][0]
        assert call_args[1]["json"]["model"] == "gpt-3.5-turbo"
        assert call_args[1]["json"]["messages"][0]["content"] == "Test prompt"

        await provider.close()

    @patch("httpx.AsyncClient")
    async def test_api_error_handling(self, mock_client_class):
        """Test API error handling"""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}  # pragma: allowlist secret

        mock_client.post.return_value = mock_response

        config = LLMConfig(
            provider=LLMProvider.OPENROUTER,
            model="gpt-3.5-turbo",
            api_key="neutral-mock-key-for-testing",  # pragma: allowlist secret
        )

        provider = OpenRouterProvider(config)

        with pytest.raises(OpenRouterError, match="Invalid API key"):
            await provider.generate_response("Test prompt")

        await provider.close()

    @patch("httpx.AsyncClient")
    async def test_timeout_handling(self, mock_client_class):
        """Test timeout handling"""
        import httpx

        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.post.side_effect = httpx.TimeoutException("Request timed out")  # pragma: allowlist secret

        config = LLMConfig(
            provider=LLMProvider.OPENROUTER, model="gpt-3.5-turbo", api_key="neutral-mock-key-for-testing"  # pragma: allowlist secret
        )

        provider = OpenRouterProvider(config)

        with pytest.raises(OpenRouterError, match="timed out"):
            await provider.generate_response("Test prompt")

        await provider.close()

    def test_provider_info(self):
        """Test provider info retrieval"""
        config = LLMConfig(
            provider=LLMProvider.OPENROUTER, model="gpt-4", api_key="neutral-mock-key-for-testing"  # pragma: allowlist secret
        )

        provider = OpenRouterProvider(config)
        info = provider.get_provider_info()

        assert info["provider"] == "openrouter"
        assert info["model"] == "gpt-4"
        assert info["total_calls"] == 0
        assert info["total_tokens"] == 0
        assert info["total_cost_usd"] == 0.0
        assert "api_base" in info


class TestRealOpenRouterIntegration:
    """Test real OpenRouter API integration (requires API key)"""

    @pytest.mark.skipif(
        not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
    )
    async def test_real_api_call(self):
        """Test actual API call to OpenRouter (only runs if API key is set)"""
        config = LLMConfig(
            provider=LLMProvider.OPENROUTER,
            model="gpt-3.5-turbo",  # Use a cost-effective model for testing
            temperature=0.1,
            max_tokens=50,  # Keep it small for testing
        )

        provider = LLMFactory.create_provider(config)
        assert isinstance(provider, OpenRouterProvider)

        try:
            response = await provider.generate_response(
                "Say exactly: 'OpenRouter integration test successful'"
            )

            assert response.content is not None
            assert len(response.content) > 0
            assert response.usage["total_tokens"] > 0
            assert response.latency_ms > 0

            # Should have resolved model name
            assert response.model.startswith("openai/gpt")

            print("✅ Real OpenRouter test successful!")
            print(f"   Model: {response.model}")
            print(f"   Tokens: {response.usage['total_tokens']}")
            print(f"   Cost: ${response.cost_usd:.6f}")
            print(f"   Latency: {response.latency_ms:.1f}ms")
            print(f"   Response: {response.content[:100]}...")

        finally:
            await provider.close()

    @pytest.mark.skipif(
        not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
    )
    async def test_model_shortcuts(self):
        """Test that model shortcuts work with real API"""
        test_models = [
            "gpt-3.5-turbo",  # Should resolve to openai/gpt-3.5-turbo
            # Add more models as needed, but keep costs low for testing
        ]

        for model_shortcut in test_models:
            config = LLMConfig(
                provider=LLMProvider.OPENROUTER,
                model=model_shortcut,
                max_tokens=10,  # Very small to minimize cost
            )

            provider = LLMFactory.create_provider(config)

            try:
                response = await provider.generate_response("Hi")
                assert response.content is not None
                assert len(response.content) > 0

                print(
                    f"✅ Model shortcut '{model_shortcut}' -> '{response.model}' works"
                )

            finally:
                await provider.close()


if __name__ == "__main__":
    # Run a simple test manually
    async def manual_test():
        if os.getenv("OPENROUTER_API_KEY"):
            print("🧪 Running manual OpenRouter test...")
            test = TestRealOpenRouterIntegration()
            await test.test_real_api_call()
        else:
            print(
                "💡 Set OPENROUTER_API_KEY environment variable to test real API integration"
            )
            print("🧪 Running mock tests only...")

            # Test basic functionality
            test = TestOpenRouterProvider()
            test.test_resolve_model_name()
            print("✅ Model name resolution works")

            test.test_llm_factory_creates_openrouter_provider()
            print("✅ LLMFactory integration works")

    asyncio.run(manual_test())
