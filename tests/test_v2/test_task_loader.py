"""
Unit tests for task loader.

Tests YAML parsing and validation.
"""

import pytest
import tempfile
from pathlib import Path

from src.v2.task_loader import load_task, load_task_from_string, parse_task
from src.v2.models import Task, Checkpoint, WorkpadCheck


class TestLoadTaskFromString:
    """Tests for loading tasks from YAML strings."""
    
    def test_minimal_task(self):
        yaml_content = """
task_id: test_task
title: Test Task
checkpoints:
  - id: cp1
    prompt: "Do something"
"""
        task = load_task_from_string(yaml_content)
        
        assert task.task_id == "test_task"
        assert task.title == "Test Task"
        assert len(task.checkpoints) == 1
        assert task.checkpoints[0].id == "cp1"
    
    def test_task_with_checks(self):
        yaml_content = """
task_id: test_task
title: Test Task
checkpoints:
  - id: cp1
    prompt: "Record facts"
    checks:
      - pillar: fidelity
        must_contain:
          - "fact1"
          - "fact2"
"""
        task = load_task_from_string(yaml_content)
        
        assert len(task.checkpoints[0].checks) == 1
        check = task.checkpoints[0].checks[0]
        assert check.pillar == "fidelity"
        assert check.must_contain == ["fact1", "fact2"]
    
    def test_task_with_all_check_types(self):
        yaml_content = '''
task_id: test_task
title: Test Task
checkpoints:
  - id: cp1
    prompt: "Test all check types"
    checks:
      - pillar: relevance
        must_contain:
          - "keep"
        must_contain_one_of:
          - "reject"
          - "ignore"
        must_not_contain:
          - "accept blindly"
        regex_patterns:
          - '\\d+ days'
        weight: 2.0
        description: "Test check"
'''
        task = load_task_from_string(yaml_content)
        
        check = task.checkpoints[0].checks[0]
        assert check.must_contain == ["keep"]
        assert check.must_contain_one_of == ["reject", "ignore"]
        assert check.must_not_contain == ["accept blindly"]
        assert check.regex_patterns == ["\\d+ days"]
        assert check.weight == 2.0
        assert check.description == "Test check"
    
    def test_task_with_metadata(self):
        yaml_content = """
task_id: test_task
title: Test Task
description: A test task for testing
template: some_template
history_file: path/to/history.json
workpad_file: NOTES.md
instructions: |
  Follow these instructions
tags:
  - test
  - demo
checkpoints:
  - id: cp1
    prompt: "Do something"
"""
        task = load_task_from_string(yaml_content)
        
        assert task.description == "A test task for testing"
        assert task.template == "some_template"
        assert task.history_file == "path/to/history.json"
        assert task.workpad_file == "NOTES.md"
        assert "Follow these instructions" in task.instructions
        assert task.tags == ["test", "demo"]
    
    def test_multiple_checkpoints(self):
        yaml_content = """
task_id: test_task
title: Test Task
checkpoints:
  - id: cp1
    prompt: "First"
  - id: cp2
    prompt: "Second"
  - id: cp3
    prompt: "Third"
"""
        task = load_task_from_string(yaml_content)
        
        assert len(task.checkpoints) == 3
        assert [cp.id for cp in task.checkpoints] == ["cp1", "cp2", "cp3"]
    
    def test_checkpoint_inject_files(self):
        yaml_content = """
task_id: test_task
title: Test Task
checkpoints:
  - id: cp1
    prompt: "Check injected file"
    inject_files:
      suggestion.md: |
        This is a suggestion
      update.txt: |
        This is an update
"""
        task = load_task_from_string(yaml_content)
        
        inject = task.checkpoints[0].inject_files
        assert "suggestion.md" in inject
        assert "update.txt" in inject
        assert "This is a suggestion" in inject["suggestion.md"]


class TestValidation:
    """Tests for validation errors."""
    
    def test_missing_task_id(self):
        yaml_content = """
title: Test Task
checkpoints:
  - id: cp1
    prompt: "Do something"
"""
        with pytest.raises(ValueError, match="task_id"):
            load_task_from_string(yaml_content)
    
    def test_missing_checkpoints(self):
        yaml_content = """
task_id: test_task
title: Test Task
"""
        with pytest.raises(ValueError, match="checkpoint"):
            load_task_from_string(yaml_content)
    
    def test_empty_checkpoints(self):
        yaml_content = """
task_id: test_task
title: Test Task
checkpoints: []
"""
        with pytest.raises(ValueError, match="checkpoint"):
            load_task_from_string(yaml_content)
    
    def test_checkpoint_missing_id(self):
        yaml_content = """
task_id: test_task
title: Test Task
checkpoints:
  - prompt: "No ID"
"""
        with pytest.raises(ValueError, match="id"):
            load_task_from_string(yaml_content)
    
    def test_checkpoint_missing_prompt(self):
        yaml_content = """
task_id: test_task
title: Test Task
checkpoints:
  - id: cp1
"""
        with pytest.raises(ValueError, match="prompt"):
            load_task_from_string(yaml_content)
    
    def test_invalid_pillar(self):
        yaml_content = """
task_id: test_task
title: Test Task
checkpoints:
  - id: cp1
    prompt: "Test"
    checks:
      - pillar: invalid_pillar
        must_contain: ["test"]
"""
        with pytest.raises(ValueError, match="pillar"):
            load_task_from_string(yaml_content)


class TestLoadFromFile:
    """Tests for loading from actual files."""
    
    def test_load_from_file(self):
        yaml_content = """
task_id: file_test
title: File Test
checkpoints:
  - id: cp1
    prompt: "From file"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            task = load_task(Path(f.name))
            
            assert task.task_id == "file_test"
    
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_task(Path("/nonexistent/path.yaml"))
