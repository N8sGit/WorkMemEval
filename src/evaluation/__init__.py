"""
WorkMemEval: Evaluation Framework

Main evaluation components for orchestrating task execution and results analysis.
"""

from .results import CheckpointResult, ComparisonResult, EvaluationResult
from .runner import BasicWorkMemEvalRunner, TaskSpecificationLoader

__all__ = [
    "BasicWorkMemEvalRunner",
    "TaskSpecificationLoader",
    "EvaluationResult",
    "CheckpointResult",
    "ComparisonResult",
]
