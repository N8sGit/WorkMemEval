"""
Secure File Operations for WorkMemEval Agents

Provides controlled file I/O with strict path validation and access controls
to safely allow agents to perform real file operations within sandboxed directories.
"""

import os
import re
from pathlib import Path
from typing import Optional, List, Set
import logging

logger = logging.getLogger(__name__)


class SecurityViolationError(Exception):
    """Raised when an agent attempts an unauthorized file operation"""
    pass


class SecureFileOperations:
    """
    Secure file operations manager that restricts agent access to designated directories
    with comprehensive validation and logging.
    """
    
    def __init__(self, allowed_base_path: Path, max_file_size: int = 1024 * 1024):
        """
        Initialize secure file operations.
        
        Args:
            allowed_base_path: Base directory where agent can operate
            max_file_size: Maximum file size in bytes (default 1MB)
        """
        self.allowed_base_path = Path(allowed_base_path).resolve()
        self.max_file_size = max_file_size
        
        # Ensure base path exists
        self.allowed_base_path.mkdir(parents=True, exist_ok=True)
        
        # Dangerous file patterns to block
        self.blocked_patterns = {
            r'\.\./',  # Directory traversal
            r'__pycache__',  # Python cache
            r'\.git/',  # Git directory
            r'\.env',  # Environment files
            r'config\.py$',  # Config files
            r'settings\.py$',  # Settings files
            r'/etc/',  # System configs
            r'/usr/',  # System binaries
            r'/home/.*\.ssh/',  # SSH keys
            r'\.key$',  # Private keys
            r'\.pem$',  # Certificates
        }
        
        # Allowed file extensions
        self.allowed_extensions = {
            '.py', '.txt', '.md', '.json', '.yaml', '.yml',
            '.csv', '.log', '.cfg', '.ini'
        }
        
        logger.info(f"SecureFileOperations initialized for {self.allowed_base_path}")
    
    def _validate_path(self, file_path: str) -> Path:
        """
        Validate and resolve a file path, ensuring it's within allowed boundaries.
        
        Args:
            file_path: Path to validate
            
        Returns:
            Resolved Path object
            
        Raises:
            SecurityViolationError: If path is invalid or outside allowed area
        """
        try:
            # Convert to Path and resolve
            path = Path(file_path)
            
            # If relative, make it relative to allowed base
            if not path.is_absolute():
                path = self.allowed_base_path / path
            
            # Resolve to handle any .. or symlinks
            resolved_path = path.resolve()
            
            # Ensure it's within allowed base path
            try:
                resolved_path.relative_to(self.allowed_base_path)
            except ValueError:
                raise SecurityViolationError(
                    f"Path {file_path} is outside allowed directory {self.allowed_base_path}"
                )
            
            # Check against blocked patterns
            path_str = str(resolved_path)
            for pattern in self.blocked_patterns:
                if re.search(pattern, path_str):
                    raise SecurityViolationError(
                        f"Path {file_path} matches blocked pattern: {pattern}"
                    )
            
            # Check file extension
            if resolved_path.suffix and resolved_path.suffix not in self.allowed_extensions:
                raise SecurityViolationError(
                    f"File extension {resolved_path.suffix} not allowed"
                )
            
            return resolved_path
            
        except Exception as e:
            if isinstance(e, SecurityViolationError):
                raise
            raise SecurityViolationError(f"Invalid path {file_path}: {e}")
    
    def read_file(self, file_path: str) -> str:
        """
        Safely read a file within the allowed directory.
        
        Args:
            file_path: Path to file to read
            
        Returns:
            File contents as string
            
        Raises:
            SecurityViolationError: If path is invalid
            FileNotFoundError: If file doesn't exist
            OSError: If file can't be read
        """
        validated_path = self._validate_path(file_path)
        
        if not validated_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not validated_path.is_file():
            raise SecurityViolationError(f"Path is not a file: {file_path}")
        
        # Check file size
        size = validated_path.stat().st_size
        if size > self.max_file_size:
            raise SecurityViolationError(
                f"File {file_path} too large: {size} bytes (max {self.max_file_size})"
            )
        
        logger.info(f"Reading file: {validated_path}")
        
        with open(validated_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def write_file(self, file_path: str, content: str, append: bool = False) -> None:
        """
        Safely write to a file within the allowed directory.
        
        Args:
            file_path: Path to file to write
            content: Content to write
            append: Whether to append (True) or overwrite (False)
            
        Raises:
            SecurityViolationError: If path is invalid or content too large
            OSError: If file can't be written
        """
        validated_path = self._validate_path(file_path)
        
        # Check content size
        content_size = len(content.encode('utf-8'))
        if content_size > self.max_file_size:
            raise SecurityViolationError(
                f"Content too large: {content_size} bytes (max {self.max_file_size})"
            )
        
        # Ensure parent directory exists
        validated_path.parent.mkdir(parents=True, exist_ok=True)
        
        mode = 'a' if append else 'w'
        logger.info(f"Writing file: {validated_path} (mode: {mode})")
        
        with open(validated_path, mode, encoding='utf-8') as f:
            f.write(content)
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists within the allowed directory.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            validated_path = self._validate_path(file_path)
            return validated_path.exists() and validated_path.is_file()
        except SecurityViolationError:
            return False
    
    def list_files(self, directory_path: str = ".") -> List[str]:
        """
        List files in a directory within the allowed area.
        
        Args:
            directory_path: Directory to list (relative to allowed base)
            
        Returns:
            List of file paths relative to allowed base
        """
        try:
            validated_path = self._validate_path(directory_path)
            
            if not validated_path.exists():
                return []
            
            if not validated_path.is_dir():
                raise SecurityViolationError(f"Path is not a directory: {directory_path}")
            
            files = []
            for item in validated_path.iterdir():
                if item.is_file():
                    # Return path relative to the directory being listed
                    if directory_path == ".":
                        # For root directory, return relative to base
                        rel_path = item.relative_to(self.allowed_base_path)
                    else:
                        # For subdirectories, return just the filename
                        rel_path = item.name
                    files.append(str(rel_path))
            
            return sorted(files)
            
        except SecurityViolationError as e:
            logger.warning(f"Security violation in list_files: {e}")
            return []
    
    def delete_file(self, file_path: str) -> bool:
        """
        Safely delete a file within the allowed directory.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            True if file was deleted, False if it didn't exist
            
        Raises:
            SecurityViolationError: If path is invalid
        """
        validated_path = self._validate_path(file_path)
        
        if not validated_path.exists():
            return False
        
        if not validated_path.is_file():
            raise SecurityViolationError(f"Path is not a file: {file_path}")
        
        logger.info(f"Deleting file: {validated_path}")
        validated_path.unlink()
        return True
    
    def get_allowed_base_path(self) -> Path:
        """Get the allowed base path for this secure file operations instance"""
        return self.allowed_base_path
