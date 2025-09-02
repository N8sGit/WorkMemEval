"""
Validation utilities for WorkMemEval.
"""

from typing import Any, Dict


def validate_metrics_result(result: Dict[str, Any]) -> bool:
    """
    Validate metrics result dictionary structure.
    
    Args:
        result: Metrics result dictionary
        
    Returns:
        True if valid structure
    """
    if not isinstance(result, dict):
        return False
    
    for key, value in result.items():
        if not isinstance(key, str):
            return False
        if not isinstance(value, (int, float)):
            return False
    
    return True


def validate_file_path(file_path: str) -> bool:
    """
    Validate file path string.
    
    Args:
        file_path: File path to validate
        
    Returns:
        True if valid
    """
    return isinstance(file_path, str) and len(file_path.strip()) > 0
