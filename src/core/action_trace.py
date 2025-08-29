"""
WorkMemEval: Action Trace Data Structures

This module defines the core data structures for capturing and analyzing agent behavior
during WorkMemEval task execution. Action traces are the foundation for calculating
working memory metrics.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from enum import Enum
import time
import json
from pathlib import Path


class ActionType(Enum):
    """Types of actions that can be captured in the trace"""
    # File system operations
    FILE_READ = "file_read"
    FILE_WRITE = "file_write" 
    FILE_CREATE = "file_create"
    FILE_DELETE = "file_delete"
    FILE_MODIFY = "file_modify"
    
    # Command execution
    COMMAND_EXECUTE = "command_execute"
    TEST_RUN = "test_run"
    
    # Agent operations
    LLM_CALL = "llm_call"
    PLANNING = "planning"
    CHECKPOINT_START = "checkpoint_start"
    CHECKPOINT_COMPLETE = "checkpoint_complete"
    
    # Context management
    CONTEXT_UPDATE = "context_update"
    MEMORY_COMPRESSION = "memory_compression"
    
    # Working memory challenges
    REQUIREMENT_UPDATE = "requirement_update"
    CONTEXT_SWITCH_START = "context_switch_start"
    CONTEXT_SWITCH_RESUME = "context_switch_resume"
    
    # Error handling
    ERROR_ENCOUNTERED = "error_encountered"
    ERROR_RECOVERY = "error_recovery"


@dataclass
class ActionTraceEntry:
    """
    Individual action trace entry capturing agent behavior.
    
    This is the atomic unit of behavioral observation in WorkMemEval,
    designed to capture all information needed for working memory analysis.
    """
    timestamp: float
    action_type: ActionType
    success: bool
    
    # Context information
    file_path: Optional[str] = None
    function_name: Optional[str] = None
    checkpoint_id: Optional[str] = None
    
    # Performance metrics
    duration_ms: Optional[float] = None
    context_size_tokens: int = 0
    
    # Action-specific data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate action trace entry"""
        if self.timestamp <= 0:
            raise ValueError("Timestamp must be positive")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("Duration cannot be negative")


@dataclass
class ContextSnapshot:
    """
    Snapshot of agent's context state at a point in time.
    
    Captures the agent's working memory state for analysis of memory
    management patterns and efficiency.
    """
    timestamp: float
    checkpoint_id: Optional[str]
    
    # Files currently in context
    files_in_context: List[str] = field(default_factory=list)
    context_token_count: int = 0
    
    # Memory state
    working_memory_items: List[Dict[str, Any]] = field(default_factory=list)
    recent_actions_count: int = 0
    
    # System state
    working_directory: str = ""
    git_branch: str = "main"
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_context_size(self) -> int:
        """Get total context size in tokens"""
        return self.context_token_count
    
    def get_file_count(self) -> int:
        """Get number of files in context"""
        return len(self.files_in_context)


@dataclass
class CheckpointTrace:
    """
    Complete trace for a single checkpoint execution.
    
    Aggregates all actions and context snapshots for a checkpoint,
    providing the data needed for checkpoint-level metric calculation.
    """
    checkpoint_id: str
    start_timestamp: float
    end_timestamp: Optional[float] = None
    
    # Execution results
    tests_passed: bool = False
    completion_duration_ms: Optional[float] = None
    
    # Behavioral trace
    actions: List[ActionTraceEntry] = field(default_factory=list)
    context_snapshots: List[ContextSnapshot] = field(default_factory=list)
    
    # Error tracking
    errors_encountered: List[ActionTraceEntry] = field(default_factory=list)
    recovery_actions: List[ActionTraceEntry] = field(default_factory=list)
    
    def add_action(self, action: ActionTraceEntry) -> None:
        """Add action to checkpoint trace"""
        if action.checkpoint_id and action.checkpoint_id != self.checkpoint_id:
            raise ValueError(f"Action checkpoint_id {action.checkpoint_id} doesn't match trace checkpoint_id {self.checkpoint_id}")
        
        action.checkpoint_id = self.checkpoint_id
        self.actions.append(action)
        
        # Track errors separately for easy analysis
        if not action.success:
            self.errors_encountered.append(action)
        elif action.action_type == ActionType.ERROR_RECOVERY:
            self.recovery_actions.append(action)
    
    def add_context_snapshot(self, snapshot: ContextSnapshot) -> None:
        """Add context snapshot to checkpoint trace"""
        snapshot.checkpoint_id = self.checkpoint_id
        self.context_snapshots.append(snapshot)
    
    def complete_checkpoint(self, tests_passed: bool) -> None:
        """Mark checkpoint as completed"""
        self.end_timestamp = time.time()
        self.tests_passed = tests_passed
        
        if self.end_timestamp and self.start_timestamp:
            self.completion_duration_ms = (self.end_timestamp - self.start_timestamp) * 1000
    
    def get_file_access_pattern(self) -> Dict[str, List[float]]:
        """
        Get file access patterns for this checkpoint.
        
        Returns dict mapping file paths to list of access timestamps,
        useful for calculating context reread rates.
        """
        file_accesses = {}
        
        for action in self.actions:
            if action.file_path and action.action_type in [ActionType.FILE_READ, ActionType.FILE_WRITE, ActionType.FILE_MODIFY]:
                if action.file_path not in file_accesses:
                    file_accesses[action.file_path] = []
                file_accesses[action.file_path].append(action.timestamp)
        
        return file_accesses
    
    def get_error_rate(self) -> float:
        """Calculate error rate for this checkpoint"""
        if not self.actions:
            return 0.0
        return len(self.errors_encountered) / len(self.actions)


@dataclass
class TaskTrace:
    """
    Complete trace for an entire task execution.
    
    Aggregates all checkpoint traces and provides task-level analysis
    capabilities for working memory evaluation.
    """
    task_id: str
    start_timestamp: float
    end_timestamp: Optional[float] = None
    
    # Task execution results
    completed_successfully: bool = False
    total_duration_ms: Optional[float] = None
    
    # Planning phase
    planning_trace: Optional[CheckpointTrace] = None
    
    # Checkpoint execution
    checkpoint_traces: List[CheckpointTrace] = field(default_factory=list)
    
    # Memory challenges
    memory_challenge_responses: List[ActionTraceEntry] = field(default_factory=list)
    
    # Task-level aggregations
    total_actions: int = 0
    total_errors: int = 0
    unique_files_accessed: set = field(default_factory=set)
    
    def add_checkpoint_trace(self, checkpoint_trace: CheckpointTrace) -> None:
        """Add checkpoint trace to task trace"""
        self.checkpoint_traces.append(checkpoint_trace)
        
        # Update aggregations
        self.total_actions += len(checkpoint_trace.actions)
        self.total_errors += len(checkpoint_trace.errors_encountered)
        
        for action in checkpoint_trace.actions:
            if action.file_path:
                self.unique_files_accessed.add(action.file_path)
    
    def complete_task(self, completed_successfully: bool) -> None:
        """Mark task as completed"""
        self.end_timestamp = time.time()
        self.completed_successfully = completed_successfully
        
        if self.end_timestamp:
            self.total_duration_ms = (self.end_timestamp - self.start_timestamp) * 1000
    
    def get_checkpoint_trace(self, checkpoint_id: str) -> Optional[CheckpointTrace]:
        """Get trace for specific checkpoint"""
        return next((trace for trace in self.checkpoint_traces if trace.checkpoint_id == checkpoint_id), None)
    
    def calculate_overall_error_rate(self) -> float:
        """Calculate overall error rate across all checkpoints"""
        if self.total_actions == 0:
            return 0.0
        return self.total_errors / self.total_actions
    
    def get_file_reread_statistics(self) -> Dict[str, Any]:
        """
        Calculate file re-read statistics across all checkpoints.
        
        This is a key metric for Memory Fidelity evaluation.
        """
        all_file_accesses = {}
        total_accesses = 0
        
        for checkpoint_trace in self.checkpoint_traces:
            file_pattern = checkpoint_trace.get_file_access_pattern()
            
            for file_path, timestamps in file_pattern.items():
                if file_path not in all_file_accesses:
                    all_file_accesses[file_path] = []
                all_file_accesses[file_path].extend(timestamps)
                total_accesses += len(timestamps)
        
        # Calculate reread statistics
        unique_file_accesses = len(all_file_accesses)
        unnecessary_rereads = total_accesses - unique_file_accesses
        reread_rate = unnecessary_rereads / total_accesses if total_accesses > 0 else 0.0
        
        return {
            'total_file_accesses': total_accesses,
            'unique_files_accessed': unique_file_accesses,
            'unnecessary_rereads': unnecessary_rereads,
            'reread_rate': reread_rate,
            'files_with_multiple_accesses': {
                file_path: len(timestamps) 
                for file_path, timestamps in all_file_accesses.items()
                if len(timestamps) > 1
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task trace to dictionary for serialization"""
        return {
            'task_id': self.task_id,
            'start_timestamp': self.start_timestamp,
            'end_timestamp': self.end_timestamp,
            'completed_successfully': self.completed_successfully,
            'total_duration_ms': self.total_duration_ms,
            'planning_trace': self.planning_trace.to_dict() if self.planning_trace else None,
            'checkpoint_traces': [trace.to_dict() for trace in self.checkpoint_traces],
            'memory_challenge_responses': [
                {
                    'timestamp': action.timestamp,
                    'action_type': action.action_type.value,
                    'success': action.success,
                    'checkpoint_id': action.checkpoint_id,
                    'metadata': action.metadata
                }
                for action in self.memory_challenge_responses
            ],
            'summary_statistics': {
                'total_actions': self.total_actions,
                'total_errors': self.total_errors,
                'unique_files_accessed': len(self.unique_files_accessed),
                'overall_error_rate': self.calculate_overall_error_rate(),
                'file_reread_statistics': self.get_file_reread_statistics()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskTrace':
        """Create TaskTrace from dictionary"""
        task_trace = cls(
            task_id=data['task_id'],
            start_timestamp=data['start_timestamp'],
            end_timestamp=data.get('end_timestamp'),
            completed_successfully=data.get('completed_successfully', False),
            total_duration_ms=data.get('total_duration_ms')
        )
        
        # Recreate checkpoint traces
        for cp_data in data.get('checkpoint_traces', []):
            checkpoint_trace = CheckpointTrace.from_dict(cp_data)
            task_trace.add_checkpoint_trace(checkpoint_trace)
        
        # Recreate memory challenge responses
        for mc_data in data.get('memory_challenge_responses', []):
            action = ActionTraceEntry(
                timestamp=mc_data['timestamp'],
                action_type=ActionType(mc_data['action_type']),
                success=mc_data['success'],
                checkpoint_id=mc_data.get('checkpoint_id'),
                metadata=mc_data.get('metadata', {})
            )
            task_trace.memory_challenge_responses.append(action)
        
        return task_trace


# Extension for CheckpointTrace to_dict/from_dict
def checkpoint_trace_to_dict(self) -> Dict[str, Any]:
    """Convert checkpoint trace to dictionary"""
    return {
        'checkpoint_id': self.checkpoint_id,
        'start_timestamp': self.start_timestamp,
        'end_timestamp': self.end_timestamp,
        'tests_passed': self.tests_passed,
        'completion_duration_ms': self.completion_duration_ms,
        'actions': [
            {
                'timestamp': action.timestamp,
                'action_type': action.action_type.value,
                'success': action.success,
                'file_path': action.file_path,
                'function_name': action.function_name,
                'checkpoint_id': action.checkpoint_id,
                'duration_ms': action.duration_ms,
                'context_size_tokens': action.context_size_tokens,
                'metadata': action.metadata
            }
            for action in self.actions
        ],
        'context_snapshots': [
            {
                'timestamp': snapshot.timestamp,
                'checkpoint_id': snapshot.checkpoint_id,
                'files_in_context': snapshot.files_in_context,
                'context_token_count': snapshot.context_token_count,
                'working_memory_items': snapshot.working_memory_items,
                'recent_actions_count': snapshot.recent_actions_count,
                'working_directory': snapshot.working_directory,
                'git_branch': snapshot.git_branch,
                'metadata': snapshot.metadata
            }
            for snapshot in self.context_snapshots
        ],
        'summary': {
            'total_actions': len(self.actions),
            'total_errors': len(self.errors_encountered),
            'error_rate': self.get_error_rate(),
            'file_access_pattern': self.get_file_access_pattern()
        }
    }

def checkpoint_trace_from_dict(cls, data: Dict[str, Any]) -> 'CheckpointTrace':
    """Create CheckpointTrace from dictionary"""
    checkpoint_trace = cls(
        checkpoint_id=data['checkpoint_id'],
        start_timestamp=data['start_timestamp'],
        end_timestamp=data.get('end_timestamp'),
        tests_passed=data.get('tests_passed', False),
        completion_duration_ms=data.get('completion_duration_ms')
    )
    
    # Recreate actions
    for action_data in data.get('actions', []):
        action = ActionTraceEntry(
            timestamp=action_data['timestamp'],
            action_type=ActionType(action_data['action_type']),
            success=action_data['success'],
            file_path=action_data.get('file_path'),
            function_name=action_data.get('function_name'),
            checkpoint_id=action_data.get('checkpoint_id'),
            duration_ms=action_data.get('duration_ms'),
            context_size_tokens=action_data.get('context_size_tokens', 0),
            metadata=action_data.get('metadata', {})
        )
        checkpoint_trace.add_action(action)
    
    # Recreate context snapshots
    for snapshot_data in data.get('context_snapshots', []):
        snapshot = ContextSnapshot(
            timestamp=snapshot_data['timestamp'],
            checkpoint_id=snapshot_data.get('checkpoint_id'),
            files_in_context=snapshot_data.get('files_in_context', []),
            context_token_count=snapshot_data.get('context_token_count', 0),
            working_memory_items=snapshot_data.get('working_memory_items', []),
            recent_actions_count=snapshot_data.get('recent_actions_count', 0),
            working_directory=snapshot_data.get('working_directory', ''),
            git_branch=snapshot_data.get('git_branch', 'main'),
            metadata=snapshot_data.get('metadata', {})
        )
        checkpoint_trace.add_context_snapshot(snapshot)
    
    return checkpoint_trace

# Monkey patch the methods
CheckpointTrace.to_dict = checkpoint_trace_to_dict
CheckpointTrace.from_dict = classmethod(checkpoint_trace_from_dict)


class ActionTracer:
    """
    Action tracer for capturing agent behavior during task execution.
    
    This class provides the interface for recording agent actions and
    building the behavioral traces needed for working memory evaluation.
    """
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.task_trace = TaskTrace(task_id=task_id, start_timestamp=time.time())
        self.current_checkpoint_trace: Optional[CheckpointTrace] = None
    
    def start_checkpoint(self, checkpoint_id: str) -> None:
        """Start tracing a new checkpoint"""
        if self.current_checkpoint_trace:
            # Complete previous checkpoint if not already completed
            if not self.current_checkpoint_trace.end_timestamp:
                self.current_checkpoint_trace.complete_checkpoint(False)
            self.task_trace.add_checkpoint_trace(self.current_checkpoint_trace)
        
        self.current_checkpoint_trace = CheckpointTrace(
            checkpoint_id=checkpoint_id,
            start_timestamp=time.time()
        )
    
    def log_action(self, 
                   action_type: ActionType,
                   success: bool = True,
                   file_path: Optional[str] = None,
                   function_name: Optional[str] = None,
                   duration_ms: Optional[float] = None,
                   context_size_tokens: int = 0,
                   **metadata) -> ActionTraceEntry:
        """Log an agent action"""
        action = ActionTraceEntry(
            timestamp=time.time(),
            action_type=action_type,
            success=success,
            file_path=file_path,
            function_name=function_name,
            duration_ms=duration_ms,
            context_size_tokens=context_size_tokens,
            checkpoint_id=self.current_checkpoint_trace.checkpoint_id if self.current_checkpoint_trace else None,
            metadata=metadata
        )
        
        if self.current_checkpoint_trace:
            self.current_checkpoint_trace.add_action(action)
        
        return action
    
    def log_context_snapshot(self, 
                           files_in_context: List[str],
                           context_token_count: int = 0,
                           working_directory: str = "",
                           **metadata) -> ContextSnapshot:
        """Log a context snapshot"""
        snapshot = ContextSnapshot(
            timestamp=time.time(),
            checkpoint_id=self.current_checkpoint_trace.checkpoint_id if self.current_checkpoint_trace else None,
            files_in_context=files_in_context,
            context_token_count=context_token_count,
            working_directory=working_directory,
            metadata=metadata
        )
        
        if self.current_checkpoint_trace:
            self.current_checkpoint_trace.add_context_snapshot(snapshot)
        
        return snapshot
    
    def complete_checkpoint(self, tests_passed: bool) -> Optional[CheckpointTrace]:
        """Complete the current checkpoint"""
        if not self.current_checkpoint_trace:
            return None
        
        self.current_checkpoint_trace.complete_checkpoint(tests_passed)
        completed_trace = self.current_checkpoint_trace
        
        self.task_trace.add_checkpoint_trace(completed_trace)
        self.current_checkpoint_trace = None
        
        return completed_trace
    
    def complete_task(self, completed_successfully: bool) -> TaskTrace:
        """Complete the task trace"""
        # Complete any open checkpoint
        if self.current_checkpoint_trace:
            self.complete_checkpoint(False)
        
        self.task_trace.complete_task(completed_successfully)
        return self.task_trace
    
    def get_task_trace(self) -> TaskTrace:
        """Get the current task trace"""
        return self.task_trace
    
    def save_trace(self, file_path: Union[str, Path]) -> None:
        """Save task trace to file"""
        path = Path(file_path)
        with open(path, 'w') as f:
            json.dump(self.task_trace.to_dict(), f, indent=2)
    
    @classmethod
    def load_trace(cls, file_path: Union[str, Path]) -> 'TaskTrace':
        """Load task trace from file"""
        path = Path(file_path)
        with open(path, 'r') as f:
            data = json.load(f)
        return TaskTrace.from_dict(data)
