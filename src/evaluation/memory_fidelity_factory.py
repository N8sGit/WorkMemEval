"""
WorkMemEval: Memory Fidelity Metrics Factory

This module provides factory functions to create MemoryFidelityMetrics objects
from TaskTrace data using the comprehensive memory_metrics calculations.
"""

from typing import List, Optional, Dict, Any
from ..core.action_trace import TaskTrace, ContextSnapshot
from ..core.evaluation_results import MemoryFidelityMetrics
from .memory_metrics import (
    calculate_context_reread_rate,
    calculate_size_weighted_reread_penalty,
    calculate_information_retention_score,
    calculate_memory_compression_efficiency,
    analyze_memory_degradation_over_time,
    get_memory_fidelity_diagnostics
)


def create_memory_fidelity_metrics(task_trace: TaskTrace,
                                  context_snapshots: Optional[List[ContextSnapshot]] = None) -> MemoryFidelityMetrics:
    """
    Create comprehensive MemoryFidelityMetrics from a TaskTrace.
    
    Args:
        task_trace: Complete task execution trace
        context_snapshots: Optional list of context snapshots for compression analysis
        
    Returns:
        MemoryFidelityMetrics object with calculated scores and diagnostics
    """
    # Extract context snapshots from task trace if not provided
    if context_snapshots is None:
        context_snapshots = []
        for checkpoint_trace in task_trace.checkpoint_traces:
            context_snapshots.extend(checkpoint_trace.context_snapshots)
    
    # Calculate core memory fidelity metrics
    context_reread_rate = calculate_context_reread_rate(task_trace)
    size_weighted_penalty = calculate_size_weighted_reread_penalty(task_trace)
    retention_score = calculate_information_retention_score(task_trace)
    compression_efficiency = calculate_memory_compression_efficiency(task_trace, context_snapshots)
    
    # Perform temporal analysis
    degradation_analysis = analyze_memory_degradation_over_time(task_trace)
    
    # Get comprehensive diagnostics
    diagnostics = get_memory_fidelity_diagnostics(
        context_reread_rate=context_reread_rate,
        size_weighted_penalty=size_weighted_penalty,
        compression_efficiency=compression_efficiency,
        retention_score=retention_score,
        degradation_analysis=degradation_analysis
    )
    
    # Create comprehensive file access statistics
    file_access_statistics = _build_file_access_statistics(task_trace)
    
    # Create compression events log
    compression_events = _build_compression_events(context_snapshots)
    
    # Create MemoryFidelityMetrics with all calculated values
    metrics = MemoryFidelityMetrics(
        context_reread_rate=context_reread_rate,
        size_weighted_reread_penalty=size_weighted_penalty,
        information_retention_score=retention_score,
        compression_efficiency=compression_efficiency,
        degradation_analysis=degradation_analysis,
        overall_fidelity_score=0.0,  # Will be calculated in __post_init__
        diagnostics=diagnostics,
        file_access_statistics=file_access_statistics,
        compression_events=compression_events
    )
    
    return metrics


def _build_file_access_statistics(task_trace: TaskTrace) -> Dict[str, Any]:
    """
    Build detailed file access statistics for supporting analysis.
    
    Args:
        task_trace: Complete task execution trace
        
    Returns:
        Dictionary containing detailed file access patterns and statistics
    """
    file_access_patterns = {}
    total_reads = 0
    total_bytes_read = 0
    
    # Analyze file access patterns across all checkpoints
    for checkpoint_trace in task_trace.checkpoint_traces:
        for action in checkpoint_trace.actions:
            if (action.action_type.value == 'file_read' and  # Use .value to get string
                action.success and 
                action.file_path):
                
                file_path = action.file_path
                if file_path not in file_access_patterns:
                    file_access_patterns[file_path] = {
                        'read_count': 0,
                        'total_bytes': 0,
                        'checkpoints_accessed': set(),
                        'first_access': action.timestamp,
                        'last_access': action.timestamp,
                        'size_bytes': 0
                    }
                
                # Update access statistics
                pattern = file_access_patterns[file_path]
                pattern['read_count'] += 1
                pattern['checkpoints_accessed'].add(checkpoint_trace.checkpoint_id)
                pattern['last_access'] = action.timestamp
                
                if 'size_bytes' in action.metadata:
                    size_bytes = action.metadata['size_bytes']
                    pattern['total_bytes'] += size_bytes
                    pattern['size_bytes'] = size_bytes  # File size (should be consistent)
                    total_bytes_read += size_bytes
                
                total_reads += 1
    
    # Convert sets to lists for serialization
    for pattern in file_access_patterns.values():
        pattern['checkpoints_accessed'] = list(pattern['checkpoints_accessed'])
        pattern['access_span_seconds'] = pattern['last_access'] - pattern['first_access']
    
    # Calculate summary statistics
    files_read = list(file_access_patterns.keys())
    files_reread = [f for f, p in file_access_patterns.items() if p['read_count'] > 1]
    
    return {
        'total_file_reads': total_reads,
        'unique_files_read': len(files_read),
        'files_reread': files_reread,
        'reread_count': len(files_reread),
        'total_bytes_read': total_bytes_read,
        'average_file_size': total_bytes_read / len(files_read) if files_read else 0,
        'file_access_patterns': file_access_patterns,
        'reread_statistics': {
            'unnecessary_reads': total_reads - len(files_read),
            'reread_rate': (total_reads - len(files_read)) / total_reads if total_reads > 0 else 0.0,
            'most_reread_file': max(file_access_patterns.items(), 
                                  key=lambda x: x[1]['read_count'], 
                                  default=(None, {'read_count': 0}))[0],
            'largest_reread_penalty': max(
                [p['total_bytes'] - p['size_bytes'] for p in file_access_patterns.values()],
                default=0
            )
        }
    }


def _build_compression_events(context_snapshots: List[ContextSnapshot]) -> List[Dict[str, Any]]:
    """
    Build compression events log from context snapshots.
    
    Args:
        context_snapshots: List of context snapshots during execution
        
    Returns:
        List of compression events with analysis
    """
    compression_events = []
    
    for i, snapshot in enumerate(sorted(context_snapshots, key=lambda s: s.timestamp)):
        event = {
            'timestamp': snapshot.timestamp,
            'checkpoint_id': snapshot.checkpoint_id,
            'files_in_context_count': len(snapshot.files_in_context),
            'context_token_count': snapshot.context_token_count,
            'working_memory_items_count': len(snapshot.working_memory_items),
            'compression_ratio': 0.0
        }
        
        # Calculate compression ratio if we have file size information
        # This is a simplified calculation - in a real system we'd have more context
        if snapshot.files_in_context:
            # Estimate original size based on typical file sizes
            estimated_original_size = len(snapshot.files_in_context) * 1000  # Rough estimate
            if estimated_original_size > 0:
                event['compression_ratio'] = snapshot.context_token_count / estimated_original_size
        
        # Add delta from previous snapshot if available
        if i > 0:
            prev_event = compression_events[i - 1]
            event['delta_files'] = event['files_in_context_count'] - prev_event['files_in_context_count']
            event['delta_tokens'] = event['context_token_count'] - prev_event['context_token_count']
            event['time_delta_seconds'] = event['timestamp'] - prev_event['timestamp']
        
        compression_events.append(event)
    
    return compression_events


def create_memory_fidelity_metrics_from_checkpoint_traces(checkpoint_traces: List,
                                                         task_id: str = "aggregated") -> MemoryFidelityMetrics:
    """
    Create aggregated MemoryFidelityMetrics from a list of checkpoint traces.
    
    Useful for creating task-level metrics from individual checkpoint results.
    
    Args:
        checkpoint_traces: List of CheckpointTrace objects
        task_id: ID for the aggregated task
        
    Returns:
        Aggregated MemoryFidelityMetrics
    """
    # Create a synthetic TaskTrace for metric calculation
    import time
    from ..core.action_trace import TaskTrace
    
    task_trace = TaskTrace(
        task_id=task_id,
        start_timestamp=time.time(),
        checkpoint_traces=checkpoint_traces
    )
    
    # Calculate metrics using the main factory function
    return create_memory_fidelity_metrics(task_trace)


# Convenience function for testing with synthetic traces
def create_test_memory_fidelity_metrics(trace_type: str = "perfect_memory") -> MemoryFidelityMetrics:
    """
    Create test MemoryFidelityMetrics using synthetic traces.
    
    Args:
        trace_type: Type of synthetic trace to generate
                   Options: "perfect_memory", "high_rereads", "size_weighted", 
                           "degrading_memory", "mixed_performance", "with_compression"
        
    Returns:
        MemoryFidelityMetrics for testing
    """
    from ..tests.test_helpers.synthetic_traces import generate_all_test_traces
    
    traces = generate_all_test_traces()
    if trace_type not in traces:
        raise ValueError(f"Unknown trace type: {trace_type}. Options: {list(traces.keys())}")
    
    task_trace = traces[trace_type]
    return create_memory_fidelity_metrics(task_trace)
