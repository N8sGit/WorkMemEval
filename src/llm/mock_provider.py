"""
WorkMemEval: Mock LLM Provider

Mock implementation of LLM interface for testing and development.
Provides deterministic responses without external API dependencies.
"""

import asyncio
import time
from typing import Dict, Any, Optional

from ..core.llm_interfaces import (
    LLMInterface, LLMConfig, LLMResponse, LLMProvider
)


class MockProvider(LLMInterface):
    """
    Mock LLM provider for testing and development.
    
    Provides deterministic pattern-based responses that simulate
    real LLM behavior without external API calls.
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.response_delay = config.provider_config.get('response_delay', 0.1)
        self.call_count = 0
        
        # Mock usage costs
        config.input_token_cost_per_1k = 0.0
        config.output_token_cost_per_1k = 0.0
    
    async def generate_response(self, prompt: str, 
                              context: Optional[Dict[str, Any]] = None) -> LLMResponse:
        """Generate a mock response based on prompt patterns"""
        start_time = time.time()
        self.call_count += 1
        
        # Simulate processing delay
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
        
        # Generate response based on patterns
        content = self._generate_pattern_response(prompt)
        
        # Calculate metrics
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        input_tokens = self.estimate_tokens(prompt)
        output_tokens = self.estimate_tokens(content)
        
        # Create response
        response = LLMResponse(
            content=content,
            model=self.config.model,
            usage={
                'prompt_tokens': input_tokens,
                'completion_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens
            },
            latency_ms=latency_ms,
            cost_usd=0.0,
            metadata={
                'mock_call_count': self.call_count,
                'pattern_matched': self._identify_pattern(prompt)
            }
        )
        
        # Update metrics
        self.usage_metrics.add_request(input_tokens, output_tokens, latency_ms, 0.0)
        self._log_request(prompt, response)
        
        return response
    
    def _generate_pattern_response(self, prompt: str) -> str:
        """Generate response based on prompt patterns"""
        prompt_lower = prompt.lower()
        
        # Code implementation patterns
        if any(keyword in prompt_lower for keyword in ['implement', 'create', 'write']):
            if 'function' in prompt_lower:
                return self._generate_function_implementation(prompt)
            elif 'class' in prompt_lower:
                return self._generate_class_implementation(prompt)
            elif 'api' in prompt_lower:
                return self._generate_api_implementation(prompt)
            elif 'test' in prompt_lower:
                return self._generate_test_implementation(prompt)
        
        # File operation patterns
        if any(keyword in prompt_lower for keyword in ['read', 'open', 'load']):
            return "I'll read the file to understand its current contents and structure."
        
        if any(keyword in prompt_lower for keyword in ['write', 'save', 'create file']):
            return "I'll create the file with the appropriate content and proper formatting."
        
        if any(keyword in prompt_lower for keyword in ['edit', 'modify', 'update']):
            return "I'll make the necessary changes to the file while preserving existing functionality."
        
        # Analysis and planning patterns
        if any(keyword in prompt_lower for keyword in ['analyze', 'understand', 'review']):
            return ("I'll analyze the codebase structure and requirements to understand "
                   "what needs to be implemented and how it fits into the overall system.")
        
        if any(keyword in prompt_lower for keyword in ['plan', 'approach', 'strategy']):
            return ("Here's my implementation approach:\n"
                   "1. Analyze the requirements and existing code\n"
                   "2. Design the solution architecture\n"
                   "3. Implement the core functionality\n"
                   "4. Add error handling and validation\n"
                   "5. Test the implementation thoroughly")
        
        # Error handling patterns
        if any(keyword in prompt_lower for keyword in ['error', 'bug', 'debug', 'fix']):
            return ("I'll examine the error and implement a fix. This typically involves:\n"
                   "1. Understanding the root cause\n"
                   "2. Implementing the correction\n"
                   "3. Adding validation to prevent recurrence")
        
        # Testing patterns
        if 'test' in prompt_lower and any(word in prompt_lower for word in ['run', 'execute', 'check']):
            return "I'll run the tests to verify the implementation works correctly."
        
        # Default intelligent response
        return ("I understand the task. I'll proceed systematically to implement "
               "a robust solution that meets the requirements and follows best practices.")
    
    def _generate_function_implementation(self, prompt: str) -> str:
        """Generate function implementation based on context"""
        prompt_lower = prompt.lower()
        
        if 'calculator' in prompt_lower:
            if 'add' in prompt_lower:
                return '''def add(a, b):
    """Add two numbers and return the result."""
    return a + b'''
            elif 'multiply' in prompt_lower:
                return '''def multiply(a, b):
    """Multiply two numbers and return the result."""
    return a * b'''
            else:
                return '''def calculate(operation, a, b):
    """Perform basic arithmetic operations."""
    if operation == '+':
        return a + b
    elif operation == '*':
        return a * b
    elif operation == '-':
        return a - b
    elif operation == '/':
        return a / b if b != 0 else 0
    else:
        raise ValueError("Unsupported operation")'''
        
        elif 'fibonacci' in prompt_lower:
            return '''def fibonacci(n):
    """Generate fibonacci sequence up to n terms."""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib'''
        
        elif 'process' in prompt_lower or 'data' in prompt_lower:
            return '''def process_data(data):
    """Process input data and return processed result."""
    if not data:
        return []
    
    # Process the data according to requirements
    processed = []
    for item in data:
        # Add processing logic here
        processed.append(item)
    
    return processed'''
        
        else:
            return '''def main_function(param):
    """Main implementation function."""
    # Validate input
    if not param:
        raise ValueError("Parameter cannot be empty")
    
    # Process the parameter
    result = param
    
    # Return processed result
    return result'''
    
    def _generate_class_implementation(self, prompt: str) -> str:
        """Generate class implementation"""
        prompt_lower = prompt.lower()
        
        if 'user' in prompt_lower or 'model' in prompt_lower:
            return '''class User:
    """User model class."""
    
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.created_at = time.time()
    
    def validate(self):
        """Validate user data."""
        if not self.name or not self.email:
            raise ValueError("Name and email are required")
        return True
    
    def to_dict(self):
        """Convert user to dictionary."""
        return {
            'name': self.name,
            'email': self.email,
            'created_at': self.created_at
        }'''
        
        elif 'api' in prompt_lower or 'service' in prompt_lower:
            return '''class APIService:
    """API service class."""
    
    def __init__(self, config):
        self.config = config
        self.initialized = False
    
    def initialize(self):
        """Initialize the service."""
        # Setup code here
        self.initialized = True
    
    def process_request(self, request):
        """Process API request."""
        if not self.initialized:
            self.initialize()
        
        # Process the request
        return {"status": "success", "data": request}'''
        
        else:
            return '''class MainClass:
    """Main implementation class."""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.status = "initialized"
    
    def execute(self, params):
        """Execute main functionality."""
        # Implementation logic
        return {"result": "completed", "params": params}
    
    def get_status(self):
        """Get current status."""
        return self.status'''
    
    def _generate_api_implementation(self, prompt: str) -> str:
        """Generate API implementation"""
        return '''async def create_user(user_data):
    """Create a new user via API endpoint."""
    # Validate input data
    if not user_data or 'name' not in user_data:
        return {"error": "Invalid user data"}
    
    # Create user
    user = User(user_data['name'], user_data.get('email'))
    user.validate()
    
    # Save to database
    # db.save(user)
    
    return {"status": "created", "user": user.to_dict()}

async def get_user(user_id):
    """Get user by ID."""
    # Fetch from database
    # user = db.get(user_id)
    
    if not user_id:
        return {"error": "User not found"}
    
    return {"status": "success", "user": {"id": user_id}}'''
    
    def _generate_test_implementation(self, prompt: str) -> str:
        """Generate test implementation"""
        return '''def test_main_functionality():
    """Test the main functionality."""
    # Arrange
    test_data = {"key": "value"}
    expected = {"result": "completed", "params": test_data}
    
    # Act
    instance = MainClass()
    result = instance.execute(test_data)
    
    # Assert
    assert result == expected
    assert instance.get_status() == "initialized"

def test_error_handling():
    """Test error handling."""
    instance = MainClass()
    
    # Test with invalid input
    try:
        instance.execute(None)
        assert False, "Should have raised an error"
    except ValueError:
        pass  # Expected'''
    
    def _identify_pattern(self, prompt: str) -> str:
        """Identify which pattern was matched"""
        prompt_lower = prompt.lower()
        
        if 'implement' in prompt_lower:
            if 'function' in prompt_lower:
                return 'function_implementation'
            elif 'class' in prompt_lower:
                return 'class_implementation'
            elif 'api' in prompt_lower:
                return 'api_implementation'
            elif 'test' in prompt_lower:
                return 'test_implementation'
            else:
                return 'general_implementation'
        elif any(word in prompt_lower for word in ['read', 'write', 'edit']):
            return 'file_operation'
        elif any(word in prompt_lower for word in ['analyze', 'plan']):
            return 'analysis_planning'
        elif any(word in prompt_lower for word in ['error', 'debug']):
            return 'error_handling'
        else:
            return 'default_response'
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get mock provider information"""
        return {
            "provider": "mock",
            "model": self.config.model,
            "supports_streaming": False,
            "supports_function_calling": False,
            "max_context_length": 4096,
            "pricing": {
                "input_per_1k": 0.0,
                "output_per_1k": 0.0
            },
            "total_calls": self.call_count
        }
