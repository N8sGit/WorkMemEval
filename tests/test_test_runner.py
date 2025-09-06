#!/usr/bin/env python3
"""
Unit tests for the TestRunner component.
"""

import sys
import textwrap
from pathlib import Path

import pytest

from src.evaluation.test_runner import PytestRunner


class TestPytestRunner:
    def test_passing_test_file(self, tmp_path: Path):
        # Create a simple passing pytest file
        test_file = tmp_path / "test_ok.py"
        test_file.write_text(
            textwrap.dedent(
                """
                def test_ok():
                    assert 1 + 1 == 2
                """
            )
        )

        runner = PytestRunner()
        result = runner.run(str(test_file.name), cwd=tmp_path)

        assert result.passed is True
        assert result.exit_code == 0
        assert result.duration_s >= 0
        assert isinstance(result.stdout_tail, str)
        assert result.errors == []

    def test_failing_test_file(self, tmp_path: Path):
        # Create a simple failing pytest file
        test_file = tmp_path / "test_fail.py"
        test_file.write_text(
            textwrap.dedent(
                """
                def test_fail():
                    assert False
                """
            )
        )

        runner = PytestRunner()
        result = runner.run(str(test_file.name), cwd=tmp_path)

        assert result.passed is False
        assert result.exit_code != 0
        assert result.duration_s >= 0
        assert isinstance(result.stdout_tail, str)
        assert isinstance(result.errors, list)

