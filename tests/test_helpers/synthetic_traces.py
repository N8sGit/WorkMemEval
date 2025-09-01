"""
WorkMemEval: Synthetic Trace Generators for Testing

This module provides utilities to generate synthetic TaskTraces with known
memory patterns for validating memory fidelity metrics. Each generator creates
traces with predictable behaviors that can be used to test metric correctness.
"""

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.core.action_trace import (
    TaskTrace, CheckpointTrace, ActionTraceEntry, ContextSnapshot, ActionType
)


@dataclass
class TraceGenerationConfig:
    """Configuration for synthetic trace generation"""
    task_id: str = "synthetic_task"
    num_checkpoints: int = 3
    files_per_checkpoint: int = 2
    base_file_size: int = 1000  # bytes
    reread_probability: float = 0.0  # 0.0 = no rereads, 1.0 = always reread
    size_variance: float = 0.2  # Random variation in file sizes
    timestamp_interval: float = 1.0  # Seconds between actions


def generate_perfect_memory_trace(config: TraceGenerationConfig) -> TaskTrace:
    """
    Generate a trace showing perfect memory behavior.
    
    Characteristics:
    - No file rereads (each file read exactly once)
    - Consistent memory usage across checkpoints
    - Good information retention
    
    Args:
        config: Configuration for trace generation
        
    Returns:
        TaskTrace with perfect memory behavior patterns
    """
    task_trace = TaskTrace(
        task_id=config.task_id,
        start_timestamp=time.time()
    )
    
    current_time = task_trace.start_timestamp
    files_seen = set()
    
    for checkpoint_idx in range(config.num_checkpoints):
        checkpoint_id = f"cp_{checkpoint_idx + 1}"
        checkpoint_trace = CheckpointTrace(
            checkpoint_id=checkpoint_id,
            start_timestamp=current_time
        )
        
        # Create new files for this checkpoint (no rereads)
        for file_idx in range(config.files_per_checkpoint):
            file_path = f"file_{checkpoint_idx}_{file_idx}.py"
            file_size = int(config.base_file_size * (1 + config.size_variance * (file_idx - 1)))
            
            # Only read if not seen before (perfect memory)
            if file_path not in files_seen:
                action = ActionTraceEntry(
                    timestamp=current_time,
                    action_type=ActionType.FILE_READ,
                    success=True,
                    file_path=file_path,
                    checkpoint_id=checkpoint_id,
                    metadata={"size_bytes": file_size}
                )
                checkpoint_trace.add_action(action)
                files_seen.add(file_path)
                current_time += config.timestamp_interval
        
        # Add some implementation actions
        impl_action = ActionTraceEntry(
            timestamp=current_time,
            action_type=ActionType.LLM_CALL,
            success=True,
            checkpoint_id=checkpoint_id,
            metadata={"description": f"Implement {checkpoint_id}", "response_length": 500}
        )
        checkpoint_trace.add_action(impl_action)
        current_time += config.timestamp_interval
        
        checkpoint_trace.complete_checkpoint(True)
        task_trace.add_checkpoint_trace(checkpoint_trace)
    
    return task_trace


def generate_high_reread_trace(config: TraceGenerationConfig) -> TaskTrace:
    """
    Generate a trace showing poor memory behavior with many rereads.
    
    Characteristics:
    - High file reread rate (rereads files in each checkpoint)
    - Memory degradation over time
    - Poor information retention
    
    Args:
        config: Configuration for trace generation
        
    Returns:
        TaskTrace with high reread patterns
    """
    task_trace = TaskTrace(
        task_id=config.task_id,
        start_timestamp=time.time()
    )
    
    current_time = task_trace.start_timestamp
    all_files = []  # Track all files for rereading
    
    for checkpoint_idx in range(config.num_checkpoints):
        checkpoint_id = f"cp_{checkpoint_idx + 1}"
        checkpoint_trace = CheckpointTrace(
            checkpoint_id=checkpoint_id,
            start_timestamp=current_time
        )
        
        # Create new files for this checkpoint
        checkpoint_files = []
        for file_idx in range(config.files_per_checkpoint):
            file_path = f"file_{checkpoint_idx}_{file_idx}.py"
            file_size = int(config.base_file_size * (1 + config.size_variance * (file_idx - 1)))
            checkpoint_files.append((file_path, file_size))
        
        all_files.extend(checkpoint_files)
        
        # Poor memory: reread files from previous checkpoints
        files_to_read = checkpoint_files[:]
        if checkpoint_idx > 0:
            # Add rereads from previous checkpoints
            import random
            random.seed(42)  # Deterministic for testing
            num_rereads = min(len(all_files) - len(checkpoint_files), 3)
            previous_files = [f for f in all_files if f not in checkpoint_files]
            rereads = random.sample(previous_files, min(num_rereads, len(previous_files)))
            files_to_read.extend(rereads)
        
        # Read all files (including rereads)
        for file_path, file_size in files_to_read:
            action = ActionTraceEntry(
                timestamp=current_time,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path=file_path,
                checkpoint_id=checkpoint_id,
                metadata={"size_bytes": file_size}
            )
            checkpoint_trace.add_action(action)
            current_time += config.timestamp_interval
        
        # Add implementation action
        impl_action = ActionTraceEntry(
            timestamp=current_time,
            action_type=ActionType.LLM_CALL,
            success=True,
            checkpoint_id=checkpoint_id,
            metadata={"description": f"Implement {checkpoint_id}", "response_length": 300}
        )
        checkpoint_trace.add_action(impl_action)
        current_time += config.timestamp_interval
        
        checkpoint_trace.complete_checkpoint(True)
        task_trace.add_checkpoint_trace(checkpoint_trace)
    
    return task_trace


def generate_size_weighted_scenario_trace(config: TraceGenerationConfig) -> TaskTrace:
    """
    Generate a trace with size-weighted reread patterns for testing size penalties.
    
    Characteristics:
    - Small files read once, large files reread multiple times
    - Clear size-based penalty patterns
    - Mix of efficient and inefficient memory usage
    
    Args:
        config: Configuration for trace generation
        
    Returns:
        TaskTrace with size-weighted reread patterns
    """
    task_trace = TaskTrace(
        task_id=config.task_id,
        start_timestamp=time.time()
    )
    
    current_time = task_trace.start_timestamp
    
    # Define file types with different sizes
    small_file_size = 500
    large_file_size = 5000
    
    files = [
        ("small_file_1.py", small_file_size),
        ("large_file_1.py", large_file_size),
        ("small_file_2.py", small_file_size),
        ("large_file_2.py", large_file_size)
    ]
    
    for checkpoint_idx in range(config.num_checkpoints):
        checkpoint_id = f"cp_{checkpoint_idx + 1}"
        checkpoint_trace = CheckpointTrace(
            checkpoint_id=checkpoint_id,
            start_timestamp=current_time
        )
        
        # First checkpoint: read all files once
        if checkpoint_idx == 0:
            files_to_read = files
        else:
            # Later checkpoints: reread large files, skip small files (good memory for small)
            files_to_read = [(path, size) for path, size in files if "large" in path]
        
        for file_path, file_size in files_to_read:
            action = ActionTraceEntry(
                timestamp=current_time,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path=file_path,
                checkpoint_id=checkpoint_id,
                metadata={"size_bytes": file_size}
            )
            checkpoint_trace.add_action(action)
            current_time += config.timestamp_interval
        
        # Add implementation action
        impl_action = ActionTraceEntry(
            timestamp=current_time,
            action_type=ActionType.LLM_CALL,
            success=True,
            checkpoint_id=checkpoint_id,
            metadata={"description": f"Implement {checkpoint_id}", "response_length": 400}
        )
        checkpoint_trace.add_action(impl_action)
        current_time += config.timestamp_interval
        
        checkpoint_trace.complete_checkpoint(True)
        task_trace.add_checkpoint_trace(checkpoint_trace)
    
    return task_trace


def generate_degrading_memory_trace(config: TraceGenerationConfig) -> TaskTrace:
    """
    Generate a trace showing memory performance degradation over time.
    
    Characteristics:
    - Good memory performance in early checkpoints
    - Increasingly poor memory in later checkpoints
    - Clear degradation trend
    
    Args:
        config: Configuration for trace generation
        
    Returns:
        TaskTrace with degrading memory performance
    """
    task_trace = TaskTrace(
        task_id=config.task_id,
        start_timestamp=time.time()
    )
    
    current_time = task_trace.start_timestamp
    all_files = []
    
    for checkpoint_idx in range(config.num_checkpoints):
        checkpoint_id = f"cp_{checkpoint_idx + 1}"
        checkpoint_trace = CheckpointTrace(
            checkpoint_id=checkpoint_id,
            start_timestamp=current_time
        )
        
        # Create new files for this checkpoint
        checkpoint_files = []
        for file_idx in range(config.files_per_checkpoint):
            file_path = f"file_{checkpoint_idx}_{file_idx}.py"
            file_size = config.base_file_size + (file_idx * 200)
            checkpoint_files.append((file_path, file_size))
        
        all_files.extend(checkpoint_files)
        
        # Memory degrades over time - more rereads in later checkpoints
        reread_rate = checkpoint_idx / max(1, config.num_checkpoints - 1)
        
        files_to_read = checkpoint_files[:]
        
        if checkpoint_idx > 0 and reread_rate > 0:
            # Add rereads based on degradation
            import random
            random.seed(42 + checkpoint_idx)  # Different seed per checkpoint
            
            previous_files = [f for f in all_files if f not in checkpoint_files]
            num_rereads = int(len(previous_files) * reread_rate)
            
            if num_rereads > 0:
                rereads = random.sample(previous_files, min(num_rereads, len(previous_files)))
                files_to_read.extend(rereads)
        
        # Read all files
        for file_path, file_size in files_to_read:
            action = ActionTraceEntry(
                timestamp=current_time,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path=file_path,
                checkpoint_id=checkpoint_id,
                metadata={"size_bytes": file_size}
            )
            checkpoint_trace.add_action(action)
            current_time += config.timestamp_interval
        
        # Add implementation action
        impl_action = ActionTraceEntry(
            timestamp=current_time,
            action_type=ActionType.LLM_CALL,
            success=True,
            checkpoint_id=checkpoint_id,
            metadata={"description": f"Implement {checkpoint_id}", "response_length": 350}
        )
        checkpoint_trace.add_action(impl_action)
        current_time += config.timestamp_interval
        
        checkpoint_trace.complete_checkpoint(True)
        task_trace.add_checkpoint_trace(checkpoint_trace)
    
    return task_trace


def generate_mixed_performance_trace(config: TraceGenerationConfig) -> TaskTrace:
    """
    Generate a trace with mixed memory performance patterns.
    
    Characteristics:
    - Some checkpoints show good memory, others poor
    - Inconsistent memory performance
    - Mix of different memory behaviors
    
    Args:
        config: Configuration for trace generation
        
    Returns:
        TaskTrace with mixed memory performance patterns
    """
    task_trace = TaskTrace(
        task_id=config.task_id,
        start_timestamp=time.time()
    )
    
    current_time = task_trace.start_timestamp
    all_files = []
    
    # Define performance pattern: alternating good/bad performance
    performance_pattern = ["good", "poor", "good", "poor", "moderate"]
    
    for checkpoint_idx in range(config.num_checkpoints):
        checkpoint_id = f"cp_{checkpoint_idx + 1}"
        checkpoint_trace = CheckpointTrace(
            checkpoint_id=checkpoint_id,
            start_timestamp=current_time
        )
        
        # Create new files for this checkpoint
        checkpoint_files = []
        for file_idx in range(config.files_per_checkpoint):
            file_path = f"file_{checkpoint_idx}_{file_idx}.py"
            file_size = config.base_file_size + (file_idx * 300)
            checkpoint_files.append((file_path, file_size))
        
        all_files.extend(checkpoint_files)
        
        # Determine memory behavior for this checkpoint
        behavior = performance_pattern[checkpoint_idx % len(performance_pattern)]
        files_to_read = checkpoint_files[:]
        
        if checkpoint_idx > 0:
            previous_files = [f for f in all_files if f not in checkpoint_files]
            
            if behavior == "poor":
                # Reread most previous files
                import random
                random.seed(42 + checkpoint_idx)
                num_rereads = min(len(previous_files), 4)
                rereads = random.sample(previous_files, num_rereads)
                files_to_read.extend(rereads)
            elif behavior == "moderate":
                # Reread some previous files
                import random
                random.seed(42 + checkpoint_idx)
                num_rereads = min(len(previous_files) // 2, 2)
                if num_rereads > 0:
                    rereads = random.sample(previous_files, num_rereads)
                    files_to_read.extend(rereads)
            # "good" behavior: no rereads (already in files_to_read)
        
        # Read all files
        for file_path, file_size in files_to_read:
            action = ActionTraceEntry(
                timestamp=current_time,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path=file_path,
                checkpoint_id=checkpoint_id,
                metadata={"size_bytes": file_size}
            )
            checkpoint_trace.add_action(action)
            current_time += config.timestamp_interval
        
        # Add implementation action
        impl_action = ActionTraceEntry(
            timestamp=current_time,
            action_type=ActionType.LLM_CALL,
            success=True,
            checkpoint_id=checkpoint_id,
            metadata={"description": f"Implement {checkpoint_id}", "response_length": 375}
        )
        checkpoint_trace.add_action(impl_action)
        current_time += config.timestamp_interval
        
        checkpoint_trace.complete_checkpoint(True)
        task_trace.add_checkpoint_trace(checkpoint_trace)
    
    return task_trace


def generate_trace_with_context_snapshots(config: TraceGenerationConfig,
                                         memory_efficiency: float = 0.5) -> TaskTrace:
    """
    Generate a trace that includes context snapshots for compression efficiency testing.
    
    Args:
        config: Configuration for trace generation
        memory_efficiency: How efficiently memory compresses information (0.0-1.0)
        
    Returns:
        TaskTrace with context snapshots
    """
    task_trace = generate_perfect_memory_trace(config)
    
    # Add context snapshots to each checkpoint
    total_bytes_read = 0
    
    for checkpoint_trace in task_trace.checkpoint_traces:
        checkpoint_bytes = 0
        
        # Calculate bytes read in this checkpoint
        for action in checkpoint_trace.actions:
            if (action.action_type == ActionType.FILE_READ and 
                'size_bytes' in action.metadata):
                checkpoint_bytes += action.metadata['size_bytes']
        
        total_bytes_read += checkpoint_bytes
        
        # Create context snapshot showing memory compression
        compressed_size = int(total_bytes_read * memory_efficiency)
        
        snapshot = ContextSnapshot(
            timestamp=checkpoint_trace.start_timestamp + 5.0,  # Mid-checkpoint
            checkpoint_id=checkpoint_trace.checkpoint_id,
            files_in_context=[
                action.file_path for action in checkpoint_trace.actions 
                if action.action_type == ActionType.FILE_READ and action.file_path
            ],
            context_token_count=compressed_size,
            working_memory_items=[
                f"Summary of {checkpoint_trace.checkpoint_id}",
                f"Key insights from files"
            ],
            working_directory="/test/workspace"
        )
        
        checkpoint_trace.add_context_snapshot(snapshot)
    
    return task_trace


# Convenience function to generate all test traces
def generate_all_test_traces() -> Dict[str, TaskTrace]:
    """
    Generate a complete set of test traces for comprehensive metric validation.
    
    Returns:
        Dictionary mapping trace names to TaskTrace objects
    """
    config = TraceGenerationConfig(
        num_checkpoints=4,
        files_per_checkpoint=3,
        base_file_size=1000
    )
    
    traces = {
        "perfect_memory": generate_perfect_memory_trace(config),
        "high_rereads": generate_high_reread_trace(config),
        "size_weighted": generate_size_weighted_scenario_trace(config),
        "degrading_memory": generate_degrading_memory_trace(config),
        "mixed_performance": generate_mixed_performance_trace(config),
        "with_compression": generate_trace_with_context_snapshots(config, memory_efficiency=0.3)
    }
    
    return traces
