"""
OpenRouter LLM Provider for WorkMemEval

Provides access to multiple LLM models through OpenRouter's unified API.
Supports async requests, proper error handling, and comprehensive logging.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, Any, Optional

import httpx

from ..core.llm_interfaces import LLMInterface, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class OpenRouterError(Exception):
    """Raised when OpenRouter API returns an error"""
    pass


class OpenRouterProvider(LLMInterface):
    """OpenRouter LLM provider supporting multiple models"""
    
    BASE_URL = "https://openrouter.ai/api/v1"
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_key = config.api_key or os.getenv("OPENROUTER_API_KEY")
        self.call_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable "
                "or provide api_key in config."
            )
        
        # Default headers for OpenRouter
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-org/WorkMemEval",  # Optional: for OpenRouter analytics
            "X-Title": "WorkMemEval",  # Optional: for OpenRouter analytics
        }
        
        # HTTP client with timeout configuration
        timeout = httpx.Timeout(
            connect=10.0,
            read=config.timeout_seconds,
            write=10.0,
            pool=10.0
        )
        
        self.client = httpx.AsyncClient(
            headers=self.headers,
            timeout=timeout,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        
        logger.info(f"OpenRouterProvider initialized for model: {config.model}")
    
    async def generate_response(self, prompt: str, 
                              context: Optional[Dict[str, Any]] = None) -> LLMResponse:
        """Generate a response using OpenRouter API"""
        start_time = time.time()
        
        try:
            # Prepare the request payload
            payload = {
                "model": self.config.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }
            
            # Add any additional parameters from provider config
            if self.config.provider_config:
                # Add supported OpenRouter parameters
                supported_params = {
                    'top_p', 'top_k', 'frequency_penalty', 'presence_penalty',
                    'repetition_penalty', 'min_p', 'top_a', 'seed', 'logit_bias',
                    'logprobs', 'top_logprobs', 'response_format', 'stop'
                }
                
                for key, value in self.config.provider_config.items():
                    if key in supported_params:
                        payload[key] = value
            
            logger.debug(f"Sending request to OpenRouter: {self.config.model}")
            
            # Make the API request
            response = await self.client.post(
                f"{self.BASE_URL}/chat/completions",
                json=payload
            )
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Handle HTTP errors
            if response.status_code != 200:
                error_text = response.text
                try:
                    error_data = response.json()
                    error_message = error_data.get("error", {}).get("message", error_text)
                except:
                    error_message = error_text
                
                raise OpenRouterError(
                    f"OpenRouter API error (status {response.status_code}): {error_message}"
                )
            
            # Parse the response
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise OpenRouterError(f"Failed to parse OpenRouter response: {e}")
            
            # Extract response content
            if not data.get("choices"):
                raise OpenRouterError("No choices returned from OpenRouter")
            
            content = data["choices"][0]["message"]["content"]
            
            # Extract usage information
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
            
            # Update counters
            self.call_count += 1
            self.total_tokens += total_tokens
            
            # Calculate cost (OpenRouter provides this in the response)
            cost = 0.0
            if "cost" in data:
                cost = float(data["cost"])
                self.total_cost += cost
            
            # Prepare metadata
            metadata = {
                "openrouter_id": data.get("id", ""),
                "model": data.get("model", self.config.model),
                "finish_reason": data["choices"][0].get("finish_reason", ""),
                "call_count": self.call_count,
            }
            
            # Add any provider-specific metadata
            if "provider" in data:
                metadata["provider_used"] = data["provider"]
            
            logger.info(
                f"OpenRouter response: {total_tokens} tokens, "
                f"{latency_ms:.1f}ms, ${cost:.6f}"
            )
            
            return LLMResponse(
                content=content,
                model=data.get("model", self.config.model),
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                },
                latency_ms=latency_ms,
                cost_usd=cost,
                metadata=metadata
            )
            
        except httpx.TimeoutException:
            latency_ms = (time.time() - start_time) * 1000
            raise OpenRouterError(f"Request timed out after {latency_ms:.1f}ms")
            
        except httpx.RequestError as e:
            raise OpenRouterError(f"Request failed: {e}")
            
        except Exception as e:
            if isinstance(e, OpenRouterError):
                raise
            raise OpenRouterError(f"Unexpected error: {e}")
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the OpenRouter provider"""
        return {
            "provider": "openrouter",
            "model": self.config.model,
            "total_calls": self.call_count,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost,
            "api_base": self.BASE_URL,
        }
    
    async def get_available_models(self) -> Dict[str, Any]:
        """Get list of available models from OpenRouter"""
        try:
            response = await self.client.get(f"{self.BASE_URL}/models")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get models list: {response.status_code}")
                return {"data": []}
                
        except Exception as e:
            logger.warning(f"Error getting models list: {e}")
            return {"data": []}
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Popular OpenRouter model shortcuts
POPULAR_MODELS = {
    # GPT Models
    "gpt-4": "openai/gpt-4",
    "gpt-4-turbo": "openai/gpt-4-turbo",
    "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
    
    # Claude Models
    "claude-3.5-sonnet": "anthropic/claude-3.5-sonnet",
    "claude-3-haiku": "anthropic/claude-3-haiku",
    "claude-3-opus": "anthropic/claude-3-opus",
    
    # Other Popular Models
    "llama-3.1-405b": "meta-llama/llama-3.1-405b-instruct",
    "llama-3.1-70b": "meta-llama/llama-3.1-70b-instruct",
    "llama-3.1-8b": "meta-llama/llama-3.1-8b-instruct",
    "gemini-pro": "google/gemini-pro",
    "mixtral-8x7b": "mistralai/mixtral-8x7b-instruct",
}


def resolve_model_name(model: str) -> str:
    """Resolve a model shortcut to its full OpenRouter model name"""
    return POPULAR_MODELS.get(model, model)
