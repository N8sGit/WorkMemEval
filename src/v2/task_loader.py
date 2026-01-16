"""
WorkMemEval V2: Task Loader

Load YAML task definitions into Task objects.
Simple, no magic - just YAML parsing with validation.
"""

import yaml
from pathlib import Path
from typing import Union

from .models import Task, Checkpoint, WorkpadCheck, SemanticCheck


def load_task(path: Union[str, Path]) -> Task:
    """
    Load a task definition from a YAML file.
    
    Args:
        path: Path to the YAML task file
        
    Returns:
        Task object ready for execution
        
    Raises:
        FileNotFoundError: If task file doesn't exist
        ValueError: If task definition is invalid
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Task file not found: {path}")
    
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    return parse_task(data, base_path=path.parent)


def load_task_from_string(yaml_content: str) -> Task:
    """Load task from YAML string (useful for testing)."""
    data = yaml.safe_load(yaml_content)
    return parse_task(data)


def parse_task(data: dict, base_path: Path = None) -> Task:
    """
    Parse task dictionary into Task object.
    
    Args:
        data: Dictionary from YAML parsing
        base_path: Base path for resolving relative file paths
        
    Returns:
        Validated Task object
    """
    # Required fields
    if "task_id" not in data:
        raise ValueError("Task must have 'task_id'")
    if "checkpoints" not in data or not data["checkpoints"]:
        raise ValueError("Task must have at least one checkpoint")
    
    # Parse checkpoints
    checkpoints = []
    for cp_data in data["checkpoints"]:
        checkpoint = parse_checkpoint(cp_data)
        checkpoints.append(checkpoint)
    
    # Resolve history file path if provided
    history_file = data.get("history_file")
    if history_file and base_path:
        history_path = base_path / history_file
        if history_path.exists():
            history_file = str(history_path)
    
    return Task(
        task_id=data["task_id"],
        title=data.get("title", data["task_id"]),
        checkpoints=checkpoints,
        template=data.get("template"),
        history_file=history_file,
        history_repeat=data.get("history_repeat", 1),
        history_include_last_n=data.get("history_include_last_n", 10),
        history_truncate_chars_per_msg=data.get("history_truncate_chars_per_msg", 500),
        include_history_every_checkpoint=data.get("include_history_every_checkpoint", False),
        workpad_truncate_chars=data.get("workpad_truncate_chars", 0),
        workpad_visible_in_prompt=data.get("workpad_visible_in_prompt", True),
        workpad_file=data.get("workpad_file", "WORKPAD.md"),
        instructions=data.get("instructions", ""),
        description=data.get("description", ""),
        tags=data.get("tags", []),
    )


def parse_checkpoint(data: dict) -> Checkpoint:
    """Parse checkpoint dictionary into Checkpoint object."""
    if "id" not in data:
        raise ValueError("Checkpoint must have 'id'")
    if "prompt" not in data:
        raise ValueError("Checkpoint must have 'prompt'")
    
    # Parse pattern-based checks
    checks = []
    for check_data in data.get("checks", []):
        check = parse_check(check_data)
        checks.append(check)
    
    # Parse semantic checks (LLM-graded)
    semantic_checks = []
    for sc_data in data.get("semantic_checks", []):
        sc = parse_semantic_check(sc_data)
        semantic_checks.append(sc)
    
    return Checkpoint(
        id=data["id"],
        prompt=data["prompt"],
        checks=checks,
        semantic_checks=semantic_checks,
        inject_files=data.get("inject_files", {}),
    )


def parse_check(data: dict) -> WorkpadCheck:
    """Parse check dictionary into WorkpadCheck object."""
    if "pillar" not in data:
        raise ValueError("Check must have 'pillar'")
    
    pillar = data["pillar"].lower()
    if pillar not in ("fidelity", "relevance", "integrity"):
        raise ValueError(f"Invalid pillar: {pillar}. Must be fidelity, relevance, or integrity")
    
    return WorkpadCheck(
        pillar=pillar,
        must_contain=data.get("must_contain", []),
        must_contain_one_of=data.get("must_contain_one_of", []),
        must_not_contain=data.get("must_not_contain", []),
        regex_patterns=data.get("regex_patterns", []),
        weight=data.get("weight", 1.0),
        description=data.get("description", ""),
    )


def parse_semantic_check(data: dict) -> SemanticCheck:
    """Parse semantic check dictionary into SemanticCheck object."""
    if "pillar" not in data:
        raise ValueError("Semantic check must have 'pillar'")
    if "truth" not in data:
        raise ValueError("Semantic check must have 'truth' (ground truth)")
    
    pillar = data["pillar"].lower()
    if pillar not in ("fidelity", "relevance", "integrity"):
        raise ValueError(f"Invalid pillar: {pillar}")
    
    return SemanticCheck(
        pillar=pillar,
        description=data.get("description", ""),
        truth=data["truth"],
        weight=data.get("weight", 1.0),
    )
