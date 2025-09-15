"""
Test Runner for WorkMemEval

Executes pytest for a given test file within a working directory and returns
structured results for integration into the evaluation harness.
"""

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class TestRunResult:
    passed: bool
    duration_s: float
    exit_code: int
    stdout_tail: str
    errors: List[str]


class PytestRunner:
    def __init__(self, tail_chars: int = 2000):
        self.tail_chars = tail_chars

    def run(self, test_file: str, cwd: Path, timeout_s: float = 180) -> TestRunResult:
        """
        Run pytest on the specified test file within the provided working directory.
        """
        cwd = Path(cwd)
        test_path = Path(test_file)

        # Always use relative test path from the working directory
        if test_path.is_absolute():
            # Make it relative to cwd if it's absolute
            try:
                test_path = test_path.relative_to(cwd)
            except ValueError:
                # If we can't make it relative, keep it absolute
                pass

        cmd = ["pytest", "-q", str(test_path)]
        start = time.time()
        try:
            env = os.environ.copy()
            # Ensure Python can import local modules from the working directory
            # Since we're running with cwd=working_directory, PYTHONPATH should be "."
            current_pythonpath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f".:{current_pythonpath}" if current_pythonpath else "."

            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=env,
            )
            duration = time.time() - start
            stdout_tail = (proc.stdout or "")[-self.tail_chars :]
            stderr = proc.stderr or ""
            passed = proc.returncode == 0

            errors: List[str] = []
            if not passed:
                # Simple last-lines extraction from stderr; pytest often prints failures there
                for line in stderr.splitlines()[-100:]:
                    line = line.strip()
                    if line:
                        errors.append(line)

            return TestRunResult(
                passed=passed,
                duration_s=duration,
                exit_code=proc.returncode,
                stdout_tail=stdout_tail,
                errors=errors[:20],
            )
        except subprocess.TimeoutExpired as e:
            duration = time.time() - start
            stdout_tail = getattr(e, "stdout", None) or ""
            return TestRunResult(
                passed=False,
                duration_s=duration,
                exit_code=124,
                stdout_tail=stdout_tail[-self.tail_chars :],
                errors=["Test run timed out"],
            )
