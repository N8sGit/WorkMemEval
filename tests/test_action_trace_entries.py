"""
Integration tests for ActionTraceEntry field validation and metrics data availability.

Tests that the SimpleWorkMemAgent properly populates action trace entries
with the correct data types and values needed for memory metrics calculations.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock

from src.agents.simple_agent import SimpleWorkMemAgent
from src.memory.reference_implementations import SimpleContextMemory
from src.core.action_trace import ActionTracer, ActionType
from src.core.task_specification import CheckpointSpecification


class TestActionTraceEntryFieldValidation:
    """Test that action trace entries have correct field types and values"""
    
    def setup_method(self):
        """Setup for each test"""
        self.memory = SimpleContextMemory({'max_items': 100})
        self.agent = SimpleWorkMemAgent(self.memory, {
            'llm_config': {'response_delay': 0.0},
            'use_secure_file_ops': False  # Use mock mode for testing
        })
        self.tracer = ActionTracer("test_task")
        self.agent.action_tracer = self.tracer
    
    def test_file_read_action_entry_fields(self):
        """Test that file read actions populate action trace entry fields correctly"""
        # Start a checkpoint so actions get logged
        self.tracer.start_checkpoint("test_checkpoint")
        
        # Create a file to read
        self.agent._create_file("test_read.py", "print('hello')")
        
        # Read the file - this should log a FILE_READ action
        success = self.agent._read_file("test_read.py")
        assert success is True
        
        # Complete the checkpoint so actions get added to task trace
        self.tracer.complete_checkpoint(True)
        
        # Get the task trace and find the FILE_READ action
        task_trace = self.tracer.get_task_trace()
        
        # Get all actions from all checkpoint traces
        all_actions = []
        for checkpoint_trace in task_trace.checkpoint_traces:
            all_actions.extend(checkpoint_trace.actions)
        
        read_actions = [
            action for action in all_actions 
            if action.action_type == ActionType.FILE_READ
        ]
        
        assert len(read_actions) >= 1
        read_action = read_actions[-1]  # Get the most recent read action
        
        # Validate field types and values
        assert isinstance(read_action.success, bool)
        assert read_action.success is True
        assert isinstance(read_action.file_path, str)
        assert read_action.file_path == "test_read.py"
        assert 'size_bytes' in read_action.metadata
        assert isinstance(read_action.metadata['size_bytes'], int)
        assert read_action.metadata['size_bytes'] > 0
    
    def test_file_write_action_entry_fields(self):
        """Test that file write actions populate action trace entry fields correctly"""
        # Start a checkpoint so actions get logged
        self.tracer.start_checkpoint("test_checkpoint")
        
        # Create a file - this should log a FILE_WRITE action
        test_content = "def hello():\n    print('world')\n"
        success = self.agent._create_file("test_write.py", test_content)
        assert success is True
        
        # Complete the checkpoint so actions get added to task trace
        self.tracer.complete_checkpoint(True)
        
        # Get the task trace and find the FILE_WRITE action
        task_trace = self.tracer.get_task_trace()
        
        # Get all actions from all checkpoint traces
        all_actions = []
        for checkpoint_trace in task_trace.checkpoint_traces:
            all_actions.extend(checkpoint_trace.actions)
        
        write_actions = [
            action for action in all_actions 
            if action.action_type == ActionType.FILE_WRITE
        ]
        
        assert len(write_actions) >= 1
        write_action = write_actions[-1]  # Get the most recent write action
        
        # Validate field types and values
        assert isinstance(write_action.success, bool)
        assert write_action.success is True
        assert isinstance(write_action.file_path, str)
        assert write_action.file_path == "test_write.py"
        assert 'size_bytes' in write_action.metadata
        assert isinstance(write_action.metadata['size_bytes'], int)
        assert write_action.metadata['size_bytes'] == len(test_content.encode('utf-8'))
        assert 'operation' in write_action.metadata
        assert write_action.metadata['operation'] == 'create'
    
    def test_file_edit_action_entry_fields(self):
        """Test that file edit actions populate action trace entry fields correctly"""
        # Start a checkpoint so actions get logged
        self.tracer.start_checkpoint("test_checkpoint")
        
        # Create a file first
        initial_content = "def initial():\n    pass\n"
        self.agent._create_file("test_edit.py", initial_content)
        
        # Edit the file - this should log another FILE_WRITE action with operation='edit'
        additional_content = "def additional():\n    return 42\n"
        success = self.agent._edit_file("test_edit.py", additional_content)
        assert success is True
        
        # Complete the checkpoint so actions get added to task trace
        self.tracer.complete_checkpoint(True)
        
        # Get the task trace and find the edit FILE_WRITE action
        task_trace = self.tracer.get_task_trace()
        
        # Get all actions from all checkpoint traces
        all_actions = []
        for checkpoint_trace in task_trace.checkpoint_traces:
            all_actions.extend(checkpoint_trace.actions)
        
        write_actions = [
            action for action in all_actions 
            if action.action_type == ActionType.FILE_WRITE
        ]
        
        # Should have at least 2 FILE_WRITE actions (create + edit)
        assert len(write_actions) >= 2
        
        # Find the edit action (has operation='edit' metadata)
        edit_actions = [
            action for action in write_actions
            if action.metadata.get('operation') == 'edit'
        ]
        assert len(edit_actions) >= 1
        edit_action = edit_actions[-1]
        
        # Validate field types and values
        assert isinstance(edit_action.success, bool)
        assert edit_action.success is True
        assert isinstance(edit_action.file_path, str)
        assert edit_action.file_path == "test_edit.py"
        assert 'size_bytes' in edit_action.metadata
        assert isinstance(edit_action.metadata['size_bytes'], int)
        # Size should be initial + additional + newline
        expected_size = len(initial_content.encode('utf-8')) + len(('\n' + additional_content).encode('utf-8'))
        assert edit_action.metadata['size_bytes'] == expected_size
        assert edit_action.metadata['operation'] == 'edit'
    
    def test_error_action_entry_fields(self):
        """Test that error actions populate action trace entry fields correctly"""
        # Start a checkpoint so actions get logged
        self.tracer.start_checkpoint("test_checkpoint")
        
        # Force an error by making the LLM throw an exception
        original_llm = self.agent.llm
        self.agent.llm = Mock()
        self.agent.llm.generate_response.side_effect = RuntimeError("Mock error")
        
        # Try to implement functionality - this should log an ERROR_ENCOUNTERED action
        success = self.agent._implement_functionality("test implementation")
        assert success is False
        
        # Complete the checkpoint so actions get added to task trace
        self.tracer.complete_checkpoint(False)  # Failed due to error
        
        # Get the task trace and find the ERROR_ENCOUNTERED action
        task_trace = self.tracer.get_task_trace()
        
        # Get all actions from all checkpoint traces
        all_actions = []
        for checkpoint_trace in task_trace.checkpoint_traces:
            all_actions.extend(checkpoint_trace.actions)
        
        error_actions = [
            action for action in all_actions 
            if action.action_type == ActionType.ERROR_ENCOUNTERED
        ]
        
        assert len(error_actions) >= 1
        error_action = error_actions[-1]
        
        # Validate field types and values
        assert isinstance(error_action.success, bool)
        assert error_action.success is False
        # file_path should be None for non-file-related errors
        assert error_action.file_path is None
        assert 'error_message' in error_action.metadata
        assert isinstance(error_action.metadata['error_message'], str)
        assert "Mock error" in error_action.metadata['error_message']
        
        # Restore original LLM
        self.agent.llm = original_llm
    
    def test_llm_call_action_entry_fields(self):
        """Test that LLM call actions populate action trace entry fields correctly"""
        # Start a checkpoint so actions get logged
        self.tracer.start_checkpoint("test_checkpoint")
        
        # Call implement functionality - this should log an LLM_CALL action
        success = self.agent._implement_functionality("calculator add function")
        assert success is True
        
        # Complete the checkpoint so actions get added to task trace
        self.tracer.complete_checkpoint(True)
        
        # Get the task trace and find the LLM_CALL action
        task_trace = self.tracer.get_task_trace()
        
        # Get all actions from all checkpoint traces
        all_actions = []
        for checkpoint_trace in task_trace.checkpoint_traces:
            all_actions.extend(checkpoint_trace.actions)
        
        llm_actions = [
            action for action in all_actions 
            if action.action_type == ActionType.LLM_CALL
        ]
        
        assert len(llm_actions) >= 1
        llm_action = llm_actions[-1]
        
        # Validate field types and values
        assert isinstance(llm_action.success, bool)
        assert llm_action.success is True
        # file_path should be None for LLM calls
        assert llm_action.file_path is None
        assert 'description' in llm_action.metadata
        assert isinstance(llm_action.metadata['description'], str)
        assert llm_action.metadata['description'] == "calculator add function"
        assert 'response_length' in llm_action.metadata
        assert isinstance(llm_action.metadata['response_length'], int)
        assert llm_action.metadata['response_length'] > 0
    
    def test_planning_action_entry_fields(self):
        """Test that planning actions populate action trace entry fields correctly"""
        # Start a checkpoint so actions get logged
        self.tracer.start_checkpoint("test_checkpoint")
        
        # Create a checkpoint and plan its execution
        checkpoint = CheckpointSpecification(
            checkpoint_id="test_plan",
            order=1,
            title="Test Planning",
            stub_file="test_plan.py",
            stub_function="test_function",
            requirements="Test planning checkpoint",
            test_file="test_plan_test.py",
            dependencies=[]
        )
        
        context = {'retrieved_items': []}
        plan = self.agent._plan_checkpoint_execution(checkpoint, context)
        
        # Complete the checkpoint so actions get added to task trace
        self.tracer.complete_checkpoint(True)
        
        # Get the task trace and find the PLANNING action
        task_trace = self.tracer.get_task_trace()
        
        # Get all actions from all checkpoint traces
        all_actions = []
        for checkpoint_trace in task_trace.checkpoint_traces:
            all_actions.extend(checkpoint_trace.actions)
        
        planning_actions = [
            action for action in all_actions 
            if action.action_type == ActionType.PLANNING
        ]
        
        assert len(planning_actions) >= 1
        planning_action = planning_actions[-1]
        
        # Validate field types and values
        assert isinstance(planning_action.success, bool)
        assert planning_action.success is True
        # file_path should be None for planning actions
        assert planning_action.file_path is None
        assert 'plan' in planning_action.metadata
        assert isinstance(planning_action.metadata['plan'], list)
        assert len(planning_action.metadata['plan']) > 0
        assert 'checkpoint_id' in planning_action.metadata
        assert planning_action.metadata['checkpoint_id'] == "test_plan"


class TestActionTraceEntryMetricsDataAvailability:
    """Test that action trace entries provide data needed for metrics calculations"""
    
    def setup_method(self):
        """Setup for each test"""
        self.memory = SimpleContextMemory({'max_items': 100})
        self.agent = SimpleWorkMemAgent(self.memory, {
            'llm_config': {'response_delay': 0.0},
            'use_secure_file_ops': False
        })
        self.tracer = ActionTracer("metrics_test_task")
        self.agent.action_tracer = self.tracer
    
    def test_file_reread_data_availability(self):
        """Test that file reread data is available for memory fidelity metrics"""
        # Start a checkpoint so actions get logged
        self.tracer.start_checkpoint("test_checkpoint")
        
        # Create and read the same file multiple times
        self.agent._create_file("reread_test.py", "content")
        self.agent._read_file("reread_test.py")
        self.agent._read_file("reread_test.py")  # This is a re-read
        
        # Complete the checkpoint so actions get added to task trace
        self.tracer.complete_checkpoint(True)
        
        # Get task trace
        task_trace = self.tracer.get_task_trace()
        
        # Check that we can identify file access patterns
        file_accesses = {}
        
        # Get all actions from all checkpoint traces
        all_actions = []
        for checkpoint_trace in task_trace.checkpoint_traces:
            all_actions.extend(checkpoint_trace.actions)
        
        for action in all_actions:
            if action.action_type == ActionType.FILE_READ and action.file_path:
                file_path = action.file_path
                if file_path not in file_accesses:
                    file_accesses[file_path] = []
                file_accesses[file_path].append(action)
        
        # Should have multiple reads of the same file
        assert "reread_test.py" in file_accesses
        assert len(file_accesses["reread_test.py"]) >= 2
        
        # Each read should have proper file_path and success fields
        for read_action in file_accesses["reread_test.py"]:
            assert isinstance(read_action.file_path, str)
            assert read_action.file_path == "reread_test.py"
            assert isinstance(read_action.success, bool)
            assert read_action.success is True
    
    def test_file_size_data_availability(self):
        """Test that file size data is available for size-weighted metrics"""
        # Start a checkpoint so actions get logged
        self.tracer.start_checkpoint("test_checkpoint")
        
        # Create files of different sizes
        small_content = "small"
        large_content = "large content " * 10
        
        self.agent._create_file("small.py", small_content)
        self.agent._create_file("large.py", large_content)
        
        # Complete the checkpoint so actions get added to task trace
        self.tracer.complete_checkpoint(True)
        
        # Get task trace
        task_trace = self.tracer.get_task_trace()
        
        # Find the write actions and check size_bytes metadata
        # Get all actions from all checkpoint traces
        all_actions = []
        for checkpoint_trace in task_trace.checkpoint_traces:
            all_actions.extend(checkpoint_trace.actions)
        
        write_actions = [
            action for action in all_actions 
            if action.action_type == ActionType.FILE_WRITE
        ]
        
        size_data = {}
        for action in write_actions:
            if action.file_path and 'size_bytes' in action.metadata:
                size_data[action.file_path] = action.metadata['size_bytes']
        
        # Should have size data for both files
        assert "small.py" in size_data
        assert "large.py" in size_data
        assert isinstance(size_data["small.py"], int)
        assert isinstance(size_data["large.py"], int)
        assert size_data["small.py"] == len(small_content.encode('utf-8'))
        assert size_data["large.py"] == len(large_content.encode('utf-8'))
        assert size_data["large.py"] > size_data["small.py"]
    
    def test_contextual_relevance_data_availability(self):
        """Test that contextual relevance data is available for precision/recall metrics"""
        # Store some relevant information in memory
        checkpoint = CheckpointSpecification(
            checkpoint_id="context_test",
            order=1,
            title="Context Test",
            stub_file="context.py", 
            stub_function="context_function",
            requirements="requirements with context keyword",
            test_file="test_context.py",
            dependencies=[]
        )
        
        # Execute checkpoint to trigger context retrieval and file operations
        import asyncio
        asyncio.run(self.agent.execute_checkpoint(checkpoint))
        
        # Get task trace
        task_trace = self.tracer.get_task_trace()
        
        # Should have both file accesses and context-based actions
        # Get all actions from all checkpoint traces
        all_actions = []
        for checkpoint_trace in task_trace.checkpoint_traces:
            all_actions.extend(checkpoint_trace.actions)
        
        file_actions = [
            action for action in all_actions
            if action.action_type in [ActionType.FILE_READ, ActionType.FILE_WRITE] 
            and action.file_path is not None
        ]
        
        # Each file action should have proper file_path field for accessed set calculation
        accessed_files = set()
        for action in file_actions:
            assert isinstance(action.file_path, str)
            assert len(action.file_path) > 0
            accessed_files.add(action.file_path)
        
        # Should have accessed files from the checkpoint
        assert len(accessed_files) > 0
        # Based on checkpoint, should include context.py and/or test_context.py
        expected_files = {"context.py", "test_context.py"}
        assert accessed_files.intersection(expected_files)
    
    def test_behavioral_integrity_data_availability(self):
        """Test that behavioral integrity data is available for compliance metrics"""
        # Create a checkpoint that should generate a plan
        checkpoint = CheckpointSpecification(
            checkpoint_id="behavior_test",
            order=1,
            title="Behavior Test",
            stub_file="behavior.py",
            stub_function="behavior_function", 
            requirements="implement behavior function",
            test_file="test_behavior.py",
            dependencies=[]
        )
        
        # Execute checkpoint
        import asyncio
        asyncio.run(self.agent.execute_checkpoint(checkpoint))
        
        # Get task trace
        task_trace = self.tracer.get_task_trace()
        
        # Should have planning actions with plan metadata
        # Get all actions from all checkpoint traces
        all_actions = []
        for checkpoint_trace in task_trace.checkpoint_traces:
            all_actions.extend(checkpoint_trace.actions)
        
        planning_actions = [
            action for action in all_actions
            if action.action_type == ActionType.PLANNING
        ]
        
        assert len(planning_actions) > 0
        planning_action = planning_actions[0]
        assert 'plan' in planning_action.metadata
        assert isinstance(planning_action.metadata['plan'], list)
        
        # Should have file operations that can be compared to plan
        file_actions = [
            action for action in all_actions
            if action.action_type in [ActionType.FILE_READ, ActionType.FILE_WRITE]
            and action.file_path is not None
        ]
        
        # Each file action should have the data needed for plan compliance analysis
        for action in file_actions:
            assert isinstance(action.file_path, str)
            assert isinstance(action.success, bool)
            assert isinstance(action.timestamp, float)
            # Actions should be ordered by timestamp for sequence analysis
        
        # Actions should be chronologically ordered
        timestamps = [action.timestamp for action in all_actions]
        assert timestamps == sorted(timestamps)


if __name__ == "__main__":
    pytest.main([__file__])
