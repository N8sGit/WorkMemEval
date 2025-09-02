"""
WorkMemEval: Three-Pillar Working Memory Metrics

This module implements comprehensive working memory evaluation metrics based on the
three-pillar framework:

1. Memory Fidelity: How well does the agent retain and manage information?
2. Contextual Relevance: How precisely does the agent focus on relevant information?
3. Behavioral Integrity: How consistently does the agent execute its intended plan?

Each pillar provides multiple quantitative metrics that together paint a complete
picture of an agent's working memory capabilities.
"""

from typing import Dict, List, Tuple, Optional, Any, Set, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import time
import statistics
import numpy as np
from pathlib import Path
import re
import math
from collections import defaultdict

from ..core.action_trace import TaskTrace, CheckpointTrace, ActionTraceEntry, ActionType, ContextSnapshot
from ..core.task_specification import TaskSpecification, CheckpointSpecification
from ..utils.file_utils import basename
from ..utils.math_utils import avg


def calculate_context_reread_rate(task_trace: TaskTrace) -> float:
    """
    Calculate the rate of unnecessary context rereading.
    
    This measures how often an agent rereads files it has already accessed,
    indicating potential memory retention issues.
    
    Formula: (total_file_reads - unique_files_read) / total_file_reads
    
    Args:
        task_trace: Complete task execution trace
        
    Returns:
        Float between 0.0 and 1.0, where:
        - 0.0 = Perfect memory (no unnecessary rereads)
        - 1.0 = Complete memory failure (rereading everything)
    """
    total_reads = 0
    unique_files = set()
    
    # Analyze all checkpoint traces
    for checkpoint_trace in task_trace.checkpoint_traces:
        for action in checkpoint_trace.actions:
            if (action.action_type == ActionType.FILE_READ and 
                action.success and 
                action.file_path):
                
                total_reads += 1
                unique_files.add(action.file_path)
    
    if total_reads == 0:
        return 0.0  # No reads means no rereads
    
    unnecessary_reads = total_reads - len(unique_files)
    return unnecessary_reads / total_reads


def calculate_size_weighted_reread_penalty(task_trace: TaskTrace) -> float:
    """
    Calculate a size-weighted penalty for unnecessary rereads.
    
    Larger files that are reread should incur higher penalties since they
    represent more wasted processing effort.
    
    Args:
        task_trace: Complete task execution trace
        
    Returns:
        Float penalty score where higher values indicate worse memory efficiency
    """
    file_read_history = defaultdict(list)  # file_path -> list of (timestamp, size)
    
    # Collect all file reads with sizes
    for checkpoint_trace in task_trace.checkpoint_traces:
        for action in checkpoint_trace.actions:
            if (action.action_type == ActionType.FILE_READ and 
                action.success and 
                action.file_path and
                'size_bytes' in action.metadata):
                
                file_read_history[action.file_path].append(
                    (action.timestamp, action.metadata['size_bytes'])
                )
    
    total_penalty = 0.0
    total_bytes_processed = 0
    
    # Calculate penalty for each file
    for file_path, reads in file_read_history.items():
        if len(reads) <= 1:
            # No rereads for this file
            try:
                total_bytes_processed += reads[0][1] if reads else 0
            except (TypeError, IndexError):
                # Handle corrupted metadata gracefully
                continue
            continue
            
        # Sort by timestamp to get chronological order
        reads.sort(key=lambda x: x[0])
        
        # First read is necessary, subsequent reads are penalties
        try:
            first_read_size = reads[0][1]
            total_bytes_processed += first_read_size
            
            for timestamp, size in reads[1:]:
                total_penalty += size
                total_bytes_processed += size
        except (TypeError, IndexError):
            # Handle corrupted metadata gracefully
            continue
    
    if total_bytes_processed == 0:
        return 0.0
    
    # Return penalty as fraction of total processing
    return total_penalty / total_bytes_processed


def calculate_memory_compression_efficiency(task_trace: TaskTrace, 
                                          memory_snapshots: List[ContextSnapshot]) -> float:
    """
    Calculate how efficiently the agent compresses information into memory.
    
    This compares the amount of information stored in working memory versus
    the total amount of information processed from files.
    
    Args:
        task_trace: Complete task execution trace
        memory_snapshots: List of memory state snapshots during execution
        
    Returns:
        Float efficiency score where higher values indicate better compression
    """
    total_bytes_read = 0
    
    # Calculate total information processed
    for checkpoint_trace in task_trace.checkpoint_traces:
        for action in checkpoint_trace.actions:
            if (action.action_type == ActionType.FILE_READ and 
                action.success and
                'size_bytes' in action.metadata):
                total_bytes_read += action.metadata['size_bytes']
    
    if total_bytes_read == 0:
        return 1.0  # Perfect efficiency if no data to compress
    
    # Use the most recent memory snapshot to assess compression
    if not memory_snapshots:
        return 0.0  # No compression if no memory maintained
    
    latest_snapshot = max(memory_snapshots, key=lambda s: s.timestamp)
    memory_content_size = latest_snapshot.context_token_count
    
    if memory_content_size == 0:
        return 0.0  # No information retained
    
    # Simple compression ratio: memory_content / total_input
    # This is inverted so higher values = better compression
    # Cap at 1.0 to represent perfect compression
    compression_ratio = min(1.0, memory_content_size / total_bytes_read)
    
    return compression_ratio


def calculate_information_retention_score(task_trace: TaskTrace) -> float:
    """
    Calculate how well the agent retains important information over time.
    
    This measures whether agents maintain access to key information across
    checkpoint boundaries without needing to reread everything.
    
    Args:
        task_trace: Complete task execution trace
        
    Returns:
        Float score between 0.0 and 1.0 where higher values indicate better retention
    """
    if len(task_trace.checkpoint_traces) <= 1:
        return 1.0  # Perfect retention if only one checkpoint
    
    # Track which files are accessed in each checkpoint
    checkpoint_file_accesses = []
    
    for checkpoint_trace in task_trace.checkpoint_traces:
        checkpoint_files = set()
        
        for action in checkpoint_trace.actions:
            if (action.action_type == ActionType.FILE_READ and 
                action.success and 
                action.file_path):
                checkpoint_files.add(action.file_path)
        
        checkpoint_file_accesses.append(checkpoint_files)
    
    # Calculate retention score based on cross-checkpoint file access patterns
    total_retention_opportunities = 0
    successful_retentions = 0
    
    # Look for files that should be retained across checkpoints
    for i in range(len(checkpoint_file_accesses) - 1):
        current_files = checkpoint_file_accesses[i]
        next_files = checkpoint_file_accesses[i + 1]
        
        # Files accessed in current checkpoint are retention opportunities
        total_retention_opportunities += len(current_files)
        
        # Files that don't need to be reread in next checkpoint show good retention
        files_not_reread = current_files - next_files
        successful_retentions += len(files_not_reread)
    
    if total_retention_opportunities == 0:
        return 1.0
    
    return successful_retentions / total_retention_opportunities


def analyze_memory_degradation_over_time(task_trace: TaskTrace) -> Dict[str, Any]:
    """
    Analyze how memory performance changes over the course of task execution.
    
    This provides checkpoint-by-checkpoint analysis of memory metrics to identify
    when and where memory degradation occurs.
    
    Args:
        task_trace: Complete task execution trace
        
    Returns:
        Dictionary containing:
        - checkpoint_reread_rates: List of reread rates per checkpoint
        - degradation_trend: Overall trend (improving/degrading/stable)
        - peak_degradation_checkpoint: Checkpoint with worst memory performance
        - memory_consistency: How consistent memory performance is across checkpoints
    """
    checkpoint_reread_rates = []
    checkpoint_file_counts = []
    
    cumulative_files = set()  # Files seen across all previous checkpoints
    
    for i, checkpoint_trace in enumerate(task_trace.checkpoint_traces):
        checkpoint_reads = 0
        checkpoint_files = set()
        checkpoint_rereads = 0
        
        for action in checkpoint_trace.actions:
            if (action.action_type == ActionType.FILE_READ and 
                action.success and 
                action.file_path):
                
                checkpoint_reads += 1
                checkpoint_files.add(action.file_path)
                
                # Check if this is a reread from previous checkpoints
                if action.file_path in cumulative_files:
                    checkpoint_rereads += 1
        
        # Calculate reread rate for this checkpoint
        if checkpoint_reads > 0:
            reread_rate = checkpoint_rereads / checkpoint_reads
        else:
            reread_rate = 0.0
        
        checkpoint_reread_rates.append(reread_rate)
        checkpoint_file_counts.append(len(checkpoint_files))
        
        # Update cumulative files for next iteration
        cumulative_files.update(checkpoint_files)
    
    # Analyze trends
    if len(checkpoint_reread_rates) <= 1:
        degradation_trend = "stable"
        memory_consistency = 1.0
        peak_degradation_checkpoint = 0
    else:
        # Calculate trend using simple linear correlation
        n = len(checkpoint_reread_rates)
        x_mean = (n - 1) / 2
        y_mean = sum(checkpoint_reread_rates) / n
        
        numerator = sum((i - x_mean) * (rate - y_mean) for i, rate in enumerate(checkpoint_reread_rates))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        if slope > 0.1:
            degradation_trend = "degrading"
        elif slope < -0.1:
            degradation_trend = "improving"
        else:
            degradation_trend = "stable"
        
        # Memory consistency (inverse of variance)
        variance = sum((rate - y_mean) ** 2 for rate in checkpoint_reread_rates) / n
        memory_consistency = 1.0 / (1.0 + variance)
        
        # Find peak degradation checkpoint
        peak_degradation_checkpoint = checkpoint_reread_rates.index(max(checkpoint_reread_rates))
    
    return {
        "checkpoint_reread_rates": checkpoint_reread_rates,
        "degradation_trend": degradation_trend,
        "peak_degradation_checkpoint": peak_degradation_checkpoint,
        "memory_consistency": memory_consistency,
        "total_checkpoints": len(task_trace.checkpoint_traces),
        "avg_reread_rate": sum(checkpoint_reread_rates) / len(checkpoint_reread_rates) if checkpoint_reread_rates else 0.0
    }


def get_memory_fidelity_diagnostics(context_reread_rate: float,
                                   size_weighted_penalty: float,
                                   compression_efficiency: float,
                                   retention_score: float,
                                   degradation_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Provide diagnostic categorization of memory fidelity performance.
    
    Args:
        context_reread_rate: Rate of unnecessary file rereads
        size_weighted_penalty: Size-weighted penalty for rereads
        compression_efficiency: Memory compression effectiveness
        retention_score: Information retention across checkpoints
        degradation_analysis: Temporal degradation analysis
        
    Returns:
        Dictionary containing diagnostic categories and recommendations
    """
    diagnostics = {
        "overall_category": "unknown",
        "primary_issues": [],
        "strengths": [],
        "recommendations": []
    }
    
    # Categorize based on reread rate
    if context_reread_rate < 0.1:
        diagnostics["strengths"].append("Excellent context retention - minimal rereading")
    elif context_reread_rate < 0.3:
        diagnostics["strengths"].append("Good context retention - low reread rate")
    elif context_reread_rate < 0.6:
        diagnostics["primary_issues"].append("Moderate memory inefficiency - frequent rereads")
        diagnostics["recommendations"].append("Improve information storage and retrieval mechanisms")
    else:
        diagnostics["primary_issues"].append("Severe memory problems - excessive rereading")
        diagnostics["recommendations"].append("Major memory system overhaul needed")
    
    # Analyze size-weighted penalty
    if size_weighted_penalty > 0.4:
        diagnostics["primary_issues"].append("High size-weighted penalty - rereading large files")
        diagnostics["recommendations"].append("Prioritize retention of large/important files")
    
    # Analyze compression efficiency
    if compression_efficiency > 0.7:
        diagnostics["strengths"].append("Excellent information compression")
    elif compression_efficiency < 0.3:
        diagnostics["primary_issues"].append("Poor information compression")
        diagnostics["recommendations"].append("Improve information summarization capabilities")
    
    # Analyze retention
    if retention_score > 0.7:
        diagnostics["strengths"].append("Strong cross-checkpoint information retention")
    elif retention_score < 0.4:
        diagnostics["primary_issues"].append("Weak information retention between checkpoints")
        diagnostics["recommendations"].append("Strengthen long-term memory persistence")
    
    # Analyze temporal trends
    if degradation_analysis["degradation_trend"] == "degrading":
        diagnostics["primary_issues"].append("Memory performance degrades over time")
        diagnostics["recommendations"].append("Address memory degradation with better maintenance")
    elif degradation_analysis["degradation_trend"] == "improving":
        diagnostics["strengths"].append("Memory performance improves over time")
    
    if degradation_analysis["memory_consistency"] < 0.5:
        diagnostics["primary_issues"].append("Inconsistent memory performance across checkpoints")
        diagnostics["recommendations"].append("Improve memory system reliability and consistency")
    
    # Overall categorization
    num_issues = len(diagnostics["primary_issues"])
    num_strengths = len(diagnostics["strengths"])
    
    if num_issues == 0 and num_strengths >= 2:
        diagnostics["overall_category"] = "excellent"
    elif num_issues <= 1 and num_strengths >= 1:
        diagnostics["overall_category"] = "good"
    elif num_issues <= 2:
        diagnostics["overall_category"] = "moderate"
    else:
        diagnostics["overall_category"] = "poor"
    
    return diagnostics


# ============================================================================
# COMPREHENSIVE THREE-PILLAR WORKING MEMORY EVALUATION SYSTEM
# ============================================================================

@dataclass
class MetricResult:
    """Standard result format for individual metrics"""
    name: str
    value: float
    confidence: float = 1.0  # 0-1, how confident we are in this measurement
    details: Dict[str, Any] = field(default_factory=dict)
    interpretation: str = ""  # Human-readable interpretation
    
    def __post_init__(self):
        """Validate metric result"""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be 0-1, got {self.confidence}")


@dataclass
class PillarResult:
    """Results for one of the three pillars"""
    pillar_name: str
    overall_score: float
    metrics: List[MetricResult]
    interpretation: str = ""
    recommendations: List[str] = field(default_factory=list)
    
    def get_metric(self, name: str) -> Optional[MetricResult]:
        """Get specific metric by name"""
        return next((m for m in self.metrics if m.name == name), None)


@dataclass
class WorkingMemoryEvaluation:
    """Complete working memory evaluation results"""
    task_id: str
    agent_name: str
    timestamp: float
    
    # Three-pillar results
    memory_fidelity: PillarResult
    contextual_relevance: PillarResult
    behavioral_integrity: PillarResult
    
    # Overall assessment
    overall_working_memory_score: float
    grade: str  # A, B, C, D, F
    summary: str
    
    # Diagnostic information
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)


class MetricEvaluator(ABC):
    """Base class for metric evaluators"""
    
    @abstractmethod
    def evaluate(self, task_trace: TaskTrace, task_spec: TaskSpecification) -> List[MetricResult]:
        """Evaluate metrics and return results"""
        pass
    
    def _safe_divide(self, numerator: float, denominator: float, default: float = 0.0) -> float:
        """Safe division that handles zero denominators"""
        return numerator / denominator if denominator != 0 else default
    
    def _calculate_confidence(self, sample_size: int, min_size: int = 5) -> float:
        """Calculate confidence based on sample size"""
        if sample_size >= min_size:
            return min(1.0, sample_size / (min_size * 2))  # Full confidence at 2x min_size
        return sample_size / min_size if sample_size > 0 else 0.0


class MemoryFidelityEvaluator(MetricEvaluator):
    """Pillar 1: Memory Fidelity - How well does the agent retain and manage information?"""
    
    def __init__(self, tau_seconds: int = 600):
        """Configure evaluator.
        
        tau_seconds controls the decay time constant for cross-checkpoint
        information retention weighting.
        """
        self.tau_seconds = tau_seconds
    
    def evaluate(self, task_trace: TaskTrace, task_spec: TaskSpecification) -> List[MetricResult]:
        """Evaluate all memory fidelity metrics"""
        metrics = []
        
        # Use existing functions but wrap in new format
        reread_rate = calculate_context_reread_rate(task_trace)
        metrics.append(self._create_reread_metric(task_trace, reread_rate))
        
        size_penalty = calculate_size_weighted_reread_penalty(task_trace)
        metrics.append(self._create_size_penalty_metric(task_trace, size_penalty))
        
        retention_score = calculate_information_retention_score(task_trace)
        metrics.append(self._create_retention_metric(task_trace, retention_score))
        
        # New advanced metrics
        metrics.append(self._temporal_information_loss(task_trace))
        metrics.append(self._cross_checkpoint_information_retention(task_trace, self.tau_seconds))
        metrics.append(self._memory_coherence_index(task_trace))
        
        return metrics
    
    def _create_reread_metric(self, task_trace: TaskTrace, reread_rate: float) -> MetricResult:
        """Create context reread rate metric"""
        score = 1.0 - reread_rate  # Invert so higher is better
        file_stats = task_trace.get_file_reread_statistics()
        
        if score >= 0.9:
            interpretation = "Excellent - agent rarely re-reads information"
        elif score >= 0.75:
            interpretation = "Good - agent manages context efficiently"
        elif score >= 0.5:
            interpretation = "Fair - some unnecessary information re-reading"
        else:
            interpretation = "Poor - frequent unnecessary re-reading indicates memory issues"
        
        return MetricResult(
            name="context_reread_efficiency",
            value=score,
            confidence=self._calculate_confidence(file_stats['total_file_accesses'], min_size=10),
            details=file_stats,
            interpretation=interpretation
        )
    
    def _create_size_penalty_metric(self, task_trace: TaskTrace, size_penalty: float) -> MetricResult:
        """Create size-weighted penalty metric"""
        score = max(0, 1.0 - size_penalty)  # Invert penalty to score
        
        if score >= 0.9:
            interpretation = "Excellent - minimal wasted processing on large files"
        elif score >= 0.75:
            interpretation = "Good - efficient handling of file sizes"
        elif score >= 0.5:
            interpretation = "Fair - some inefficiency in large file handling"
        else:
            interpretation = "Poor - significant wasted effort on large file rereads"
        
        # Count file reads for confidence
        total_reads = sum(1 for cp in task_trace.checkpoint_traces 
                         for action in cp.actions 
                         if action.action_type == ActionType.FILE_READ and action.success)
        
        return MetricResult(
            name="size_weighted_efficiency",
            value=score,
            confidence=self._calculate_confidence(total_reads, min_size=5),
            details={'size_penalty': size_penalty},
            interpretation=interpretation
        )
    
    def _create_retention_metric(self, task_trace: TaskTrace, retention_score: float) -> MetricResult:
        """Create information retention metric"""
        if retention_score >= 0.8:
            interpretation = "Excellent - strong information retention across checkpoints"
        elif retention_score >= 0.6:
            interpretation = "Good - generally retains relevant information"
        elif retention_score >= 0.4:
            interpretation = "Fair - some information loss between checkpoints"
        else:
            interpretation = "Poor - significant information loss"
        
        return MetricResult(
            name="information_retention",
            value=retention_score,
            confidence=self._calculate_confidence(len(task_trace.checkpoint_traces), min_size=2),
            details={'checkpoint_count': len(task_trace.checkpoint_traces)},
            interpretation=interpretation
        )
    
    def _temporal_information_loss(self, task_trace: TaskTrace) -> MetricResult:
        """Measure information loss over time within the task"""
        timeline = []
        
        for checkpoint_trace in task_trace.checkpoint_traces:
            for action in checkpoint_trace.actions:
                if (action.action_type == ActionType.FILE_READ and 
                    action.file_path and action.success):
                    timeline.append({
                        'timestamp': action.timestamp,
                        'file': action.file_path,
                        'checkpoint': action.checkpoint_id
                    })
        
        if len(timeline) < 2:
            return MetricResult(
                name="temporal_information_loss",
                value=1.0,
                confidence=0.3,
                details={'timeline_events': len(timeline)},
                interpretation="Insufficient data to measure temporal information loss"
            )
        
        # Simple heuristic: penalize long gaps between file accesses
        loss_score = self._calculate_temporal_loss_score(timeline)
        
        if loss_score >= 0.8:
            interpretation = "Excellent - minimal information loss over time"
        elif loss_score >= 0.6:
            interpretation = "Good - maintains information well over time"
        elif loss_score >= 0.4:
            interpretation = "Fair - some temporal information loss"
        else:
            interpretation = "Poor - significant information loss over time"
        
        return MetricResult(
            name="temporal_information_loss",
            value=loss_score,
            confidence=self._calculate_confidence(len(timeline), min_size=10),
            details={'timeline_events': len(timeline)},
            interpretation=interpretation
        )
    
    def _cross_checkpoint_information_retention(self, task_trace: TaskTrace, tau_seconds: int = 600) -> MetricResult:
        """Measure information retention across checkpoints without reread before reuse.
        
        Definition: For each file f that appears in checkpoint j and had a prior access
        in some checkpoint i < j, check the first access to f in checkpoint j.
        - If first access is FILE_READ => information loss event (had to reacquire)
        - If first access is FILE_WRITE or FILE_MODIFY => retained (proceeded without reread)
        Each event is weighted by last known size_bytes before j and decayed by the
        time gap since the last access: w = size_bytes * 1/(1 + gap/τ).
        The metric returns a retention score in [0,1]: 1 - (weighted_loss/weighted_total).
        Higher is better.
        """
        # Collect per-file chronological actions
        file_actions: Dict[str, List[ActionTraceEntry]] = defaultdict(list)
        for checkpoint_trace in task_trace.checkpoint_traces:
            for action in checkpoint_trace.actions:
                if action.file_path and action.action_type in [ActionType.FILE_READ, ActionType.FILE_WRITE, ActionType.FILE_MODIFY, ActionType.FILE_CREATE]:
                    file_actions[action.file_path].append(action)
        
        weighted_loss = 0.0
        weighted_total = 0.0
        raw_events = 0
        raw_losses = 0
        
        for file_path, actions in file_actions.items():
            # Group actions by checkpoint and sort chronologically
            actions.sort(key=lambda a: a.timestamp)
            by_checkpoint: Dict[str, List[ActionTraceEntry]] = defaultdict(list)
            for a in actions:
                if a.checkpoint_id:
                    by_checkpoint[a.checkpoint_id].append(a)
            
            # Build a list of checkpoints in order of appearance for this file
            checkpoints_for_file = []
            for cp_trace in task_trace.checkpoint_traces:
                if by_checkpoint.get(cp_trace.checkpoint_id):
                    checkpoints_for_file.append(cp_trace.checkpoint_id)
            
            # For each reappearance, assess first access type and weight
            last_access: Optional[ActionTraceEntry] = None
            for cp_id in checkpoints_for_file:
                cp_actions = sorted(by_checkpoint[cp_id], key=lambda a: a.timestamp)
                if last_access is None:
                    # First time we've seen this file; update and continue
                    last_access = cp_actions[-1]
                    continue
                
                first_access_current = cp_actions[0]
                gap = max(0.0, first_access_current.timestamp - last_access.timestamp)
                # Weight by size_bytes if present, else fallback to 1.0
                size_bytes = 1.0
                if isinstance(last_access.metadata, dict) and 'size_bytes' in last_access.metadata:
                    try:
                        size_bytes = float(last_access.metadata.get('size_bytes', 1.0))
                    except Exception:
                        size_bytes = 1.0
                decay = 1.0 / (1.0 + (gap / float(tau_seconds))) if tau_seconds > 0 else 1.0
                weight = max(0.0, size_bytes) * decay
                
                # Determine if loss event
                is_loss = 1 if first_access_current.action_type == ActionType.FILE_READ else 0
                raw_events += 1
                if is_loss:
                    raw_losses += 1
                weighted_loss += is_loss * weight
                weighted_total += weight
                
                # Update last_access to the last action in this checkpoint
                last_access = cp_actions[-1]
        
        if weighted_total == 0:
            # No cross-checkpoint reuse events; insufficient data
            return MetricResult(
                name="cross_checkpoint_information_retention",
                value=1.0,
                confidence=0.0,
                details={
                    'total_reuse_events': 0,
                    'loss_events': 0,
                    'weighted_loss': 0.0,
                    'weighted_total': 0.0,
                    'raw_loss_rate': 0.0,
                    'tau_seconds': tau_seconds
                },
                interpretation="Insufficient cross-checkpoint reuse data to assess information retention"
            )
        
        raw_loss_rate = raw_losses / raw_events if raw_events > 0 else 0.0
        loss_rate = weighted_loss / weighted_total
        retention_score = max(0.0, 1.0 - loss_rate)
        
        if retention_score >= 0.9:
            interpretation = "Excellent - information is retained across checkpoints without rereads"
        elif retention_score >= 0.75:
            interpretation = "Good - generally retains information with few rereads"
        elif retention_score >= 0.5:
            interpretation = "Fair - mixed retention, frequent rereads before reuse"
        else:
            interpretation = "Poor - often needs to reread before reusing information"
        
        return MetricResult(
            name="cross_checkpoint_information_retention",
            value=retention_score,
            confidence=self._calculate_confidence(raw_events, min_size=5),
            details={
                'total_reuse_events': raw_events,
                'loss_events': raw_losses,
                'weighted_loss': weighted_loss,
                'weighted_total': weighted_total,
                'raw_loss_rate': raw_loss_rate,
                'loss_rate': loss_rate,
                'tau_seconds': tau_seconds
            },
            interpretation=interpretation
        )

    def _memory_coherence_index(self, task_trace: TaskTrace) -> MetricResult:
        """Measure coherence of memory operations"""
        coherence_violations = 0
        total_operations = 0
        
        for checkpoint_trace in task_trace.checkpoint_traces:
            file_states = {}
            
            for action in checkpoint_trace.actions:
                total_operations += 1
                
                if action.action_type == ActionType.FILE_READ and action.file_path:
                    if action.file_path in file_states:
                        last_op = file_states[action.file_path]
                        # Check for incoherent patterns
                        if (last_op['type'] == 'read' and 
                            action.timestamp - last_op['timestamp'] < 60):
                            coherence_violations += 1
                    
                    file_states[action.file_path] = {'type': 'read', 'timestamp': action.timestamp}
                
                elif action.action_type in [ActionType.FILE_WRITE, ActionType.FILE_MODIFY] and action.file_path:
                    file_states[action.file_path] = {'type': 'write', 'timestamp': action.timestamp}
        
        if total_operations > 0:
            coherence_score = max(0, 1.0 - (coherence_violations / total_operations))
        else:
            coherence_score = 1.0
        
        if coherence_score >= 0.9:
            interpretation = "Excellent - highly coherent memory access patterns"
        elif coherence_score >= 0.75:
            interpretation = "Good - mostly coherent memory operations"
        elif coherence_score >= 0.5:
            interpretation = "Fair - some incoherent memory access patterns"
        else:
            interpretation = "Poor - frequent incoherent memory operations"
        
        return MetricResult(
            name="memory_coherence_index",
            value=coherence_score,
            confidence=self._calculate_confidence(total_operations, min_size=20),
            details={
                'total_operations': total_operations,
                'coherence_violations': coherence_violations
            },
            interpretation=interpretation
        )
    
    def _calculate_temporal_loss_score(self, timeline: List[Dict]) -> float:
        """Calculate score based on temporal patterns"""
        # Group by file
        file_accesses = defaultdict(list)
        for event in timeline:
            file_accesses[event['file']].append(event)
        
        loss_penalties = 0
        total_files = len(file_accesses)
        
        for file_path, accesses in file_accesses.items():
            if len(accesses) > 1:
                accesses.sort(key=lambda x: x['timestamp'])
                for i in range(1, len(accesses)):
                    time_gap = accesses[i]['timestamp'] - accesses[i-1]['timestamp']
                    if time_gap > 300:  # 5 minutes
                        loss_penalties += min(0.5, time_gap / 1800)  # Max penalty at 30 min
        
        avg_loss_penalty = loss_penalties / total_files if total_files > 0 else 0
        return max(0, 1.0 - avg_loss_penalty)


class ContextualRelevanceEvaluator(MetricEvaluator):
    """Pillar 2: Contextual Relevance - How precisely does the agent focus on relevant information?"""
    
    def evaluate(self, task_trace: TaskTrace, task_spec: TaskSpecification) -> List[MetricResult]:
        """Evaluate all contextual relevance metrics"""
        metrics = []
        
        accessed_files = task_trace.unique_files_accessed.copy()
        relevant_files = self._get_relevant_files(task_spec)
        
        # Normalize to basenames for consistent matching across absolute/relative paths
        try:
            accessed_files = {Path(f).name for f in accessed_files if isinstance(f, str)}
            relevant_files = {Path(f).name for f in relevant_files if isinstance(f, str)}
        except Exception:
            # Fallback: keep original sets if normalization fails
            accessed_files = set(accessed_files)
            relevant_files = set(relevant_files)
        
        metrics.append(self._file_access_precision(accessed_files, relevant_files))
        metrics.append(self._file_access_recall(accessed_files, relevant_files))
        metrics.append(self._relevance_f1_score(accessed_files, relevant_files))
        metrics.append(self._distractor_resistance(task_trace, task_spec))
        metrics.append(self._focus_consistency_index(task_trace, task_spec))
        
        return metrics
    
    def _file_access_precision(self, accessed_files: Set[str], relevant_files: Set[str]) -> MetricResult:
        """Calculate precision of file accesses"""
        if not accessed_files:
            return MetricResult(
                name="file_access_precision",
                value=1.0,
                confidence=0.0,
                details={'accessed_files': 0, 'relevant_files': len(relevant_files)},
                interpretation="No files accessed - cannot calculate precision"
            )
        
        relevant_accessed = accessed_files.intersection(relevant_files)
        precision = len(relevant_accessed) / len(accessed_files)
        
        if precision >= 0.9:
            interpretation = "Excellent - agent accesses almost exclusively relevant files"
        elif precision >= 0.75:
            interpretation = "Good - agent mostly accesses relevant files"
        elif precision >= 0.5:
            interpretation = "Fair - agent accesses some irrelevant files"
        else:
            interpretation = "Poor - agent frequently accesses irrelevant files"
        
        return MetricResult(
            name="file_access_precision",
            value=precision,
            confidence=self._calculate_confidence(len(accessed_files), min_size=3),
            details={
                'total_files_accessed': len(accessed_files),
                'relevant_files_accessed': len(relevant_accessed),
                'irrelevant_files_accessed': len(accessed_files) - len(relevant_accessed)
            },
            interpretation=interpretation
        )
    
    def _file_access_recall(self, accessed_files: Set[str], relevant_files: Set[str]) -> MetricResult:
        """Calculate recall of file accesses"""
        if not relevant_files:
            return MetricResult(
                name="file_access_recall",
                value=1.0,
                confidence=0.3,
                details={'accessed_files': len(accessed_files), 'relevant_files': 0},
                interpretation="No clearly relevant files defined"
            )
        
        relevant_accessed = accessed_files.intersection(relevant_files)
        recall = len(relevant_accessed) / len(relevant_files)
        
        if recall >= 0.9:
            interpretation = "Excellent - agent accesses nearly all relevant files"
        elif recall >= 0.75:
            interpretation = "Good - agent accesses most relevant files"
        elif recall >= 0.5:
            interpretation = "Fair - agent misses some relevant files"
        else:
            interpretation = "Poor - agent misses many relevant files"
        
        return MetricResult(
            name="file_access_recall",
            value=recall,
            confidence=self._calculate_confidence(len(relevant_files), min_size=2),
            details={
                'total_relevant_files': len(relevant_files),
                'relevant_files_accessed': len(relevant_accessed),
                'relevant_files_missed': len(relevant_files) - len(relevant_accessed)
            },
            interpretation=interpretation
        )
    
    def _relevance_f1_score(self, accessed_files: Set[str], relevant_files: Set[str]) -> MetricResult:
        """Calculate F1 score of file access relevance"""
        precision_metric = self._file_access_precision(accessed_files, relevant_files)
        recall_metric = self._file_access_recall(accessed_files, relevant_files)
        
        precision = precision_metric.value
        recall = recall_metric.value
        
        if precision + recall == 0:
            f1_score = 0.0
        else:
            f1_score = 2 * (precision * recall) / (precision + recall)
        
        if f1_score >= 0.9:
            interpretation = "Excellent - optimal balance of precision and recall"
        elif f1_score >= 0.75:
            interpretation = "Good - good balance of precision and recall"
        elif f1_score >= 0.5:
            interpretation = "Fair - moderate relevance in file access"
        else:
            interpretation = "Poor - poor balance of precision and recall"
        
        return MetricResult(
            name="relevance_f1_score",
            value=f1_score,
            confidence=min(precision_metric.confidence, recall_metric.confidence),
            details={
                'precision': precision,
                'recall': recall
            },
            interpretation=interpretation
        )
    
    def _distractor_resistance(self, task_trace: TaskTrace, task_spec: TaskSpecification) -> MetricResult:
        """Measure resistance to distractor files"""
        accessed_files = task_trace.unique_files_accessed.copy()
        distractor_files = set(task_spec.repository.distractor_files)
        
        # Normalize accessed and distractor filenames to basenames for consistency
        try:
            accessed_files = {Path(f).name for f in accessed_files if isinstance(f, str)}
            distractor_files = {Path(f).name for f in distractor_files if isinstance(f, str)}
        except Exception:
            accessed_files = set(accessed_files)
            distractor_files = set(distractor_files)
        
        if not distractor_files:
            return MetricResult(
                name="distractor_resistance",
                value=1.0,
                confidence=0.5,
                details={'distractor_files': 0},
                interpretation="No distractor files present"
            )
        
        distractor_accessed = accessed_files.intersection(distractor_files)
        
        if not accessed_files:
            resistance_score = 1.0
        else:
            distractor_rate = len(distractor_accessed) / len(accessed_files)
            resistance_score = max(0, 1.0 - distractor_rate)
        
        if resistance_score >= 0.95:
            interpretation = "Excellent - completely resisted distractor files"
        elif resistance_score >= 0.8:
            interpretation = "Good - mostly resisted distractors"
        elif resistance_score >= 0.6:
            interpretation = "Fair - some susceptibility to distractor files"
        else:
            interpretation = "Poor - frequently accessed distractor files"
        
        return MetricResult(
            name="distractor_resistance",
            value=resistance_score,
            confidence=self._calculate_confidence(len(accessed_files), min_size=5),
            details={
                'total_distractor_files': len(distractor_files),
                'distractor_files_accessed': len(distractor_accessed)
            },
            interpretation=interpretation
        )
    
    def _focus_consistency_index(self, task_trace: TaskTrace, task_spec: TaskSpecification) -> MetricResult:
        """Measure consistency of focus across checkpoints"""
        checkpoint_focus_scores = []
        
        for checkpoint_trace in task_trace.checkpoint_traces:
            checkpoint_files = set()
            for action in checkpoint_trace.actions:
                if (action.action_type in [ActionType.FILE_READ, ActionType.FILE_WRITE, ActionType.FILE_MODIFY] 
                    and action.file_path):
                    checkpoint_files.add(action.file_path)
            
            # Get relevant files for this checkpoint
            checkpoint_spec = None
            for cp_spec in task_spec.checkpoints:
                if cp_spec.checkpoint_id == checkpoint_trace.checkpoint_id:
                    checkpoint_spec = cp_spec
                    break
            
            if checkpoint_spec and checkpoint_files:
                checkpoint_relevant = self._get_checkpoint_relevant_files(checkpoint_spec, task_spec)
                if checkpoint_relevant:
                    # Normalize both sets to basenames for consistent comparison
                    try:
                        checkpoint_files_norm = {Path(f).name for f in checkpoint_files if isinstance(f, str)}
                        checkpoint_relevant_norm = {Path(f).name for f in checkpoint_relevant if isinstance(f, str)}
                    except Exception:
                        checkpoint_files_norm = set(checkpoint_files)
                        checkpoint_relevant_norm = set(checkpoint_relevant)
                    relevant_accessed = checkpoint_files_norm.intersection(checkpoint_relevant_norm)
                    focus_score = len(relevant_accessed) / len(checkpoint_files_norm) if checkpoint_files_norm else 0.0
                    checkpoint_focus_scores.append(focus_score)
        
        if not checkpoint_focus_scores:
            return MetricResult(
                name="focus_consistency_index",
                value=0.5,
                confidence=0.2,
                details={'checkpoint_scores': []},
                interpretation="Insufficient data to measure focus consistency"
            )
        
        mean_focus = statistics.mean(checkpoint_focus_scores)
        if len(checkpoint_focus_scores) > 1:
            focus_variance = statistics.variance(checkpoint_focus_scores)
            consistency_score = max(0, mean_focus - focus_variance)  # Penalize high variance
        else:
            consistency_score = mean_focus
        
        if consistency_score >= 0.8:
            interpretation = "Excellent - consistently focused across checkpoints"
        elif consistency_score >= 0.6:
            interpretation = "Good - generally consistent focus"
        elif consistency_score >= 0.4:
            interpretation = "Fair - some inconsistency in focus"
        else:
            interpretation = "Poor - highly inconsistent focus"
        
        return MetricResult(
            name="focus_consistency_index",
            value=consistency_score,
            confidence=self._calculate_confidence(len(checkpoint_focus_scores), min_size=2),
            details={'checkpoint_focus_scores': checkpoint_focus_scores},
            interpretation=interpretation
        )
    
    def _get_relevant_files(self, task_spec: TaskSpecification) -> Set[str]:
        """Get set of files relevant to the task.
        
        Union of repository-provided files and all files required by each checkpoint,
        including dependencies and common files via TaskSpecification.get_required_files_for_checkpoint.
        """
        relevant_files: Set[str] = set()
        
        # Repository-provided files
        relevant_files.update(task_spec.repository.provided_files)
        
        # All checkpoint-required files (stub, test, dependency stubs, common files)
        for checkpoint in task_spec.checkpoints:
            relevant_files.update(task_spec.get_required_files_for_checkpoint(checkpoint.checkpoint_id))
        
        # Backward-compatibility: exclude global common files from recall denominator
        # Tests expect recall based on stub+test across checkpoints only
        common_basenames = {"requirements.txt", "README.md"}
        relevant_files = {f for f in relevant_files if Path(f).name not in common_basenames}
        
        return relevant_files
    
    def _get_checkpoint_relevant_files(self, checkpoint_spec: CheckpointSpecification, task_spec: TaskSpecification) -> Set[str]:
        """Get files relevant to a specific checkpoint using TaskSpecification API."""
        return set(task_spec.get_required_files_for_checkpoint(checkpoint_spec.checkpoint_id))


class BehavioralIntegrityEvaluator(MetricEvaluator):
    """Pillar 3: Behavioral Integrity - How consistently does the agent execute its plan?"""
    
    def evaluate(self, task_trace: TaskTrace, task_spec: TaskSpecification) -> List[MetricResult]:
        """Evaluate all behavioral integrity metrics"""
        metrics = []
        
        metrics.append(self._error_correction_overhead(task_trace))
        metrics.append(self._state_coherence_index(task_trace))
        metrics.append(self._backtracking_rate(task_trace))
        metrics.append(self._decision_consistency_index(task_trace))
        metrics.append(self._recovery_effectiveness(task_trace))
        
        # Planning compliance
        try:
            plan_metric = self._plan_compliance(task_trace, task_spec)
            if plan_metric is not None:
                metrics.append(plan_metric)
        except Exception:
            pass
        
        # Challenge-driven adaptation metrics (UR and RSR)
        try:
            ur_metric = self._update_robustness(task_trace, task_spec)
            if ur_metric is not None:
                metrics.append(ur_metric)
        except Exception:
            # Be robust to missing or malformed challenge data
            pass
        try:
            rsr_metric = self._resumption_success_rate(task_trace, task_spec)
            if rsr_metric is not None:
                metrics.append(rsr_metric)
        except Exception:
            pass
        
        return metrics
    
    def _error_correction_overhead(self, task_trace: TaskTrace) -> MetricResult:
        """Measure overhead from error correction activities"""
        total_actions = task_trace.total_actions
        error_actions = task_trace.total_errors
        recovery_actions = sum(len(cp.recovery_actions) for cp in task_trace.checkpoint_traces)
        
        if total_actions == 0:
            return MetricResult(
                name="error_correction_overhead",
                value=1.0,
                confidence=0.0,
                details={'total_actions': 0},
                interpretation="No actions recorded"
            )
        
        overhead_rate = (error_actions + recovery_actions) / total_actions
        overhead_score = max(0, 1.0 - overhead_rate)
        
        if overhead_score >= 0.9:
            interpretation = "Excellent - minimal error correction overhead"
        elif overhead_score >= 0.75:
            interpretation = "Good - low error correction overhead"
        elif overhead_score >= 0.5:
            interpretation = "Fair - moderate error correction overhead"
        else:
            interpretation = "Poor - high error correction overhead"
        
        return MetricResult(
            name="error_correction_overhead",
            value=overhead_score,
            confidence=self._calculate_confidence(total_actions, min_size=10),
            details={
                'total_actions': total_actions,
                'error_actions': error_actions,
                'recovery_actions': recovery_actions,
                'overhead_rate': overhead_rate
            },
            interpretation=interpretation
        )
    
    def _state_coherence_index(self, task_trace: TaskTrace) -> MetricResult:
        """Measure coherence of system state throughout execution"""
        coherence_violations = []
        state_operations = 0
        
        for checkpoint_trace in task_trace.checkpoint_traces:
            for action in checkpoint_trace.actions:
                if action.action_type in [ActionType.FILE_WRITE, ActionType.FILE_MODIFY, ActionType.FILE_CREATE]:
                    state_operations += 1
                    if not action.success:
                        coherence_violations.append({
                            'type': 'failed_state_change',
                            'file': action.file_path,
                            'action': action.action_type.value
                        })
        
        if state_operations > 0:
            violation_rate = len(coherence_violations) / state_operations
            coherence_score = max(0, 1.0 - violation_rate)
        else:
            coherence_score = 1.0
        
        if coherence_score >= 0.95:
            interpretation = "Excellent - highly coherent state management"
        elif coherence_score >= 0.8:
            interpretation = "Good - mostly coherent system state"
        elif coherence_score >= 0.6:
            interpretation = "Fair - some state coherence issues"
        else:
            interpretation = "Poor - frequent state coherence violations"
        
        return MetricResult(
            name="state_coherence_index",
            value=coherence_score,
            confidence=self._calculate_confidence(state_operations, min_size=5),
            details={
                'state_operations': state_operations,
                'coherence_violations': len(coherence_violations)
            },
            interpretation=interpretation
        )
    
    def _backtracking_rate(self, task_trace: TaskTrace) -> MetricResult:
        """Measure frequency of backtracking (undoing previous work)"""
        backtracking_events = []
        total_modifications = 0
        
        for checkpoint_trace in task_trace.checkpoint_traces:
            file_modifications = defaultdict(list)
            
            for action in checkpoint_trace.actions:
                if action.action_type in [ActionType.FILE_WRITE, ActionType.FILE_MODIFY] and action.file_path:
                    total_modifications += 1
                    file_modifications[action.file_path].append({
                        'timestamp': action.timestamp,
                        'size_bytes': action.metadata.get('size_bytes', 0)
                    })
            
            # Detect backtracking patterns
            for file_path, modifications in file_modifications.items():
                if len(modifications) >= 3:
                    for i in range(2, len(modifications)):
                        current_size = modifications[i]['size_bytes']
                        prev_size = modifications[i-1]['size_bytes']
                        
                        if current_size < prev_size * 0.8:  # 20% reduction threshold
                            backtracking_events.append({
                                'file': file_path,
                                'timestamp': modifications[i]['timestamp'],
                                'size_reduction': prev_size - current_size
                            })
        
        backtracking_rate = len(backtracking_events) / total_modifications if total_modifications > 0 else 0
        backtracking_score = max(0, 1.0 - backtracking_rate)
        
        if backtracking_score >= 0.9:
            interpretation = "Excellent - minimal backtracking, strong forward progress"
        elif backtracking_score >= 0.75:
            interpretation = "Good - low backtracking rate"
        elif backtracking_score >= 0.5:
            interpretation = "Fair - moderate backtracking"
        else:
            interpretation = "Poor - frequent backtracking indicates planning issues"
        
        return MetricResult(
            name="backtracking_rate",
            value=backtracking_score,
            confidence=self._calculate_confidence(total_modifications, min_size=5),
            details={
                'total_modifications': total_modifications,
                'backtracking_events': len(backtracking_events),
                'backtracking_rate': backtracking_rate
            },
            interpretation=interpretation
        )
    
    def _decision_consistency_index(self, task_trace: TaskTrace) -> MetricResult:
        """Measure consistency of decision-making throughout execution"""
        decision_patterns = defaultdict(list)
        total_decisions = 0
        
        for checkpoint_trace in task_trace.checkpoint_traces:
            for action in checkpoint_trace.actions:
                if action.action_type in [ActionType.FILE_READ, ActionType.FILE_WRITE, ActionType.LLM_CALL]:
                    total_decisions += 1
                    
                    # Simple context categorization
                    context_key = action.action_type.value
                    if action.file_path:
                        if action.file_path.endswith('.py'):
                            context_key += '_python'
                        elif 'test' in action.file_path.lower():
                            context_key += '_test'
                    
                    decision_patterns[context_key].append({
                        'success': action.success,
                        'timestamp': action.timestamp
                    })
        
        # Calculate consistency
        consistency_scores = []
        for context, decisions in decision_patterns.items():
            if len(decisions) >= 2:
                success_rate = sum(1 for d in decisions if d['success']) / len(decisions)
                # Consistency is high when success rate is either very high or very low
                context_consistency = 1.0 - 2 * abs(success_rate - 0.5)
                consistency_scores.append(context_consistency)
        
        if consistency_scores:
            overall_consistency = statistics.mean(consistency_scores)
        else:
            overall_consistency = 1.0
        
        if overall_consistency >= 0.8:
            interpretation = "Excellent - highly consistent decision-making"
        elif overall_consistency >= 0.6:
            interpretation = "Good - mostly consistent decisions"
        elif overall_consistency >= 0.4:
            interpretation = "Fair - some inconsistency in decision-making"
        else:
            interpretation = "Poor - highly inconsistent decision patterns"
        
        return MetricResult(
            name="decision_consistency_index",
            value=overall_consistency,
            confidence=self._calculate_confidence(len(consistency_scores), min_size=3),
            details={
                'total_decisions': total_decisions,
                'decision_contexts': len(decision_patterns)
            },
            interpretation=interpretation
        )
    
    def _recovery_effectiveness(self, task_trace: TaskTrace) -> MetricResult:
        """Measure effectiveness of error recovery"""
        error_recovery_pairs = []
        
        for checkpoint_trace in task_trace.checkpoint_traces:
            errors = checkpoint_trace.errors_encountered
            recoveries = checkpoint_trace.recovery_actions
            
            for error in errors:
                related_recoveries = []
                for recovery in recoveries:
                    if (recovery.timestamp > error.timestamp and 
                        recovery.timestamp - error.timestamp < 300):
                        related_recoveries.append(recovery)
                
                if related_recoveries:
                    recovery_success = any(r.success for r in related_recoveries)
                    error_recovery_pairs.append({
                        'recovery_successful': recovery_success,
                        'recovery_attempts': len(related_recoveries),
                        'recovery_time': min(r.timestamp - error.timestamp for r in related_recoveries)
                    })
        
        if not error_recovery_pairs:
            return MetricResult(
                name="recovery_effectiveness",
                value=1.0,
                confidence=0.5,
                details={'recovery_events': 0},
                interpretation="No error recovery events to evaluate"
            )
        
        successful_recoveries = sum(1 for pair in error_recovery_pairs if pair['recovery_successful'])
        recovery_rate = successful_recoveries / len(error_recovery_pairs)
        
        # Factor in recovery speed
        avg_recovery_time = statistics.mean([pair['recovery_time'] for pair in error_recovery_pairs])
        time_penalty = min(0.2, avg_recovery_time / 300)
        
        effectiveness_score = max(0, recovery_rate - time_penalty)
        
        if effectiveness_score >= 0.85:
            interpretation = "Excellent - highly effective error recovery"
        elif effectiveness_score >= 0.7:
            interpretation = "Good - effective error recovery with minor delays"
        elif effectiveness_score >= 0.5:
            interpretation = "Fair - moderate error recovery effectiveness"
        else:
            interpretation = "Poor - ineffective error recovery"
        
        return MetricResult(
            name="recovery_effectiveness",
            value=effectiveness_score,
            confidence=self._calculate_confidence(len(error_recovery_pairs), min_size=3),
            details={
                'error_recovery_pairs': len(error_recovery_pairs),
                'successful_recoveries': successful_recoveries,
                'recovery_rate': recovery_rate,
                'avg_recovery_time_seconds': avg_recovery_time
            },
            interpretation=interpretation
        )

    def _plan_compliance(self, task_trace: TaskTrace, task_spec: TaskSpecification) -> Optional[MetricResult]:
        """Plan compliance metric (native implementation).
        Combines coverage, order, on-plan ratio, and time-on-plan with a small penalty for replans.
        """
        stats = _compute_plan_compliance(task_spec, task_trace)
        coverage = float(stats.get('plan_coverage', 0.0))
        order = float(stats.get('plan_order_score', 0.0))
        on_plan = float(stats.get('on_plan_action_ratio', 0.0))
        time_on_plan = float(stats.get('time_on_plan_ratio', 0.0))
        replan_count = float(stats.get('replan_count', 0.0))
        # Weighted aggregate
        penalty = min(0.2, replan_count * 0.05)
        value = max(0.0, (0.4*coverage + 0.3*order + 0.15*on_plan + 0.15*time_on_plan) - penalty)
        # Confidence: number of checkpoints with a planning action
        planning_samples = 0
        for cp in task_trace.checkpoint_traces:
            if any(a.action_type == ActionType.PLANNING for a in cp.actions):
                planning_samples += 1
        confidence = self._calculate_confidence(planning_samples, min_size=2)
        interpretation = (
            "Excellent plan adherence" if value >= 0.85 else
            "Good plan adherence" if value >= 0.7 else
            "Moderate plan adherence" if value >= 0.5 else
            "Poor plan adherence"
        )
        return MetricResult(
            name="plan_compliance",
            value=value,
            confidence=confidence,
            details={
                'plan_coverage': coverage,
                'plan_order_score': order,
                'on_plan_action_ratio': on_plan,
                'time_on_plan_ratio': time_on_plan,
                'replan_count': replan_count
            },
            interpretation=interpretation
        )

    # -------------------------------
    # Challenge-driven adaptation UR/RSR
    # -------------------------------
    def _update_robustness(self, task_trace: TaskTrace, task_spec: TaskSpecification) -> Optional[MetricResult]:
        """Compute Update Robustness (UR) from requirement update and integration constraint challenges.
        
        Components and weights (default):
        - compliance (0.40): 1.0 if a passing TEST_RUN occurs after the update; 0.5 if only write/modify to
          affected files (fallback when no tests present); 0.0 otherwise.
        - latency (0.20): exp(-steps_to_first_signal / τ), where τ depends on severity (small=10, medium=25, large=50).
        - stability (0.20): 1/(1 + conflicts/3) based on subsequent modifications to affected files in a short window
          after the first signal.
        - consistency (0.20): fraction of touches in the next window that target the affected files.
        
        Binary success signal:
        - per-challenge details include binary_success = 1 only if a passing TEST_RUN is observed after the update.
        - details.binary_success_rate aggregates binary_success across all UR challenges.
        
        Returns a MetricResult with per-challenge details and a confidence-weighted aggregate value. Confidence is
        higher when a passing test is observed (grounded) and slightly reduced if consistency cannot be computed.
        """
        # Collect relevant challenge events
        challenge_events = [e for e in task_trace.memory_challenge_responses \
                            if e.action_type in [ActionType.REQUIREMENT_UPDATE, ActionType.INTEGRATION_CONSTRAINT]]
        if not challenge_events:
            return MetricResult(
                name="update_robustness",
                value=1.0,
                confidence=0.0,
                details={'coverage': 0, 'per_challenge': []},
                interpretation="No requirement update or constraint challenges present"
            )
        
        all_actions = _flatten_all_actions(task_trace)
        per_challenge = []
        weights = []
        values = []
        
        binary_outcomes: List[int] = []
        for ev in challenge_events:
            issued_ts = ev.timestamp
            severity = str(ev.metadata.get('severity', 'medium')).lower()
            tau_steps = {'small': 10, 'medium': 25, 'large': 50}.get(severity, 25)
            
            # Determine affected files (heuristic): use affected checkpoint stub/test files if available
            candidate_files: Set[str] = set()
            affected_cps: List[str] = []
            if ev.action_type == ActionType.REQUIREMENT_UPDATE:
                affected_cp_id = ev.metadata.get('affected_checkpoint')
                if affected_cp_id:
                    affected_cps = [affected_cp_id]
            elif ev.action_type == ActionType.INTEGRATION_CONSTRAINT:
                affected_cps = list(ev.metadata.get('affected_checkpoints', []))
            
            for cp_id in affected_cps:
                cp = task_spec.get_checkpoint_by_id(cp_id) if hasattr(task_spec, 'get_checkpoint_by_id') else None
                if cp:
                    if cp.stub_file:
                        candidate_files.add(cp.stub_file)
                    if cp.test_file:
                        candidate_files.add(cp.test_file)
            # Fallback: if no candidate files, use all checkpoint stub/test files
            if not candidate_files:
                for cp in task_spec.checkpoints:
                    if cp.stub_file:
                        candidate_files.add(cp.stub_file)
                    if cp.test_file:
                        candidate_files.add(cp.test_file)
            
            # Find first clear compliance signal: a passing TEST_RUN after the update
            first_test_pass_idx = _first_action_index_after(
                all_actions, issued_ts,
                lambda a: a.action_type == ActionType.TEST_RUN and a.success is True
            )
            # Fallback: first write/modify to candidate files
            first_write_idx = _first_action_index_after(
                all_actions, issued_ts,
                lambda a: a.action_type in [ActionType.FILE_WRITE, ActionType.FILE_MODIFY] and (a.file_path in candidate_files if a.file_path else False)
            )
            
            grounded = first_test_pass_idx is not None
            if first_test_pass_idx is not None:
                compliance = 1.0
                first_signal_idx = first_test_pass_idx
                binary_success = 1
            elif first_write_idx is not None:
                compliance = 0.5
                first_signal_idx = first_write_idx
                binary_success = 0
            else:
                compliance = 0.0
                first_signal_idx = None
                binary_success = 0
            
            # Latency score
            if first_signal_idx is None:
                latency_score = 0.0
                steps_to_signal = None
            else:
                # Count steps as number of actions between issued_ts and first_signal_idx
                issued_idx = _first_action_index_after(all_actions, issued_ts, lambda a: True)
                if issued_idx is None:
                    issued_idx = 0
                steps_to_signal = max(0, first_signal_idx - issued_idx)
                latency_score = math.exp(-steps_to_signal / max(1, tau_steps))
            
            # Stability: number of subsequent modifications to candidate files within a window after compliance
            stability_window = 30
            conflicts = 0
            if first_signal_idx is not None:
                window_actions = _actions_in_window(all_actions, first_signal_idx + 1, stability_window)
                for a in window_actions:
                    if a.action_type in [ActionType.FILE_WRITE, ActionType.FILE_MODIFY] and (a.file_path in candidate_files if a.file_path else False):
                        conflicts += 1
            stability_score = 1.0 / (1.0 + (conflicts / 3.0))
            
            # Consistency approximation: focus on candidate files in next window
            if first_signal_idx is not None:
                window_actions = _actions_in_window(all_actions, first_signal_idx + 1, 30)
                touches = [a for a in window_actions if a.action_type in [ActionType.FILE_READ, ActionType.FILE_WRITE, ActionType.FILE_MODIFY] and a.file_path]
                if touches:
                    aligned = sum(1 for a in touches if a.file_path in candidate_files)
                    consistency_score = aligned / len(touches)
                else:
                    consistency_score = None
            else:
                consistency_score = None
            
            # Aggregate with renormalization
            parts: List[Tuple[str, Optional[float], float]] = [
                ("compliance", compliance, 0.40),
                ("latency", latency_score, 0.20),
                ("stability", stability_score, 0.20),
                ("consistency", consistency_score, 0.20),
            ]
            available = [(n, v, w) for (n, v, w) in parts if v is not None]
            weight_sum = sum(w for _, _, w in available)
            value = sum((v if v is not None else 0.0) * w for _, v, w in parts) / (weight_sum if weight_sum > 0 else 1.0)
            
            confidence = 0.9 if grounded else 0.6
            # Reduce confidence if we couldn't compute consistency
            if consistency_score is None:
                confidence = max(0.0, confidence - 0.1)
            
            per = {
                'challenge_type': ev.action_type.value,
                'issued_timestamp': issued_ts,
                'severity': severity,
                'components': {
                    'compliance': compliance,
                    'latency': latency_score,
                    'stability': stability_score,
                    'consistency': consistency_score,
                    'steps_to_first_signal': steps_to_signal,
                    'stability_conflicts': conflicts
                },
                'confidence': _clamp01(confidence),
                'value': _clamp01(value),
                'binary_success': binary_success
            }
            per_challenge.append(per)
            weights.append(per['confidence'])
            values.append(per['value'])
            binary_outcomes.append(binary_success)
        
        # Aggregate across challenges with confidence weighting
        if sum(weights) > 0:
            overall = sum(v * w for v, w in zip(values, weights)) / sum(weights)
            conf = min(1.0, sum(weights) / max(1, len(weights)))
        else:
            overall = statistics.mean(values) if values else 1.0
            conf = 0.0
        
        binary_success_rate = (sum(binary_outcomes) / len(binary_outcomes)) if binary_outcomes else 0.0
        
        interpretation = (
            "Excellent adaptation to updates" if overall >= 0.85 else
            "Good adaptation to updates" if overall >= 0.7 else
            "Moderate adaptation to updates" if overall >= 0.5 else
            "Poor adaptation to updates"
        )
        
        return MetricResult(
            name="update_robustness",
            value=_clamp01(overall),
            confidence=_clamp01(conf),
            details={
                'coverage': len(per_challenge),
                'per_challenge': per_challenge,
                'binary_success_rate': _clamp01(binary_success_rate)
            },
            interpretation=interpretation
        )
    
    def _resumption_success_rate(self, task_trace: TaskTrace, task_spec: TaskSpecification) -> Optional[MetricResult]:
        """Compute Resumption Success Rate (RSR) from context switch resume events.
        
        Components and weights (default):
        - latency (0.35): exp(-steps_to_productive / τ), τ depends on severity (small=12, medium=18, large=25).
        - recall (0.25): Jaccard(files_touched_soon_after_resume, pre_switch_files_in_context) if a pre-switch
          ContextSnapshot exists; otherwise omitted.
        - fidelity (0.25): Same Jaccard proxy as recall, emphasizing early correct focus when plan hints are absent.
        - overhead (0.15): 1 - min(1, exploratory_action_ratio) in first N actions post-resume, to penalize thrash.
        
        Binary success signal:
        - per-event binary_success = 1 if the CONTEXT_SWITCH_RESUME action has success=True.
        - details.binary_success_rate aggregates these across resumes.
        
        Pre-switch context:
        - RSR benefits from a ContextSnapshot captured just before the switch; the runner captures one automatically
          using files accessed in the checkpoint to improve recall/fidelity confidence.
        """
        resume_events = [e for e in task_trace.memory_challenge_responses if e.action_type == ActionType.CONTEXT_SWITCH_RESUME]
        if not resume_events:
            return MetricResult(
                name="resumption_success_rate",
                value=1.0,
                confidence=0.0,
                details={'coverage': 0, 'per_challenge': []},
                interpretation="No context switch resumption events present"
            )
        
        all_actions = _flatten_all_actions(task_trace)
        # Gather all context snapshots across checkpoints
        all_snapshots: List[ContextSnapshot] = []
        for cp in task_trace.checkpoint_traces:
            all_snapshots.extend(cp.context_snapshots)
        all_snapshots.sort(key=lambda s: s.timestamp)
        
        per_challenge = []
        weights = []
        values = []
        
        # Helper: get previous CONTEXT_SWITCH_START before a resume
        start_events = [e for e in task_trace.memory_challenge_responses if e.action_type == ActionType.CONTEXT_SWITCH_START]
        start_events.sort(key=lambda e: e.timestamp)
        
        binary_outcomes: List[int] = []
        for resume in sorted(resume_events, key=lambda e: e.timestamp):
            resume_ts = resume.timestamp
            # Find matching start (most recent before resume)
            start_candidates = [s for s in start_events if s.timestamp <= resume_ts]
            start_ts = start_candidates[-1].timestamp if start_candidates else None
            
            # Pre-switch snapshot: last snapshot at or before start_ts
            pre_snapshot = None
            if start_ts is not None:
                candidates = [s for s in all_snapshots if s.timestamp <= start_ts]
                pre_snapshot = candidates[-1] if candidates else None
            
            # Steps to first productive action after resume
            first_prod_idx = _first_action_index_after(all_actions, resume_ts, _is_productive)
            if first_prod_idx is None:
                resume_latency = 0.0
                steps_to_prod = None
            else:
                issued_idx = _first_action_index_after(all_actions, resume_ts, lambda a: True)
                if issued_idx is None:
                    issued_idx = 0
                steps_to_prod = max(0, first_prod_idx - issued_idx)
                tau_steps = {'small': 12, 'medium': 18, 'large': 25}.get(str(resume.metadata.get('severity', 'medium')).lower(), 18)
                resume_latency = math.exp(-steps_to_prod / max(1, tau_steps))
            
            # Context recall: compare pre fileset with files touched in first K actions after resume
            files_after_resume: Set[str] = set()
            if first_prod_idx is not None:
                window = _actions_in_window(all_actions, first_prod_idx, 20)
            else:
                window = _actions_in_window(all_actions, _first_action_index_after(all_actions, resume_ts, lambda a: True) or 0, 20)
            for a in window:
                if a.file_path and a.action_type in [ActionType.FILE_READ, ActionType.FILE_WRITE, ActionType.FILE_MODIFY]:
                    files_after_resume.add(a.file_path)
            pre_fileset = set(pre_snapshot.files_in_context) if pre_snapshot else set()
            recall_score = _jaccard(files_after_resume, pre_fileset) if pre_snapshot else None
            
            # Fidelity: overlap of first touched files with pre fileset (fallback when no plan hints)
            fidelity_score = None
            if pre_snapshot:
                fidelity_score = _jaccard(files_after_resume, pre_fileset)
            
            # Overhead: proportion of exploratory actions in first N actions after resume
            N = 20
            first_idx = _first_action_index_after(all_actions, resume_ts, lambda a: True)
            exploratory_count = 0
            if first_idx is not None:
                window2 = _actions_in_window(all_actions, first_idx, N)
                for a in window2:
                    exploratory_count += 1 if _is_exploratory(a) else 0
            overhead_score = 1.0 - min(1.0, exploratory_count / float(N))
            
            parts: List[Tuple[str, Optional[float], float]] = [
                ("latency", resume_latency, 0.35),
                ("recall", recall_score, 0.25),
                ("fidelity", fidelity_score, 0.25),
                ("overhead", overhead_score, 0.15),
            ]
            # Binary success derived from resume event success flag
            binary_success = 1 if getattr(resume, 'success', False) else 0
            available = [(n, v, w) for (n, v, w) in parts if v is not None]
            weight_sum = sum(w for _, _, w in available)
            value = sum((v if v is not None else 0.0) * w for _, v, w in parts) / (weight_sum if weight_sum > 0 else 1.0)
            
            confidence = 0.8
            if pre_snapshot is None:
                confidence -= 0.15
            
            per = {
                'issued_timestamp': start_ts,
                'resume_timestamp': resume_ts,
                'components': {
                    'latency': resume_latency,
                    'steps_to_productive': steps_to_prod,
                    'recall': recall_score,
                    'fidelity': fidelity_score,
                    'overhead': overhead_score,
                },
                'confidence': _clamp01(confidence),
                'value': _clamp01(value),
                'binary_success': binary_success
            }
            per_challenge.append(per)
            weights.append(per['confidence'])
            values.append(per['value'])
            binary_outcomes.append(binary_success)
        
        if sum(weights) > 0:
            overall = sum(v * w for v, w in zip(values, weights)) / sum(weights)
            conf = min(1.0, sum(weights) / max(1, len(weights)))
        else:
            overall = statistics.mean(values) if values else 1.0
            conf = 0.0
        
        interpretation = (
            "Excellent resumption performance" if overall >= 0.85 else
            "Good resumption performance" if overall >= 0.7 else
            "Moderate resumption performance" if overall >= 0.5 else
            "Poor resumption performance"
        )
        
        binary_success_rate = (sum(binary_outcomes) / len(binary_outcomes)) if binary_outcomes else 0.0
        
        return MetricResult(
            name="resumption_success_rate",
            value=_clamp01(overall),
            confidence=_clamp01(conf),
            details={
                'coverage': len(per_challenge),
                'per_challenge': per_challenge,
                'binary_success_rate': _clamp01(binary_success_rate)
            },
            interpretation=interpretation
        )


# -------------------------
# Helper utilities (module)
# -------------------------

def _planned_step_token(step: Dict) -> Optional[str]:
    action = step.get("action")
    if action == "read_file":
        return f"read_file:{Path(step.get('file_path','')).name}"
    if action in ("create_file", "edit_file"):
        return f"write_file:{Path(step.get('file_path','')).name}"
    if action == "implement":
        return "implement"
    return None


def _executed_action_token(a: ActionTraceEntry) -> Optional[str]:
    if a.action_type == ActionType.FILE_READ and a.file_path:
        return f"read_file:{Path(a.file_path).name}"
    if a.action_type in (ActionType.FILE_WRITE, ActionType.FILE_MODIFY) and a.file_path:
        return f"write_file:{Path(a.file_path).name}"
    if a.action_type == ActionType.LLM_CALL:
        return "implement"
    return None


def _lcs_len(a: List[str], b: List[str]) -> int:
    n, m = len(a), len(b)
    dp = [[0]*(m+1) for _ in range(n+1)]
    for i in range(1, n+1):
        ai = a[i-1]
        for j in range(1, m+1):
            if ai == b[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[n][m]


def _greedy_match_ratio(plan: List[str], exec_: List[str], numerator_over: str) -> float:
    i = j = matched = 0
    while i < len(plan) and j < len(exec_):
        if plan[i] == exec_[j]:
            matched += 1
            i += 1
            j += 1
        else:
            j += 1
    denom = len(plan) if numerator_over == 'plan' else len(exec_)
    return matched / max(1, denom)


def _time_on_plan_ratio(exec_actions: List[ActionTraceEntry], exec_tokens: List[str], plan: List[str]) -> float:
    i = j = 0
    matched_exec_idxs: set[int] = set()
    while i < len(plan) and j < len(exec_tokens):
        if plan[i] == exec_tokens[j]:
            matched_exec_idxs.add(j)
            i += 1
            j += 1
        else:
            j += 1

    total = 0.0
    on_plan = 0.0
    for k in range(len(exec_actions) - 1):
        dt = max(0.0, (exec_actions[k+1].timestamp - exec_actions[k].timestamp) or 0.0)
        total += dt
        if k in matched_exec_idxs:
            on_plan += dt
    return (on_plan / total) if total > 0 else 0.0


def _compute_plan_compliance(task_spec: TaskSpecification, task_trace: TaskTrace) -> Dict[str, float]:
    if not task_trace or not task_trace.checkpoint_traces:
        return {
            "plan_coverage": 0.0,
            "plan_order_score": 0.0,
            "on_plan_action_ratio": 0.0,
            "time_on_plan_ratio": 0.0,
            "replan_count": 0.0,
        }

    from collections import Counter

    coverages: List[float] = []
    orders: List[float] = []
    on_plan_ratios: List[float] = []
    time_ratios: List[float] = []
    replans: int = 0

    for cp in task_trace.checkpoint_traces:
        plan_steps: List[Dict] = []
        planning_actions = [a for a in cp.actions if a.action_type == ActionType.PLANNING]
        if planning_actions:
            first_plan = planning_actions[0]
            plan_steps = first_plan.metadata.get("plan", []) or []
            replans += max(0, len(planning_actions) - 1)

        planned_tokens = [t for t in (_planned_step_token(s) for s in plan_steps) if t]

        exec_tokens: List[str] = []
        exec_actions: List[ActionTraceEntry] = []
        for a in cp.actions:
            t = _executed_action_token(a)
            if t:
                exec_tokens.append(t)
                exec_actions.append(a)

        plan_counts = Counter(planned_tokens)
        exec_counts = Counter(exec_tokens)
        matched_counts = sum(min(plan_counts[t], exec_counts.get(t, 0)) for t in plan_counts)
        coverage = matched_counts / max(1, len(planned_tokens))
        order = (_lcs_len(planned_tokens, exec_tokens) / max(1, len(planned_tokens))) if planned_tokens else 0.0
        on_plan = _greedy_match_ratio(planned_tokens, exec_tokens, numerator_over='exec')
        time_ratio = _time_on_plan_ratio(exec_actions, exec_tokens, planned_tokens) if exec_actions else 0.0

        coverages.append(coverage)
        orders.append(order)
        on_plan_ratios.append(on_plan)
        time_ratios.append(time_ratio)

    def avg(xs: List[float]) -> float:
        return (sum(xs) / len(xs)) if xs else 0.0

    return {
        "plan_coverage": avg(coverages),
        "plan_order_score": avg(orders),
        "on_plan_action_ratio": avg(on_plan_ratios),
        "time_on_plan_ratio": avg(time_ratios),
        "replan_count": float(replans),
    }


def _clamp01(x: Optional[float]) -> float:
    if x is None:
        return 0.0
    return max(0.0, min(1.0, x))


def _jaccard(a: Optional[Set[str]], b: Optional[Set[str]]) -> float:
    a = a or set()
    b = b or set()
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a.intersection(b))
    union = len(a.union(b))
    return inter / union if union > 0 else 0.0


def _flatten_all_actions(task_trace: TaskTrace) -> List[ActionTraceEntry]:
    """Chronologically flatten all actions across checkpoints and challenge events."""
    actions: List[ActionTraceEntry] = []
    for cp in task_trace.checkpoint_traces:
        actions.extend(cp.actions)
    actions.extend(task_trace.memory_challenge_responses)
    actions.sort(key=lambda a: a.timestamp)
    return actions


def _is_productive(action: ActionTraceEntry) -> bool:
    if action.action_type in [ActionType.FILE_WRITE, ActionType.FILE_MODIFY, ActionType.FILE_CREATE, ActionType.TEST_RUN]:
        return True
    if action.action_type == ActionType.COMMAND_EXECUTE:
        cmd = str(action.metadata.get('command', '')).lower()
        return 'pytest' in cmd or 'test' in cmd
    return False


def _is_exploratory(action: ActionTraceEntry) -> bool:
    if action.action_type in [ActionType.FILE_READ, ActionType.LLM_CALL, ActionType.PLANNING, ActionType.CONTEXT_UPDATE, ActionType.MEMORY_RETRIEVE]:
        return True
    if action.action_type == ActionType.COMMAND_EXECUTE:
        # Non-test commands considered exploratory
        cmd = str(action.metadata.get('command', '')).lower()
        return not ('pytest' in cmd or 'test' in cmd)
    return False


def _first_action_index_after(actions: List[ActionTraceEntry], ts: float, predicate) -> Optional[int]:
    for i, act in enumerate(actions):
        if act.timestamp > ts and predicate(act):
            return i
    return None


def _actions_in_window(actions: List[ActionTraceEntry], start_idx: int, count: int) -> List[ActionTraceEntry]:
    if start_idx is None:
        return []
    end = min(len(actions), start_idx + count)
    return actions[start_idx:end]


class WorkingMemoryEvaluationEngine:
    """Main evaluation engine that orchestrates the three-pillar analysis"""
    
    def __init__(self):
        self.memory_fidelity_evaluator = MemoryFidelityEvaluator()
        self.contextual_relevance_evaluator = ContextualRelevanceEvaluator()
        self.behavioral_integrity_evaluator = BehavioralIntegrityEvaluator()
    
    def evaluate_working_memory(
        self, 
        task_trace: TaskTrace, 
        task_spec: TaskSpecification,
        agent_name: str = "unknown"
    ) -> WorkingMemoryEvaluation:
        """Perform complete three-pillar working memory evaluation"""
        
        # Evaluate each pillar
        memory_fidelity_metrics = self.memory_fidelity_evaluator.evaluate(task_trace, task_spec)
        contextual_relevance_metrics = self.contextual_relevance_evaluator.evaluate(task_trace, task_spec)
        behavioral_integrity_metrics = self.behavioral_integrity_evaluator.evaluate(task_trace, task_spec)
        
        # Create pillar results
        memory_fidelity_result = self._create_pillar_result(
            "Memory Fidelity", 
            memory_fidelity_metrics,
            "Evaluates how effectively the agent retains and manages information over time"
        )
        
        contextual_relevance_result = self._create_pillar_result(
            "Contextual Relevance", 
            contextual_relevance_metrics,
            "Measures precision in accessing relevant information and avoiding distractors"
        )
        
        behavioral_integrity_result = self._create_pillar_result(
            "Behavioral Integrity", 
            behavioral_integrity_metrics,
            "Assesses consistency and coherence of agent behavior throughout execution"
        )
        
        # Calculate overall score
        overall_score = self._calculate_overall_score([
            memory_fidelity_result,
            contextual_relevance_result, 
            behavioral_integrity_result
        ])
        
        # Generate assessment
        grade = self._calculate_grade(overall_score)
        summary = self._generate_summary(overall_score, [
            memory_fidelity_result,
            contextual_relevance_result,
            behavioral_integrity_result
        ])
        
        strengths, weaknesses, improvements = self._generate_recommendations([
            memory_fidelity_result,
            contextual_relevance_result,
            behavioral_integrity_result
        ])
        
        return WorkingMemoryEvaluation(
            task_id=task_trace.task_id,
            agent_name=agent_name,
            timestamp=time.time(),
            memory_fidelity=memory_fidelity_result,
            contextual_relevance=contextual_relevance_result,
            behavioral_integrity=behavioral_integrity_result,
            overall_working_memory_score=overall_score,
            grade=grade,
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
            improvement_suggestions=improvements
        )
    
    def _create_pillar_result(self, pillar_name: str, metrics: List[MetricResult], description: str) -> PillarResult:
        """Create pillar result from individual metrics"""
        if not metrics:
            return PillarResult(
                pillar_name=pillar_name,
                overall_score=0.0,
                metrics=[],
                interpretation=f"No {pillar_name.lower()} metrics available"
            )
        
        # Calculate weighted average (higher confidence metrics have more weight)
        weighted_sum = sum(metric.value * metric.confidence for metric in metrics)
        weight_sum = sum(metric.confidence for metric in metrics)
        
        if weight_sum > 0:
            overall_score = weighted_sum / weight_sum
        else:
            overall_score = statistics.mean([metric.value for metric in metrics])
        
        # Generate interpretation
        if overall_score >= 0.85:
            interpretation = f"Excellent {pillar_name.lower()} - agent demonstrates strong capabilities"
        elif overall_score >= 0.7:
            interpretation = f"Good {pillar_name.lower()} - agent performs well with minor room for improvement"
        elif overall_score >= 0.5:
            interpretation = f"Fair {pillar_name.lower()} - mixed performance with clear areas for improvement"
        else:
            interpretation = f"Poor {pillar_name.lower()} - significant weaknesses impact overall performance"
        
        return PillarResult(
            pillar_name=pillar_name,
            overall_score=overall_score,
            metrics=metrics,
            interpretation=interpretation
        )
    
    def _calculate_overall_score(self, pillar_results: List[PillarResult]) -> float:
        """Calculate overall working memory score from pillar scores"""
        if not pillar_results:
            return 0.0
        return statistics.mean([pillar.overall_score for pillar in pillar_results])
    
    def _calculate_grade(self, overall_score: float) -> str:
        """Convert overall score to letter grade"""
        if overall_score >= 0.9:
            return "A"
        elif overall_score >= 0.8:
            return "B"
        elif overall_score >= 0.7:
            return "C"
        elif overall_score >= 0.6:
            return "D"
        else:
            return "F"
    
    def _generate_summary(self, overall_score: float, pillar_results: List[PillarResult]) -> str:
        """Generate human-readable summary"""
        grade = self._calculate_grade(overall_score)
        
        best_pillar = max(pillar_results, key=lambda p: p.overall_score)
        worst_pillar = min(pillar_results, key=lambda p: p.overall_score)
        
        summary = f"Overall Working Memory Grade: {grade} ({overall_score:.2f}/1.0)\n\n"
        summary += f"Strongest area: {best_pillar.pillar_name} ({best_pillar.overall_score:.2f})\n"
        summary += f"Weakest area: {worst_pillar.pillar_name} ({worst_pillar.overall_score:.2f})\n\n"
        
        for pillar in pillar_results:
            summary += f"{pillar.pillar_name}: {pillar.interpretation}\n"
        
        return summary
    
    def _generate_recommendations(self, pillar_results: List[PillarResult]) -> Tuple[List[str], List[str], List[str]]:
        """Generate strengths, weaknesses, and improvement suggestions"""
        strengths = []
        weaknesses = []
        improvements = []
        
        for pillar in pillar_results:
            if pillar.overall_score >= 0.8:
                strengths.append(f"Strong {pillar.pillar_name.lower()}")
            elif pillar.overall_score < 0.5:
                weaknesses.append(f"Weak {pillar.pillar_name.lower()}")
            
            # Generate specific recommendations based on metrics
            for metric in pillar.metrics:
                if metric.value < 0.5:
                    if "reread" in metric.name:
                        improvements.append("Reduce unnecessary file re-reading through better information retention")
                    elif "precision" in metric.name:
                        improvements.append("Improve focus on relevant files, avoid accessing unrelated content")
                    elif "recall" in metric.name:
                        improvements.append("Ensure all necessary files are accessed for complete understanding")
                    elif "error" in metric.name:
                        improvements.append("Reduce errors through better planning and validation")
                    elif "backtrack" in metric.name:
                        improvements.append("Improve forward planning to reduce backtracking")
                    elif "consistency" in metric.name:
                        improvements.append("Maintain more consistent approaches to similar problems")
        
        return strengths, weaknesses, improvements


# Export main classes
__all__ = [
    # Legacy functions (maintained for backward compatibility)
    'calculate_context_reread_rate',
    'calculate_size_weighted_reread_penalty', 
    'calculate_memory_compression_efficiency',
    'calculate_information_retention_score',
    'analyze_memory_degradation_over_time',
    'get_memory_fidelity_diagnostics',
    
    # New three-pillar system
    'MetricResult',
    'PillarResult', 
    'WorkingMemoryEvaluation',
    'WorkingMemoryEvaluationEngine',
    'MemoryFidelityEvaluator',
    'ContextualRelevanceEvaluator',
    'BehavioralIntegrityEvaluator'
]
