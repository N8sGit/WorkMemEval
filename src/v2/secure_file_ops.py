import logging
import re
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class SecurityViolationError(Exception):
    pass


class SecureFileOperations:
    def __init__(self, allowed_base_path: Path, max_file_size: int = 1024 * 1024):
        self.allowed_base_path = Path(allowed_base_path).resolve()
        self.max_file_size = max_file_size

        self.allowed_base_path.mkdir(parents=True, exist_ok=True)

        self.blocked_patterns = {
            r"\.\./",
            r"__pycache__",
            r"\.git/",
            r"\.env",
            r"config\.py$",
            r"settings\.py$",
            r"/etc/",
            r"/usr/",
            r"/home/.*\.ssh/",
            r"\.key$",
            r"\.pem$",
        }

        self.allowed_extensions = {
            ".py",
            ".txt",
            ".md",
            ".json",
            ".yaml",
            ".yml",
            ".csv",
            ".log",
            ".cfg",
            ".ini",
        }

        logger.info("SecureFileOperations initialized for %s", self.allowed_base_path)

    def _validate_path(self, file_path: str) -> Path:
        try:
            path = Path(file_path)

            if not path.is_absolute():
                path = self.allowed_base_path / path

            resolved_path = path.resolve()

            try:
                resolved_path.relative_to(self.allowed_base_path)
            except ValueError:
                raise SecurityViolationError(
                    f"Path {file_path} is outside allowed directory {self.allowed_base_path}"
                )

            path_str = str(resolved_path)
            for pattern in self.blocked_patterns:
                if re.search(pattern, path_str):
                    raise SecurityViolationError(
                        f"Path {file_path} matches blocked pattern: {pattern}"
                    )

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
        validated_path = self._validate_path(file_path)

        if not validated_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not validated_path.is_file():
            raise SecurityViolationError(f"Path is not a file: {file_path}")

        size = validated_path.stat().st_size
        if size > self.max_file_size:
            raise SecurityViolationError(
                f"File {file_path} too large: {size} bytes (max {self.max_file_size})"
            )

        logger.info("Reading file: %s", validated_path)

        with open(validated_path, "r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, file_path: str, content: str, append: bool = False) -> None:
        validated_path = self._validate_path(file_path)

        content_size = len(content.encode("utf-8"))
        if content_size > self.max_file_size:
            raise SecurityViolationError(
                f"Content too large: {content_size} bytes (max {self.max_file_size})"
            )

        validated_path.parent.mkdir(parents=True, exist_ok=True)

        mode = "a" if append else "w"
        logger.info("Writing file: %s (mode: %s)", validated_path, mode)

        with open(validated_path, mode, encoding="utf-8") as f:
            f.write(content)

    def file_exists(self, file_path: str) -> bool:
        try:
            validated_path = self._validate_path(file_path)
            return validated_path.exists() and validated_path.is_file()
        except SecurityViolationError:
            return False

    def list_files(self, directory_path: str = ".") -> List[str]:
        try:
            validated_path = self._validate_path(directory_path)

            if not validated_path.exists():
                return []

            if not validated_path.is_dir():
                raise SecurityViolationError(f"Path is not a directory: {directory_path}")

            files = []
            for item in validated_path.iterdir():
                if item.is_file():
                    if directory_path == ".":
                        rel_path = item.relative_to(self.allowed_base_path)
                    else:
                        rel_path = item.name
                    files.append(str(rel_path))

            return sorted(files)

        except SecurityViolationError:
            return []

    def delete_file(self, file_path: str) -> bool:
        validated_path = self._validate_path(file_path)
        if not validated_path.exists():
            return False
        if not validated_path.is_file():
            raise SecurityViolationError(f"Path is not a file: {file_path}")
        validated_path.unlink()
        return True
