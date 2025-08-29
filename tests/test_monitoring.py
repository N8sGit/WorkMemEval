#!/usr/bin/env python3
"""
Unit tests for FileSystemWatcher snapshot and diff behavior.
"""

from pathlib import Path
import time

from src.evaluation.monitoring import FileSystemWatcher


def test_filesystem_watcher_snapshot_and_diff(tmp_path: Path):
    watcher = FileSystemWatcher()

    # Initial snapshot (empty)
    before = watcher.snapshot(tmp_path)

    # Create files and modify
    f1 = tmp_path / "a.txt"
    f1.write_text("hello")
    f2 = tmp_path / "b.txt"
    f2.write_text("world")

    # Snapshot after creation
    after_create = watcher.snapshot(tmp_path)
    delta = watcher.diff(before, after_create)
    assert str(f1) in delta["created"]
    assert str(f2) in delta["created"]
    assert delta["deleted"] == []

    # Modify one file
    time.sleep(0.01)  # ensure mtime difference
    f1.write_text("hello!!!")
    after_modify = watcher.snapshot(tmp_path)
    delta2 = watcher.diff(after_create, after_modify)
    assert str(f1) in delta2["modified"]

    # Delete one file
    f2.unlink()
    after_delete = watcher.snapshot(tmp_path)
    delta3 = watcher.diff(after_modify, after_delete)
    assert str(f2) in delta3["deleted"]

