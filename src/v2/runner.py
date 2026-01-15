"""
WorkMemEval V2: Simple Runner

Executes tasks by:
1. Setting up the workspace (materialize template, load history)
2. Running each checkpoint (prompt agent, read workpad, score)
3. Collecting and aggregating results

Supports:
- Local execution (default)
- Docker containerized execution (--container flag)
- Secure file operations (path validation, extension filtering)
"""

import json
import shutil
import time
from pathlib import Path
from typing import Any, Optional, Protocol

from .models import Task, Checkpoint, EvaluationResult, CheckpointResult, SemanticCheck
from .assessor import WorkpadAssessor
from .secure_file_ops import SecureFileOperations

# Optional semantic assessor
try:
    from .semantic_assessor import SemanticAssessor
    SEMANTIC_AVAILABLE = True
except ImportError:
    SemanticAssessor = None
    SEMANTIC_AVAILABLE = False


class AgentProtocol(Protocol):
    """Minimal interface for agents to implement."""
    
    async def execute(self, prompt: str, working_dir: Path) -> None:
        """
        Execute a task given a prompt.
        
        The agent should:
        1. Read the prompt
        2. Do whatever work is needed
        3. Update WORKPAD.md with its understanding/decisions
        
        Args:
            prompt: The checkpoint prompt
            working_dir: Working directory containing files
        """
        ...


class V2Runner:
    """
    Simple task runner for V2 evaluation.
    
    Supports both local and containerized execution with secure file operations.
    """
    
    def __init__(
        self,
        output_dir: Optional[Path] = None,
        use_container: bool = False,
        docker_image: str = "workmemeval/eval:local",
        secure_mode: bool = True,
        enable_semantic: bool = True,
    ):
        """
        Initialize runner.
        
        Args:
            output_dir: Directory to save evaluation results (optional)
            use_container: Run in Docker container for isolation
            docker_image: Docker image to use (if use_container=True)
            secure_mode: Enable secure file operations (path validation)
            enable_semantic: Enable LLM-based semantic assessment (if available)
        """
        self.output_dir = output_dir or Path("evaluation_runs/v2")
        self.assessor = WorkpadAssessor()
        self.use_container = use_container
        self.docker_image = docker_image
        self.secure_mode = secure_mode
        self.docker_runner = None
        self.secure_file_ops = None
        
        # Initialize semantic assessor if enabled and available
        self.semantic_assessor = None
        if enable_semantic and SEMANTIC_AVAILABLE:
            import os
            api_key = os.getenv("OPENROUTER_API_KEY")
            if api_key:
                self.semantic_assessor = SemanticAssessor(api_key=api_key)
                print("  Semantic assessment: enabled")
    
    async def run(
        self,
        task: Task,
        agent: Any,
        working_dir: Optional[Path] = None,
    ) -> EvaluationResult:
        """
        Execute a complete task evaluation.
        
        Args:
            task: Task specification to run
            agent: Agent implementing execute(prompt, working_dir)
            working_dir: Working directory (created if not provided)
            
        Returns:
            Complete evaluation results
        """
        start_time = time.time()
        
        # Setup workspace
        if working_dir is None:
            working_dir = Path("evaluation_workspace") / task.task_id
        
        self._setup_workspace(task, working_dir)
        
        print(f"\n{'='*60}")
        print(f"STARTING V2 EVALUATION: {task.title}")
        print(f"{'='*60}")
        print(f"Task ID: {task.task_id}")
        print(f"Checkpoints: {len(task.checkpoints)}")
        print(f"Working directory: {working_dir}")
        print()
        
        # Initialize workpad
        workpad_path = working_dir / task.workpad_file
        secure_ops = SecureFileOperations(working_dir) if self.secure_mode else None
        if not workpad_path.exists():
            if secure_ops:
                secure_ops.write_file(task.workpad_file, "# Working Memory\n\n")
            else:
                workpad_path.write_text("# Working Memory\n\n")
        
        # Execute checkpoints
        checkpoint_results = []
        
        for i, checkpoint in enumerate(task.checkpoints, 1):
            print(f"--- Checkpoint {i}/{len(task.checkpoints)}: {checkpoint.id} ---")
            
            # Inject any checkpoint-specific files
            for filename, content in checkpoint.inject_files.items():
                if secure_ops:
                    secure_ops.write_file(filename, content)
                else:
                    (working_dir / filename).write_text(content)
            
            # Build full prompt with task instructions
            full_prompt = self._build_prompt(task, checkpoint)
            
            # Execute checkpoint
            try:
                await agent.execute(full_prompt, working_dir)
            except Exception as e:
                print(f"  ⚠ Agent error: {e}")
            
            # Read and evaluate workpad
            if workpad_path.exists():
                workpad_content = secure_ops.read_file(task.workpad_file) if secure_ops else workpad_path.read_text()
            else:
                workpad_content = ""
            
            # Pattern-based assessment (deterministic)
            pillar_scores, check_details = self.assessor.evaluate_with_details(
                workpad_content, checkpoint.checks
            )
            
            # Semantic assessment (LLM-based) if checks exist and assessor available
            semantic_details = []
            if checkpoint.semantic_checks and self.semantic_assessor:
                print(f"  [Semantic] Evaluating {len(checkpoint.semantic_checks)} checks...")
                semantic_scores, semantic_details = await self.semantic_assessor.evaluate_with_details(
                    workpad_content, checkpoint.semantic_checks
                )
                # Merge semantic scores with pattern scores (average if both exist)
                for pillar, score in semantic_scores.items():
                    if pillar in pillar_scores:
                        # Average pattern and semantic scores
                        pillar_scores[pillar] = (pillar_scores[pillar] + score) / 2
                    else:
                        pillar_scores[pillar] = score
                print(f"  [Semantic] Done")
            
            # Record result
            context_metrics = self._collect_context_metrics(agent)
            cp_result = CheckpointResult(
                checkpoint_id=checkpoint.id,
                pillar_scores=pillar_scores,
                workpad_snapshot=workpad_content,
                check_details=check_details + semantic_details,
                context_metrics=context_metrics,
            )
            checkpoint_results.append(cp_result)
            
            # Print checkpoint summary
            for pillar, score in pillar_scores.items():
                status = "✓" if score >= 0.5 else "✗"
                print(f"  {status} {pillar}: {score*100:.0f}%")
            print()
        
        # Aggregate pillar scores across all checkpoints
        aggregate_scores = self._aggregate_scores(checkpoint_results)
        
        # Read final workpad
        final_workpad = workpad_path.read_text() if workpad_path.exists() else ""
        
        # Build result
        result = EvaluationResult(
            task_id=task.task_id,
            agent_name=agent.__class__.__name__,
            pillar_scores=aggregate_scores,
            checkpoint_results=checkpoint_results,
            execution_time_seconds=time.time() - start_time,
            final_workpad=final_workpad,
        )
        
        # Save results
        self._save_results(result)
        
        result.print_summary()
        
        return result
    
    def _setup_workspace(self, task: Task, working_dir: Path) -> None:
        """Set up the working directory with template and history."""
        # Clean and create workspace
        if working_dir.exists():
            shutil.rmtree(working_dir)
        working_dir.mkdir(parents=True)

        # Materialize template if provided
        if task.template:
            self._materialize_template(task.template, working_dir)
        
        # Load history file if provided
        if task.history_file:
            self._load_history(task.history_file, working_dir)
        
        if self.use_container:
            print(f"  Container mode: {self.docker_image}")

    def _collect_context_metrics(self, agent: Any) -> dict[str, Any]:
        metrics: dict[str, Any] = {}

        messages = getattr(agent, "messages", None)
        if isinstance(messages, list):
            metrics["message_count"] = len(messages)
            metrics["non_system_message_count"] = len([m for m in messages if m.get("role") != "system"])
            non_system_chars = sum(len(m.get("content", "")) for m in messages if m.get("role") != "system")
            metrics["non_system_chars"] = non_system_chars
            metrics["approx_tokens"] = int(non_system_chars / 4) if non_system_chars else 0

        max_ctx_messages = getattr(agent, "max_context_messages", None)
        if max_ctx_messages is not None:
            metrics["max_context_messages"] = max_ctx_messages
        max_ctx_chars = getattr(agent, "max_context_chars", None)
        if max_ctx_chars is not None:
            metrics["max_context_chars"] = max_ctx_chars

        return metrics
    
    def _materialize_template(self, template_name: str, working_dir: Path) -> None:
        """Copy template files into working directory."""
        # Search for template in standard locations
        search_paths = [
            Path.cwd() / "templates" / template_name,
            Path(__file__).parent.parent.parent / "templates" / template_name,
        ]
        
        template_path = None
        for path in search_paths:
            if path.exists():
                template_path = path
                break
        
        if not template_path:
            print(f"  Warning: Template '{template_name}' not found")
            return
        
        # Copy template contents
        for item in template_path.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(template_path)
                dest = working_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest)
        
        print(f"  Materialized template: {template_name}")
    
    def _load_history(self, history_file: str, working_dir: Path) -> None:
        """Load conversation history and make it available to agent."""
        history_path = Path(history_file)
        if not history_path.exists():
            # Try relative to project root
            history_path = Path.cwd() / history_file
        
        if history_path.exists():
            # Copy history to workspace
            dest = working_dir / "HISTORY.json"
            shutil.copy2(history_path, dest)
            print(f"  Loaded history: {history_path.name}")
        else:
            print(f"  Warning: History file not found: {history_file}")
    
    def _build_prompt(self, task: Task, checkpoint: Checkpoint) -> str:
        """Build the full prompt for a checkpoint."""
        parts = []
        
        # Task-level instructions
        if task.instructions:
            parts.append(task.instructions.strip())
            parts.append("")
        
        # Checkpoint prompt
        parts.append(checkpoint.prompt.strip())
        
        # Workpad reminder
        parts.append("")
        parts.append(f"Remember to update {task.workpad_file} with your understanding and decisions.")
        
        return "\n".join(parts)
    
    def _aggregate_scores(self, checkpoint_results: list[CheckpointResult]) -> dict[str, float]:
        """Calculate aggregate pillar scores across all checkpoints."""
        pillar_totals: dict[str, list[float]] = {}
        
        for cp_result in checkpoint_results:
            for pillar, score in cp_result.pillar_scores.items():
                if pillar not in pillar_totals:
                    pillar_totals[pillar] = []
                pillar_totals[pillar].append(score)
        
        return {
            pillar: sum(scores) / len(scores)
            for pillar, scores in pillar_totals.items()
        }
    
    def _save_results(self, result: EvaluationResult) -> None:
        """Save evaluation results to JSON file."""
        try:
            results_dir = self.output_dir / result.task_id
            results_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = time.strftime("%Y%m%dT%H%M%S")
            output_path = results_dir / f"{timestamp}.json"
            
            with open(output_path, "w") as f:
                json.dump(result.to_dict(), f, indent=2)
            
            print(f"Results saved to: {output_path}")
        except Exception as e:
            print(f"Warning: Failed to save results: {e}")
