"""
Tests for YAML Task Loader and Models

Tests the YAML task configuration infrastructure including validation,
error handling, and schema compliance.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from pydantic import ValidationError

from src.core.yaml_task_models import (
    YAMLTaskSpecification, 
    MemoryDimensions, 
    MemoryProbe, 
    EvaluationConfig,
    TaskValidationError,
    MemoryProbeType,
    TaskDomain,
    TaskDifficulty
)
from src.core.yaml_task_loader import TaskLoader, load_yaml_task


class TestYAMLTaskModels:
    """Test YAML task model validation"""
    
    def test_valid_task_specification(self):
        """Test that a valid task specification passes validation"""
        valid_task_data = {
            "task_id": "test_task_001",
            "title": "Test Task for Validation",
            "domain": "distributed_systems",
            "difficulty": "intermediate",
            "description": "This is a test task description that is long enough to pass validation requirements.",
            "checkpoints": [
                {
                    "id": "cp1",
                    "title": "Checkpoint 1",
                    "order": 1,
                    "stub_file": "src/main.py",
                    "requirements": "Implement the main function",
                    "test_file": "tests/test_main.py"
                }
            ],
            "memory_dimensions": {
                "information_density": 500,
                "temporal_span": 30,
                "context_switches": 2,
                "dependency_depth": 3
            },
            "success_criteria": [
                "System must handle requests correctly",
                "Performance should meet specified requirements",
                "Error handling must be implemented properly"
            ],
            "memory_probes": [
                {
                    "type": "n_back_recall",
                    "trigger_at_minute": 15,
                    "target_information": "initial_requirements",
                    "description": "Test recall of initial requirements"
                }
            ],
            "evaluation_config": {
                "max_duration_minutes": 45,
                "allow_external_memory": True,
                "track_context_usage": True
            }
        }
        
        task_spec = YAMLTaskSpecification(**valid_task_data)
        assert task_spec.task_id == "test_task_001"
        assert task_spec.domain == TaskDomain.DISTRIBUTED_SYSTEMS
        assert task_spec.difficulty == TaskDifficulty.INTERMEDIATE
        assert len(task_spec.memory_probes) == 1
        assert task_spec.memory_probes[0].type == MemoryProbeType.N_BACK_RECALL
    
    def test_invalid_task_id(self):
        """Test that invalid task IDs are rejected"""
        invalid_data = {
            "task_id": "Invalid Task ID!",  # Contains spaces and special chars
            "title": "Test Task",
            "domain": "distributed_systems",
            "difficulty": "intermediate",
            "description": "Test description that is long enough for validation.",
            "memory_dimensions": {
                "information_density": 500,
                "temporal_span": 30,
                "context_switches": 2,
                "dependency_depth": 3
            },
            "success_criteria": [
                "Must work correctly",
                "Should handle errors properly",
                "Will meet performance requirements"
            ]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            YAMLTaskSpecification(**invalid_data)
        
        assert "task_id" in str(exc_info.value)
    
    def test_memory_dimensions_validation(self):
        """Test memory dimensions validation"""
        # Test information density too low
        with pytest.raises(ValidationError) as exc_info:
            MemoryDimensions(
                information_density=50,  # Too low
                temporal_span=30,
                context_switches=2,
                dependency_depth=3
            )
        # Pydantic's built-in validation now runs first
        assert "greater than or equal to 100" in str(exc_info.value)
        
        # Test temporal span too high
        with pytest.raises(ValidationError) as exc_info:
            MemoryDimensions(
                information_density=500,
                temporal_span=200,  # Too high
                context_switches=2,
                dependency_depth=3
            )
        # Pydantic's built-in validation now runs first
        assert "less than or equal to 180" in str(exc_info.value)
    
    def test_memory_probe_validation(self):
        """Test memory probe validation"""
        # Test n_back_recall probe without target_information
        with pytest.raises(ValidationError) as exc_info:
            MemoryProbe(
                type="n_back_recall",
                trigger_at_minute=15,
                description="Test probe without target information"
                # Missing target_information
            )
        assert "target_information" in str(exc_info.value)
        
        # Test context_switch probe without required fields
        with pytest.raises(ValidationError) as exc_info:
            MemoryProbe(
                type="context_switch",
                trigger_at_minute=20,
                description="Test context switch probe"
                # Missing interruption_task and duration_minutes
            )
        assert "interruption_task" in str(exc_info.value)
    
    def test_success_criteria_validation(self):
        """Test success criteria validation"""
        task_data = {
            "task_id": "test_task_002",
            "title": "Test Task for Success Criteria",
            "domain": "web_services",
            "difficulty": "beginner",
            "description": "Test task for validating success criteria requirements.",
            "memory_dimensions": {
                "information_density": 200,
                "temporal_span": 20,
                "context_switches": 1,
                "dependency_depth": 2
            },
            "success_criteria": [
                "Short",  # Too short
                "Another short one"  # Also too short
            ]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            YAMLTaskSpecification(**task_data)
        
        # The list length validation runs first in Pydantic v2
        assert "at least 3 items" in str(exc_info.value)


class TestTaskLoader:
    """Test YAML task loader functionality"""
    
    def test_load_valid_yaml_task(self):
        """Test loading a valid YAML task file"""
        valid_task_yaml = """
task_id: distributed_cache_001
title: Distributed Cache Implementation
domain: distributed_systems
difficulty: intermediate
description: |
  Implement a distributed caching system that handles node failures gracefully.
  The system should support consistent hashing, replication, and automatic failover.
  
checkpoints:
  - id: cp1
    title: Initial Setup
    order: 1
    stub_file: cache.py
    requirements: "Setup basic cache structure"
    test_file: tests/test_cache.py

memory_dimensions:
  information_density: 600  # Within intermediate range (300-800)
  temporal_span: 45
  context_switches: 3
  dependency_depth: 4

success_criteria:
  - "Cache operations (GET/PUT/DELETE) must work correctly under normal conditions"
  - "System must handle node failures without data loss"
  - "Performance must degrade gracefully under increasing load"
  - "Configuration must be maintainable and well-documented"

memory_probes:
  - type: n_back_recall
    trigger_at_minute: 25
    target_information: initial_architecture_decisions
    description: "Recall the key architectural decisions made in the first 10 minutes"
  
  - type: context_switch
    trigger_at_minute: 30
    interruption_task: debug_authentication_service_issue
    duration_minutes: 8
    description: "Handle unrelated debugging task, then resume cache implementation"

evaluation_config:
  max_duration_minutes: 60
  context_window_limit: 8192
  allow_external_memory: true
  track_context_usage: true
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(valid_task_yaml)
            temp_path = f.name
        
        try:
            loader = TaskLoader(strict_mode=True)
            task_spec = loader.load_task(temp_path)
            
            assert task_spec.task_id == "distributed_cache_001"
            assert task_spec.domain == TaskDomain.DISTRIBUTED_SYSTEMS
            assert task_spec.difficulty == TaskDifficulty.INTERMEDIATE
            assert len(task_spec.memory_probes) == 2
            assert task_spec.evaluation_config.context_window_limit == 8192
            
        finally:
            Path(temp_path).unlink()
    
    def test_load_invalid_yaml_syntax(self):
        """Test handling of invalid YAML syntax"""
        invalid_yaml = """
task_id: test_task
title: Test Task
domain: distributed_systems
difficulty: intermediate
description: Test description that is long enough for validation requirements
memory_dimensions:
  information_density: 500
  temporal_span: 30
  context_switches: 2
  dependency_depth: 3
success_criteria:
  - "Valid criterion that must work correctly"
  - "Another valid criterion that should work properly"
  - "Third criterion that must work properly"
  - Invalid criterion without quotes and [brackets
    causing YAML parsing error due to unmatched bracket
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name
        
        try:
            loader = TaskLoader(strict_mode=True)
            with pytest.raises(TaskValidationError) as exc_info:
                loader.load_task(temp_path)
            
            assert "YAML parsing error" in str(exc_info.value)
            
        finally:
            Path(temp_path).unlink()
    
    def test_load_missing_required_fields(self):
        """Test handling of missing required fields"""
        incomplete_yaml = """
task_id: test_task
title: Test Task
# Missing domain, difficulty, description, memory_dimensions, success_criteria, checkpoints
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(incomplete_yaml)
            temp_path = f.name
        
        try:
            loader = TaskLoader(strict_mode=True)
            with pytest.raises(TaskValidationError) as exc_info:
                loader.load_task(temp_path)
            
            assert "Missing required fields" in str(exc_info.value)
            assert "domain" in str(exc_info.value)
            
        finally:
            Path(temp_path).unlink()
    
    def test_file_not_found(self):
        """Test handling of non-existent files"""
        loader = TaskLoader()
        
        with pytest.raises(FileNotFoundError):
            loader.load_task("non_existent_file.yaml")
    
    def test_non_yaml_extension(self):
        """Test rejection of files without YAML extension"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("task_id: test")
            temp_path = f.name
        
        try:
            loader = TaskLoader()
            with pytest.raises(TaskValidationError) as exc_info:
                loader.load_task(temp_path)
            
            assert "must have .yaml or .yml extension" in str(exc_info.value)
            
        finally:
            Path(temp_path).unlink()
    
    def test_validation_warnings_strict_mode(self):
        """Test that validation warnings cause failure in strict mode"""
        # Create a task with complexity mismatch (beginner difficulty but high complexity)
        warning_task_yaml = """
task_id: warning_test_task
title: Warning Test Task
domain: distributed_systems
difficulty: beginner
description: This task has complexity that doesn't match its beginner difficulty level.
checkpoints:
  - id: cp1
    title: Simple Task
    order: 1
    stub_file: main.py
    requirements: "Do something simple"
    test_file: tests/test_main.py
memory_dimensions:
  information_density: 1500  # Too high for beginner
  temporal_span: 120         # Too long for beginner
  context_switches: 8        # Too many for beginner
  dependency_depth: 6        # Too deep for beginner

success_criteria:
  - "System must work correctly"
  - "Performance should be good"  # Subjective language
  - "Code must be clean and elegant"  # More subjective language

evaluation_config:
  max_duration_minutes: 150
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(warning_task_yaml)
            temp_path = f.name
        
        try:
            # Strict mode should fail with warnings
            strict_loader = TaskLoader(strict_mode=True)
            with pytest.raises(TaskValidationError) as exc_info:
                strict_loader.load_task(temp_path)
            assert "validation failed with warnings" in str(exc_info.value)
            
            # Non-strict mode should succeed but log warnings
            permissive_loader = TaskLoader(strict_mode=False)
            task_spec = permissive_loader.load_task(temp_path)
            assert task_spec.task_id == "warning_test_task"
            assert len(permissive_loader.get_validation_warnings()) > 0
            
        finally:
            Path(temp_path).unlink()


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_load_yaml_task_function(self):
        """Test the load_yaml_task convenience function"""
        simple_yaml = """
task_id: convenience_test
title: Convenience Function Test
domain: web_services
difficulty: beginner
description: Simple task to test the convenience function for loading YAML tasks.
checkpoints:
  - id: cp1
    title: Simple Task
    order: 1
    stub_file: main.py
    requirements: "Do something simple"
    test_file: tests/test_main.py
memory_dimensions:
  information_density: 300  # Within beginner range but meets web_services minimum
  temporal_span: 25         # Meets web_services minimum
  context_switches: 1
  dependency_depth: 2       # Meets web_services minimum
success_criteria:
  - "Function must work correctly"
  - "Task should load successfully"
  - "Validation must pass completely"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(simple_yaml)
            temp_path = f.name
        
        try:
            task_spec = load_yaml_task(temp_path, strict_mode=True)
            assert task_spec.task_id == "convenience_test"
            assert task_spec.domain == TaskDomain.WEB_SERVICES
            
        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__])