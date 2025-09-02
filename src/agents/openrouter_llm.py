"""
OpenRouter LLM Integration for WorkMemEval

Real LLM client for agentic coding tasks via OpenRouter API.
"""

import os
import requests
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path


class OpenRouterLLM:
    """
    Real LLM client using OpenRouter API for agentic coding tasks.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = os.getenv('LLM_API_KEY')
        if not self.api_key:
            raise ValueError("LLM_API_KEY environment variable not found. Please set it in your .env file.")
        
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = config.get('model', 'moonshotai/kimi-k2')
        self.max_tokens = config.get('max_tokens', 4000)
        self.temperature = config.get('temperature', 0.1)  # Low for coding tasks
        self.timeout = config.get('timeout', 60)
        self.call_count = 0
        
    def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """
        Generate response using OpenRouter API
        
        Args:
            prompt: The prompt to send to the LLM
            context: Additional context (files, requirements, etc.)
            
        Returns:
            The LLM's response as a string
        """
        self.call_count += 1
        
        # Build system prompt for coding tasks
        system_prompt = self._build_system_prompt(context)
        
        # Prepare messages
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user", 
                "content": prompt
            }
        ]
        
        # Add context if provided
        if context:
            context_str = self._format_context(context)
            messages[0]["content"] += f"\n\nCurrent Context:\n{context_str}"
        
        try:
            response = requests.post(
                url=f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://workmemeval.dev",
                    "X-Title": "WorkMemEval",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                },
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result['choices'][0]['message']['content'].strip()
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"OpenRouter API request failed: {str(e)}")
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Invalid response format from OpenRouter: {str(e)}")
    
    def _build_system_prompt(self, context: Optional[Dict[str, Any]]) -> str:
        """Build system prompt for coding tasks"""
        base_prompt = """You are an expert software engineer tasked with completing programming checkpoints.
You will be given specific requirements and must provide working code solutions.

Key behaviors:
- Write clean, tested, and documented code
- Follow the exact requirements provided
- Consider edge cases and error handling
- Write appropriate tests when needed
- Provide clear explanations of your approach

Always structure your response with:
1. Analysis of requirements
2. Implementation approach
3. Code solution (with file paths if creating new files)
4. Testing strategy"""
        return base_prompt
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context information for the LLM"""
        context_parts = []
        
        if 'files' in context:
            context_parts.append("Current Files:")
            for file_path, content in context['files'].items():
                context_parts.append(f"- {file_path}:\n```\n{content[:500]}...\n```")
        
        if 'requirements' in context:
            context_parts.append(f"Requirements: {context['requirements']}")
        
        if 'test_results' in context:
            context_parts.append(f"Test Results: {context['test_results']}")
        
        return "\n".join(context_parts)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            'api_calls': self.call_count,
            'model': self.model,
            'provider': 'openrouter'
        }
