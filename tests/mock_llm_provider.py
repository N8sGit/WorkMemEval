"""
Mock LLM Provider for Testing

A simple mock implementation of LLMInterface for unit testing purposes.
This allows tests to run without requiring real LLM API keys.
"""

import asyncio
import time
from typing import Dict, Any, Optional

from src.core.llm_interfaces import LLMInterface, LLMConfig, LLMResponse


class MockLLMProvider(LLMInterface):
    """Mock LLM provider for testing"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.call_count = 0
        
    async def generate_response(self, prompt: str, 
                              context: Optional[Dict[str, Any]] = None) -> LLMResponse:
        """Generate mock response based on patterns"""
        self.call_count += 1
        
        # Simulate small delay
        await asyncio.sleep(0.01)
        
        prompt_lower = prompt.lower()
        
        # Pattern-based responses
        if 'implement' in prompt_lower and 'function' in prompt_lower:
            content = '''def example_function():
    """Example function implementation"""
    return "completed"'''
        elif 'implement' in prompt_lower and 'class' in prompt_lower:
            content = '''class ExampleClass:
    """Example class implementation"""
    def __init__(self):
        self.value = "initialized"'''
        elif 'plan' in prompt_lower or 'approach' in prompt_lower:
            content = '''Here's my approach:
1. Analyze the requirements
2. Design the solution
3. Implement the functionality
4. Test the implementation'''
        else:
            content = "I'll complete this task step by step."
        
        return LLMResponse(
            content=content,
            model=self.config.model,
            usage={'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30},
            latency_ms=10.0,
            cost_usd=0.0,
            metadata={'mock_call_count': self.call_count}
        )
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get mock provider info"""
        return {
            'provider': 'mock_test',
            'model': self.config.model,
            'total_calls': self.call_count
        }
