"""
WorkMemEval V2: Core Data Models

Simple dataclasses for task specification and evaluation results.
No complex inheritance, no legacy compatibility layers - just clean data.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class Pillar(str, Enum):
    """The three pillars of working memory evaluation."""
    FIDELITY = "fidelity"      # Retention & recall of information
    RELEVANCE = "relevance"    # Filtering noise, focusing on signal
    INTEGRITY = "integrity"    # Adapting to changes, maintaining consistency


@dataclass
class WorkpadCheck:
    """
    A single verification check against the workpad content.
    
    Checks are simple pattern matching - no AST, no code analysis.
    """
    pillar: str
    must_contain: list[str] = field(default_factory=list)
    must_contain_one_of: list[str] = field(default_factory=list)
    must_not_contain: list[str] = field(default_factory=list)
    regex_patterns: list[str] = field(default_factory=list)
    weight: float = 1.0
    description: str = ""


@dataclass
class SemanticCheck:
    """
    A semantic check that uses LLM grading against a truth source.
    
    Unlike pattern matching, this allows:
    - Semantic equivalence ("$75" = "seventy-five dollars")
    - Partial credit for close answers
    - Understanding of context and meaning
    """
    pillar: str
    description: str
    truth: str              # Ground truth the agent should have remembered
    weight: float = 1.0


@dataclass
class Checkpoint:
    """
    A single step in the evaluation task.
    
    Each checkpoint gives the agent a prompt and defines what
    should appear in the workpad after completion.
    """
    id: str
    prompt: str
    checks: list[WorkpadCheck] = field(default_factory=list)
    
    # Optional: semantic checks (LLM-graded)
    semantic_checks: list[SemanticCheck] = field(default_factory=list)
    
    # Optional: inject context files the agent should notice
    inject_files: dict[str, str] = field(default_factory=dict)


@dataclass
class Task:
    """
    Complete task specification loaded from YAML.
    
    A task defines the evaluation scenario, including any
    pre-existing context (history) and the checkpoints to execute.
    """
    task_id: str
    title: str
    checkpoints: list[Checkpoint]
    
    # Optional codebase template to materialize
    template: Optional[str] = None
    
    # Optional conversation history file (for continuation tasks)
    history_file: Optional[str] = None
    
    # The file the agent must maintain (default: WORKPAD.md)
    workpad_file: str = "WORKPAD.md"
    
    # Instructions prepended to all prompts
    instructions: str = ""
    
    # Metadata
    description: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class CheckpointResult:
    """Result of evaluating a single checkpoint."""
    checkpoint_id: str
    pillar_scores: dict[str, float] = field(default_factory=dict)
    workpad_snapshot: str = ""
    check_details: list[dict[str, Any]] = field(default_factory=list)
    context_metrics: dict[str, Any] = field(default_factory=dict)


@dataclass 
class EvaluationResult:
    """Complete evaluation result for a task run."""
    task_id: str
    agent_name: str
    
    # Aggregate scores per pillar (0.0 - 1.0)
    pillar_scores: dict[str, float] = field(default_factory=dict)
    
    # Per-checkpoint details
    checkpoint_results: list[CheckpointResult] = field(default_factory=list)
    
    # Execution metadata
    execution_time_seconds: float = 0.0
    timestamp: float = field(default_factory=lambda: __import__('time').time())
    
    # Final workpad content
    final_workpad: str = ""
    
    def print_summary(self):
        """Print human-readable summary."""
        print(f"\n{'='*60}")
        print(f"EVALUATION RESULT: {self.task_id}")
        print(f"{'='*60}")
        print(f"Agent: {self.agent_name}")
        print(f"Time: {self.execution_time_seconds:.1f}s")
        print()
        print("PILLAR SCORES:")
        for pillar, score in self.pillar_scores.items():
            bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
            print(f"  {pillar:12} [{bar}] {score*100:.0f}%")
        print()
        print("CHECKPOINT BREAKDOWN:")
        for cp in self.checkpoint_results:
            status = "✓" if all(s >= 0.5 for s in cp.pillar_scores.values()) else "✗"
            print(f"  {status} {cp.checkpoint_id}")
            for pillar, score in cp.pillar_scores.items():
                print(f"      {pillar}: {score*100:.0f}%")
        print(f"{'='*60}\n")
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON output."""
        return {
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "pillar_scores": self.pillar_scores,
            "checkpoint_results": [
                {
                    "checkpoint_id": cp.checkpoint_id,
                    "pillar_scores": cp.pillar_scores,
                    "workpad_snapshot": cp.workpad_snapshot,
                    "check_details": cp.check_details,
                    "context_metrics": cp.context_metrics,
                }
                for cp in self.checkpoint_results
            ],
            "execution_time_seconds": self.execution_time_seconds,
            "timestamp": self.timestamp,
            "final_workpad": self.final_workpad,
        }
