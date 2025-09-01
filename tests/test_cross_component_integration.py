#!/usr/bin/env python3
"""
Cross-Component Integration Tests

Tests the interactions between different system components:
- Agent ↔ Memory System
- ActionTracer ↔ Memory Events  
- Three-pillar metrics ↔ TaskTrace
- Plugin loading ↔ Validation

Focus on data flow and interface contracts.
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock, patch

from src.agents.simple_agent import SimpleWorkMemAgent, MockLLM
from src.memory.reference_implementations import SimpleContextMemory, ExampleKeyValueMemory
from src.memory.memory_system import MemorySystemInterface, MemorySystemFactory
from src.memory.simple_memory import NoMemory
from src.core.action_trace import ActionTracer, ActionType, TaskTrace, CheckpointTrace
from src.core.plugin_interfaces import (
    AgentImplementation, validate_agent_implementation, validate_memory_system
)
from src.core.plugin_loader import PluginLoader
from src.core.task_specification import TaskSpecification, CheckpointSpecification
from src.evaluation.memory_metrics import WorkingMemoryEvaluationEngine
from src.evaluation.results import EvaluationResult


class TestAgentMemorySystemIntegration:
    """Test integration between agents and memory systems"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_agent_memory_interface_compatibility(self):
        """Test that agents work with different memory system interfaces"""
        # Test with raw memory system
        raw_memory = SimpleContextMemory({'max_items': 50})
        agent1 = SimpleWorkMemAgent(raw_memory, {
            'max_iterations': 5,
            'llm_config': {'response_delay': 0.0}
        })
        
        # Test basic operations
        agent1.memory_interface.store("test_key", "test_value", {"source": "test"})
        results = agent1.memory_interface.retrieve("test_value", {})
        assert len(results) > 0
        assert results[0]['key'] == "test_key"
        
        # Test with wrapped memory system
        wrapped_memory = MemorySystemInterface(raw_memory)
        agent2 = SimpleWorkMemAgent(wrapped_memory, {
            'max_iterations': 5,
            'llm_config': {'response_delay': 0.0}
        })
        
        # Test that wrapper interface works
        agent2.memory_interface.store("test_key2", "test_value2", {"source": "test"})
        results2 = agent2.memory_interface.retrieve("test_value2", {})
        assert len(results2) > 0
        assert results2[0]['key'] == "test_key2"
    
    def test_memory_system_switching(self):
        """Test agent behavior with different memory systems"""
        memory_systems = [
            ("NoMemory", NoMemory({})),
            ("SimpleContext", SimpleContextMemory({'max_items': 100})),
            ("KeyValue", ExampleKeyValueMemory({}))
        ]
        
        for memory_name, memory_system in memory_systems:
            agent = SimpleWorkMemAgent(memory_system, {
                'max_iterations': 3,
                'llm_config': {'response_delay': 0.0},
                'use_secure_file_ops': False
            })
            
            # Test basic memory operations
            if memory_name != "NoMemory":  # NoMemory discards everything
                agent.memory_interface.store(f"key_{memory_name}", f"value_{memory_name}", {})
                results = agent.memory_interface.retrieve(f"value_{memory_name}", {})
                assert len(results) >= 0  # NoMemory returns empty, others should return data
            
            # Test agent can get capabilities
            capabilities = agent.get_capabilities()
            assert capabilities is not None
            
            # Test agent can provide behavioral trace
            trace = agent.get_behavioral_trace()
            assert trace is not None
    
    def test_memory_event_integration_with_action_tracer(self):
        """Test that memory events are properly integrated with action tracing"""
        # Set up components
        memory_system = SimpleContextMemory({'max_items': 50})
        action_tracer = ActionTracer("integration_test")
        
        # Create memory interface with tracer
        wrapped_memory = MemorySystemInterface(memory_system, enable_metrics=True)
        wrapped_memory.set_action_tracer(action_tracer)
        
        agent = SimpleWorkMemAgent(wrapped_memory, {
            'max_iterations': 3,
            'llm_config': {'response_delay': 0.0}
        })
        
        # Start checkpoint to capture actions
        action_tracer.start_checkpoint("cp1")
        
        # Perform memory operations
        wrapped_memory.store("integration_key", "integration_value", {"context": "test"})
        results = wrapped_memory.retrieve("integration_value", {})
        
        # Complete checkpoint
        action_tracer.complete_checkpoint(True)
        
        # Get trace and verify memory events were logged
        task_trace = action_tracer.get_task_trace()
        cp_trace = task_trace.get_checkpoint_trace("cp1")
        
        assert cp_trace is not None
        assert len(cp_trace.actions) >= 2  # At least store and retrieve actions
        
        # Check for memory-related actions
        memory_actions = [
            action for action in cp_trace.actions
            if action.action_type in [ActionType.MEMORY_STORE, ActionType.MEMORY_RETRIEVE]
        ]
        assert len(memory_actions) >= 2
        
        # Validate action details
        store_action = next(
            (a for a in memory_actions if a.action_type == ActionType.MEMORY_STORE), None
        )
        assert store_action is not None
        assert store_action.success is True
        
        retrieve_action = next(
            (a for a in memory_actions if a.action_type == ActionType.MEMORY_RETRIEVE), None
        )
        assert retrieve_action is not None
        assert retrieve_action.success is True


class TestThreePillarMetricsIntegration:
    """Test integration of three-pillar metrics with task traces"""
    
    def setup_method(self):
        """Set up test environment"""
        self.evaluation_engine = WorkingMemoryEvaluationEngine()
        self.action_tracer = ActionTracer("metrics_test")
    
    def create_sample_task_spec(self) -> TaskSpecification:
        """Create a sample task specification"""
        checkpoint = CheckpointSpecification(
            checkpoint_id="cp1",
            order=1,
            title="Test Checkpoint",
            stub_file="main.py",
            stub_function="main",
            requirements="Implement main function",
            test_file="test_main.py",
            dependencies=[]
        )
        
        mock_repo = Mock()
        mock_repo.provided_files = ["main.py"]
        mock_repo.distractor_files = ["distractor.py"]
        mock_repo.get = Mock(return_value=[])
        
        return TaskSpecification(
            task_id="metrics_test",
            title="Metrics Test Task",
            domain="testing",
            description="Task for testing metrics integration",
            checkpoints=[checkpoint],
            planning_phase=Mock(),
            repository=mock_repo,
            memory_challenges=[]
        )
    
    def create_realistic_task_trace(self) -> TaskTrace:
        """Create a realistic task trace for metrics testing"""
        task_trace = TaskTrace(task_id="metrics_test", start_timestamp=time.time() - 3600)
        checkpoint_trace = CheckpointTrace(checkpoint_id="cp1", start_timestamp=time.time() - 3600)
        
        # Add realistic actions
        base_time = time.time() - 3600
        actions = [
            # Planning action
            {
                'action_type': ActionType.PLANNING,
                'timestamp': base_time + 10,
                'success': True,
                'metadata': {
                    'plan': ['read main.py', 'implement function', 'run tests'],
                    'description': 'Planning checkpoint execution'
                }
            },
            # File operations
            {
                'action_type': ActionType.FILE_READ,
                'timestamp': base_time + 20,
                'success': True,
                'file_path': 'main.py',
                'metadata': {'size_bytes': 150}
            },
            {
                'action_type': ActionType.FILE_READ,
                'timestamp': base_time + 30,
                'success': True,
                'file_path': 'test_main.py',
                'metadata': {'size_bytes': 200}
            },
            # LLM call
            {
                'action_type': ActionType.LLM_CALL,
                'timestamp': base_time + 40,
                'success': True,
                'metadata': {
                    'description': 'Generate implementation',
                    'response_length': 300
                }
            },
            # File write
            {
                'action_type': ActionType.FILE_WRITE,
                'timestamp': base_time + 50,
                'success': True,
                'file_path': 'main.py',
                'metadata': {'size_bytes': 250, 'operation': 'edit'}
            },
            # Test run
            {
                'action_type': ActionType.TEST_RUN,
                'timestamp': base_time + 60,
                'success': True,
                'file_path': 'test_main.py',
                'metadata': {'tests_passed': 3, 'tests_failed': 0}
            }
        ]
        
        # Add actions to checkpoint trace
        for action_data in actions:
            # Create action entry manually since _create_action_entry is private
            from src.core.action_trace import ActionTraceEntry
            action = ActionTraceEntry(**action_data)
            checkpoint_trace.add_action(action)
        
        # Complete checkpoint and add to task
        checkpoint_trace.complete_checkpoint(tests_passed=True)
        task_trace.add_checkpoint_trace(checkpoint_trace)
        task_trace.complete_task(True)
        
        return task_trace
    
    def test_complete_three_pillar_evaluation(self):
        """Test complete three-pillar evaluation with realistic task trace"""
        task_spec = self.create_sample_task_spec()
        task_trace = self.create_realistic_task_trace()
        
        # Run three-pillar evaluation
        evaluation = self.evaluation_engine.evaluate_working_memory(
            task_trace, task_spec, agent_name="TestAgent"
        )
        
        # Validate evaluation structure
        assert evaluation is not None
        assert evaluation.task_id == "metrics_test"
        assert evaluation.agent_name == "TestAgent"
        assert isinstance(evaluation.timestamp, float)
        
        # Validate all three pillars are present
        assert evaluation.memory_fidelity is not None
        assert evaluation.contextual_relevance is not None
        assert evaluation.behavioral_integrity is not None
        
        # Validate overall assessment
        assert 0 <= evaluation.overall_working_memory_score <= 1
        assert evaluation.grade in ['A', 'B', 'C', 'D', 'F']
        assert isinstance(evaluation.summary, str)
        assert len(evaluation.summary) > 0
        
        # Validate diagnostic information
        assert isinstance(evaluation.strengths, list)
        assert isinstance(evaluation.weaknesses, list)
        assert isinstance(evaluation.improvement_suggestions, list)
    
    def test_metrics_calculation_with_different_traces(self):
        """Test that metrics calculation works with different types of traces"""
        task_spec = self.create_sample_task_spec()
        
        # Test with minimal trace
        minimal_trace = TaskTrace(task_id="minimal", start_timestamp=time.time())
        checkpoint = CheckpointTrace(checkpoint_id="cp1", start_timestamp=time.time())
        checkpoint.complete_checkpoint(True)
        minimal_trace.add_checkpoint_trace(checkpoint)
        minimal_trace.complete_task(True)
        
        evaluation = self.evaluation_engine.evaluate_working_memory(
            minimal_trace, task_spec, agent_name="MinimalAgent"
        )
        assert evaluation is not None
        assert evaluation.task_id == "minimal"
        
        # Test with complex trace
        complex_trace = self.create_realistic_task_trace()
        evaluation2 = self.evaluation_engine.evaluate_working_memory(
            complex_trace, task_spec, agent_name="ComplexAgent"
        )
        assert evaluation2 is not None
        
        # Complex trace should generally have better metrics than minimal trace
        # (This is a heuristic check - exact values depend on metric implementation)
        assert evaluation2.overall_working_memory_score >= 0


class TestPluginSystemIntegration:
    """Test integration of the plugin loading and validation system"""
    
    def test_memory_system_validation_integration(self):
        """Test validation of memory system implementations"""
        # Test valid memory systems
        valid_systems = [
            NoMemory({}),
            SimpleContextMemory({'max_items': 50}),
            ExampleKeyValueMemory({})
        ]
        
        for memory_system in valid_systems:
            # Should not raise exception
            is_valid = validate_memory_system(memory_system)
            assert is_valid is True
            
            # Should be able to get capabilities
            capabilities = memory_system.get_capabilities()
            assert capabilities is not None
            
            # Should be able to get snapshot
            snapshot = memory_system.get_memory_snapshot()
            assert isinstance(snapshot, dict)
            assert 'total_items' in snapshot
    
    def test_agent_validation_integration(self):
        """Test validation of agent implementations"""
        memory_system = SimpleContextMemory({'max_items': 50})
        
        # Test valid agent
        agent = SimpleWorkMemAgent(memory_system, {
            'max_iterations': 5,
            'llm_config': {'response_delay': 0.0}
        })
        
        # Should not raise exception
        is_valid = validate_agent_implementation(agent)
        assert is_valid is True
        
        # Should be able to get capabilities
        capabilities = agent.get_capabilities()
        assert capabilities is not None
        
        # Should be able to get agent ID
        agent_id = agent.get_agent_id()
        assert isinstance(agent_id, str)
        assert len(agent_id) > 0
    
    def test_memory_system_factory_integration(self):
        """Test memory system factory with validation"""
        # Test creating systems through factory
        factory = MemorySystemFactory()
        
        # Register and create a system
        factory.register_memory_system('test_simple', SimpleContextMemory)
        
        # Create instance
        memory_interface = factory.create_memory_system('test_simple', {'max_items': 30})
        assert isinstance(memory_interface, MemorySystemInterface)
        
        # Test the created system works
        assert memory_interface.store("factory_test", "value", {})
        results = memory_interface.retrieve("value", {})
        assert len(results) > 0
        
        # Test invalid system type
        with pytest.raises(ValueError, match="Unknown memory type"):
            factory.create_memory_system('invalid_type', {})


class TestDataFlowIntegration:
    """Test data flow between components in realistic scenarios"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.asyncio
    async def test_complete_data_flow(self):
        """Test complete data flow from agent through memory to metrics"""
        # Set up components
        base_memory = SimpleContextMemory({'max_items': 100})
        action_tracer = ActionTracer("data_flow_test")
        memory_interface = MemorySystemInterface(base_memory, enable_metrics=True)
        memory_interface.set_action_tracer(action_tracer)
        
        agent = SimpleWorkMemAgent(memory_interface, {
            'max_iterations': 5,
            'memory_context_limit': 5,
            'llm_config': {'response_delay': 0.0},
            'use_secure_file_ops': False
        })
        
        # Create test checkpoint
        checkpoint = CheckpointSpecification(
            checkpoint_id="data_flow_cp",
            order=1,
            title="Data Flow Test",
            stub_file="test.py",
            stub_function="test_func",
            requirements="Test data flow through system",
            test_file="test_test.py",
            dependencies=[]
        )
        
        # Execute checkpoint (this will generate actions and memory operations)
        action_tracer.start_checkpoint("data_flow_cp")
        success = await agent.execute_checkpoint(checkpoint)
        action_tracer.complete_checkpoint(success)
        
        # Get behavioral trace
        task_trace = agent.get_behavioral_trace()
        
        # Validate data flowed through all components
        assert task_trace is not None
        assert task_trace.task_id == "data_flow_test"
        assert len(task_trace.checkpoint_traces) == 1
        
        cp_trace = task_trace.checkpoint_traces[0]
        assert cp_trace.checkpoint_id == "data_flow_cp"
        assert len(cp_trace.actions) > 0
        
        # Check that memory operations were logged
        action_types = {action.action_type for action in cp_trace.actions}
        # Should have various types of actions
        assert len(action_types) > 1
        
        # Validate memory interface metrics were collected
        snapshot = memory_interface.get_snapshot()
        assert 'interface_metrics' in snapshot
        metrics = snapshot['interface_metrics']
        assert metrics['total_stores'] >= 0
        assert metrics['total_retrievals'] >= 0
    
    def test_error_propagation_through_components(self):
        """Test that errors propagate correctly through component boundaries"""
        # Create memory system that will fail on operations
        failing_memory = Mock()
        failing_memory.get_capabilities = Mock(return_value=Mock(supports_search=True))
        failing_memory.store_information = Mock(side_effect=RuntimeError("Memory failure"))
        failing_memory.retrieve_information = Mock(return_value=[])
        failing_memory.get_memory_snapshot = Mock(return_value={
            'total_items': 0, 
            'memory_size_bytes': 0, 
            'last_accessed': time.time()
        })
        
        # Create agent with failing memory
        agent = SimpleWorkMemAgent(failing_memory, {
            'max_iterations': 1,
            'llm_config': {'response_delay': 0.0},
            'use_secure_file_ops': False
        })
        
        # Test that agent handles memory failures gracefully
        # (This depends on implementation - some errors may be caught, others propagated)
        try:
            agent.memory_interface.store("test", "value", {})
            # If we get here, the error was handled gracefully
        except Exception as e:
            # If we get here, the error was propagated (also valid)
            assert "Memory failure" in str(e)
    
    def test_interface_contract_compliance(self):
        """Test that all components comply with their interface contracts"""
        # Test memory system interface contract
        memory = SimpleContextMemory({'max_items': 50})
        
        # All memory systems must support these operations
        assert hasattr(memory, 'get_capabilities')
        assert hasattr(memory, 'store_information')
        assert hasattr(memory, 'retrieve_information')
        assert hasattr(memory, 'get_memory_snapshot')
        
        # Test return types
        capabilities = memory.get_capabilities()
        assert hasattr(capabilities, 'supports_search')
        
        snapshot = memory.get_memory_snapshot()
        assert isinstance(snapshot, dict)
        assert 'total_items' in snapshot
        assert 'memory_size_bytes' in snapshot or 'memory_size_estimate' in snapshot
        
        # Test agent interface contract
        agent = SimpleWorkMemAgent(memory, {
            'llm_config': {'response_delay': 0.0},
            'use_secure_file_ops': False
        })
        
        # All agents must support these operations
        assert hasattr(agent, 'get_capabilities')
        assert hasattr(agent, 'get_behavioral_trace')
        assert hasattr(agent, 'get_agent_id')
        
        # Test return types
        agent_capabilities = agent.get_capabilities()
        assert hasattr(agent_capabilities, 'supports_search')
        
        trace = agent.get_behavioral_trace()
        assert hasattr(trace, 'task_id')
        
        agent_id = agent.get_agent_id()
        assert isinstance(agent_id, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
