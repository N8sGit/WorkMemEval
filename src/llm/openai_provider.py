"""
WorkMemEval: OpenAI/OpenRouter LLM Provider

Production-ready implementation of LLM interface for OpenAI and OpenRouter APIs.
Includes error handling, rate limiting, token management, and cost tracking.
"""

import asyncio
import json
import time
import os
from typing import Dict, Any, Optional
import aiohttp
import backoff

from ..core.llm_interfaces import (
    LLMInterface, LLMConfig, LLMResponse, LLMProvider,
    LLMError, LLMRateLimitError, LLMAuthenticationError, 
    LLMTimeoutError, LLMInvalidResponseError
)


class OpenAIProvider(LLMInterface):
    """
    OpenAI/OpenRouter LLM provider implementation.
    
    Supports both OpenAI API and OpenRouter for model diversity.
    Features comprehensive error handling, rate limiting, and usage tracking.
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        
        # Set up API endpoints and headers
        self._setup_api_config()
        
        # Initialize session
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Model pricing (per 1K tokens)
        self._model_pricing = self._get_model_pricing()
        
        # Update config with pricing if available
        if config.model in self._model_pricing:
            pricing = self._model_pricing[config.model]
            config.input_token_cost_per_1k = pricing.get('input', 0.0)
            config.output_token_cost_per_1k = pricing.get('output', 0.0)
    
    def _setup_api_config(self):
        """Set up API configuration based on provider"""
        if self.config.provider == LLMProvider.OPENAI:
            self.api_base = self.config.api_base or "https://api.openai.com/v1"
            self.headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}"
            }
        elif self.config.provider == LLMProvider.OPENROUTER:
            self.api_base = self.config.api_base or "https://openrouter.ai/api/v1"
            self.headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
                "HTTP-Referer": "https://github.com/WorkMemEval/WorkMemEval",
                "X-Title": "WorkMemEval"
            }
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")
    
    def _get_model_pricing(self) -> Dict[str, Dict[str, float]]:
        """Get pricing information for different models"""
        return {
            # OpenAI models (per 1K tokens)
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            
            # Common OpenRouter models (approximate)
            "anthropic/claude-3-opus": {"input": 0.015, "output": 0.075},
            "anthropic/claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "anthropic/claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            "meta-llama/llama-3.1-70b-instruct": {"input": 0.00088, "output": 0.00088},
            "meta-llama/llama-3.1-8b-instruct": {"input": 0.00018, "output": 0.00018},
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self.headers
            )
        return self._session
    
    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=60
    )
    async def generate_response(self, prompt: str, 
                              context: Optional[Dict[str, Any]] = None) -> LLMResponse:
        """Generate response from OpenAI/OpenRouter API"""
        start_time = time.time()
        
        try:
            # Enforce rate limits
            await self._enforce_rate_limits()
            
            # Prepare request payload
            payload = self._build_request_payload(prompt, context)
            
            # Make API request
            session = await self._get_session()
            async with session.post(f"{self.api_base}/chat/completions", json=payload) as response:
                
                # Handle different HTTP status codes
                if response.status == 401:
                    raise LLMAuthenticationError("Invalid API key")
                elif response.status == 429:
                    raise LLMRateLimitError("Rate limit exceeded")
                elif response.status >= 400:
                    error_text = await response.text()
                    raise LLMError(f"API error {response.status}: {error_text}")
                
                # Parse response
                response_data = await response.json()
                
        except asyncio.TimeoutError:
            self.usage_metrics.add_error()
            raise LLMTimeoutError("Request timed out")
        except aiohttp.ClientError as e:
            self.usage_metrics.add_error()
            raise LLMError(f"HTTP client error: {e}")
        except json.JSONDecodeError:
            self.usage_metrics.add_error()
            raise LLMInvalidResponseError("Invalid JSON response")
        
        # Process response
        try:
            llm_response = self._process_response(response_data, start_time)
            
            # Update metrics
            usage = llm_response.usage
            self.usage_metrics.add_request(
                input_tokens=usage.get('prompt_tokens', 0),
                output_tokens=usage.get('completion_tokens', 0),
                latency_ms=llm_response.latency_ms,
                cost_usd=llm_response.cost_usd
            )
            
            # Log request
            self._log_request(prompt, llm_response)
            
            return llm_response
            
        except KeyError as e:
            self.usage_metrics.add_error()
            raise LLMInvalidResponseError(f"Missing expected field in response: {e}")
    
    def _build_request_payload(self, prompt: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build the API request payload"""
        messages = [{"role": "user", "content": prompt}]
        
        # Add system message if provided in context
        if context and "system_message" in context:
            messages.insert(0, {"role": "system", "content": context["system_message"]})
        
        # Add conversation history if provided
        if context and "conversation_history" in context:
            for msg in context["conversation_history"]:
                messages.append(msg)
            messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        
        # Add provider-specific parameters
        payload.update(self.config.provider_config)
        
        return payload
    
    def _process_response(self, response_data: Dict[str, Any], start_time: float) -> LLMResponse:
        """Process API response into LLMResponse object"""
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        # Extract content
        try:
            content = response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise LLMInvalidResponseError("No content in response")
        
        # Extract usage information
        usage = response_data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        # Calculate cost
        cost_usd = self.calculate_cost(input_tokens, output_tokens)
        
        # Extract model info
        model = response_data.get("model", self.config.model)
        
        # Build metadata
        metadata = {
            "finish_reason": response_data.get("choices", [{}])[0].get("finish_reason"),
            "response_id": response_data.get("id"),
            "created": response_data.get("created"),
        }
        
        return LLMResponse(
            content=content,
            model=model,
            usage=usage,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            metadata=metadata
        )
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "provider": self.config.provider.value,
            "model": self.config.model,
            "api_base": self.api_base,
            "supports_streaming": False,
            "supports_function_calling": True,
            "max_context_length": self._get_max_context_length(),
            "pricing": {
                "input_per_1k": self.config.input_token_cost_per_1k,
                "output_per_1k": self.config.output_token_cost_per_1k
            }
        }
    
    def _get_max_context_length(self) -> int:
        """Get maximum context length for the model"""
        context_lengths = {
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "gpt-3.5-turbo": 16384,
            "anthropic/claude-3-opus": 200000,
            "anthropic/claude-3-sonnet": 200000,
            "anthropic/claude-3-haiku": 200000,
        }
        return context_lengths.get(self.config.model, 4096)
    
    def estimate_tokens(self, text: str) -> int:
        """Improved token estimation using tiktoken if available"""
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(self.config.model)
            return len(encoding.encode(text))
        except ImportError:
            # Fallback to simple estimation
            return super().estimate_tokens(text)
        except Exception:
            # If tiktoken fails for any reason, use fallback
            return super().estimate_tokens(text)


def create_openai_config(
    model: str = "gpt-4o-mini",
    api_key: Optional[str] = None,
    provider: LLMProvider = LLMProvider.OPENAI,
    **kwargs
) -> LLMConfig:
    """
    Convenience function to create OpenAI configuration.
    
    Args:
        model: Model name (e.g., 'gpt-4o-mini', 'gpt-4')
        api_key: API key (defaults to OPENAI_API_KEY env var)
        provider: Provider type (OPENAI or OPENROUTER)
        **kwargs: Additional configuration parameters
        
    Returns:
        LLMConfig configured for OpenAI/OpenRouter
    """
    if api_key is None:
        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        raise ValueError("API key must be provided or set in environment variables")
    
    config_defaults = {
        'temperature': 0.1,
        'max_tokens': 4000,
        'timeout_seconds': 60,
        'requests_per_minute': 60 if provider == LLMProvider.OPENAI else 30,
    }
    
    # Merge defaults with provided kwargs
    config_params = {**config_defaults, **kwargs}
    
    return LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        **config_params
    )
