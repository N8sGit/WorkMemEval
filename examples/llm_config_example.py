"""
WorkMemEval: LLM Configuration Examples

This file shows how to configure different LLM providers for use with WorkMemEval agents.
"""

# Example 1: OpenAI GPT-4o-mini (cost-effective, fast)
openai_config_basic = {
    'llm_config': {
        'provider': 'openai',
        'model': 'gpt-4o-mini',
        'api_key': None,  # Will use OPENAI_API_KEY environment variable
        'temperature': 0.1,
        'max_tokens': 4000,
        'timeout_seconds': 60
    }
}

# Example 2: OpenAI GPT-4o (balanced performance)
openai_config_advanced = {
    'llm_config': {
        'provider': 'openai',
        'model': 'gpt-4o',
        'api_key': None,  # Will use OPENAI_API_KEY environment variable
        'temperature': 0.0,  # Deterministic for evaluation
        'max_tokens': 8000,
        'timeout_seconds': 120,
        'requests_per_minute': 60
    }
}

# Example 3: OpenRouter with Claude-3-Haiku (cost-effective alternative)
openrouter_config = {
    'llm_config': {
        'provider': 'openrouter',
        'model': 'anthropic/claude-3-haiku',
        'api_key': None,  # Will use OPENROUTER_API_KEY environment variable
        'temperature': 0.1,
        'max_tokens': 4000,
        'timeout_seconds': 90,
        'requests_per_minute': 30  # Lower rate limit for OpenRouter
    }
}

# Example 4: OpenRouter with Llama (open source model)
openrouter_llama_config = {
    'llm_config': {
        'provider': 'openrouter',
        'model': 'meta-llama/llama-3.1-70b-instruct',
        'api_key': None,  # Will use OPENROUTER_API_KEY environment variable
        'temperature': 0.2,
        'max_tokens': 6000,
        'timeout_seconds': 150
    }
}

# Example 5: Mock provider for testing (no API key required)
mock_config = {
    'llm_config': {
        'provider': 'mock',
        'model': 'mock-gpt',
        'response_delay': 0.1  # Simulate processing time
    }
}

# Example 6: High-performance configuration with detailed logging
high_performance_config = {
    'llm_config': {
        'provider': 'openai',
        'model': 'gpt-4',
        'api_key': None,
        'temperature': 0.0,
        'max_tokens': 8000,
        'timeout_seconds': 180,
        'requests_per_minute': 30,  # Conservative for high-cost model
    },
    'max_iterations': 20,
    'memory_context_limit': 10,
    'use_secure_file_ops': True
}

# Complete agent configuration example
def get_production_agent_config(llm_provider='openai', model='gpt-4o-mini'):
    """
    Get a production-ready agent configuration.
    
    Args:
        llm_provider: 'openai', 'openrouter', or 'mock'
        model: Model name appropriate for the provider
        
    Returns:
        Complete agent configuration dictionary
    """
    
    base_config = {
        'max_iterations': 15,
        'memory_context_limit': 8,
        'use_secure_file_ops': True,
        'working_directory': '.'
    }
    
    if llm_provider == 'openai':
        llm_config = {
            'provider': 'openai',
            'model': model,
            'temperature': 0.1,
            'max_tokens': 4000,
            'timeout_seconds': 60
        }
    elif llm_provider == 'openrouter':
        llm_config = {
            'provider': 'openrouter',
            'model': model,
            'temperature': 0.1,
            'max_tokens': 4000,
            'timeout_seconds': 90,
            'requests_per_minute': 30
        }
    else:  # mock
        llm_config = {
            'provider': 'mock',
            'model': model or 'mock-gpt',
            'response_delay': 0.0  # Fast for testing
        }
    
    return {
        **base_config,
        'llm_config': llm_config
    }


# Environment variable setup examples
"""
To use real LLM providers, set these environment variables:

# For OpenAI
export OPENAI_API_KEY="your-openai-api-key-here"

# For OpenRouter  
export OPENROUTER_API_KEY="your-openrouter-api-key-here"

# Optional: Enable debug logging
export WM_LLM_DEBUG=1
"""

# Usage in evaluation runner
"""
from src.agents.simple_agent import SimpleWorkMemAgent
from src.memory.simple_memory import SimpleContextMemory
from examples.llm_config_example import get_production_agent_config

# Create memory system
memory = SimpleContextMemory({'max_items': 200})

# Create agent with production LLM configuration
config = get_production_agent_config('openai', 'gpt-4o-mini')
agent = SimpleWorkMemAgent(memory, config)

# Use in evaluation
runner.run_evaluation(task_file, agent, memory, working_directory)
"""
