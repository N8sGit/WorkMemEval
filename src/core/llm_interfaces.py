"""
WorkMemEval: LLM Interfaces

Core interfaces and data structures for LLM integration.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class LLMProvider(Enum):
    """Supported LLM providers"""

    OPENAI = "openai"
    OPENROUTER = "openrouter"


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
    temperature: float = 0.1
    max_tokens: int = 4000
    timeout_seconds: int = 60
    provider_config: Dict[str, Any] = field(default_factory=dict)


class LLMInterface(ABC):
    """Abstract interface for Language Model providers"""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    async def generate_response(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """Generate a response from the LLM"""
        pass

    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the LLM provider"""
        pass
