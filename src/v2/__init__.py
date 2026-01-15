"""
WorkMemEval V2: Simplified Memory Evaluation

This module provides a streamlined approach to evaluating agent working memory
through the "workpad" pattern - agents maintain a WORKPAD.md file that captures
their understanding, decisions, and recalled information.

Key Components:
- models: Dataclasses for Task, Checkpoint, WorkpadCheck, SemanticCheck
- task_loader: Load YAML task definitions
- assessor: Evaluate workpad content against expected patterns
- semantic_assessor: Optional LLM-based semantic grading
- runner: Execute tasks and collect results
"""

from .models import Task, Checkpoint, WorkpadCheck, SemanticCheck, EvaluationResult, CheckpointResult
from .task_loader import load_task
from .assessor import WorkpadAssessor
from .runner import V2Runner

# Optional: LLM-based semantic assessment
try:
    from .semantic_assessor import SemanticAssessor, HybridAssessor
except ImportError:
    SemanticAssessor = None
    HybridAssessor = None

__all__ = [
    "Task",
    "Checkpoint", 
    "WorkpadCheck",
    "SemanticCheck",
    "EvaluationResult",
    "CheckpointResult",
    "load_task",
    "WorkpadAssessor",
    "SemanticAssessor",
    "HybridAssessor",
    "V2Runner",
]
