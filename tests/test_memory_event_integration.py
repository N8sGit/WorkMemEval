"""
Integration test for memory event logging through MemorySystemInterface.

This test demonstrates that memory operations are automatically logged as 
action trace events when using the MemorySystemInterface with an ActionTracer.
"""

import pytest
import asyncio
from unittest.mock import Mock

from src.agents.simple_agent import SimpleWorkMemAgent
from src.memory.reference_implementations import SimpleContextMemory
from src.memory.memory_system import MemorySystemInterface, MemorySystemFactory
from src.core.action_trace import ActionTracer, ActionType
from src.core.task_specification import CheckpointSpecification


class TestMemoryEventIntegration:
    """Test that memory operations are logged as action trace events"""
    
    def setup_method(self):
        """Setup for each test"""
        # Create memory system with interface wrapper
        self.memory_system = SimpleContextMemory({'max_items': 100})
        self.memory_interface = MemorySystemInterface(self.memory_system)
        
        # Create agent with memory interface
        self.agent = SimpleWorkMemAgent(self.memory_interface, {
            'llm_config': {'response_delay': 0.0},
            'use_secure_file_ops': False
        })
        
        # Create action tracer and attach to both interface and agent
        self.tracer = ActionTracer("memory_integration_test")
        self.memory_interface.set_action_tracer(self.tracer)
        self.agent.action_tracer = self.tracer
    
    def test_memory_store_events_are_logged(self):
        """Test that memory store operations generate action trace events"""
        # Start a checkpoint so actions get logged
        self.tracer.start_checkpoint("test_store_checkpoint")
        
        # Perform memory operations through the agent (which uses memory interface)
        self.agent._implement_functionality("test implementation")
        
        # Complete the checkpoint
        self.tracer.complete_checkpoint(True)
        
        # Get task trace and check for memory store events
        task_trace = self.tracer.get_task_trace()
        
        # Get all actions from all checkpoint traces
        all_actions = []
        for checkpoint_trace in task_trace.checkpoint_traces:
            all_actions.extend(checkpoint_trace.actions)
        
        # Find memory store actions
        memory_store_actions = [
            action for action in all_actions
            if action.action_type == ActionType.MEMORY_STORE
        ]
        
        # Should have at least one memory store action
        assert len(memory_store_actions) >= 1
        
        # Verify the memory store action has proper fields
        memory_action = memory_store_actions[0]
        assert memory_action.success is True
        assert 'key' in memory_action.metadata
        assert 'size_bytes' in memory_action.metadata
        assert 'memory_type' in memory_action.metadata
        assert memory_action.metadata['memory_type'] == 'SimpleContextMemory'
    
    def test_memory_retrieve_events_are_logged(self):
        """Test that memory retrieve operations generate action trace events"""
        # Start a checkpoint so actions get logged
        self.tracer.start_checkpoint("test_retrieve_checkpoint")
        
        # Store something first so we have something to retrieve
        self.memory_interface.store("test_key", "test_value", {"type": "test"})
        
        # Perform a checkpoint execution that will trigger memory retrieval
        checkpoint = CheckpointSpecification(
            checkpoint_id="memory_test",
            order=1,
            title="Memory Test",
            stub_file="test.py",
            stub_function="test_function",
            requirements="test with memory retrieval",
            test_file="test_test.py",
            dependencies=[]
        )
        
        # Execute checkpoint (this will call _retrieve_relevant_context internally)
        asyncio.run(self.agent.execute_checkpoint(checkpoint))
        
        # Complete the checkpoint
        self.tracer.complete_checkpoint(True)
        
        # Get task trace and check for memory retrieve events
        task_trace = self.tracer.get_task_trace()
        
        # Get all actions from all checkpoint traces
        all_actions = []
        for checkpoint_trace in task_trace.checkpoint_traces:
            all_actions.extend(checkpoint_trace.actions)
        
        # Find memory actions
        memory_store_actions = [
            action for action in all_actions
            if action.action_type == ActionType.MEMORY_STORE
        ]
        memory_retrieve_actions = [
            action for action in all_actions
            if action.action_type == ActionType.MEMORY_RETRIEVE
        ]
        
        # Should have both store and retrieve actions
        assert len(memory_store_actions) >= 1
        assert len(memory_retrieve_actions) >= 1
        
        # Verify retrieve action has proper fields
        retrieve_action = memory_retrieve_actions[0]
        assert retrieve_action.success is True
        assert 'query' in retrieve_action.metadata
        assert 'total_returned_size' in retrieve_action.metadata
        assert 'hit_count' in retrieve_action.metadata
        assert 'memory_type' in retrieve_action.metadata
    
    def test_memory_events_contain_detailed_metadata(self):
        """Test that memory events contain detailed metadata for analysis"""
        # Start a checkpoint so actions get logged
        self.tracer.start_checkpoint("test_metadata_checkpoint")
        
        # Store different sized content
        small_content = "small"
        large_content = "large content " * 20
        
        self.memory_interface.store("small_key", small_content, {"type": "small"})
        self.memory_interface.store("large_key", large_content, {"type": "large"})
        
        # Retrieve with different queries
        small_results = self.memory_interface.retrieve("small", {"limit": 1})
        large_results = self.memory_interface.retrieve("large", {"limit": 1})
        
        # Complete the checkpoint
        self.tracer.complete_checkpoint(True)
        
        # Get task trace
        task_trace = self.tracer.get_task_trace()
        
        # Get all actions from all checkpoint traces
        all_actions = []
        for checkpoint_trace in task_trace.checkpoint_traces:
            all_actions.extend(checkpoint_trace.actions)
        
        # Find memory actions
        memory_store_actions = [
            action for action in all_actions
            if action.action_type == ActionType.MEMORY_STORE
        ]
        memory_retrieve_actions = [
            action for action in all_actions
            if action.action_type == ActionType.MEMORY_RETRIEVE
        ]
        
        # Should have 2 stores and 2 retrieves
        assert len(memory_store_actions) >= 2
        assert len(memory_retrieve_actions) >= 2
        
        # Check that size metadata varies appropriately
        store_sizes = [action.metadata.get('size_bytes', 0) for action in memory_store_actions]
        assert min(store_sizes) < max(store_sizes)  # Different sizes
        
        # Check that retrieve actions have hit counts
        for retrieve_action in memory_retrieve_actions:
            assert 'hit_count' in retrieve_action.metadata
            assert isinstance(retrieve_action.metadata['hit_count'], int)
            assert retrieve_action.metadata['hit_count'] >= 0
    
    def test_factory_created_memory_interface_logs_events(self):
        """Test that memory systems created via factory also log events correctly"""
        # Create memory system using factory
        factory_interface = MemorySystemFactory.create_memory_system('simple_context', {'max_items': 50})
        factory_interface.set_action_tracer(self.tracer)
        
        # Start a checkpoint
        self.tracer.start_checkpoint("factory_test_checkpoint")
        
        # Use factory-created interface directly
        factory_interface.store("factory_key", "factory_value", {"source": "factory"})
        results = factory_interface.retrieve("factory", {})
        
        # Complete the checkpoint
        self.tracer.complete_checkpoint(True)
        
        # Get task trace and verify events
        task_trace = self.tracer.get_task_trace()
        
        # Get all actions from all checkpoint traces
        all_actions = []
        for checkpoint_trace in task_trace.checkpoint_traces:
            all_actions.extend(checkpoint_trace.actions)
        
        memory_actions = [
            action for action in all_actions
            if action.action_type in [ActionType.MEMORY_STORE, ActionType.MEMORY_RETRIEVE]
        ]
        
        # Should have both store and retrieve actions
        assert len(memory_actions) >= 2
        
        # Verify proper memory type is logged
        for action in memory_actions:
            assert 'memory_type' in action.metadata
            assert action.metadata['memory_type'] == 'SimpleContextMemory'


if __name__ == "__main__":
    pytest.main([__file__])
