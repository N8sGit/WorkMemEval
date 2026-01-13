"""
WorkMemEval: Basic Evaluation Runner

Minimal viable evaluation harness for orchestrating task execution,
agent coordination, and result collection.
"""

import json
import shutil
import time
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..core.action_trace import ActionTracer, ActionType, TaskTrace
from ..core.plugin_interfaces import AgentImplementation, MemorySystem
from ..core.task_specification import CheckpointSpecification, TaskSpecification
from ..evaluation.monitoring import FileSystemWatcher
from ..evaluation.results import CheckpointResult, EvaluationResult
from ..evaluation.test_runner import PytestRunner


class TaskSpecificationLoader:
    """
    Loads and validates task specifications from JSON files.
    """

    def __init__(self):
        self.loaded_tasks: Dict[str, TaskSpecification] = {}

    def load_task(self, task_path: Path) -> TaskSpecification:
        """
        Load a task specification from a JSON or YAML file.

        Args:
            task_path: Path to the task file (json or yaml)

        Returns:
            TaskSpecification object

        Raises:
            FileNotFoundError: If task file doesn't exist
            ValueError: If task specification is invalid
        """
        if not task_path.exists():
            raise FileNotFoundError(f"Task file not found: {task_path}")

        try:
            # Handle YAML files
            if task_path.suffix.lower() in ['.yaml', '.yml']:
                from ..core.yaml_task_loader import load_yaml_task
                yaml_spec = load_yaml_task(task_path, strict_mode=False)
                task_spec = yaml_spec.to_task_specification(base_path=task_path.parent)
                
                # Auto-enable enhanced mode for YAML tasks since they are modern
                task_spec.enable_enhanced_mode()
                
                self.loaded_tasks[task_spec.task_id] = task_spec
                return task_spec

            # Handle JSON files
            with open(task_path, "r") as f:
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
            if "planning_phase" in task_data and "repository" in task_data:
                return TaskSpecification.from_dict(task_data)
        except Exception:
            # Fall through to legacy minimal parse
            pass

        from unittest.mock import Mock

        # Legacy minimal parse
        checkpoints = []
        for i, cp_data in enumerate(task_data.get("checkpoints", [])):
            checkpoint = CheckpointSpecification(
                checkpoint_id=cp_data.get("id", f"checkpoint_{i}"),
                order=cp_data.get("order", i + 1),
                title=cp_data.get("title", f"Checkpoint {i+1}"),
                stub_file=cp_data.get("stub_file", "main.py"),
                stub_function=cp_data.get("stub_function", "main"),
                requirements=cp_data.get("requirements", ""),
                test_file=cp_data.get("test_file", "test_main.py"),
                dependencies=cp_data.get("dependencies", []),
            )
            checkpoints.append(checkpoint)

        task_spec = TaskSpecification(
            task_id=task_data.get("task_id", "unknown_task"),
            title=task_data.get("title", "Unknown Task"),
            domain=task_data.get("domain", "general"),
            description=task_data.get("description", ""),
            checkpoints=checkpoints,
            planning_phase=Mock(),
            repository=Mock(),
            memory_challenges=task_data.get("memory_challenges", []),
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
                    raise ValueError(
                        f"Checkpoint {checkpoint.checkpoint_id} depends on unknown checkpoint {dep_id}"
                    )


class BasicWorkMemEvalRunner:
    """
    Basic evaluation runner that orchestrates task execution and result collection.

    This is the minimal viable evaluation harness that coordinates:
    - Task loading and validation
    - Agent and memory system initialization
    - Checkpoint progression
    - Action tracing and result collection
    
    Enhanced Features (Tier 2):
    - Memory probe injection and scoring
    - Context window management
    - Three-pillar metrics calculation
    """

    def __init__(self, 
                 containerized: bool = False, 
                 docker_image: Optional[str] = None,
                 enable_enhanced_evaluation: bool = False,
                 context_condition: Optional[str] = None):
        """
        Initialize the evaluation runner.
        
        Args:
            containerized: Use Docker for test execution
            docker_image: Docker image for containerized execution
            enable_enhanced_evaluation: Enable enhanced memory evaluation features
            context_condition: Context window condition ("standardized", "native", "overflow")
        """
        self.task_loader = TaskSpecificationLoader()
        self.current_evaluation: Optional[Dict[str, Any]] = None
        
        # Enhanced evaluation feature flags
        self.enhanced_evaluation_enabled = enable_enhanced_evaluation
        self.context_condition = context_condition
        
        # Initialize enhanced components (will be None if not enabled)
        self.context_window_manager = None
        self.probe_scheduler = None
        
        # Initialize enhanced components if enabled
        if self.enhanced_evaluation_enabled:
            self._initialize_enhanced_components()
        
        if containerized:
            try:
                from ..evaluation.docker_test_runner import DockerTestRunner

                self.test_runner = DockerTestRunner(image=docker_image)
            except Exception as e:
                print(
                    f"Warning: failed to initialize DockerTestRunner, falling back to local PytestRunner: {e}"
                )
                self.test_runner = PytestRunner()
        else:
            self.test_runner = PytestRunner()
        self.fs_watcher = FileSystemWatcher()
    
    def _initialize_enhanced_components(self):
        """Initialize enhanced evaluation components when feature is enabled"""
        try:
            # Import enhanced components (will be implemented in subsequent tasks)
            from .context_window_manager import ContextWindowManager
            from .probe_scheduler import ProbeScheduler
            
            self.context_window_manager = ContextWindowManager()
            self.probe_scheduler = ProbeScheduler()
            print("Enhanced evaluation components initialized")
        except ImportError:
            # Enhanced components not yet available, use placeholder
            self.context_window_manager = None
            self.probe_scheduler = None
            print("Warning: Enhanced evaluation enabled but components not available")

    async def run_evaluation(
        self,
        task_path: Path,
        agent: AgentImplementation,
        memory_system: MemorySystem,
        working_directory: Optional[Path] = None,
        context_condition: Optional[str] = None,
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
        
        # Enable enhanced mode if task has enhanced features or if explicitly enabled
        if self.enhanced_evaluation_enabled or task_spec.is_enhanced_mode():
            task_spec = task_spec.enable_enhanced_mode()
            print(f"Enhanced evaluation mode enabled for task: {task_spec.task_id}")
            
            # Lazy initialize enhanced components if needed
            if not self.context_window_manager or not self.probe_scheduler:
                self._initialize_enhanced_components()
        
        # Override context condition if provided, or use default from task
        effective_context_condition = context_condition or self.context_condition
        if not effective_context_condition:
            if task_spec.context_conditions:
                effective_context_condition = task_spec.context_conditions[0].condition_name
            elif task_spec.is_enhanced_mode():
                effective_context_condition = "native"

        # Set up working directory
        if working_directory is None:
            working_directory = Path.cwd() / "evaluation_workspace" / task_spec.task_id
        working_directory.mkdir(parents=True, exist_ok=True)

        # Materialize repository template if provided
        try:
            template_name = getattr(task_spec.repository, "template_name", None)
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
                "task_spec": task_spec,
                "agent": agent,
                "memory_system": memory_system,
                "working_directory": working_directory,
                "action_tracer": action_tracer,
                "start_time": evaluation_start,
            }

            # Execute the task (enhanced or legacy mode)
            if self.enhanced_evaluation_enabled or task_spec.is_enhanced_mode():
                success, checkpoint_results = await self._execute_enhanced_task(
                    task_spec, agent, action_tracer, working_directory, effective_context_condition
                )
            else:
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
                working_memory_metrics=self._calculate_basic_metrics(task_trace),
            )

            # Persist results to evaluation_runs/{task_id}/{timestamp}.json
            try:
                ts_str = time.strftime(
                    "%Y%m%dT%H%M%S", time.localtime(evaluation_result.timestamp)
                )
                results_root = Path.cwd() / "evaluation_runs" / task_spec.task_id
                results_root.mkdir(parents=True, exist_ok=True)
                out_path = results_root / f"{ts_str}.json"
                import json

                with open(out_path, "w") as f:
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
        working_directory: Path,
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
        if hasattr(agent, "initialize_secure_file_ops"):
            agent.initialize_secure_file_ops(working_directory)

        # Store initial task context (delegate to agent)
        if hasattr(agent, "_store_task_context"):
            agent._store_task_context(task_spec)

        # Track per-checkpoint results
        checkpoint_results: List[CheckpointResult] = []

        # Execute each checkpoint in sequence with proper orchestration
        for checkpoint in task_spec.checkpoints:
            print(f"\n--- Executing Checkpoint: {checkpoint.checkpoint_id} ---")

            # Start checkpoint tracing
            action_tracer.start_checkpoint(checkpoint.checkpoint_id)
            action_tracer.log_action(
                ActionType.CHECKPOINT_START, success=True, title=checkpoint.title
            )

            # File system snapshot before execution
            snapshot_before = self.fs_watcher.snapshot(working_directory)

            try:
                # Execute the checkpoint (properly awaited)
                await agent.execute_checkpoint(checkpoint)

                # After agent work, run tests for this checkpoint
                cmd_display = f"pytest -q {checkpoint.test_file}"
                test_result = self.test_runner.run(
                    checkpoint.test_file, cwd=working_directory
                )
                test_duration_ms = int(test_result.duration_s * 1000)

                # Log command execution
                action_tracer.log_action(
                    ActionType.COMMAND_EXECUTE,
                    success=(test_result.exit_code == 0),
                    duration_ms=test_duration_ms,
                    command=cmd_display,
                    exit_code=test_result.exit_code,
                )

                # Log test run
                action_tracer.log_action(
                    ActionType.TEST_RUN,
                    success=test_result.passed,
                    duration_ms=test_duration_ms,
                    test_file=checkpoint.test_file,
                    exit_code=test_result.exit_code,
                )

                # Compute file system delta and log a context snapshot
                snapshot_after = self.fs_watcher.snapshot(working_directory)
                fs_delta = self.fs_watcher.diff(snapshot_before, snapshot_after)
                files_in_context = fs_delta.get("created", []) + fs_delta.get(
                    "modified", []
                )
                action_tracer.log_context_snapshot(
                    files_in_context=files_in_context,
                    working_directory=str(working_directory),
                    created=fs_delta.get("created", []),
                    modified=fs_delta.get("modified", []),
                    deleted=fs_delta.get("deleted", []),
                    created_count=len(fs_delta.get("created", [])),
                    modified_count=len(fs_delta.get("modified", [])),
                    deleted_count=len(fs_delta.get("deleted", [])),
                )

                # Log checkpoint completion before closing the trace, so it's captured in the checkpoint
                action_tracer.log_action(
                    ActionType.CHECKPOINT_COMPLETE,
                    success=test_result.passed,
                    tests_passed=test_result.passed,
                )

                # Complete the checkpoint trace using tests_passed as the completion criteria
                action_tracer.complete_checkpoint(tests_passed=test_result.passed)

                # Retrieve the checkpoint trace to compute actions/files
                cp_trace = agent.get_behavioral_trace().get_checkpoint_trace(
                    checkpoint.checkpoint_id
                )
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
                    print(
                        f"❌ Checkpoint {checkpoint.checkpoint_id} tests failed (exit {test_result.exit_code})"
                    )

            except Exception as e:
                print(f"❌ Checkpoint {checkpoint.checkpoint_id} failed with error: {e}")
                action_tracer.log_action(
                    ActionType.ERROR_ENCOUNTERED, success=False, error_message=str(e)
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
        success = (
            all(cp.tests_passed for cp in checkpoint_results)
            if checkpoint_results
            else False
        )

        if success:
            print("✅ All checkpoints completed successfully (tests passed)")
        else:
            print("⚠️  One or more checkpoints failed tests")

        return success, checkpoint_results

    async def _execute_enhanced_task(
        self,
        task_spec: TaskSpecification,
        agent: AgentImplementation,
        action_tracer: ActionTracer,
        working_directory: Path,
        context_condition: Optional[str] = None,
    ) -> Tuple[bool, List[CheckpointResult]]:
        """
        Execute task with enhanced evaluation features including:
        - Memory probe injection
        - Context window management
        - Enhanced metrics collection
        """
        print(f"\n=== Executing Enhanced Task: {task_spec.title} ===")
        
        # Initialize context window management
        if self.context_window_manager and context_condition:
            self.context_window_manager.configure_condition(context_condition, agent)
            print(f"Context window condition: {context_condition}")
        
        # Set up the agent's action tracer
        agent.action_tracer = action_tracer

        # Initialize secure file operations for the agent
        if hasattr(agent, "initialize_secure_file_ops"):
            agent.initialize_secure_file_ops(working_directory)

        # Store initial task context (delegate to agent)
        if hasattr(agent, "_store_task_context"):
            agent._store_task_context(task_spec)

        # Track per-checkpoint results
        checkpoint_results: List[CheckpointResult] = []
        
        # Schedule memory probes if available
        scheduled_probes = {}
        if self.probe_scheduler and task_spec.memory_probes:
            scheduled_probes = self.probe_scheduler.schedule_probes(task_spec.memory_probes, task_spec)
            total_probes = sum(len(probes) for probes in scheduled_probes.values())
            print(f"Scheduled {total_probes} memory probes across {len(scheduled_probes)} checkpoints")

        # Execute each checkpoint in sequence with enhanced orchestration
        for checkpoint in task_spec.checkpoints:
            print(f"\n--- Executing Enhanced Checkpoint: {checkpoint.checkpoint_id} ---")

            # Start checkpoint tracing
            action_tracer.start_checkpoint(checkpoint.checkpoint_id)
            action_tracer.log_action(
                ActionType.CHECKPOINT_START, success=True, title=checkpoint.title
            )

            # File system snapshot before execution
            snapshot_before = self.fs_watcher.snapshot(working_directory)
            
            # Initialize enhanced metrics for this checkpoint
            enhanced_metrics = {}
            
            # Context window monitoring
            if self.context_window_manager:
                context_metrics = self.context_window_manager.monitor_context_usage(agent, checkpoint)
                action_tracer.log_action(
                    ActionType.CONTEXT_SNAPSHOT,
                    success=True,
                    context_tokens=context_metrics.current_tokens,
                    context_condition=context_condition,
                    utilization_percentage=context_metrics.utilization_percentage,
                    efficiency_score=context_metrics.efficiency_score,
                    context_state=context_metrics.state.value
                )
                
                # Trigger compression if approaching overflow
                if (context_metrics.state in [context_metrics.state.APPROACHING_LIMIT, context_metrics.state.OVERFLOW] 
                    and hasattr(memory_system, 'compress_context')):
                    compression_result = self.context_window_manager.trigger_compression_event(
                        agent, memory_system, action_tracer
                    )

            try:
                # Inject memory probes if scheduled for this checkpoint
                if checkpoint.checkpoint_id in scheduled_probes:
                    probes = scheduled_probes[checkpoint.checkpoint_id]
                    for probe in probes:
                        probe_response = await self.probe_scheduler.inject_probe_at_checkpoint(
                            probe, agent, action_tracer, checkpoint
                        )
                        # Store probe response in enhanced metrics
                        if "probe_responses" not in enhanced_metrics:
                            enhanced_metrics["probe_responses"] = []
                        enhanced_metrics["probe_responses"].append({
                            "probe_id": probe_response.probe_id,
                            "success": probe_response.success,
                            "score": probe_response.score,
                            "pillar": probe.pillar.value
                        })

                # Execute the checkpoint (properly awaited)
                await agent.execute_checkpoint(checkpoint)

                # After agent work, run tests for this checkpoint
                cmd_display = f"pytest -q {checkpoint.test_file}"
                test_result = self.test_runner.run(
                    checkpoint.test_file, cwd=working_directory
                )
                test_duration_ms = int(test_result.duration_s * 1000)

                # Log command execution
                action_tracer.log_action(
                    ActionType.COMMAND_EXECUTE,
                    success=(test_result.exit_code == 0),
                    duration_ms=test_duration_ms,
                    command=cmd_display,
                    exit_code=test_result.exit_code,
                )

                # Log test run
                action_tracer.log_action(
                    ActionType.TEST_RUN,
                    success=test_result.passed,
                    duration_ms=test_duration_ms,
                    test_file=checkpoint.test_file,
                    exit_code=test_result.exit_code,
                )

                # Compute file system delta and log a context snapshot
                snapshot_after = self.fs_watcher.snapshot(working_directory)
                fs_delta = self.fs_watcher.diff(snapshot_before, snapshot_after)
                files_in_context = fs_delta.get("created", []) + fs_delta.get(
                    "modified", []
                )
                action_tracer.log_context_snapshot(
                    files_in_context=files_in_context,
                    working_directory=str(working_directory),
                    created=fs_delta.get("created", []),
                    modified=fs_delta.get("modified", []),
                    deleted=fs_delta.get("deleted", []),
                    created_count=len(fs_delta.get("created", [])),
                    modified_count=len(fs_delta.get("modified", [])),
                    deleted_count=len(fs_delta.get("deleted", [])),
                )

                # Enhanced metrics collection
                if self.context_window_manager:
                    efficiency_metrics = self.context_window_manager.calculate_context_efficiency(agent, checkpoint)
                    enhanced_metrics.update({
                        "context_efficiency": efficiency_metrics.relevance_precision,
                        "information_density": efficiency_metrics.information_density,
                        "redundancy_rate": efficiency_metrics.redundancy_rate,
                        "compression_effectiveness": efficiency_metrics.compression_effectiveness
                    })
                    
                    # Detect context re-reading patterns
                    reread_events = self.context_window_manager.detect_context_rereading(agent)
                    if reread_events:
                        enhanced_metrics["context_rereading_events"] = len(reread_events)
                        enhanced_metrics["redundancy_penalty"] = sum(e["redundancy_score"] for e in reread_events)

                # Log checkpoint completion before closing the trace
                action_tracer.log_action(
                    ActionType.CHECKPOINT_COMPLETE,
                    success=test_result.passed,
                    tests_passed=test_result.passed,
                    enhanced_metrics=enhanced_metrics,
                )

                # Complete the checkpoint trace using tests_passed as the completion criteria
                action_tracer.complete_checkpoint(tests_passed=test_result.passed)

                # Retrieve the checkpoint trace to compute actions/files
                cp_trace = agent.get_behavioral_trace().get_checkpoint_trace(
                    checkpoint.checkpoint_id
                )
                actions_taken = len(cp_trace.actions) if cp_trace else 0
                files_accessed = []
                if cp_trace:
                    files_accessed = list(cp_trace.get_file_access_pattern().keys())

                # Build enhanced checkpoint result
                checkpoint_result = CheckpointResult(
                    checkpoint_id=checkpoint.checkpoint_id,
                    completed_successfully=test_result.passed,
                    execution_time_seconds=test_result.duration_s,
                    tests_passed=test_result.passed,
                    actions_taken=actions_taken,
                    files_accessed=files_accessed,
                    errors_encountered=test_result.errors,
                )
                
                # Add enhanced metrics if available
                if enhanced_metrics:
                    checkpoint_result.metadata = enhanced_metrics
                
                checkpoint_results.append(checkpoint_result)

                if test_result.passed:
                    print(f"✅ Enhanced Checkpoint {checkpoint.checkpoint_id} tests passed")
                else:
                    print(
                        f"❌ Enhanced Checkpoint {checkpoint.checkpoint_id} tests failed (exit {test_result.exit_code})"
                    )

            except Exception as e:
                print(f"❌ Enhanced Checkpoint {checkpoint.checkpoint_id} failed with error: {e}")
                action_tracer.log_action(
                    ActionType.ERROR_ENCOUNTERED, success=False, error_message=str(e)
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
        success = (
            all(cp.tests_passed for cp in checkpoint_results)
            if checkpoint_results
            else False
        )

        if success:
            print("✅ All enhanced checkpoints completed successfully (tests passed)")
        else:
            print("⚠️  One or more enhanced checkpoints failed tests")

        return success, checkpoint_results

    def _create_checkpoint_results(
        self, task_spec: TaskSpecification, task_trace: TaskTrace
    ) -> List[CheckpointResult]:
        """
        Deprecated: Checkpoint results are now built during execution.
        This method remains for compatibility and returns an empty list.
        """
        return []

    def _materialize_repository(
        self, template_name: str, working_directory: Path
    ) -> None:
        """Copy template directory into working directory.
        Looks for templates in several locations:
        1. templates/{template_name} under current working directory
        2. /app/templates/{template_name} (Docker)
        3. ../../templates/{template_name} relative to this file
        """
        # Potential template roots
        roots = [
            Path.cwd() / "templates",
            Path("/app/templates"),
            Path(__file__).parent.parent.parent / "templates"
        ]
        
        src = None
        for root in roots:
            candidate = root / template_name
            if candidate.exists():
                src = candidate
                break
        
        if not src:
            raise FileNotFoundError(f"Template '{template_name}' not found in any searched locations: {[str(r) for r in roots]}")

        print(f"Materializing template from {src} to {working_directory}")
        # Copy contents of src into working_directory
        copied_count = 0
        for path in src.rglob("*"):
            rel = path.relative_to(src)
            dest = working_directory / rel
            if path.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
                copied_count += 1

    def _calculate_basic_metrics(self, task_trace: TaskTrace) -> Dict[str, float]:
        """
        Calculate basic working memory metrics from trace data.
        """
        # Placeholder for basic metrics
        return {
            "action_count": len(task_trace.actions),
            "checkpoints_attempted": len(task_trace.checkpoints),
        }


class AgentifiedRunner:
    """
    Runner for the Agentified Architecture.
    Orchestrates the A2A message loop between Assessor and Assessee.
    """
    def __init__(self):
        self.task_loader = TaskSpecificationLoader()

    async def run_evaluation(
        self,
        task_path: Path,
        agent: AgentImplementation,
        memory_system: MemorySystem,
        working_directory: Optional[Path] = None,
    ) -> EvaluationResult:
        # 1. Setup
        task_spec = self.task_loader.load_task(task_path)
        
        if working_directory is None:
            working_directory = Path.cwd() / "evaluation_workspace" / task_spec.task_id
        
        # Ensure clean workspace
        if working_directory.exists():
            shutil.rmtree(working_directory)
        working_directory.mkdir(parents=True)

        # Materialize template if needed
        if hasattr(task_spec.repository, 'template_name') and task_spec.repository.template_name:
             self._materialize_repository(task_spec.repository.template_name, working_directory)

        # 2. Initialize Agents
        from ..agents.assessor import AssessorAgent
        from ..agents.adapter import AssesseeAdapter
        from ..core.a2a import MessageType
        
        tracer = ActionTracer(task_id=task_spec.task_id)
        assessor = AssessorAgent(task_spec, working_directory)
        
        # Initialize agent context
        if hasattr(agent, "initialize_secure_file_ops"):
            agent.initialize_secure_file_ops(working_directory)
            
        if hasattr(agent, "_store_task_context"):
            agent._store_task_context(task_spec)
        
        # Wrap user agent
        assessee = AssesseeAdapter(agent, agent_name=agent.__class__.__name__)
        
        # 3. Execution Loop
        start_time = time.time()
        print(f"--- STARTING AGENTIFIED EVALUATION: {task_spec.title} ---")
        
        current_message = assessor.initialize_session(tracer)
        
        max_turns = 100 # Safety limit
        turn = 0
        task_success = False
        task_finished = False
        failure_reason = None
        
        while turn < max_turns:
            turn += 1
            
            # 1. Send Message to Agent (if pending)
            if current_message:
                print(f"Runner -> Agent: {current_message.type} ({current_message.payload.keys()})")
                try:
                    response = await assessee.process_message(current_message)
                    if response:
                        print(f"Agent -> Runner (Sync): {response.type}")
                        # Synchronous response (e.g. PROBE_RESPONSE)
                        # Immediately process with Assessor
                        current_message = assessor.process_message(response)
                    else:
                        # Message consumed / Async operation started
                        current_message = None
                except Exception as e:
                    failure_reason = f"Agent crashed processing message: {e}"
                    print(f"❌ Agent Error: {e}")
                    break

            # 2. Check for Agent Output (Async)
            # Drain outbox or wait a bit if we are idle
            if not assessee.outbox.empty():
                while not assessee.outbox.empty():
                    msg = await assessee.outbox.get()
                    print(f"Agent (Async) -> Runner: {msg.type}")
                    
                    if msg.type == MessageType.TASK_COMPLETE:
                         print("Received TASK_COMPLETE from Agent")
                         # Finalize
                         assessor.process_message(msg) # Let assessor calculate scores
                         task_success = True # Tentative, assessor decides real success
                         break
                    
                    # Send to Assessor
                    result_msg = assessor.process_message(msg)
                    print(f"Assessor -> Runner: {result_msg.type}")
                    
                    if result_msg.type == MessageType.TASK_COMPLETE:
                        print("Assessor declared TASK_COMPLETE")
                        task_finished = True
                        break

                    # The result becomes the next message for the agent
                    current_message = result_msg
                    
                if task_finished:
                    break
            
            else:
                # If we have no message to send AND no output from agent, wait
                if current_message is None:
                    await asyncio.sleep(0.05)


        # 4. Collect Results
        execution_time = time.time() - start_time
        
        # Get Pillar Scores from Assessor
        pillar_scores = {}
        # We can extract them from the last message or Assessor state
        # AssessorAgent.pillar_scores is available
        for pillar, stats in assessor.pillar_scores.items():
            if stats["total"] > 0:
                pillar_scores[pillar.value] = stats["hits"] / stats["total"]
            else:
                pillar_scores[pillar.value] = 0.0

        # Construct EvaluationResult
        task_trace = tracer.get_task_trace()
        checkpoint_results = []
        
        for cp_trace in task_trace.checkpoint_traces:
            # Calculate duration
            duration = 0.0
            if cp_trace.end_timestamp and cp_trace.start_timestamp:
                duration = cp_trace.end_timestamp - cp_trace.start_timestamp
            elif cp_trace.completion_duration_ms:
                duration = cp_trace.completion_duration_ms / 1000.0
                
            # Get file accesses
            files_accessed = list(cp_trace.get_file_access_pattern().keys())
            
            # Get errors
            errors = [e.metadata.get("error_message", "Unknown error") for e in cp_trace.errors_encountered]
            
            checkpoint_results.append(CheckpointResult(
                checkpoint_id=cp_trace.checkpoint_id,
                completed_successfully=cp_trace.tests_passed,
                execution_time_seconds=duration,
                tests_passed=cp_trace.tests_passed,
                actions_taken=len(cp_trace.actions),
                files_accessed=files_accessed,
                errors_encountered=errors
            ))
        
        # Determine final success: Task must finish AND all checkpoints must pass
        all_checkpoints_passed = len(checkpoint_results) > 0 and all(cp.completed_successfully for cp in checkpoint_results)
        final_success = task_finished and all_checkpoints_passed
        
        return EvaluationResult(
            task_id=task_spec.task_id,
            agent_name=agent.__class__.__name__,
            memory_system_name=memory_system.__class__.__name__,
            task_completed_successfully=final_success,
            execution_time_seconds=execution_time,
            task_trace=task_trace,
            checkpoint_results=checkpoint_results,
            working_memory_metrics={},
            pillar_scores=pillar_scores,
            failure_reason=failure_reason
        )

    def _materialize_repository(
        self, template_name: str, working_directory: Path
    ) -> None:
        """Copy template directory into working directory.
        Looks for templates in several locations:
        1. templates/{template_name} under current working directory
        2. /app/templates/{template_name} (Docker)
        3. ../../templates/{template_name} relative to this file
        """
        # Potential template roots
        roots = [
            Path.cwd() / "templates",
            Path("/app/templates"),
            Path(__file__).parent.parent.parent / "templates"
        ]
        
        src = None
        for root in roots:
            candidate = root / template_name
            if candidate.exists():
                src = candidate
                break
        
        if not src:
            print(f"Warning: Template '{template_name}' not found in any searched locations: {[str(r) for r in roots]}")
            return

        print(f"DEBUG: Materializing template from {src} to {working_directory}")
        # Copy contents of src into working_directory
        copied_count = 0
        for path in src.rglob("*"):
            rel = path.relative_to(src)
            dest = working_directory / rel
            if path.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
                copied_count += 1
        print(f"DEBUG: Materialized {copied_count} files from template")
