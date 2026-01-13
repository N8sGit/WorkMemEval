"""
WorkMemEval: Evaluation Results Data Structures

Basic data structures for capturing and storing evaluation results.
These will be progressively enhanced as we add more sophisticated metrics.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..core.action_trace import TaskTrace


@dataclass
class CheckpointResult:
    """
    Results from executing a single checkpoint.
    """

    checkpoint_id: str
    completed_successfully: bool
    execution_time_seconds: float
    tests_passed: bool
    actions_taken: int
    files_accessed: List[str] = field(default_factory=list)
    errors_encountered: List[str] = field(default_factory=list)

    # Additional metrics (to be enhanced later)
    memory_usage_peak_mb: Optional[float] = None
    llm_calls_made: Optional[int] = None
    context_switches: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "completed_successfully": self.completed_successfully,
            "execution_time_seconds": self.execution_time_seconds,
            "tests_passed": self.tests_passed,
            "actions_taken": self.actions_taken,
            "files_accessed": self.files_accessed,
            "errors_encountered": self.errors_encountered,
            "memory_usage_peak_mb": self.memory_usage_peak_mb,
            "llm_calls_made": self.llm_calls_made,
            "context_switches": self.context_switches,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckpointResult":
        return cls(
            checkpoint_id=data["checkpoint_id"],
            completed_successfully=data.get("completed_successfully", False),
            execution_time_seconds=data.get("execution_time_seconds", 0.0),
            tests_passed=data.get("tests_passed", False),
            actions_taken=data.get("actions_taken", 0),
            files_accessed=data.get("files_accessed", []),
            errors_encountered=data.get("errors_encountered", []),
            memory_usage_peak_mb=data.get("memory_usage_peak_mb"),
            llm_calls_made=data.get("llm_calls_made"),
            context_switches=data.get("context_switches"),
        )


@dataclass
class EvaluationResult:
    """
    Complete results from evaluating an agent on a task.

    This is the primary output of the evaluation system and contains
    all information needed for analysis and reporting.
    """

    # Basic identification
    task_id: str
    agent_name: str
    memory_system_name: str

    # Execution results
    task_completed_successfully: bool
    execution_time_seconds: float

    # Detailed traces and results (required fields first)
    task_trace: TaskTrace

    # Optional fields with defaults
    timestamp: float = field(default_factory=time.time)
    checkpoint_results: List[CheckpointResult] = field(default_factory=list)

    # Working memory metrics (basic for now)
    working_memory_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Pillar-specific scores (Explicit Memory Evaluation)
    pillar_scores: Dict[str, float] = field(default_factory=dict)

    # Error information
    failure_reason: Optional[str] = None

    # Metadata
    evaluation_config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "memory_system_name": self.memory_system_name,
            "task_completed_successfully": self.task_completed_successfully,
            "execution_time_seconds": self.execution_time_seconds,
            "timestamp": self.timestamp,
            "task_trace": self.task_trace.to_dict(),
            "checkpoint_results": [cp.to_dict() for cp in self.checkpoint_results],
            "working_memory_metrics": self.working_memory_metrics,
            "failure_reason": self.failure_reason,
            "evaluation_config": self.evaluation_config,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvaluationResult":
        # Rehydrate task trace
        task_trace = (
            TaskTrace.from_dict(data["task_trace"])
            if isinstance(data.get("task_trace"), dict)
            else data["task_trace"]
        )
        checkpoint_results = [
            CheckpointResult.from_dict(cp) for cp in data.get("checkpoint_results", [])
        ]
        return cls(
            task_id=data["task_id"],
            agent_name=data["agent_name"],
            memory_system_name=data["memory_system_name"],
            task_completed_successfully=data.get("task_completed_successfully", False),
            execution_time_seconds=data.get("execution_time_seconds", 0.0),
            task_trace=task_trace,
            timestamp=data.get("timestamp", time.time()),
            checkpoint_results=checkpoint_results,
            working_memory_metrics=data.get("working_memory_metrics", {}),
            failure_reason=data.get("failure_reason"),
            evaluation_config=data.get("evaluation_config", {}),
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the evaluation results"""
        return {
            "task_id": self.task_id,
            "agent": self.agent_name,
            "memory_system": self.memory_system_name,
            "success": self.task_completed_successfully,
            "execution_time": f"{self.execution_time_seconds:.2f}s",
            "checkpoints_completed": len(
                [cp for cp in self.checkpoint_results if cp.completed_successfully]
            ),
            "total_checkpoints": len(self.checkpoint_results),
            "working_memory_metrics": self.working_memory_metrics,
            "timestamp": time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp)
            ),
        }

    def print_summary(self):
        """Print a human-readable summary of the results"""
        print("\n=== Evaluation Summary ===")
        print(f"Task: {self.task_id}")
        print(f"Agent: {self.agent_name}")
        print(f"Memory System: {self.memory_system_name}")
        print(
            f"Status: {'✅ SUCCESS' if self.task_completed_successfully else '❌ FAILED'}"
        )
        print(f"Execution Time: {self.execution_time_seconds:.2f}s")

        # Checkpoint summary
        completed = len(
            [cp for cp in self.checkpoint_results if cp.completed_successfully]
        )
        total = len(self.checkpoint_results)
        print(f"Checkpoints: {completed}/{total} completed")

        # Pillar Scores (Memory Efficiency)
        if self.pillar_scores:
            print("\nMemory Pillar Scores:")
            for pillar, score in self.pillar_scores.items():
                # Format likely keys: memory_fidelity, contextual_relevance, behavioral_integrity
                name = pillar.replace("_", " ").title()
                bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
                print(f"  {name:<25} {bar} {score:.1%}")

        # Working memory metrics
        if self.working_memory_metrics:
            print("\nWorking Memory Metrics:")
            for metric_name, value in self.working_memory_metrics.items():
                print(f"  {metric_name}: {value:.3f}")

        if self.failure_reason:
            print(f"\nFailure Reason: {self.failure_reason}")


@dataclass
class ComparisonResult:
    """
    Results from comparing multiple evaluation runs.

    Used for analyzing performance across different agents, memory systems,
    or task configurations.
    """

    comparison_name: str
    evaluation_results: List[EvaluationResult] = field(default_factory=list)
    comparison_metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def add_evaluation(self, result: EvaluationResult):
        """Add an evaluation result to this comparison"""
        self.evaluation_results.append(result)

    def calculate_comparison_metrics(self):
        """Calculate metrics comparing the evaluation results"""
        if not self.evaluation_results:
            return

        # Basic comparison metrics
        success_rates = []
        execution_times = []
        memory_metrics = {}

        for result in self.evaluation_results:
            success_rates.append(1.0 if result.task_completed_successfully else 0.0)
            execution_times.append(result.execution_time_seconds)

            # Aggregate working memory metrics
            for metric_name, value in result.working_memory_metrics.items():
                if metric_name not in memory_metrics:
                    memory_metrics[metric_name] = []
                memory_metrics[metric_name].append(value)

        self.comparison_metrics = {
            "success_rate": sum(success_rates) / len(success_rates),
            "average_execution_time": sum(execution_times) / len(execution_times),
            "min_execution_time": min(execution_times),
            "max_execution_time": max(execution_times),
        }

        # Add aggregated memory metrics
        for metric_name, values in memory_metrics.items():
            self.comparison_metrics[f"avg_{metric_name}"] = sum(values) / len(values)
            self.comparison_metrics[f"min_{metric_name}"] = min(values)
            self.comparison_metrics[f"max_{metric_name}"] = max(values)

    def print_comparison(self):
        """Print a human-readable comparison of the results"""
        print(f"\n=== Comparison Results: {self.comparison_name} ===")
        print(f"Evaluations: {len(self.evaluation_results)}")

        if self.comparison_metrics:
            print(f"Success Rate: {self.comparison_metrics['success_rate']:.1%}")
            print(
                f"Avg Execution Time: {self.comparison_metrics['average_execution_time']:.2f}s"
            )
            print(
                f"Execution Time Range: {self.comparison_metrics['min_execution_time']:.2f}s - {self.comparison_metrics['max_execution_time']:.2f}s"
            )

            # Print memory metrics
            memory_metrics = [
                k for k in self.comparison_metrics.keys() if k.startswith("avg_")
            ]
            if memory_metrics:
                print("\nWorking Memory Metrics (Average):")
                for metric_key in memory_metrics:
                    metric_name = metric_key.replace("avg_", "")
                    avg_value = self.comparison_metrics[metric_key]
                    print(f"  {metric_name}: {avg_value:.3f}")

        # Individual results
        print("\nIndividual Results:")
        for i, result in enumerate(self.evaluation_results, 1):
            status = "✅" if result.task_completed_successfully else "❌"
            print(
                f"  {i}. {result.agent_name} + {result.memory_system_name}: {status} ({result.execution_time_seconds:.2f}s)"
            )
