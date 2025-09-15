#!/usr/bin/env python3
"""
Unit tests for repository template materialization and loader parsing.
"""

from pathlib import Path

from src.evaluation.runner import BasicWorkMemEvalRunner, TaskSpecificationLoader


def test_loader_parses_repository_and_planning(tmp_path: Path):
    # Copy the existing task JSON to a temp dir
    repo_root = Path.cwd()
    src_task = repo_root / "tasks" / "calculator_demo.json"
    dst_task = tmp_path / "task.json"
    dst_task.write_text(src_task.read_text())

    loader = TaskSpecificationLoader()
    task_spec = loader.load_task(dst_task)

    assert task_spec.repository.template_name == "calculator_demo"
    assert task_spec.planning_phase.overview_prompt


def test_materialize_repository(tmp_path: Path):
    # Materialize the calculator_demo template
    runner = BasicWorkMemEvalRunner()
    runner._materialize_repository("calculator_demo", tmp_path)

    # Verify expected files exist
    assert (tmp_path / "calculator.py").exists()
    assert (tmp_path / "tests" / "test_calculator_cp1.py").exists()
    assert (tmp_path / "tests" / "test_calculator_cp2.py").exists()
    assert (tmp_path / "tests" / "test_calculator_cp3.py").exists()
