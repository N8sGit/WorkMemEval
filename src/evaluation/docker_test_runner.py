"""
Docker-based Test Runner for WorkMemEval

Executes pytest inside a hardened Docker container with network disabled by
default, non-root user, read-only root FS, and constrained resources.
"""

import subprocess
import time
from pathlib import Path
from typing import List, Optional

from .test_runner import TestRunResult


class DockerTestRunner:
    def __init__(self, image: Optional[str] = None, tail_chars: int = 2000):
        # Default image matches docker/compose.dev.yml tag
        self.image = image or "workmemeval/eval:local"
        self.tail_chars = tail_chars

    def run(self, test_file: str, cwd: Path, timeout_s: float = 180) -> TestRunResult:
        """
        Run pytest on the specified test file inside a Docker container.
        """
        start = time.time()

        try:
            workspace_host = Path(cwd).resolve()
            test_path = Path(test_file)

            # Map test path to container /workspace
            if not test_path.is_absolute():
                rel_test = test_path
            else:
                try:
                    rel_test = test_path.relative_to(workspace_host)
                except Exception:
                    # Fallback: if absolute but not under workspace, try using name
                    rel_test = Path(test_path.name)

            container_test_path = f"/workspace/{str(rel_test).lstrip('/')}"

            # Determine repo root on host; default to current working directory
            repo_root = Path.cwd().resolve()

            cmd: List[str] = [
                "docker",
                "run",
                "--rm",
                "--user",
                "10001:10001",
                "--read-only",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,nodev,size=64m",
                "--network",
                "none",
                "--cpus",
                "1.0",
                "--memory",
                "2g",
                "--security-opt",
                "no-new-privileges:true",
                "--cap-drop",
                "ALL",
                "-e",
                "PYTHONPATH=/workspace:/app",
                "-e",
                "HOME=/workspace",
                "-v",
                f"{str(workspace_host)}:/workspace:rw",
                "-v",
                f"{str(repo_root)}:/app:ro",
                self.image,
                f"pytest -q {container_test_path}",
            ]

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )

            duration = time.time() - start
            stdout_tail = (proc.stdout or "")[-self.tail_chars :]
            stderr = proc.stderr or ""
            passed = proc.returncode == 0

            errors: List[str] = []
            if not passed:
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
        except FileNotFoundError:
            # docker CLI not found
            duration = time.time() - start
            return TestRunResult(
                passed=False,
                duration_s=duration,
                exit_code=127,
                stdout_tail="",
                errors=["docker not found on PATH"],
            )
        except Exception as e:
            duration = time.time() - start
            return TestRunResult(
                passed=False,
                duration_s=duration,
                exit_code=1,
                stdout_tail="",
                errors=[f"Docker test runner error: {e}"],
            )
