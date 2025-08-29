"""
WorkMemEval: Basic Evaluation Runner

Minimal viable evaluation harness for orchestrating task execution,
agent coordination, and result collection.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import shutil

from ..core.task_specification import TaskSpecification, CheckpointSpecification
from ..core.action_trace import ActionTracer, TaskTrace, ActionType
from ..core.plugin_interfaces import AgentImplementation, MemorySystem
from ..evaluation.results import EvaluationResult, CheckpointResult
from ..evaluation.test_runner import TestRunner, TestRunResult
from ..evaluation.monitoring import FileSystemWatcher


class TaskSpecificationLoader:
    """
    Loads and validates task specifications from JSON files.
    """
    
    def __init__(self):
        self.loaded_tasks: Dict[str, TaskSpecification] = {}
    
    def load_task(self, task_path: Path) -> TaskSpecification:
        """
        Load a task specification from a JSON file.
        
        Args:
            task_path: Path to the task JSON file
            
        Returns:
            TaskSpecification object
            
        Raises:
            FileNotFoundError: If task file doesn't exist
            ValueError: If task specification is invalid
        """
        if not task_path.exists():
            raise FileNotFoundError(f"Task file not found: {task_path}")
        
        try:
            with open(task_path, 'r') as f:
                task_data = json.load(f)
            
            task_spec = self._parse_task_json(task_data)
            self._validate_task_spec(task_spec)
            
            # Cache the loaded task
            self.loaded_tasks[task_spec.task_id] = task_spec
            
            return task_spec
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in task file {task_path}: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load task from {task_path}: {e}")
    
    def _parse_task_json(self, task_data: Dict[str, Any]) -> TaskSpecification:
        """Parse JSON data into TaskSpecification object.
        If full schema is present (planning_phase/repository), delegate to TaskSpecification.from_dict;
        otherwise, build a minimal compatible spec for legacy tasks.
        """
        try:
            if 'planning_phase' in task_data and 'repository' in task_data:
                return TaskSpecification.from_dict(task_data)
        except Exception:
            # Fall through to legacy minimal parse
            pass

        from unittest.mock import Mock

        # Legacy minimal parse
        checkpoints = []
        for i, cp_data in enumerate(task_data.get('checkpoints', [])):
            checkpoint = CheckpointSpecification(
                checkpoint_id=cp_data.get('id', f'checkpoint_{i}'),
                order=cp_data.get('order', i + 1),
                title=cp_data.get('title', f'Checkpoint {i+1}'),
                stub_file=cp_data.get('stub_file', 'main.py'),
                stub_function=cp_data.get('stub_function', 'main'),
                requirements=cp_data.get('requirements', ''),
                test_file=cp_data.get('test_file', 'test_main.py'),
                dependencies=cp_data.get('dependencies', [])
            )
            checkpoints.append(checkpoint)

        task_spec = TaskSpecification(
            task_id=task_data.get('task_id', 'unknown_task'),
            title=task_data.get('title', 'Unknown Task'),
            domain=task_data.get('domain', 'general'),
            description=task_data.get('description', ''),
            checkpoints=checkpoints,
            planning_phase=Mock(),
            repository=Mock(),
            memory_challenges=task_data.get('memory_challenges', [])
        )
        return task_spec
    
    def _validate_task_spec(self, task_spec: TaskSpecification):
        """Validate that task specification is complete and valid"""
        if not task_spec.task_id:
            raise ValueError("Task must have a task_id")
        
        if not task_spec.checkpoints:
            raise ValueError("Task must have at least one checkpoint")
        
        # Validate checkpoint dependencies
        checkpoint_ids = {cp.checkpoint_id for cp in task_spec.checkpoints}
        for checkpoint in task_spec.checkpoints:
            for dep_id in checkpoint.dependencies:
                if dep_id not in checkpoint_ids:
                    raise ValueError(f"Checkpoint {checkpoint.checkpoint_id} depends on unknown checkpoint {dep_id}")


class BasicWorkMemEvalRunner:
    """
    Basic evaluation runner that orchestrates task execution and result collection.
    
    This is the minimal viable evaluation harness that coordinates:
    - Task loading and validation
    - Agent and memory system initialization
    - Checkpoint progression
    - Action tracing and result collection
    """
    
    def __init__(self, containerized: bool = False, docker_image: Optional[str] = None):
        self.task_loader = TaskSpecificationLoader()
        self.current_evaluation: Optional[Dict[str, Any]] = None
        if containerized:
            try:
                from ..evaluation.docker_test_runner import DockerTestRunner
                self.test_runner = DockerTestRunner(image=docker_image)
            except Exception as e:
                print(f"Warning: failed to initialize DockerTestRunner, falling back to local TestRunner: {e}")
                self.test_runner = TestRunner()
        else:
            self.test_runner = TestRunner()
        self.fs_watcher = FileSystemWatcher()
    
    async def run_evaluation(
        self,
        task_path: Path,
        agent: AgentImplementation,
        memory_system: MemorySystem,
        working_directory: Optional[Path] = None
    ) -> EvaluationResult:
        """
        Run a complete evaluation of an agent on a task.
        
        Args:
            task_path: Path to task JSON specification
            agent: Agent implementation to evaluate
            memory_system: Memory system for the agent
            working_directory: Directory for task execution (optional)
            
        Returns:
            Complete evaluation results
        """
        # Load and validate task
        task_spec = self.task_loader.load_task(task_path)
        
        # Set up working directory
        if working_directory is None:
            working_directory = Path.cwd() / "evaluation_workspace" / task_spec.task_id
        working_directory.mkdir(parents=True, exist_ok=True)

        # Materialize repository template if provided
        try:
            template_name = getattr(task_spec.repository, 'template_name', None)
            if template_name and isinstance(template_name, str):
                self._materialize_repository(template_name, working_directory)
        except Exception as e:
            print(f"Warning: failed to materialize repository template: {e}")
        
        # Initialize action tracer
        action_tracer = ActionTracer(task_spec.task_id)
        
        # Start evaluation
        evaluation_start = time.time()
        print(f"Starting evaluation: {task_spec.title}")
        print(f"Task ID: {task_spec.task_id}")
        print(f"Checkpoints: {len(task_spec.checkpoints)}")
        print(f"Working directory: {working_directory}")
        
        try:
            # Set up evaluation context
            self.current_evaluation = {
                'task_spec': task_spec,
                'agent': agent,
                'memory_system': memory_system,
                'working_directory': working_directory,
                'action_tracer': action_tracer,
                'start_time': evaluation_start
            }
            
            # Execute the task
            success, checkpoint_results = await self._execute_task(
                task_spec, agent, action_tracer, working_directory
            )
            
            # Get behavioral trace
            task_trace = agent.get_behavioral_trace()
            
            # Create evaluation result
            evaluation_result = EvaluationResult(
                task_id=task_spec.task_id,
                agent_name=agent.__class__.__name__,
                memory_system_name=memory_system.__class__.__name__,
                task_completed_successfully=success,
                execution_time_seconds=time.time() - evaluation_start,
                task_trace=task_trace,
                checkpoint_results=checkpoint_results,
                working_memory_metrics=self._calculate_basic_metrics(task_trace)
            )
            
            # Persist results to evaluation_runs/{task_id}/{timestamp}.json
            try:
                ts_str = time.strftime('%Y%m%dT%H%M%S', time.localtime(evaluation_result.timestamp))
                results_root = Path.cwd() / 'evaluation_runs' / task_spec.task_id
                results_root.mkdir(parents=True, exist_ok=True)
                out_path = results_root / f"{ts_str}.json"
                import json
                with open(out_path, 'w') as f:
                    json.dump(evaluation_result.to_dict(), f, indent=2)
                print(f"Results written to {out_path}")
            except Exception as persist_err:
                print(f"Warning: failed to persist results: {persist_err}")
            
            print(f"Evaluation completed: {'SUCCESS' if success else 'FAILED'}")
            print(f"Execution time: {evaluation_result.execution_time_seconds:.2f}s")
            
            return evaluation_result
            
        except Exception as e:
            print(f"Evaluation failed with error: {e}")
            raise
        finally:
            self.current_evaluation = None
    
    async def _execute_task(
        self,
        task_spec: TaskSpecification,
        agent: AgentImplementation,
        action_tracer: ActionTracer,
        working_directory: Path
    ) -> Tuple[bool, List[CheckpointResult]]:
        """
        Execute the complete task with checkpoint progression.
        
        Args:
            task_spec: Task to execute
            agent: Agent to run the task
            action_tracer: Action tracer for logging
            working_directory: Working directory for execution
            
        Returns:
            True if task completed successfully
        """
        print(f"\n=== Executing Task: {task_spec.title} ===")
        
        # Set up the agent's action tracer
        agent.action_tracer = action_tracer
        
        # Initialize secure file operations for the agent
        if hasattr(agent, 'initialize_secure_file_ops'):
            agent.initialize_secure_file_ops(working_directory)
        
        # Store initial task context (delegate to agent)
        agent._store_task_context(task_spec)
        
        # Track per-checkpoint results
        checkpoint_results: List[CheckpointResult] = []
        
        # Execute each checkpoint in sequence with proper orchestration
        for checkpoint in task_spec.checkpoints:
            print(f"\n--- Executing Checkpoint: {checkpoint.checkpoint_id} ---")
            
            # Start checkpoint tracing
            action_tracer.start_checkpoint(checkpoint.checkpoint_id)
            action_tracer.log_action(
                ActionType.CHECKPOINT_START,
                success=True,
                title=checkpoint.title
            )

            # File system snapshot before execution
            snapshot_before = self.fs_watcher.snapshot(working_directory)
            
            try:
                # Execute the checkpoint (properly awaited)
                checkpoint_success = await agent.execute_checkpoint(checkpoint)
                
                # After agent work, run tests for this checkpoint
                cmd_display = f"pytest -q {checkpoint.test_file}"
                test_start = time.time()
                test_result = self.test_runner.run(checkpoint.test_file, cwd=working_directory)
                test_duration_ms = int(test_result.duration_s * 1000)
                
                # Log command execution
                action_tracer.log_action(
                    ActionType.COMMAND_EXECUTE,
                    success=(test_result.exit_code == 0),
                    duration_ms=test_duration_ms,
                    command=cmd_display,
                    exit_code=test_result.exit_code
                )
                
                # Log test run
                action_tracer.log_action(
                    ActionType.TEST_RUN,
                    success=test_result.passed,
                    duration_ms=test_duration_ms,
                    test_file=checkpoint.test_file,
                    exit_code=test_result.exit_code
                )
                
                # Compute file system delta and log a context snapshot
                snapshot_after = self.fs_watcher.snapshot(working_directory)
                fs_delta = self.fs_watcher.diff(snapshot_before, snapshot_after)
                files_in_context = fs_delta.get('created', []) + fs_delta.get('modified', [])
                action_tracer.log_context_snapshot(
                    files_in_context=files_in_context,
                    working_directory=str(working_directory),
                    created=fs_delta.get('created', []),
                    modified=fs_delta.get('modified', []),
                    deleted=fs_delta.get('deleted', []),
                    created_count=len(fs_delta.get('created', [])),
                    modified_count=len(fs_delta.get('modified', [])),
                    deleted_count=len(fs_delta.get('deleted', [])),
                )

                # Log checkpoint completion before closing the trace, so it's captured in the checkpoint
                action_tracer.log_action(
                    ActionType.CHECKPOINT_COMPLETE,
                    success=test_result.passed,
                    tests_passed=test_result.passed
                )
                
                # Complete the checkpoint trace using tests_passed as the completion criteria
                action_tracer.complete_checkpoint(tests_passed=test_result.passed)
                
                # Retrieve the checkpoint trace to compute actions/files
                cp_trace = agent.get_behavioral_trace().get_checkpoint_trace(checkpoint.checkpoint_id)
                actions_taken = len(cp_trace.actions) if cp_trace else 0
                files_accessed = []
                if cp_trace:
                    files_accessed = list(cp_trace.get_file_access_pattern().keys())
                
                # Build a real checkpoint result
                checkpoint_results.append(
                    CheckpointResult(
                        checkpoint_id=checkpoint.checkpoint_id,
                        completed_successfully=test_result.passed,
                        execution_time_seconds=test_result.duration_s,
                        tests_passed=test_result.passed,
                        actions_taken=actions_taken,
                        files_accessed=files_accessed,
                        errors_encountered=test_result.errors,
                    )
                )
                
                if test_result.passed:
                    print(f"✅ Checkpoint {checkpoint.checkpoint_id} tests passed")
                else:
                    print(f"❌ Checkpoint {checkpoint.checkpoint_id} tests failed (exit {test_result.exit_code})")
                
            except Exception as e:
                print(f"❌ Checkpoint {checkpoint.checkpoint_id} failed with error: {e}")
                action_tracer.log_action(
                    ActionType.ERROR_ENCOUNTERED,
                    success=False,
                    error_message=str(e)
                )
                action_tracer.complete_checkpoint(tests_passed=False)
                checkpoint_results.append(
                    CheckpointResult(
                        checkpoint_id=checkpoint.checkpoint_id,
                        completed_successfully=False,
                        execution_time_seconds=0.0,
                        tests_passed=False,
                        actions_taken=0,
                        files_accessed=[],
                        errors_encountered=[str(e)],
                    )
                )
                # Continue to next checkpoint for observability rather than early exit
                
        # Task success is defined as all checkpoint tests passing
        success = all(cp.tests_passed for cp in checkpoint_results) if checkpoint_results else False
        
        if success:
            print("✅ All checkpoints completed successfully (tests passed)")
        else:
            print("⚠️  One or more checkpoints failed tests")
        
        return success, checkpoint_results
    
    def _create_checkpoint_results(
        self,
        task_spec: TaskSpecification,
        task_trace: TaskTrace
    ) -> List[CheckpointResult]:
        """
        Deprecated: Checkpoint results are now built during execution.
        This method remains for compatibility and returns an empty list.
        """
        return []

    def _materialize_repository(self, template_name: str, working_directory: Path) -> None:
        """Copy template directory into working directory.
        Looks for templates/{template_name} under current working directory.
        """
        templates_root = Path.cwd() / 'templates'
        src = templates_root / template_name
        if not src.exists():
            raise FileNotFoundError(f"Template not found: {src}")
        # Copy contents of src into working_directory
        for path in src.rglob('*'):
            rel = path.relative_to(src)
            dest = working_directory / rel
            if path.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
    
    def _calculate_basic_metrics(self, task_trace: TaskTrace) -> Dict[str, float]:
        """
        Calculate working memory metrics using the metrics module.
        """
        try:
            from ..evaluation import metrics
            task_spec = self.current_evaluation.get('task_spec') if self.current_evaluation else None
            if task_spec is None:
                return {}
            return metrics.compute_all_metrics(task_spec, task_trace)
        except Exception:
            # Fallback to empty metrics on failure
            return {}
