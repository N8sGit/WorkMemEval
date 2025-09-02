"""
File path utilities for WorkMemEval.
"""

from pathlib import Path
from typing import Union


def basename(path_str: Union[str, Path]) -> str:
    """
    Safely extract basename from file path.
    
    Args:
        path_str: File path as string or Path object
        
    Returns:
        Base filename
    """
    try:
        return Path(path_str).name
    except Exception:
        return str(path_str)


def normalize_path(path_str: str) -> str:
    """
    Normalize file path for consistent comparison.
    
    Args:
        path_str: File path to normalize
        
    Returns:
        Normalized path string
    """
    try:
        return str(Path(path_str).resolve())
    except Exception:
        return path_str


def validate_file_path(file_path: str) -> bool:
    """
    Validate if a file path is valid and accessible.
    
    Args:
        file_path: Path to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        path = Path(file_path)
        return path.exists() or path.parent.exists()
    except Exception:
        return False
