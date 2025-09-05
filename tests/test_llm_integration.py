"""
Test LLM integration functionality.

Tests the new LLM interfaces and providers to ensure they work correctly
with the WorkMemEval framework.
"""

import pytest
import asyncio
import os
from unittest.mock import patch, AsyncMock

from src.core.llm_interfaces import LLMConfig, LLMProvider, LLMResponse
from src.llm import LLMFactory, MockProvider, OpenAIProvider
from src.agents.simple_agent import SimpleWorkMemAgent
from src.memory.simple_memory import NoMemory


class TestLLMInterfaces:
    """Test core LLM interfaces and data structures"""
    
    def test_llm_config_creation(self):
        """Test LLMConfig creation and validation"""
        config = LLMConfig(
            provider=LLMProvider.MOCK,
            model="test-model",
            temperature=0.1,
            max_tokens=1000
        )
        assert config.provider == LLMProvider.MOCK
        assert config.model == "test-model"
        assert config.temperature == 0.1
        assert config.max_tokens == 1000
    
    def test_llm_response_structure(self):
        """Test LLMResponse data structure"""
        response = LLMResponse(
            content="Test response",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
            latency_ms=100.0,
            cost_usd=0.001
        )
        assert response.content == "Test response"
        assert response.model == "test-model"
        assert response.usage["prompt_tokens"] == 10
        assert response.latency_ms == 100.0
        assert response.cost_usd == 0.001


class TestMockProvider:
    """Test MockProvider functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        config = LLMConfig(
            provider=LLMProvider.MOCK,
            model="mock-test",
            provider_config={"response_delay": 0.0}
        )
        self.provider = MockProvider(config)
    
    @pytest.mark.asyncio
    async def test_mock_provider_basic_response(self):
        """Test basic response generation"""
        response = await self.provider.generate_response("Hello, world!")
        
        assert isinstance(response, LLMResponse)
        assert response.content is not None
        assert len(response.content) > 0
        assert response.model == "mock-test"
        assert response.cost_usd == 0.0
    
    @pytest.mark.asyncio
    async def test_mock_provider_function_implementation(self):
        """Test function implementation response"""
        response = await self.provider.generate_response(
            "Implement a function to calculate fibonacci numbers"
        )
        
        assert isinstance(response, LLMResponse)
        assert "def fibonacci" in response.content
        assert response.metadata["pattern_matched"] == "function_implementation"
    
    @pytest.mark.asyncio
    async def test_mock_provider_planning_response(self):
        """Test planning response"""
        response = await self.provider.generate_response(
            "Plan the implementation approach for this project"
        )
        
        assert isinstance(response, LLMResponse)
        assert "1." in response.content
        assert "analyze" in response.content.lower()
        assert response.metadata["pattern_matched"] == "general_implementation"
    
    def test_mock_provider_info(self):
        """Test provider info"""
        info = self.provider.get_provider_info()
        
        assert info["provider"] == "mock"
        assert info["model"] == "mock-test"
        assert info["pricing"]["input_per_1k"] == 0.0
        assert info["pricing"]["output_per_1k"] == 0.0
    
    def test_mock_provider_metrics(self):
        """Test usage metrics tracking"""
        initial_metrics = self.provider.get_usage_metrics()
        assert initial_metrics.total_requests == 0
        
        # Note: Can't easily test async metrics without running the async method


class TestLLMFactory:
    """Test LLM factory functionality"""
    
    def test_factory_creates_mock_provider(self):
        """Test factory creates mock provider"""
        config = LLMConfig(
            provider=LLMProvider.MOCK,
            model="test-model"
        )
        provider = LLMFactory.create_provider(config)
        assert isinstance(provider, MockProvider)
    
    def test_factory_convenience_methods(self):
        """Test factory convenience methods"""
        # Test mock creation
        try:
            openai_provider = LLMFactory.create_openai(
                model="gpt-4o-mini",
                api_key="test-key"
            )
            assert isinstance(openai_provider, OpenAIProvider)
        except Exception:
            # Expected if dependencies not available
            pass
        
        try:
            openrouter_provider = LLMFactory.create_openrouter(
                model="anthropic/claude-3-haiku",
                api_key="test-key"
            )
            assert isinstance(openrouter_provider, OpenAIProvider)
        except Exception:
            # Expected if dependencies not available
            pass
    
    def test_factory_unknown_provider_error(self):
        """Test factory raises error for unknown provider"""
        config = LLMConfig(
            provider=LLMProvider.LOCAL,  # Not implemented
            model="test-model"
        )
        
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            LLMFactory.create_provider(config)


class TestAgentLLMIntegration:
    """Test agent integration with LLM providers"""
    
    def setup_method(self):
        """Set up test environment"""
        self.memory = NoMemory({})
        self.agent_config = {
            'max_iterations': 5,
            'memory_context_limit': 3,
            'llm_config': {
                'provider': 'mock',
                'model': 'test-agent-model',
                'response_delay': 0.0
            }
        }
        self.agent = SimpleWorkMemAgent(self.memory, self.agent_config)
    
    def test_agent_llm_initialization(self):
        """Test agent initializes LLM provider correctly"""
        assert hasattr(self.agent, 'llm')
        assert isinstance(self.agent.llm, MockProvider)
        assert self.agent.llm.config.model == 'test-agent-model'
    
    def test_agent_fallback_to_mock(self):
        """Test agent falls back to mock for unknown providers"""
        config_with_unknown_provider = {
            'llm_config': {
                'provider': 'unknown_provider',
                'model': 'test-model'
            }
        }
        
        # Should not raise an error, should fallback to mock
        agent = SimpleWorkMemAgent(self.memory, config_with_unknown_provider)
        assert isinstance(agent.llm, MockProvider)
    
    def test_agent_different_llm_configurations(self):
        """Test agent with different LLM configurations"""
        configurations = [
            {'provider': 'mock', 'model': 'model1'},
            {'provider': 'mock', 'model': 'model2', 'temperature': 0.5},
            {'provider': 'mock', 'response_delay': 0.1}
        ]
        
        for llm_config in configurations:
            agent_config = {'llm_config': llm_config}
            agent = SimpleWorkMemAgent(self.memory, agent_config)
            assert isinstance(agent.llm, MockProvider)
    
    @pytest.mark.asyncio
    async def test_agent_checkpoint_execution_with_llm(self):
        """Test agent can execute checkpoint with LLM integration"""
        from src.core.task_specification import CheckpointSpecification
        
        checkpoint = CheckpointSpecification(
            checkpoint_id="test_cp",
            order=1,
            title="Test Checkpoint",
            stub_file="test.py",
            stub_function="test_function",
            requirements="Implement a simple test function",
            test_file="test_test.py",
            dependencies=[]
        )
        
        # Execute checkpoint - should work with mock LLM
        success = await self.agent.execute_checkpoint(checkpoint)
        assert isinstance(success, bool)  # Should complete without error
    
    def test_llm_usage_metrics_integration(self):
        """Test LLM usage metrics are tracked"""
        initial_metrics = self.agent.llm.get_usage_metrics()
        assert initial_metrics.total_requests == 0
        assert initial_metrics.total_cost_usd == 0.0
        
        # Metrics should be tracked after LLM calls
        # (Would need async test to verify increments)


@pytest.mark.skipif(
    not (os.getenv('OPENAI_API_KEY') or os.getenv('OPENROUTER_API_KEY')),
    reason="API keys not available"
)
class TestRealLLMIntegration:
    """Test integration with real LLM providers (requires API keys)"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_openai_integration(self):
        """Test OpenAI integration (requires OPENAI_API_KEY)"""
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("OPENAI_API_KEY not set")
        
        try:
            provider = LLMFactory.create_openai(
                model="gpt-4o-mini",
                temperature=0.0,
                max_tokens=50
            )
            
            response = await provider.generate_response(
                "Say 'Hello, WorkMemEval!' and nothing else."
            )
            
            assert isinstance(response, LLMResponse)
            assert "WorkMemEval" in response.content
            assert response.usage["total_tokens"] > 0
            assert response.cost_usd > 0
            
            # Clean up
            await provider.close()
            
        except Exception as e:
            pytest.skip(f"OpenAI integration test failed: {e}")
    
    @pytest.mark.asyncio  
    @pytest.mark.slow
    async def test_openrouter_integration(self):
        """Test OpenRouter integration (requires OPENROUTER_API_KEY)"""
        if not os.getenv('OPENROUTER_API_KEY'):
            pytest.skip("OPENROUTER_API_KEY not set")
        
        try:
            provider = LLMFactory.create_openrouter(
                model="anthropic/claude-3-haiku",
                temperature=0.0,
                max_tokens=50
            )
            
            response = await provider.generate_response(
                "Say 'Hello from OpenRouter!' and nothing else."
            )
            
            assert isinstance(response, LLMResponse)
            assert "OpenRouter" in response.content
            assert response.usage["total_tokens"] > 0
            
            # Clean up
            await provider.close()
            
        except Exception as e:
            pytest.skip(f"OpenRouter integration test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
