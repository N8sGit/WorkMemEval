"""
WorkMemEval: Evaluation Framework

Main evaluation components for orchestrating task execution and results analysis.
"""

from .runner import BasicWorkMemEvalRunner, TaskSpecificationLoader
from .results import EvaluationResult, CheckpointResult, ComparisonResult

__all__ = [
    'BasicWorkMemEvalRunner',
    'TaskSpecificationLoader', 
    'EvaluationResult',
    'CheckpointResult',
    'ComparisonResult'
]
