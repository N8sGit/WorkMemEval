#!/usr/bin/env python3
"""
Comprehensive Integration Tests for Runner Orchestration

Tests the complete runner pipeline from task loading through result collection,
including repository materialization, agent execution, checkpoint progression,
and error handling scenarios.
"""

import pytest
import tempfile
import shutil
import json
import time
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch

from src.evaluation.runner import BasicWorkMemEvalRunner, TaskSpecificationLoader
from src.agents.simple_agent import SimpleWorkMemAgent
from src.memory.reference_implementations import SimpleContextMemory, ExampleKeyValueMemory
from src.memory.simple_memory import NoMemory
from src.core.task_specification import (
    TaskSpecification, CheckpointSpecification, MemoryChallenge, MemoryChallengeType
)
from src.core.action_trace import ActionType, ActionTracer
from src.evaluation.results import EvaluationResult


class TestRunnerOrchestrationIntegration:
    """Integration tests for the complete runner orchestration pipeline"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.runner = BasicWorkMemEvalRunner()
        self.memory_system = SimpleContextMemory({'max_items': 100})
        self.agent = SimpleWorkMemAgent(self.memory_system, {
            'max_iterations': 10,
            'memory_context_limit': 5,
            'llm_config': {'response_delay': 0.0},  # No delay for tests
            'use_secure_file_ops': False  # Use mock file ops for testing
        })
    
    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_simple_task_spec(self, task_id: str = "test_task") -> TaskSpecification:
        """Create a simple task specification for testing"""
        checkpoint1 = CheckpointSpecification(
            checkpoint_id="cp1",
            order=1,
            title="Addition Function",
            stub_file="calculator.py",
            stub_function="add",
            requirements="Implement an add(a, b) function",
            test_file="test_calculator_cp1.py",
            dependencies=[]
        )
        
        checkpoint2 = CheckpointSpecification(
            checkpoint_id="cp2",
            order=2,
            title="Multiplication Function", 
            stub_file="calculator.py",
            stub_function="multiply",
            requirements="Implement a multiply(a, b) function",
            test_file="test_calculator_cp2.py",
            dependencies=["cp1"]
        )
        
        # Mock repository
        mock_repository = Mock()
        mock_repository.template_name = "simple_calculator"
        mock_repository.provided_files = ["calculator.py"]
        mock_repository.distractor_files = []
        mock_repository.get = Mock(return_value=[])
        
        return TaskSpecification(
            task_id=task_id,
            title="Test Calculator Task",
            domain="programming",
            description="Test task for integration testing",
            checkpoints=[checkpoint1, checkpoint2],
            planning_phase=Mock(),
            repository=mock_repository,
            memory_challenges=[]
        )
    
    def create_test_task_file(self, task_spec: TaskSpecification) -> Path:
        """Create a test task JSON file"""
        task_file = self.temp_dir / f"{task_spec.task_id}.json"
        
        # Convert to dict format (simplified)
        task_dict = {
            "task_id": task_spec.task_id,
            "title": task_spec.title,
            "domain": task_spec.domain,
            "description": task_spec.description,
            "checkpoints": [
                {
                    "id": cp.checkpoint_id,
                    "order": cp.order,
                    "title": cp.title,
                    "stub_file": cp.stub_file,
                    "stub_function": cp.stub_function,
                    "requirements": cp.requirements,
                    "test_file": cp.test_file,
                    "dependencies": cp.dependencies
                }
                for cp in task_spec.checkpoints
            ],
            "repository": {
                "template_name": "simple_calculator",
                "provided_files": ["calculator.py"]
            },
            "memory_challenges": []
        }
        
        with open(task_file, 'w') as f:
            json.dump(task_dict, f, indent=2)
        
        return task_file
    
    @pytest.mark.asyncio
    async def test_complete_pipeline_success(self):
        """Test complete successful pipeline execution"""
        # Create task specification and file
        task_spec = self.create_simple_task_spec("success_task")
        task_file = self.create_test_task_file(task_spec)
        
        # Mock repository materialization 
        with patch.object(self.runner, '_materialize_repository') as mock_materialize:
            mock_materialize.return_value = True
            
            # Mock agent secure file ops initialization
            with patch.object(self.agent, 'initialize_secure_file_ops'):
                
                # Run evaluation
                result = await self.runner.run_evaluation(
                    task_file, 
                    self.agent, 
                    self.memory_system,
                    working_directory=self.temp_dir
                )
        
        # Validate result structure
        assert isinstance(result, EvaluationResult)
        assert result.task_id == "success_task"
        assert result.agent_name == "SimpleWorkMemAgent"
        assert result.memory_system_name == "SimpleContextMemory"
        assert isinstance(result.execution_time_seconds, float)
        assert result.execution_time_seconds > 0
        
        # Validate task trace was captured
        assert result.task_trace is not None
        assert result.task_trace.task_id == "success_task"
        assert len(result.task_trace.checkpoint_traces) == 2
        
        # Validate checkpoint results
        assert len(result.checkpoint_results) == 2
        for cp_result in result.checkpoint_results:
            assert cp_result.checkpoint_id in ["cp1", "cp2"]
            assert isinstance(cp_result.execution_time_seconds, float)
        
        # Validate working memory metrics were calculated
        assert result.working_memory_metrics is not None
        assert isinstance(result.working_memory_metrics, dict)
    
    @pytest.mark.asyncio
    async def test_task_loading_pipeline(self):
        """Test task loading and validation pipeline"""
        # Test valid task loading
        task_spec = self.create_simple_task_spec("valid_task")
        task_file = self.create_test_task_file(task_spec)
        
        loader = TaskSpecificationLoader()
        loaded_spec = loader.load_task(task_file)
        
        assert loaded_spec.task_id == "valid_task"
        assert loaded_spec.title == "Test Calculator Task"
        assert len(loaded_spec.checkpoints) == 2
        assert loaded_spec.checkpoints[0].checkpoint_id == "cp1"
        assert loaded_spec.checkpoints[1].dependencies == ["cp1"]
    
    @pytest.mark.asyncio 
    async def test_invalid_task_handling(self):
        """Test handling of invalid task specifications"""
        loader = TaskSpecificationLoader()
        
        # Test non-existent file
        with pytest.raises(FileNotFoundError):
            loader.load_task(Path("nonexistent.json"))
        
        # Test invalid JSON
        invalid_json_file = self.temp_dir / "invalid.json"
        invalid_json_file.write_text("{ invalid json }")
        
        with pytest.raises(ValueError, match="Invalid JSON"):
            loader.load_task(invalid_json_file)
        
        # Test missing required fields
        incomplete_task = self.temp_dir / "incomplete.json"
        incomplete_task.write_text(json.dumps({
            "title": "Incomplete Task"
            # Missing task_id and checkpoints
        }))
        
        with pytest.raises(ValueError):
            loader.load_task(incomplete_task)
    
    @pytest.mark.asyncio
    async def test_checkpoint_dependency_validation(self):
        """Test checkpoint dependency validation"""
        # Create task with invalid dependencies
        checkpoint1 = CheckpointSpecification(
            checkpoint_id="cp1",
            order=1,
            title="First",
            stub_file="main.py",
            stub_function="main",
            requirements="Do something",
            test_file="test_main.py",
            dependencies=["nonexistent_cp"]  # Invalid dependency
        )
        
        task_dict = {
            "task_id": "invalid_deps",
            "title": "Invalid Dependencies Task",
            "domain": "test",
            "description": "Task with invalid checkpoint dependencies",
            "checkpoints": [{
                "id": "cp1",
                "order": 1,
                "title": "First",
                "stub_file": "main.py",
                "requirements": "Do something",
                "test_file": "test_main.py",
                "dependencies": ["nonexistent_cp"]
            }],
            "repository": {"template_name": "test"}
        }
        
        task_file = self.temp_dir / "invalid_deps.json"
        with open(task_file, 'w') as f:
            json.dump(task_dict, f)
        
        loader = TaskSpecificationLoader()
        with pytest.raises(ValueError, match="depends on non-existent checkpoint"):
            loader.load_task(task_file)
    
    @pytest.mark.asyncio
    async def test_different_memory_systems(self):
        """Test pipeline with different memory systems"""
        task_spec = self.create_simple_task_spec("memory_test")
        task_file = self.create_test_task_file(task_spec)
        
        # Test with different memory systems
        memory_systems = [
            ("NoMemory", NoMemory({})),
            ("SimpleContextMemory", SimpleContextMemory({'max_items': 50})),
            ("ExampleKeyValueMemory", ExampleKeyValueMemory({}))
        ]
        
        for memory_name, memory_system in memory_systems:
            # Create agent with this memory system
            agent = SimpleWorkMemAgent(memory_system, {
                'max_iterations': 5,
                'memory_context_limit': 3,
                'llm_config': {'response_delay': 0.0},
                'use_secure_file_ops': False
            })
            
            with patch.object(self.runner, '_materialize_repository'):
                with patch.object(agent, 'initialize_secure_file_ops'):
                    # Run evaluation
                    result = await self.runner.run_evaluation(
                        task_file,
                        agent, 
                        memory_system,
                        working_directory=self.temp_dir / f"test_{memory_name}"
                    )
            
            # Validate result
            assert result.memory_system_name == memory_name
            assert result.task_trace is not None
    
    @pytest.mark.asyncio
    async def test_action_tracing_integration(self):
        """Test that action tracing is properly integrated throughout pipeline"""
        task_spec = self.create_simple_task_spec("trace_test")
        task_file = self.create_test_task_file(task_spec)
        
        with patch.object(self.runner, '_materialize_repository'):
            with patch.object(self.agent, 'initialize_secure_file_ops'):
                result = await self.runner.run_evaluation(
                    task_file,
                    self.agent,
                    self.memory_system,
                    working_directory=self.temp_dir
                )
        
        # Validate task trace structure
        task_trace = result.task_trace
        assert task_trace is not None
        assert task_trace.task_id == "trace_test"
        assert len(task_trace.checkpoint_traces) == 2
        
        # Check that actions were logged
        for cp_trace in task_trace.checkpoint_traces:
            assert len(cp_trace.actions) > 0
            
            # Should have various action types
            action_types = {action.action_type for action in cp_trace.actions}
            assert ActionType.PLANNING in action_types or ActionType.LLM_CALL in action_types
            
            # Validate action structure
            for action in cp_trace.actions:
                assert action.timestamp > 0
                assert action.success is not None
    
    @pytest.mark.asyncio
    async def test_working_directory_setup(self):
        """Test working directory setup and cleanup"""
        task_spec = self.create_simple_task_spec("directory_test")
        task_file = self.create_test_task_file(task_spec)
        
        # Test with explicit working directory
        test_workspace = self.temp_dir / "explicit_workspace"
        
        with patch.object(self.runner, '_materialize_repository'):
            with patch.object(self.agent, 'initialize_secure_file_ops'):
                result = await self.runner.run_evaluation(
                    task_file,
                    self.agent,
                    self.memory_system,
                    working_directory=test_workspace
                )
        
        # Validate working directory was created and used
        assert test_workspace.exists()
        assert result.task_trace is not None
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_reporting(self):
        """Test error recovery and proper error reporting"""
        task_spec = self.create_simple_task_spec("error_test")
        task_file = self.create_test_task_file(task_spec)
        
        # Mock agent to raise an error during execution
        error_agent = SimpleWorkMemAgent(self.memory_system, {
            'max_iterations': 1,
            'llm_config': {'response_delay': 0.0},
            'use_secure_file_ops': False
        })
        
        # Patch execute_checkpoint to raise an error
        async def failing_execute_checkpoint(checkpoint):
            raise RuntimeError("Simulated agent failure")
        
        with patch.object(error_agent, 'execute_checkpoint', side_effect=failing_execute_checkpoint):
            with patch.object(self.runner, '_materialize_repository'):
                with patch.object(error_agent, 'initialize_secure_file_ops'):
                    # This should handle the error gracefully and still return results
                    with pytest.raises(Exception):  # Should propagate the error
                        await self.runner.run_evaluation(
                            task_file,
                            error_agent,
                            self.memory_system,
                            working_directory=self.temp_dir
                        )
    
    @pytest.mark.asyncio
    async def test_result_persistence(self):
        """Test that evaluation results are properly persisted"""
        task_spec = self.create_simple_task_spec("persistence_test")
        task_file = self.create_test_task_file(task_spec)
        
        # Create evaluation_runs directory in temp location
        original_cwd = Path.cwd()
        
        try:
            # Temporarily change to temp directory
            import os
            os.chdir(self.temp_dir)
            
            with patch.object(self.runner, '_materialize_repository'):
                with patch.object(self.agent, 'initialize_secure_file_ops'):
                    result = await self.runner.run_evaluation(
                        task_file,
                        self.agent,
                        self.memory_system,
                        working_directory=self.temp_dir / "workspace"
                    )
            
            # Check that results were persisted
            evaluation_runs_dir = self.temp_dir / "evaluation_runs" / "persistence_test"
            assert evaluation_runs_dir.exists()
            
            # Should have at least one result file
            result_files = list(evaluation_runs_dir.glob("*.json"))
            assert len(result_files) >= 1
            
            # Validate result file content
            result_file = result_files[0]
            with open(result_file) as f:
                persisted_result = json.load(f)
            
            assert persisted_result['task_id'] == "persistence_test"
            assert 'task_trace' in persisted_result
            assert 'checkpoint_results' in persisted_result
            
        finally:
            os.chdir(original_cwd)


class TestMemorySystemIntegration:
    """Test memory system integration with the runner"""
    
    @pytest.mark.asyncio
    async def test_memory_system_interface_integration(self):
        """Test that memory system interface is properly integrated"""
        from src.memory.memory_system import MemorySystemInterface
        
        # Create wrapped memory system
        base_memory = SimpleContextMemory({'max_items': 50})
        wrapped_memory = MemorySystemInterface(base_memory)
        
        agent = SimpleWorkMemAgent(wrapped_memory, {
            'max_iterations': 3,
            'llm_config': {'response_delay': 0.0},
            'use_secure_file_ops': False
        })
        
        # Test basic memory operations
        assert wrapped_memory.store("test_key", "test_value", {"context": "test"})
        
        results = wrapped_memory.retrieve("test_value", {})
        assert len(results) > 0
        assert results[0]['key'] == "test_key"
        assert results[0]['value'] == "test_value"
        
        # Test snapshot functionality
        snapshot = wrapped_memory.get_snapshot()
        assert 'total_items' in snapshot
        assert 'interface_metrics' in snapshot


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
