"""
WorkMemEval: LLM Interfaces and Provider Architecture

This module defines the core LLM interfaces and base classes for integrating
real language models as first-class components in the evaluation framework.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import time
import logging


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    AZURE_OPENAI = "azure_openai"
    LOCAL = "local"
    MOCK = "mock"  # For testing only


@dataclass
class LLMUsageMetrics:
    """Metrics for tracking LLM usage and performance"""
    total_requests: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_cost_usd: float = 0.0
    average_latency_ms: float = 0.0
    error_count: int = 0
    
    def add_request(self, input_tokens: int, output_tokens: int, 
                   latency_ms: float, cost_usd: float = 0.0):
        """Add metrics for a single request"""
        self.total_requests += 1
        self.total_tokens_input += input_tokens
        self.total_tokens_output += output_tokens
        self.total_cost_usd += cost_usd
        
        # Update rolling average latency
        if self.total_requests == 1:
            self.average_latency_ms = latency_ms
        else:
            self.average_latency_ms = (
                (self.average_latency_ms * (self.total_requests - 1) + latency_ms) 
                / self.total_requests
            )
    
    def add_error(self):
        """Record an error"""
        self.error_count += 1


@dataclass
class LLMResponse:
    """Response from LLM provider"""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMConfig:
    """Configuration for LLM providers"""
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4000
    timeout_seconds: int = 60
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    
    # Rate limiting
    requests_per_minute: int = 60
    tokens_per_minute: int = 150000
    
    # Cost tracking
    input_token_cost_per_1k: float = 0.0
    output_token_cost_per_1k: float = 0.0
    
    # Provider-specific settings
    provider_config: Dict[str, Any] = field(default_factory=dict)


class LLMInterface(ABC):
    """
    Abstract interface for Language Model providers.
    
    This interface provides a consistent API for different LLM providers
    while supporting provider-specific features and optimizations.
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.usage_metrics = LLMUsageMetrics()
        self._last_request_time = 0.0
        
    @abstractmethod
    async def generate_response(self, prompt: str, 
                              context: Optional[Dict[str, Any]] = None) -> LLMResponse:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The input prompt for the LLM
            context: Optional context information for the request
            
        Returns:
            LLMResponse containing the generated content and metadata
            
        Raises:
            LLMError: If the request fails
        """
        pass
    
    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the LLM provider"""
        pass
    
    def get_usage_metrics(self) -> LLMUsageMetrics:
        """Get current usage metrics"""
        return self.usage_metrics
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)"""
        # Simple approximation: ~4 characters per token
        return max(1, len(text) // 4)
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for token usage"""
        input_cost = (input_tokens / 1000) * self.config.input_token_cost_per_1k
        output_cost = (output_tokens / 1000) * self.config.output_token_cost_per_1k
        return input_cost + output_cost
    
    async def _enforce_rate_limits(self):
        """Enforce rate limiting between requests"""
        now = time.time()
        min_interval = 60.0 / self.config.requests_per_minute
        
        time_since_last = now - self._last_request_time
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            self.logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        self._last_request_time = time.time()
    
    def _log_request(self, prompt: str, response: LLMResponse):
        """Log request details for debugging"""
        self.logger.debug(
            f"LLM request completed: model={response.model}, "
            f"input_tokens={response.usage.get('prompt_tokens', 0)}, "
            f"output_tokens={response.usage.get('completion_tokens', 0)}, "
            f"latency={response.latency_ms:.0f}ms, "
            f"cost=${response.cost_usd:.4f}"
        )


class LLMError(Exception):
    """Base exception for LLM-related errors"""
    pass


class LLMRateLimitError(LLMError):
    """Raised when rate limits are exceeded"""
    pass


class LLMAuthenticationError(LLMError):
    """Raised when authentication fails"""
    pass


class LLMTimeoutError(LLMError):
    """Raised when requests timeout"""
    pass


class LLMInvalidResponseError(LLMError):
    """Raised when LLM returns invalid response"""
    pass


# Import asyncio at the end to avoid circular imports
import asyncio
