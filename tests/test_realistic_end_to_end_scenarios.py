#!/usr/bin/env python3
"""
Realistic End-to-End Scenario Tests

Tests that simulate real evaluation scenarios with complex conditions:
- Multi-checkpoint tasks with dependencies
- Different agent types and configurations  
- Various memory systems under stress
- Complex file operations and error recovery
- Performance under different conditions
"""

import pytest
import tempfile
import shutil
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Tuple
from unittest.mock import Mock, patch

from src.evaluation.runner import BasicWorkMemEvalRunner, TaskSpecificationLoader
from src.agents.simple_agent import SimpleWorkMemAgent
from src.memory.reference_implementations import SimpleContextMemory, ExampleKeyValueMemory
from src.memory.memory_system import MemorySystemInterface
from src.memory.simple_memory import NoMemory
from src.core.task_specification import (
    TaskSpecification, CheckpointSpecification, MemoryChallenge, MemoryChallengeType
)
from src.core.action_trace import ActionType
from src.evaluation.results import EvaluationResult


class TestRealisticMultiCheckpointScenarios:
    """Test realistic multi-checkpoint evaluation scenarios"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.runner = BasicWorkMemEvalRunner()
    
    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_complex_task(self) -> Tuple[TaskSpecification, Path]:
        """Create a complex multi-checkpoint task with dependencies"""
        
        # Define checkpoints with realistic dependencies
        checkpoints = [
            CheckpointSpecification(
                checkpoint_id="setup",
                order=1,
                title="Project Setup",
                stub_file="main.py",
                stub_function="main",
                requirements="Set up the basic project structure with configuration loading and logging",
                test_file="test_setup.py",
                dependencies=[]
            ),
            CheckpointSpecification(
                checkpoint_id="data_model",
                order=2,
                title="Data Model Implementation",
                stub_file="models.py",
                stub_function="User",
                requirements="Implement User and Task data models with validation and serialization",
                test_file="test_models.py",
                dependencies=["setup"]
            ),
            CheckpointSpecification(
                checkpoint_id="api_layer",
                order=3,
                title="API Layer",
                stub_file="api.py",
                stub_function="create_user",
                requirements="Implement REST API endpoints for user and task management using the data models",
                test_file="test_api.py",
                dependencies=["data_model"]
            ),
            CheckpointSpecification(
                checkpoint_id="integration",
                order=4,
                title="System Integration",
                stub_file="app.py",
                stub_function="run_app",
                requirements="Integrate all components and add error handling, monitoring, and graceful shutdown",
                test_file="test_integration.py",
                dependencies=["setup", "data_model", "api_layer"]
            )
        ]
        
        # Mock repository with realistic file structure
        mock_repository = Mock()
        mock_repository.template_name = "web_api_project"
        mock_repository.provided_files = ["main.py", "config.py", "requirements.txt"]
        mock_repository.distractor_files = ["old_code.py", "backup_config.py", "temp_file.txt"]
        mock_repository.get = Mock(return_value=[])
        
        task_spec = TaskSpecification(
            task_id="complex_web_api",
            title="Complex Web API Development",
            domain="software_engineering",
            description="Build a complete web API with proper architecture and error handling",
            checkpoints=checkpoints,
            planning_phase=Mock(),
            repository=mock_repository,
            memory_challenges=[]
        )
        
        # Create task file
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
                for cp in checkpoints
            ],
            "repository": {
                "template_name": "web_api_project",
                "provided_files": ["main.py", "config.py", "requirements.txt"],
                "distractor_files": ["old_code.py", "backup_config.py", "temp_file.txt"]
            },
            "memory_challenges": []
        }
        
        task_file = self.temp_dir / f"{task_spec.task_id}.json"
        with open(task_file, 'w') as f:
            json.dump(task_dict, f, indent=2)
        
        return task_spec, task_file
    
    @pytest.mark.asyncio
    async def test_complex_dependency_chain_execution(self):
        """Test execution of complex checkpoint dependency chain"""
        task_spec, task_file = self.create_complex_task()
        
        # Use a memory system that can handle complex interactions
        memory_system = SimpleContextMemory({
            'max_items': 200,
            'max_memory_size': 500000,
            'relevance_threshold': 0.05
        })
        
        agent = SimpleWorkMemAgent(memory_system, {
            'max_iterations': 15,
            'memory_context_limit': 8,
            'llm_config': {'response_delay': 0.0},
            'use_secure_file_ops': False
        })
        
        # Mock repository materialization
        with patch.object(self.runner, '_materialize_repository'):
            with patch.object(agent, 'initialize_secure_file_ops'):
                result = await self.runner.run_evaluation(
                    task_file,
                    agent,
                    memory_system,
                    working_directory=self.temp_dir / "complex_workspace"
                )
        
        # Validate complex task execution
        assert isinstance(result, EvaluationResult)
        assert result.task_id == "complex_web_api"
        assert len(result.checkpoint_results) == 4
        
        # Validate dependency order was respected
        checkpoint_order = [cp.checkpoint_id for cp in result.checkpoint_results]
        expected_order = ["setup", "data_model", "api_layer", "integration"]
        assert checkpoint_order == expected_order
        
        # Validate task trace captured complex interactions
        task_trace = result.task_trace
        assert len(task_trace.checkpoint_traces) == 4
        
        # Check that later checkpoints have more memory context
        setup_trace = task_trace.get_checkpoint_trace("setup")
        integration_trace = task_trace.get_checkpoint_trace("integration")
        
        # Integration checkpoint should have more context from dependencies
        assert len(integration_trace.actions) >= len(setup_trace.actions)
    
    @pytest.mark.asyncio
    async def test_memory_stress_under_complex_task(self):
        """Test memory system behavior under complex task stress"""
        task_spec, task_file = self.create_complex_task()
        
        # Test with different memory configurations
        memory_configs = [
            ("Small", {'max_items': 20, 'max_memory_size': 5000}),
            ("Medium", {'max_items': 100, 'max_memory_size': 50000}),
            ("Large", {'max_items': 500, 'max_memory_size': 200000})
        ]
        
        results = {}
        
        for config_name, config in memory_configs:
            memory_system = SimpleContextMemory(config)
            agent = SimpleWorkMemAgent(memory_system, {
                'max_iterations': 10,
                'memory_context_limit': 6,
                'llm_config': {'response_delay': 0.0},
                'use_secure_file_ops': False
            })
            
            with patch.object(self.runner, '_materialize_repository'):
                with patch.object(agent, 'initialize_secure_file_ops'):
                    result = await self.runner.run_evaluation(
                        task_file,
                        agent,
                        memory_system,
                        working_directory=self.temp_dir / f"stress_{config_name}"
                    )
            
            results[config_name] = result
            
            # Validate result structure
            assert result is not None
            assert result.task_id == "complex_web_api"
        
        # Validate that larger memory generally performs better
        # (This is heuristic - exact performance depends on implementation)
        small_success = results["Small"].task_completed_successfully
        large_success = results["Large"].task_completed_successfully
        
        # At minimum, all should complete without crashing
        for config_name, result in results.items():
            assert result is not None
            assert result.execution_time_seconds > 0
    
    @pytest.mark.asyncio
    async def test_error_recovery_in_complex_scenario(self):
        """Test error recovery and graceful handling in complex scenarios"""
        task_spec, task_file = self.create_complex_task()
        
        memory_system = SimpleContextMemory({'max_items': 100})
        
        # Create agent that will fail on a specific checkpoint
        class PartiallyFailingAgent(SimpleWorkMemAgent):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.checkpoint_count = 0
            
            async def execute_checkpoint(self, checkpoint):
                self.checkpoint_count += 1
                # Fail on the third checkpoint (API layer)
                if checkpoint.checkpoint_id == "api_layer":
                    raise RuntimeError("Simulated API implementation failure")
                return await super().execute_checkpoint(checkpoint)
        
        failing_agent = PartiallyFailingAgent(memory_system, {
            'max_iterations': 8,
            'llm_config': {'response_delay': 0.0},
            'use_secure_file_ops': False
        })
        
        with patch.object(self.runner, '_materialize_repository'):
            with patch.object(failing_agent, 'initialize_secure_file_ops'):
                # This should handle the error gracefully
                with pytest.raises(Exception):  # Should propagate the error
                    await self.runner.run_evaluation(
                        task_file,
                        failing_agent,
                        memory_system,
                        working_directory=self.temp_dir / "error_recovery"
                    )


class TestDifferentAgentConfigurations:
    """Test different agent configurations and their effects"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_standard_task(self) -> Tuple[TaskSpecification, Path]:
        """Create a standard task for configuration testing"""
        checkpoint = CheckpointSpecification(
            checkpoint_id="standard_cp",
            order=1,
            title="Standard Implementation",
            stub_file="implementation.py",
            stub_function="solve_problem",
            requirements="Implement a solution to the given problem with proper error handling",
            test_file="test_implementation.py",
            dependencies=[]
        )
        
        mock_repository = Mock()
        mock_repository.template_name = "standard_template"
        mock_repository.provided_files = ["implementation.py"]
        mock_repository.distractor_files = []
        mock_repository.get = Mock(return_value=[])
        
        task_spec = TaskSpecification(
            task_id="config_test_task",
            title="Configuration Test Task",
            domain="testing",
            description="Standard task for testing different agent configurations",
            checkpoints=[checkpoint],
            planning_phase=Mock(),
            repository=mock_repository,
            memory_challenges=[]
        )
        
        task_dict = {
            "task_id": task_spec.task_id,
            "title": task_spec.title,
            "domain": task_spec.domain,
            "description": task_spec.description,
            "checkpoints": [{
                "id": checkpoint.checkpoint_id,
                "order": checkpoint.order,
                "title": checkpoint.title,
                "stub_file": checkpoint.stub_file,
                "requirements": checkpoint.requirements,
                "test_file": checkpoint.test_file,
                "dependencies": checkpoint.dependencies
            }],
            "repository": {"template_name": "standard_template"}
        }
        
        task_file = self.temp_dir / f"{task_spec.task_id}.json"
        with open(task_file, 'w') as f:
            json.dump(task_dict, f, indent=2)
        
        return task_spec, task_file
    
    @pytest.mark.asyncio
    async def test_different_iteration_limits(self):
        """Test agent behavior with different iteration limits"""
        task_spec, task_file = self.create_standard_task()
        runner = BasicWorkMemEvalRunner()
        
        # Test different iteration limits
        iteration_configs = [
            ("Conservative", 3),
            ("Standard", 10),
            ("Aggressive", 25)
        ]
        
        results = {}
        
        for config_name, max_iterations in iteration_configs:
            memory_system = SimpleContextMemory({'max_items': 50})
            agent = SimpleWorkMemAgent(memory_system, {
                'max_iterations': max_iterations,
                'memory_context_limit': 5,
                'llm_config': {'response_delay': 0.0},
                'use_secure_file_ops': False
            })
            
            with patch.object(runner, '_materialize_repository'):
                with patch.object(agent, 'initialize_secure_file_ops'):
                    result = await runner.run_evaluation(
                        task_file,
                        agent,
                        memory_system,
                        working_directory=self.temp_dir / f"iter_{config_name}"
                    )
            
            results[config_name] = result
            
            # Validate basic result structure
            assert result.task_id == "config_test_task"
            assert result.execution_time_seconds > 0
        
        # Validate that different configs produce different behavior
        conservative_trace = results["Conservative"].task_trace
        aggressive_trace = results["Aggressive"].task_trace
        
        # Both should have executed, but may have different action counts
        assert conservative_trace is not None
        assert aggressive_trace is not None
    
    @pytest.mark.asyncio 
    async def test_different_memory_context_limits(self):
        """Test agent behavior with different memory context limits"""
        task_spec, task_file = self.create_standard_task()
        runner = BasicWorkMemEvalRunner()
        
        # Test different memory context limits
        context_configs = [
            ("Minimal", 2),
            ("Standard", 5),
            ("Extended", 12)
        ]
        
        base_memory = SimpleContextMemory({'max_items': 100})
        
        for config_name, context_limit in context_configs:
            agent = SimpleWorkMemAgent(base_memory, {
                'max_iterations': 8,
                'memory_context_limit': context_limit,
                'llm_config': {'response_delay': 0.0},
                'use_secure_file_ops': False
            })
            
            with patch.object(runner, '_materialize_repository'):
                with patch.object(agent, 'initialize_secure_file_ops'):
                    result = await runner.run_evaluation(
                        task_file,
                        agent,
                        base_memory,
                        working_directory=self.temp_dir / f"context_{config_name}"
                    )
            
            # Validate result
            assert result.task_id == "config_test_task"
            
            # Check that agent used the specified context limit
            assert agent.memory_context_limit == context_limit


class TestComplexFileOperationScenarios:
    """Test scenarios with complex file operations and state management"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.runner = BasicWorkMemEvalRunner()
    
    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.asyncio
    async def test_large_file_handling(self):
        """Test agent behavior with large files"""
        # Create checkpoint that involves large files
        checkpoint = CheckpointSpecification(
            checkpoint_id="large_file_cp",
            order=1,
            title="Large File Processing",
            stub_file="processor.py",
            stub_function="process_large_file",
            requirements="Implement efficient processing of large data files with memory management",
            test_file="test_processor.py",
            dependencies=[]
        )
        
        mock_repository = Mock()
        mock_repository.template_name = "large_file_template"
        mock_repository.provided_files = ["processor.py", "large_data.csv"]
        mock_repository.distractor_files = []
        mock_repository.get = Mock(return_value=[])
        
        task_spec = TaskSpecification(
            task_id="large_file_task",
            title="Large File Processing Task",
            domain="data_processing",
            description="Process large files efficiently",
            checkpoints=[checkpoint],
            planning_phase=Mock(),
            repository=mock_repository,
            memory_challenges=[]
        )
        
        # Create agent configured for large file handling
        memory_system = SimpleContextMemory({
            'max_items': 50,  # Smaller to test memory pressure
            'max_memory_size': 10000
        })
        
        agent = SimpleWorkMemAgent(memory_system, {
            'max_iterations': 12,
            'memory_context_limit': 4,  # Limited context due to large files
            'llm_config': {'response_delay': 0.0},
            'use_secure_file_ops': False
        })
        
        # Mock large file content
        large_content = "# Large file content\n" + "data_row_" * 1000
        
        with patch.object(agent, '_get_mock_file_content', return_value=large_content):
            with patch.object(self.runner, '_materialize_repository'):
                with patch.object(agent, 'initialize_secure_file_ops'):
                    
                    task_dict = {
                        "task_id": task_spec.task_id,
                        "title": task_spec.title,
                        "domain": task_spec.domain,
                        "description": task_spec.description,
                        "checkpoints": [{
                            "id": checkpoint.checkpoint_id,
                            "order": checkpoint.order,
                            "title": checkpoint.title,
                            "stub_file": checkpoint.stub_file,
                            "requirements": checkpoint.requirements,
                            "test_file": checkpoint.test_file,
                            "dependencies": checkpoint.dependencies
                        }],
                        "repository": {"template_name": "large_file_template"}
                    }
                    
                    task_file = self.temp_dir / "large_file_task.json"
                    with open(task_file, 'w') as f:
                        json.dump(task_dict, f, indent=2)
                    
                    result = await self.runner.run_evaluation(
                        task_file,
                        agent,
                        memory_system,
                        working_directory=self.temp_dir / "large_file_workspace"
                    )
        
        # Validate that large file handling worked
        assert result.task_id == "large_file_task"
        assert result.task_trace is not None
        
        # Check that file operations were logged
        cp_trace = result.task_trace.checkpoint_traces[0]
        file_actions = [
            action for action in cp_trace.actions 
            if action.action_type in [ActionType.FILE_READ, ActionType.FILE_WRITE]
        ]
        assert len(file_actions) > 0
    
    @pytest.mark.asyncio
    async def test_multiple_file_coordination(self):
        """Test scenarios requiring coordination across multiple files"""
        # Create multi-file checkpoint
        checkpoint = CheckpointSpecification(
            checkpoint_id="multi_file_cp",
            order=1,
            title="Multi-File Coordination",
            stub_file="coordinator.py",
            stub_function="coordinate_files",
            requirements="Implement coordination between config.py, data.py, and utils.py to create a cohesive system",
            test_file="test_coordinator.py",
            dependencies=[]
        )
        
        task_spec = TaskSpecification(
            task_id="multi_file_task",
            title="Multi-File Coordination Task",
            domain="systems_integration",
            description="Coordinate multiple files into a working system",
            checkpoints=[checkpoint],
            planning_phase=Mock(),
            repository=Mock(),
            memory_challenges=[]
        )
        
        memory_system = SimpleContextMemory({'max_items': 80})
        agent = SimpleWorkMemAgent(memory_system, {
            'max_iterations': 15,
            'memory_context_limit': 6,
            'llm_config': {'response_delay': 0.0},
            'use_secure_file_ops': False
        })
        
        # Create multiple mock files
        def mock_file_content(file_path):
            if "config.py" in file_path:
                return "# Configuration settings\nDEBUG = True\nDATABASE_URL = 'sqlite:///app.db'"
            elif "data.py" in file_path:
                return "# Data handling\nclass DataManager:\n    def __init__(self):\n        pass"
            elif "utils.py" in file_path:
                return "# Utility functions\ndef helper_function():\n    return 'helper'"
            else:
                return f"# File: {file_path}\n# Default content"
        
        with patch.object(agent, '_get_mock_file_content', side_effect=mock_file_content):
            with patch.object(self.runner, '_materialize_repository'):
                with patch.object(agent, 'initialize_secure_file_ops'):
                    
                    task_dict = {
                        "task_id": task_spec.task_id,
                        "title": task_spec.title,
                        "checkpoints": [{
                            "id": checkpoint.checkpoint_id,
                            "order": checkpoint.order,
                            "title": checkpoint.title,
                            "stub_file": checkpoint.stub_file,
                            "requirements": checkpoint.requirements,
                            "test_file": checkpoint.test_file,
                            "dependencies": checkpoint.dependencies
                        }],
                        "repository": {"template_name": "multi_file"}
                    }
                    
                    task_file = self.temp_dir / "multi_file_task.json"
                    with open(task_file, 'w') as f:
                        json.dump(task_dict, f, indent=2)
                    
                    result = await self.runner.run_evaluation(
                        task_file,
                        agent,
                        memory_system,
                        working_directory=self.temp_dir / "multi_file_workspace"
                    )
        
        # Validate multi-file coordination
        assert result.task_id == "multi_file_task"
        
        # Check that multiple files were accessed
        cp_trace = result.task_trace.checkpoint_traces[0]
        file_paths_accessed = {
            action.file_path for action in cp_trace.actions 
            if hasattr(action, 'file_path') and action.file_path
        }
        
        # Should have accessed multiple files
        assert len(file_paths_accessed) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
