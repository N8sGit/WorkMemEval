"""
Monitoring utilities for WorkMemEval

Includes a simple file system watcher (polling) and a process monitor placeholder.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
import time


@dataclass
class FileSnapshot:
    timestamp: float
    files: Dict[str, Dict[str, float]]  # {path: {"size": int, "mtime": float}}


class FileSystemWatcher:
    def snapshot(self, directory: Path) -> FileSnapshot:
        directory = Path(directory)
        files: Dict[str, Dict[str, float]] = {}
        for p in directory.rglob("*"):
            try:
                if p.is_file():
                    stat = p.stat()
                    files[str(p)] = {"size": stat.st_size, "mtime": stat.st_mtime}
            except FileNotFoundError:
                # File could disappear between rglob and stat; ignore
                continue
        return FileSnapshot(timestamp=time.time(), files=files)

    def diff(self, before: FileSnapshot, after: FileSnapshot) -> Dict[str, List[str]]:
        before_keys = set(before.files.keys())
        after_keys = set(after.files.keys())

        created = sorted(after_keys - before_keys)
        deleted = sorted(before_keys - after_keys)

        modified: List[str] = []
        for path in (before_keys & after_keys):
            b = before.files[path]
            a = after.files[path]
            if b.get("mtime") != a.get("mtime") or b.get("size") != a.get("size"):
                modified.append(path)
        modified.sort()

        return {
            "created": created,
            "deleted": deleted,
            "modified": modified,
        }


class ProcessMonitor:
    """Placeholder for process-level monitoring.

    Currently not used directly because PytestRunner already captures timing and exit code.
    This can be extended later to capture CPU/mem metrics.
    """

    def __init__(self) -> None:
        pass

