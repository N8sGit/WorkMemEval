"""
Unit tests for ReferenceWorkMemAgent.

Tests the reference agent implementation with comprehensive
coverage following TDD principles.
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, MagicMock

from src.agents.reference_agent import ReferenceWorkMemAgent
from src.memory.context_memory import ContextMemorySystem
from src.memory.memory_system import NoMemoryBaseline as NoMemory
from src.core.plugin_interfaces import PluginCapabilities
from src.core.action_trace import ActionTracer, ActionType
from src.core.task_specification import (
    TaskSpecification, CheckpointSpecification, TaskComplexityMetrics
)
from src.core.llm_interfaces import LLMConfig, LLMProvider
from .mock_llm_provider import MockLLMProvider


class TestReferenceWorkMemAgent:
    """Test ReferenceWorkMemAgent functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.memory = ContextMemorySystem({'max_items': 100})
        self.agent = ReferenceWorkMemAgent(self.memory, {
            'max_iterations': 10,
            'memory_context_limit': 5,
            'llm_config': {'response_delay': 0.0}
        })
    
    def test_agent_creation(self):
        """Test creating ReferenceWorkMemAgent"""
        assert isinstance(self.agent, ReferenceWorkMemAgent)
        assert self.agent.memory_system is self.memory
        assert self.agent.max_iterations == 10
        assert self.agent.memory_context_limit == 5
        assert isinstance(self.agent.llm, MockLLMProvider)
    
    def test_agent_capabilities(self):
        """Test agent capabilities"""
        caps = self.agent.get_capabilities()
        assert isinstance(caps, PluginCapabilities)
        assert caps.supports_search is True
        assert caps.supports_introspection is True
        assert caps.supports_embeddings is False
    
    def test_file_operations(self):
        """Test basic file operations"""
        # Test file creation
        success = self.agent._create_file("test.py", "print('hello')")
        assert success is True
        assert "test.py" in self.agent.file_read_cache
        assert self.agent.file_read_cache["test.py"] == "print('hello')"
        
        # Test file reading
        success = self.agent._read_file("test.py")
        assert success is True
        
        # Test file editing
        success = self.agent._edit_file("test.py", "print('world')")
        assert success is True
        assert "print('world')" in self.agent.file_read_cache["test.py"]
    
    def test_file_exists_check(self):
        """Test file existence checking"""
        assert self.agent._file_exists("nonexistent.py") is False
        
        self.agent._create_file("exists.py", "content")
        assert self.agent._file_exists("exists.py") is True
    
    def test_mock_file_content_generation(self):
        """Test generation of mock file content"""
        # Python files
        content = self.agent._get_mock_file_content("example.py")
        assert "# Python file" in content
        assert "TODO" in content
        
        # Text files
        content = self.agent._get_mock_file_content("readme.txt")
        assert "Text file" in content
        
        # JSON files
        content = self.agent._get_mock_file_content("config.json")
        assert '"file"' in content
        assert "placeholder" in content
    
    def test_memory_integration(self):
        """Test integration with memory system"""
        # Test storing task context
        task_spec = self._create_sample_task()
        self.agent._store_task_context(task_spec)
        
        # Check that task was stored in memory
        results = self.memory.retrieve_information("sample_task", {})
        assert len(results) > 0
        
        # Test storing checkpoint context
        checkpoint = task_spec.checkpoints[0]
        self.agent._store_checkpoint_context(checkpoint)
        
        results = self.memory.retrieve_information("setup", {})
        assert len(results) > 0
    
    def test_context_retrieval(self):
        """Test retrieval of relevant context from memory"""
        # Store some context first
        self.memory.store_information("test_key", "test_value", {"type": "test"})
        
        checkpoint = CheckpointSpecification(
            checkpoint_id="test_checkpoint",
            order=1,
            title="Test Checkpoint",
            stub_file="test.py",
            stub_function="test_function",
            requirements="Test checkpoint with test keyword",
            test_file="test_test.py",
            dependencies=[]
        )
        
        context = self.agent._retrieve_relevant_context(checkpoint)
        assert 'retrieved_items' in context
        # Should find the item with "test" keyword
        assert len(context['retrieved_items']) > 0
    
    def test_plan_generation(self):
        """Test execution plan generation"""
        checkpoint = CheckpointSpecification(
            checkpoint_id="impl",
            order=1,
            title="Calculator Implementation",
            stub_file="calculator.py",
            stub_function="Calculator",
            requirements="Implement calculator functions",
            test_file="test_calculator.py",
            dependencies=[]
        )
        
        context = {'retrieved_items': []}
        
        async def run_test():
            plan = await self.agent._plan_checkpoint_execution(checkpoint, context)
            return plan
        
        plan = asyncio.run(run_test())
        
        assert isinstance(plan, list)
        assert len(plan) > 0
        
        # Should have steps for each required file
        file_actions = [step for step in plan if 'file_path' in step]
        assert len(file_actions) >= 2  # One for each required file
    
    def test_plan_parsing(self):
        """Test parsing of LLM response into execution plan"""
        checkpoint = CheckpointSpecification(
            checkpoint_id="test",
            order=1,
            title="Test Implementation",
            stub_file="main.py",
            stub_function="main",
            requirements="Test implementation",
            test_file="test_main.py",
            dependencies=[]
        )
        
        response = "I will implement the functionality step by step"
        plan = self.agent._parse_plan_from_response(response, checkpoint)
        
        assert isinstance(plan, list)
        # Should have at least create_file and implement actions
        actions = [step['action'] for step in plan]
        assert 'create_file' in actions
        assert 'implement' in actions
    
    def test_step_execution(self):
        """Test execution of individual plan steps"""
        async def run_test():
            # Test read_file step
            self.agent._create_file("test.py", "content")
            step = {'action': 'read_file', 'file_path': 'test.py'}
            success = await self.agent._execute_step(step)
            assert success is True
            
            # Test create_file step
            step = {'action': 'create_file', 'file_path': 'new.py', 'content': 'new content'}
            success = await self.agent._execute_step(step)
            assert success is True
            
            # Test implement step
            step = {'action': 'implement', 'description': 'calculator functions'}
            success = await self.agent._execute_step(step)
            assert success is True
            
            # Test unknown action
            step = {'action': 'unknown_action'}
            success = await self.agent._execute_step(step)
            assert success is False
        
        asyncio.run(run_test())
    
    def test_implementation_functionality(self):
        """Test implementation of functionality"""
        async def run_test():
            success = await self.agent._implement_functionality("create calculator functions")
            assert success is True
            
            # Should store implementation in memory
            results = self.memory.retrieve_information("calculator", {})
            assert len(results) > 0
        
        asyncio.run(run_test())
    
    def test_context_formatting(self):
        """Test formatting of context for prompts"""
        context = {
            'retrieved_items': [
                {'key': 'test1', 'value': 'This is test value 1'},
                {'key': 'test2', 'value': 'This is test value 2'}
            ]
        }
        
        formatted = self.agent._format_context_for_prompt(context)
        assert 'test1' in formatted
        assert 'test2' in formatted
        assert 'This is test value 1' in formatted
        
        # Test empty context
        empty_context = {'retrieved_items': []}
        formatted = self.agent._format_context_for_prompt(empty_context)
        assert 'No relevant context' in formatted
    
    def test_checkpoint_execution(self):
        """Test execution of a complete checkpoint"""
        checkpoint = CheckpointSpecification(
            checkpoint_id="test_checkpoint",
            order=1,
            title="Calculator Implementation",
            stub_file="calculator.py",
            stub_function="Calculator",
            requirements="Implement basic calculator",
            test_file="test_calculator.py",
            dependencies=[]
        )
        
        # Since execute_checkpoint is now async, we need to run it in an event loop
        async def run_test():
            success = await self.agent.execute_checkpoint(checkpoint)
            return success
        
        success = asyncio.run(run_test())
        assert success is True
    
    def test_task_execution(self):
        """Test execution of a complete task"""
        # Create a mock action tracer
        action_tracer = Mock()
        
        task_spec = self._create_sample_task()
        success = self.agent.execute_task(task_spec, action_tracer)
        assert success is True
        
        # Should have stored task context in memory
        results = self.memory.retrieve_information("sample_task", {})
        assert len(results) > 0
    
    def test_error_handling(self):
        """Test error handling in various operations"""
        async def run_test():
            # Test with a mock that raises an exception
            original_llm = self.agent.llm
            self.agent.llm = Mock()
            self.agent.llm.generate_response.side_effect = Exception("Mock error")
            
            success = await self.agent._implement_functionality("test")
            assert success is False
            
            # Restore original LLM
            self.agent.llm = original_llm
        
        asyncio.run(run_test())
    
    def test_action_logging(self):
        """Test that actions are logged correctly"""
        mock_tracer = Mock()
        self.agent.action_tracer = mock_tracer
        
        # Test logging different action types
        self.agent._log_action(ActionType.FILE_READ, "test.py")
        mock_tracer.log_action.assert_called_with(ActionType.FILE_READ, "test.py")
        
        self.agent._log_action(ActionType.PLANNING, "Planning step")
        mock_tracer.log_action.assert_called_with(ActionType.PLANNING, "Planning step")
    
    def test_memory_system_integration(self):
        """Test integration with different memory systems"""
        # Test with NoMemory
        no_memory = NoMemory({})
        no_mem_agent = ReferenceWorkMemAgent(no_memory, {})
        
        async def run_test():
            # Should still work, just no memory persistence
            success = await no_mem_agent._implement_functionality("test")
            assert success is True
        
        asyncio.run(run_test())
        
        # NoMemory should show empty retrieval
        context = no_mem_agent._retrieve_relevant_context(
            CheckpointSpecification(
                checkpoint_id="test",
                order=1,
                title="Test",
                stub_file="test.py",
                stub_function="test",
                requirements="test requirements",
                test_file="test_test.py",
                dependencies=[]
            )
        )
        assert len(context['retrieved_items']) == 0
    
    def test_behavioral_trace(self):
        """Test getting behavioral trace from agent"""
        # Test with no action tracer - should return empty trace
        trace = self.agent.get_behavioral_trace()
        assert trace.task_id == "unknown"
        assert trace.completed_successfully is False
        
        # Test with mock action tracer
        mock_tracer = Mock()
        mock_trace = Mock()
        mock_tracer.get_task_trace.return_value = mock_trace
        self.agent.action_tracer = mock_tracer
        
        trace = self.agent.get_behavioral_trace()
        assert trace is mock_trace
        mock_tracer.get_task_trace.assert_called_once()
    
    def _create_sample_task(self) -> TaskSpecification:
        """Create a sample task for testing"""
        checkpoint1 = CheckpointSpecification(
            checkpoint_id="setup",
            order=1,
            title="Setup Calculator",
            stub_file="calculator.py",
            stub_function="Calculator",
            requirements="Set up calculator project structure",
            test_file="test_calculator.py",
            dependencies=[]
        )
        
        checkpoint2 = CheckpointSpecification(
            checkpoint_id="implement",
            order=2,
            title="Implement Calculator",
            stub_file="calculator.py",
            stub_function="Calculator",
            requirements="Implement calculator functions",
            test_file="test_calculator.py",
            dependencies=["setup"]
        )
        
        return TaskSpecification(
            task_id="sample_task",
            title="Simple Calculator",
            domain="calculator",
            description="Create a simple calculator",
            checkpoints=[checkpoint1, checkpoint2],
            planning_phase=Mock(),
            repository=Mock(),
            memory_challenges=[]
        )


class TestAgentMemoryInteraction:
    """Test agent interaction with different memory systems"""
    
    def test_with_simple_memory(self):
        """Test agent with ContextMemorySystem"""
        memory = ContextMemorySystem({'max_items': 10})
        agent = ReferenceWorkMemAgent(memory, {})
        
        async def run_test():
            # Store and retrieve information
            await agent._implement_functionality("calculator add function")
            
            # Should be able to find the implementation
            results = memory.retrieve_information("calculator", {})
            assert len(results) > 0
        
        asyncio.run(run_test())
    
    def test_with_no_memory(self):
        """Test agent with NoMemory system"""
        memory = NoMemory({})
        agent = ReferenceWorkMemAgent(memory, {})
        
        async def run_test():
            # Should work without errors even with no memory
            success = await agent._implement_functionality("test function")
            assert success is True
        
        asyncio.run(run_test())
        
        # But memory won't retrieve anything
        context = agent._retrieve_relevant_context(
            CheckpointSpecification(
                checkpoint_id="test",
                order=1,
                title="Test",
                stub_file="test.py",
                stub_function="test",
                requirements="test requirements",
                test_file="test_test.py"
            )
        )
        assert len(context['retrieved_items']) == 0
    
    def test_memory_context_limiting(self):
        """Test that memory context is properly limited"""
        memory = ContextMemorySystem({'max_items': 100})
        agent = ReferenceWorkMemAgent(memory, {'memory_context_limit': 2})
        
        # Store multiple items
        for i in range(5):
            memory.store_information(f"test_{i}", f"test content {i}", {'type': 'test'})
        
        checkpoint = CheckpointSpecification(
            checkpoint_id="test",
            order=1,
            title="Test Checkpoint",
            stub_file="test.py",
            stub_function="test_function",
            requirements="test checkpoint",
            test_file="test_test.py",
            dependencies=[]
        )
        
        context = agent._retrieve_relevant_context(checkpoint)
        # Should be limited by memory_context_limit setting (2 per query, max 4 queries)
        assert len(context['retrieved_items']) <= 2 * 4  # Max 4 queries * 2 limit each


if __name__ == "__main__":
    pytest.main([__file__])
