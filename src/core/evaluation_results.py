"""
WorkMemEval: Evaluation Results Data Structures

This module defines the data structures for storing and analyzing WorkMemEval
evaluation results, including the three-pillar working memory metrics and
diagnostic analysis capabilities.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from enum import Enum
import json
from pathlib import Path
import statistics
import time


class WorkingMemoryPillar(Enum):
    """Three pillars of working memory evaluation"""
    MEMORY_FIDELITY = "memory_fidelity"           # Information retention and compression
    CONTEXTUAL_RELEVANCE = "contextual_relevance"  # Information filtering and selection
    BEHAVIORAL_INTEGRITY = "behavioral_integrity"  # Coherent action under complexity


@dataclass
class MemoryFidelityMetrics:
    """
    Memory Fidelity pillar metrics.
    
    Measures the agent's ability to maintain accurate, complete information
    over time without degradation or unnecessary redundancy.
    """
    # Core memory fidelity measurements
    context_reread_rate: float              # Proportion of unnecessary file re-accesses
    size_weighted_reread_penalty: float     # Size-weighted penalty for rereads
    information_retention_score: float      # Cross-checkpoint information retention
    compression_efficiency: float           # Memory compression effectiveness
    overall_fidelity_score: float          # Combined fidelity assessment
    
    # Temporal analysis
    degradation_analysis: Dict[str, Any] = field(default_factory=dict)
    
    # Diagnostic information
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    
    # Supporting data (preserved for compatibility)
    file_access_statistics: Dict[str, Any] = field(default_factory=dict)
    compression_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Deprecated fields (kept for compatibility)
    information_persistence_score: float = 0.0  # Replaced by information_retention_score
    tcil_score: float = 0.0                    # Replaced by compression_efficiency
    
    def __post_init__(self):
        """Calculate overall fidelity score from component metrics"""
        if self.overall_fidelity_score == 0.0:
            # Calculate weighted average of core metrics
            # Lower reread rate and penalty = higher score
            reread_score = 1.0 - self.context_reread_rate
            penalty_score = 1.0 - self.size_weighted_reread_penalty
            retention_score = self.information_retention_score
            compression_score = self.compression_efficiency
            
            # Weighted combination (can be tuned based on importance)
            weights = {'reread': 0.3, 'penalty': 0.2, 'retention': 0.3, 'compression': 0.2}
            
            self.overall_fidelity_score = (
                weights['reread'] * reread_score +
                weights['penalty'] * penalty_score +
                weights['retention'] * retention_score +
                weights['compression'] * compression_score
            )
            
            # Ensure score is in valid range
            self.overall_fidelity_score = max(0.0, min(1.0, self.overall_fidelity_score))
        
        # Set deprecated fields for compatibility
        self.information_persistence_score = self.information_retention_score
        self.tcil_score = self.compression_efficiency
    
    def get_pillar_score(self) -> float:
        """Get the overall pillar score (0.0 to 1.0)"""
        return self.overall_fidelity_score
    
    def get_diagnostic_summary(self) -> Dict[str, str]:
        """Get diagnostic interpretation of memory fidelity performance"""
        diagnostics = {}
        
        if self.context_reread_rate > 0.3:
            diagnostics['retention'] = "Poor information retention - excessive context re-reading"
        elif self.context_reread_rate > 0.1:
            diagnostics['retention'] = "Moderate information retention issues"
        else:
            diagnostics['retention'] = "Good information retention"
        
        if self.tcil_score < 0.7:
            diagnostics['compression'] = "Significant information loss during compression"
        elif self.tcil_score < 0.9:
            diagnostics['compression'] = "Minor information loss during compression"
        else:
            diagnostics['compression'] = "High-quality information compression"
        
        return diagnostics


@dataclass
class ContextualRelevanceMetrics:
    """
    Contextual Relevance pillar metrics.
    
    Measures the agent's ability to select and surface the right information
    at the right time for the current task context.
    """
    # Relevance assessment
    relevance_f1_score: float          # F1 of relevant vs accessed information
    relevance_precision: float         # Precision of information selection
    relevance_recall: float            # Recall of required information
    
    # Distractor resistance
    distractor_resistance_score: float # Ability to ignore irrelevant information
    focus_maintenance_score: float     # Sustained attention to relevant info
    
    # Aggregate score  
    overall_relevance_score: float     # Combined relevance assessment
    
    # Supporting data
    file_relevance_analysis: Dict[str, Any] = field(default_factory=dict)
    distractor_access_log: List[str] = field(default_factory=list)
    
    def get_pillar_score(self) -> float:
        """Get the overall pillar score (0.0 to 1.0)"""
        return self.overall_relevance_score
    
    def get_diagnostic_summary(self) -> Dict[str, str]:
        """Get diagnostic interpretation of contextual relevance performance"""
        diagnostics = {}
        
        if self.relevance_precision < 0.6:
            diagnostics['precision'] = "Poor information filtering - accessing too much irrelevant content"
        elif self.relevance_precision < 0.8:
            diagnostics['precision'] = "Moderate information filtering issues"
        else:
            diagnostics['precision'] = "Good information filtering"
        
        if self.relevance_recall < 0.6:
            diagnostics['recall'] = "Missing critical information - incomplete coverage"
        elif self.relevance_recall < 0.8:
            diagnostics['recall'] = "Minor gaps in information coverage"
        else:
            diagnostics['recall'] = "Comprehensive information coverage"
        
        if self.distractor_resistance_score < 0.7:
            diagnostics['distraction'] = "High susceptibility to irrelevant information"
        else:
            diagnostics['distraction'] = "Good resistance to distractors"
        
        return diagnostics


@dataclass
class BehavioralIntegrityMetrics:
    """
    Behavioral Integrity pillar metrics.
    
    Measures whether good memory translates into coherent, correct action
    under complexity and working memory load.
    """
    # Error patterns
    error_correction_overhead: float   # Frequency of unforced errors
    unforced_error_rate: float        # Proportion of avoidable errors
    backtracking_frequency: float     # Rate of implementation reversals
    
    # State coherence
    state_coherence_index: float      # Consistency of system state
    integration_success_rate: float   # Success at component integration
    
    # Adaptation capability
    update_robustness: float          # Success with requirement changes
    resumption_success_rate: float   # Recovery from interruptions
    
    # Aggregate score
    overall_integrity_score: float   # Combined integrity assessment
    
    # Supporting data
    error_pattern_analysis: Dict[str, Any] = field(default_factory=dict)
    coherence_check_results: List[Dict[str, Any]] = field(default_factory=list)
    adaptation_events: List[Dict[str, Any]] = field(default_factory=list)
    
    def get_pillar_score(self) -> float:
        """Get the overall pillar score (0.0 to 1.0)"""
        return self.overall_integrity_score
    
    def get_diagnostic_summary(self) -> Dict[str, str]:
        """Get diagnostic interpretation of behavioral integrity performance"""
        diagnostics = {}
        
        if self.error_correction_overhead > 0.3:
            diagnostics['errors'] = "High error rate - frequent mistakes and corrections"
        elif self.error_correction_overhead > 0.1:
            diagnostics['errors'] = "Moderate error rate"
        else:
            diagnostics['errors'] = "Low error rate - good execution quality"
        
        if self.state_coherence_index < 0.7:
            diagnostics['coherence'] = "Poor system state coherence - inconsistent implementation"
        elif self.state_coherence_index < 0.9:
            diagnostics['coherence'] = "Minor coherence issues"
        else:
            diagnostics['coherence'] = "Good system state coherence"
        
        if self.update_robustness < 0.5:
            diagnostics['adaptation'] = "Poor adaptation to requirement changes"
        elif self.update_robustness < 0.8:
            diagnostics['adaptation'] = "Moderate adaptation capability"
        else:
            diagnostics['adaptation'] = "Good adaptation to changes"
        
        return diagnostics


@dataclass
class WorkingMemoryMetrics:
    """
    Complete working memory evaluation metrics across all three pillars.
    
    Provides comprehensive assessment and diagnostic capabilities for
    agent working memory performance.
    """
    # Three pillar metrics
    memory_fidelity: MemoryFidelityMetrics
    contextual_relevance: ContextualRelevanceMetrics
    behavioral_integrity: BehavioralIntegrityMetrics
    
    # Overall assessment
    overall_working_memory_score: float = 0.0
    task_completion_success: bool = False  # Gating metric
    
    def __post_init__(self):
        """Calculate overall working memory score"""
        if self.task_completion_success:
            # Only calculate if task was completed successfully
            pillar_scores = [
                self.memory_fidelity.get_pillar_score(),
                self.contextual_relevance.get_pillar_score(),
                self.behavioral_integrity.get_pillar_score()
            ]
            self.overall_working_memory_score = statistics.mean(pillar_scores)
        else:
            self.overall_working_memory_score = 0.0
    
    def get_failure_mode_diagnosis(self) -> Dict[str, Any]:
        """
        Diagnose working memory failure modes based on pillar performance patterns.
        
        This implements the diagnostic power of the three-pillar framework.
        """
        fidelity_score = self.memory_fidelity.get_pillar_score()
        relevance_score = self.contextual_relevance.get_pillar_score()
        integrity_score = self.behavioral_integrity.get_pillar_score()
        
        # Define thresholds for high/low performance
        HIGH_THRESHOLD = 0.7
        LOW_THRESHOLD = 0.5
        
        # Classify pillar performance
        high_fidelity = fidelity_score >= HIGH_THRESHOLD
        high_relevance = relevance_score >= HIGH_THRESHOLD
        high_integrity = integrity_score >= HIGH_THRESHOLD
        
        low_fidelity = fidelity_score <= LOW_THRESHOLD
        low_relevance = relevance_score <= LOW_THRESHOLD
        low_integrity = integrity_score <= LOW_THRESHOLD
        
        # Diagnostic patterns from the framework
        diagnosis = {
            'pattern': 'unknown',
            'primary_issue': 'unclear',
            'secondary_issues': [],
            'recommendations': []
        }
        
        if high_fidelity and high_relevance and low_integrity:
            diagnosis.update({
                'pattern': 'reasoning_execution_failure',
                'primary_issue': 'Reasoning or execution failure, not memory failure',
                'recommendations': [
                    'Check reasoning capabilities',
                    'Examine code generation quality',
                    'Verify execution environment'
                ]
            })
        elif low_fidelity and not low_relevance and not low_integrity:
            # Only fidelity is low, other pillars are OK
            diagnosis.update({
                'pattern': 'memory_storage_problems',
                'primary_issue': 'Memory storage and retention problems',
                'recommendations': [
                    'Improve information retention mechanisms',
                    'Reduce context re-reading',
                    'Enhance compression quality'
                ]
            })
        elif high_fidelity and low_relevance and not low_integrity:
            # Only relevance is low, other pillars are OK
            diagnosis.update({
                'pattern': 'memory_retrieval_selection_problems',
                'primary_issue': 'Memory retrieval and selection problems',
                'recommendations': [
                    'Improve information filtering',
                    'Enhance relevance detection',
                    'Reduce distractor susceptibility'
                ]
            })
        elif high_fidelity and high_relevance and high_integrity:
            diagnosis.update({
                'pattern': 'successful_working_memory',
                'primary_issue': 'No significant working memory issues detected',
                'recommendations': [
                    'Performance is good across all pillars',
                    'Consider increasing task complexity for further evaluation'
                ]
            })
        else:
            # Mixed or unclear pattern
            issues = []
            if low_fidelity:
                issues.append('memory_fidelity')
            if low_relevance:
                issues.append('contextual_relevance')
            if low_integrity:
                issues.append('behavioral_integrity')
            
            diagnosis.update({
                'pattern': 'mixed_performance',
                'primary_issue': f'Multiple working memory issues: {", ".join(issues)}',
                'secondary_issues': issues,
                'recommendations': [
                    'Address multiple pillar deficiencies',
                    'Consider systematic working memory improvement'
                ]
            })
        
        # Add pillar scores for reference
        diagnosis['pillar_scores'] = {
            'memory_fidelity': fidelity_score,
            'contextual_relevance': relevance_score,
            'behavioral_integrity': integrity_score
        }
        
        return diagnosis
    
    def get_comprehensive_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of working memory evaluation"""
        return {
            'overall_score': self.overall_working_memory_score,
            'task_completion_success': self.task_completion_success,
            'pillar_scores': {
                'memory_fidelity': self.memory_fidelity.get_pillar_score(),
                'contextual_relevance': self.contextual_relevance.get_pillar_score(),
                'behavioral_integrity': self.behavioral_integrity.get_pillar_score()
            },
            'pillar_diagnostics': {
                'memory_fidelity': self.memory_fidelity.get_diagnostic_summary(),
                'contextual_relevance': self.contextual_relevance.get_diagnostic_summary(),
                'behavioral_integrity': self.behavioral_integrity.get_diagnostic_summary()
            },
            'failure_mode_diagnosis': self.get_failure_mode_diagnosis()
        }


@dataclass
class CheckpointEvaluationResult:
    """
    Evaluation results for a single checkpoint.
    
    Contains both objective test results and working memory metrics
    for checkpoint-level analysis.
    """
    checkpoint_id: str
    task_success: bool                 # Gating metric - did tests pass?
    completion_time_ms: float         # Time to complete checkpoint
    
    # Working memory metrics (only valid if task_success is True)
    working_memory_metrics: Optional[WorkingMemoryMetrics] = None
    
    # Supporting data
    test_results: Dict[str, Any] = field(default_factory=dict)
    action_count: int = 0
    error_count: int = 0
    
    def is_valid_for_analysis(self) -> bool:
        """Check if checkpoint results are valid for working memory analysis"""
        return self.task_success and self.working_memory_metrics is not None


@dataclass
class TaskEvaluationResult:
    """
    Complete evaluation results for a WorkMemEval task.
    
    Aggregates checkpoint results and provides task-level working memory
    assessment with comprehensive diagnostic capabilities.
    """
    task_id: str
    start_timestamp: float
    end_timestamp: float
    total_duration_ms: float
    
    # Task completion status
    completed_successfully: bool       # Did agent complete all checkpoints?
    checkpoints_completed: int        # Number of checkpoints completed
    total_checkpoints: int           # Total checkpoints in task
    
    # Checkpoint results
    checkpoint_results: List[CheckpointEvaluationResult] = field(default_factory=list)
    
    # Aggregated working memory metrics
    aggregated_metrics: Optional[WorkingMemoryMetrics] = None
    
    # Task-level statistics
    total_actions: int = 0
    total_errors: int = 0
    overall_error_rate: float = 0.0
    
    # Complexity scaling analysis
    complexity_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate aggregated metrics and task-level statistics"""
        self._calculate_task_statistics()
        if self.completed_successfully:
            self._calculate_aggregated_metrics()
    
    def _calculate_task_statistics(self):
        """Calculate task-level statistics from checkpoint results"""
        self.total_actions = sum(cp.action_count for cp in self.checkpoint_results)
        self.total_errors = sum(cp.error_count for cp in self.checkpoint_results)
        
        if self.total_actions > 0:
            self.overall_error_rate = self.total_errors / self.total_actions
        
        self.checkpoints_completed = sum(1 for cp in self.checkpoint_results if cp.task_success)
    
    def _calculate_aggregated_metrics(self):
        """Calculate aggregated working memory metrics across checkpoints"""
        valid_checkpoints = [cp for cp in self.checkpoint_results if cp.is_valid_for_analysis()]
        
        if not valid_checkpoints:
            return
        
        # Aggregate memory fidelity metrics
        fidelity_metrics = []
        for cp in valid_checkpoints:
            fidelity_metrics.append(cp.working_memory_metrics.memory_fidelity)
        
        avg_fidelity = MemoryFidelityMetrics(
            context_reread_rate=statistics.mean(m.context_reread_rate for m in fidelity_metrics),
            size_weighted_reread_penalty=statistics.mean(m.size_weighted_reread_penalty for m in fidelity_metrics),
            information_retention_score=statistics.mean(m.information_retention_score for m in fidelity_metrics),
            compression_efficiency=statistics.mean(m.compression_efficiency for m in fidelity_metrics),
            overall_fidelity_score=statistics.mean(m.overall_fidelity_score for m in fidelity_metrics)
        )
        
        # Aggregate contextual relevance metrics
        relevance_metrics = []
        for cp in valid_checkpoints:
            relevance_metrics.append(cp.working_memory_metrics.contextual_relevance)
        
        avg_relevance = ContextualRelevanceMetrics(
            relevance_f1_score=statistics.mean(m.relevance_f1_score for m in relevance_metrics),
            relevance_precision=statistics.mean(m.relevance_precision for m in relevance_metrics),
            relevance_recall=statistics.mean(m.relevance_recall for m in relevance_metrics),
            distractor_resistance_score=statistics.mean(m.distractor_resistance_score for m in relevance_metrics),
            focus_maintenance_score=statistics.mean(m.focus_maintenance_score for m in relevance_metrics),
            overall_relevance_score=statistics.mean(m.overall_relevance_score for m in relevance_metrics)
        )
        
        # Aggregate behavioral integrity metrics
        integrity_metrics = []
        for cp in valid_checkpoints:
            integrity_metrics.append(cp.working_memory_metrics.behavioral_integrity)
        
        avg_integrity = BehavioralIntegrityMetrics(
            error_correction_overhead=statistics.mean(m.error_correction_overhead for m in integrity_metrics),
            unforced_error_rate=statistics.mean(m.unforced_error_rate for m in integrity_metrics),
            backtracking_frequency=statistics.mean(m.backtracking_frequency for m in integrity_metrics),
            state_coherence_index=statistics.mean(m.state_coherence_index for m in integrity_metrics),
            integration_success_rate=statistics.mean(m.integration_success_rate for m in integrity_metrics),
            update_robustness=statistics.mean(m.update_robustness for m in integrity_metrics),
            resumption_success_rate=statistics.mean(m.resumption_success_rate for m in integrity_metrics),
            overall_integrity_score=statistics.mean(m.overall_integrity_score for m in integrity_metrics)
        )
        
        # Create aggregated working memory metrics
        self.aggregated_metrics = WorkingMemoryMetrics(
            memory_fidelity=avg_fidelity,
            contextual_relevance=avg_relevance,
            behavioral_integrity=avg_integrity,
            task_completion_success=self.completed_successfully
        )
    
    def get_completion_rate(self) -> float:
        """Get task completion rate (0.0 to 1.0)"""
        if self.total_checkpoints == 0:
            return 0.0
        return self.checkpoints_completed / self.total_checkpoints
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        summary = {
            'task_id': self.task_id,
            'completed_successfully': self.completed_successfully,
            'completion_rate': self.get_completion_rate(),
            'total_duration_minutes': self.total_duration_ms / (1000 * 60),
            'overall_error_rate': self.overall_error_rate,
            'checkpoints_completed': self.checkpoints_completed,
            'total_checkpoints': self.total_checkpoints
        }
        
        if self.aggregated_metrics:
            summary.update({
                'working_memory_score': self.aggregated_metrics.overall_working_memory_score,
                'working_memory_summary': self.aggregated_metrics.get_comprehensive_summary()
            })
        
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task evaluation result to dictionary for serialization"""
        return {
            'task_id': self.task_id,
            'start_timestamp': self.start_timestamp,
            'end_timestamp': self.end_timestamp,
            'total_duration_ms': self.total_duration_ms,
            'completed_successfully': self.completed_successfully,
            'checkpoints_completed': self.checkpoints_completed,
            'total_checkpoints': self.total_checkpoints,
            'checkpoint_results': [
                {
                    'checkpoint_id': cp.checkpoint_id,
                    'task_success': cp.task_success,
                    'completion_time_ms': cp.completion_time_ms,
                    'action_count': cp.action_count,
                    'error_count': cp.error_count,
                    'test_results': cp.test_results,
                    # Note: working_memory_metrics would need custom serialization
                }
                for cp in self.checkpoint_results
            ],
            'task_statistics': {
                'total_actions': self.total_actions,
                'total_errors': self.total_errors,
                'overall_error_rate': self.overall_error_rate,
                'completion_rate': self.get_completion_rate()
            },
            'complexity_metrics': self.complexity_metrics,
            'performance_summary': self.get_performance_summary()
        }
    
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save evaluation result to JSON file"""
        path = Path(file_path)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


@dataclass
class EvaluationSession:
    """
    Results from evaluating multiple tasks in a single session.
    
    Provides comparative analysis capabilities and session-level insights
    for working memory performance across multiple tasks.
    """
    session_id: str
    start_timestamp: float
    end_timestamp: Optional[float] = None
    
    # Task results
    task_results: List[TaskEvaluationResult] = field(default_factory=list)
    
    # Session statistics
    total_tasks_attempted: int = 0
    total_tasks_completed: int = 0
    session_duration_ms: Optional[float] = None
    
    def add_task_result(self, task_result: TaskEvaluationResult):
        """Add a task result to the session"""
        self.task_results.append(task_result)
        self.total_tasks_attempted = len(self.task_results)
        self.total_tasks_completed = sum(1 for tr in self.task_results if tr.completed_successfully)
    
    def complete_session(self):
        """Mark the session as completed"""
        self.end_timestamp = time.time()
        if self.end_timestamp:
            self.session_duration_ms = (self.end_timestamp - self.start_timestamp) * 1000
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get comprehensive session summary with comparative analysis"""
        if not self.task_results:
            return {'message': 'No task results in session'}
        
        completed_tasks = [tr for tr in self.task_results if tr.completed_successfully]
        
        summary = {
            'session_id': self.session_id,
            'total_tasks_attempted': self.total_tasks_attempted,
            'total_tasks_completed': self.total_tasks_completed,
            'session_completion_rate': self.total_tasks_completed / self.total_tasks_attempted,
            'session_duration_minutes': (self.session_duration_ms / (1000 * 60)) if self.session_duration_ms else None
        }
        
        if completed_tasks:
            # Calculate session-level working memory metrics
            session_wm_scores = [
                tr.aggregated_metrics.overall_working_memory_score 
                for tr in completed_tasks 
                if tr.aggregated_metrics
            ]
            
            if session_wm_scores:
                summary.update({
                    'average_working_memory_score': statistics.mean(session_wm_scores),
                    'working_memory_score_std': statistics.stdev(session_wm_scores) if len(session_wm_scores) > 1 else 0.0,
                    'min_working_memory_score': min(session_wm_scores),
                    'max_working_memory_score': max(session_wm_scores)
                })
        
        return summary
