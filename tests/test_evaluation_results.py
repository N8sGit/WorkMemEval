"""
Unit tests for WorkMemEval evaluation results module.

Tests three-pillar metrics, diagnostic capabilities, and result aggregation
following TDD principles with comprehensive coverage.
"""

import time

import pytest

from src.core.evaluation_results import (
    BehavioralIntegrityMetrics,
    CheckpointEvaluationResult,
    ContextualRelevanceMetrics,
    EvaluationSession,
    MemoryFidelityMetrics,
    TaskEvaluationResult,
    WorkingMemoryMetrics,
)


class TestMemoryFidelityMetrics:
    """Test Memory Fidelity pillar metrics"""

    def test_memory_fidelity_creation(self):
        """Test creating memory fidelity metrics"""
        metrics = MemoryFidelityMetrics(
            context_reread_rate=0.15,
            information_persistence_score=0.85,
            tcil_score=0.92,
            compression_efficiency=0.88,
            overall_fidelity_score=0.87,
        )

        assert metrics.context_reread_rate == 0.15
        assert metrics.information_persistence_score == 0.85
        assert metrics.tcil_score == 0.92
        assert metrics.compression_efficiency == 0.88
        assert metrics.get_pillar_score() == 0.87

    def test_fidelity_diagnostic_good_performance(self):
        """Test diagnostics for good memory fidelity performance"""
        metrics = MemoryFidelityMetrics(
            context_reread_rate=0.05,  # Good
            information_persistence_score=0.9,
            tcil_score=0.95,  # Good
            compression_efficiency=0.9,
            overall_fidelity_score=0.9,
        )

        diagnostics = metrics.get_diagnostic_summary()
        assert "Good information retention" in diagnostics["retention"]
        assert "High-quality information compression" in diagnostics["compression"]

    def test_fidelity_diagnostic_poor_performance(self):
        """Test diagnostics for poor memory fidelity performance"""
        metrics = MemoryFidelityMetrics(
            context_reread_rate=0.4,  # Poor
            information_persistence_score=0.6,
            tcil_score=0.65,  # Poor
            compression_efficiency=0.6,
            overall_fidelity_score=0.6,
        )

        diagnostics = metrics.get_diagnostic_summary()
        assert "Poor information retention" in diagnostics["retention"]
        assert "Significant information loss" in diagnostics["compression"]


class TestContextualRelevanceMetrics:
    """Test Contextual Relevance pillar metrics"""

    def test_contextual_relevance_creation(self):
        """Test creating contextual relevance metrics"""
        metrics = ContextualRelevanceMetrics(
            relevance_f1_score=0.82,
            relevance_precision=0.85,
            relevance_recall=0.79,
            distractor_resistance_score=0.88,
            focus_maintenance_score=0.91,
            overall_relevance_score=0.85,
        )

        assert metrics.relevance_f1_score == 0.82
        assert metrics.relevance_precision == 0.85
        assert metrics.relevance_recall == 0.79
        assert metrics.get_pillar_score() == 0.85

    def test_relevance_diagnostic_good_performance(self):
        """Test diagnostics for good contextual relevance performance"""
        metrics = ContextualRelevanceMetrics(
            relevance_f1_score=0.9,
            relevance_precision=0.85,  # Good
            relevance_recall=0.87,  # Good
            distractor_resistance_score=0.9,  # Good
            focus_maintenance_score=0.9,
            overall_relevance_score=0.88,
        )

        diagnostics = metrics.get_diagnostic_summary()
        assert "Good information filtering" in diagnostics["precision"]
        assert "Comprehensive information coverage" in diagnostics["recall"]
        assert "Good resistance to distractors" in diagnostics["distraction"]

    def test_relevance_diagnostic_poor_performance(self):
        """Test diagnostics for poor contextual relevance performance"""
        metrics = ContextualRelevanceMetrics(
            relevance_f1_score=0.5,
            relevance_precision=0.5,  # Poor
            relevance_recall=0.5,  # Poor
            distractor_resistance_score=0.6,  # Poor
            focus_maintenance_score=0.6,
            overall_relevance_score=0.55,
        )

        diagnostics = metrics.get_diagnostic_summary()
        assert "Poor information filtering" in diagnostics["precision"]
        assert "Missing critical information" in diagnostics["recall"]
        assert "High susceptibility" in diagnostics["distraction"]


class TestBehavioralIntegrityMetrics:
    """Test Behavioral Integrity pillar metrics"""

    def test_behavioral_integrity_creation(self):
        """Test creating behavioral integrity metrics"""
        metrics = BehavioralIntegrityMetrics(
            error_correction_overhead=0.08,
            unforced_error_rate=0.05,
            backtracking_frequency=0.03,
            state_coherence_index=0.92,
            integration_success_rate=0.95,
            update_robustness=0.88,
            resumption_success_rate=0.9,
            overall_integrity_score=0.89,
        )

        assert metrics.error_correction_overhead == 0.08
        assert metrics.state_coherence_index == 0.92
        assert metrics.update_robustness == 0.88
        assert metrics.get_pillar_score() == 0.89

    def test_integrity_diagnostic_good_performance(self):
        """Test diagnostics for good behavioral integrity performance"""
        metrics = BehavioralIntegrityMetrics(
            error_correction_overhead=0.05,  # Good
            unforced_error_rate=0.03,
            backtracking_frequency=0.02,
            state_coherence_index=0.95,  # Good
            integration_success_rate=0.95,
            update_robustness=0.9,  # Good
            resumption_success_rate=0.9,
            overall_integrity_score=0.9,
        )

        diagnostics = metrics.get_diagnostic_summary()
        assert "Low error rate" in diagnostics["errors"]
        assert "Good system state coherence" in diagnostics["coherence"]
        assert "Good adaptation" in diagnostics["adaptation"]

    def test_integrity_diagnostic_poor_performance(self):
        """Test diagnostics for poor behavioral integrity performance"""
        metrics = BehavioralIntegrityMetrics(
            error_correction_overhead=0.4,  # Poor
            unforced_error_rate=0.3,
            backtracking_frequency=0.2,
            state_coherence_index=0.6,  # Poor
            integration_success_rate=0.7,
            update_robustness=0.4,  # Poor
            resumption_success_rate=0.5,
            overall_integrity_score=0.55,
        )

        diagnostics = metrics.get_diagnostic_summary()
        assert "High error rate" in diagnostics["errors"]
        assert "Poor system state coherence" in diagnostics["coherence"]
        assert "Poor adaptation" in diagnostics["adaptation"]


class TestWorkingMemoryMetrics:
    """Test complete working memory metrics and diagnostics"""

    def create_sample_metrics(
        self, fidelity_score=0.8, relevance_score=0.8, integrity_score=0.8
    ) -> WorkingMemoryMetrics:
        """Create sample working memory metrics for testing"""
        fidelity = MemoryFidelityMetrics(
            context_reread_rate=0.1,
            information_persistence_score=fidelity_score,
            tcil_score=fidelity_score,
            compression_efficiency=fidelity_score,
            overall_fidelity_score=fidelity_score,
        )

        relevance = ContextualRelevanceMetrics(
            relevance_f1_score=relevance_score,
            relevance_precision=relevance_score,
            relevance_recall=relevance_score,
            distractor_resistance_score=relevance_score,
            focus_maintenance_score=relevance_score,
            overall_relevance_score=relevance_score,
        )

        integrity = BehavioralIntegrityMetrics(
            error_correction_overhead=0.1,
            unforced_error_rate=0.05,
            backtracking_frequency=0.03,
            state_coherence_index=integrity_score,
            integration_success_rate=integrity_score,
            update_robustness=integrity_score,
            resumption_success_rate=integrity_score,
            overall_integrity_score=integrity_score,
        )

        return WorkingMemoryMetrics(
            memory_fidelity=fidelity,
            contextual_relevance=relevance,
            behavioral_integrity=integrity,
            task_completion_success=True,
        )

    def test_working_memory_metrics_successful_task(self):
        """Test working memory metrics for successful task"""
        metrics = self.create_sample_metrics(0.8, 0.7, 0.9)

        assert metrics.task_completion_success is True
        # Use statistics.mean for consistent floating point calculation
        import statistics

        expected_score = statistics.mean([0.8, 0.7, 0.9])
        assert metrics.overall_working_memory_score == expected_score

    def test_working_memory_metrics_failed_task(self):
        """Test working memory metrics for failed task (gating metric)"""
        metrics = self.create_sample_metrics()
        metrics.task_completion_success = False
        metrics.__post_init__()  # Recalculate score

        assert metrics.task_completion_success is False
        assert metrics.overall_working_memory_score == 0.0

    def test_failure_mode_reasoning_execution_failure(self):
        """Test diagnosis of reasoning/execution failure pattern"""
        metrics = self.create_sample_metrics(
            fidelity_score=0.8,  # High
            relevance_score=0.8,  # High
            integrity_score=0.4,  # Low
        )

        diagnosis = metrics.get_failure_mode_diagnosis()
        assert diagnosis["pattern"] == "reasoning_execution_failure"
        assert "not memory failure" in diagnosis["primary_issue"]
        assert "reasoning capabilities" in diagnosis["recommendations"][0]

    def test_failure_mode_memory_storage_problems(self):
        """Test diagnosis of memory storage problems pattern"""
        metrics = self.create_sample_metrics(
            fidelity_score=0.4,  # Low
            relevance_score=0.8,  # High
            integrity_score=0.8,  # High
        )

        diagnosis = metrics.get_failure_mode_diagnosis()
        assert diagnosis["pattern"] == "memory_storage_problems"
        assert "Memory storage" in diagnosis["primary_issue"]
        assert "retention mechanisms" in diagnosis["recommendations"][0]

    def test_failure_mode_memory_retrieval_problems(self):
        """Test diagnosis of memory retrieval/selection problems pattern"""
        metrics = self.create_sample_metrics(
            fidelity_score=0.8,  # High
            relevance_score=0.4,  # Low
            integrity_score=0.8,  # High
        )

        diagnosis = metrics.get_failure_mode_diagnosis()
        assert diagnosis["pattern"] == "memory_retrieval_selection_problems"
        assert "retrieval and selection" in diagnosis["primary_issue"]
        assert "information filtering" in diagnosis["recommendations"][0]

    def test_failure_mode_successful_working_memory(self):
        """Test diagnosis of successful working memory pattern"""
        metrics = self.create_sample_metrics(
            fidelity_score=0.8,  # High
            relevance_score=0.8,  # High
            integrity_score=0.8,  # High
        )

        diagnosis = metrics.get_failure_mode_diagnosis()
        assert diagnosis["pattern"] == "successful_working_memory"
        assert "No significant" in diagnosis["primary_issue"]
        assert "good across all pillars" in diagnosis["recommendations"][0]

    def test_failure_mode_mixed_performance(self):
        """Test diagnosis of mixed performance pattern"""
        metrics = self.create_sample_metrics(
            fidelity_score=0.4,  # Low
            relevance_score=0.4,  # Low
            integrity_score=0.8,  # High
        )

        diagnosis = metrics.get_failure_mode_diagnosis()
        assert diagnosis["pattern"] == "mixed_performance"
        assert "Multiple working memory issues" in diagnosis["primary_issue"]
        assert "memory_fidelity" in diagnosis["secondary_issues"]
        assert "contextual_relevance" in diagnosis["secondary_issues"]

    def test_comprehensive_summary(self):
        """Test comprehensive summary generation"""
        metrics = self.create_sample_metrics(0.8, 0.7, 0.9)
        summary = metrics.get_comprehensive_summary()

        assert "overall_score" in summary
        assert "pillar_scores" in summary
        assert "pillar_diagnostics" in summary
        assert "failure_mode_diagnosis" in summary

        assert summary["pillar_scores"]["memory_fidelity"] == 0.8
        assert summary["pillar_scores"]["contextual_relevance"] == 0.7
        assert summary["pillar_scores"]["behavioral_integrity"] == 0.9


class TestCheckpointEvaluationResult:
    """Test checkpoint evaluation result"""

    def test_checkpoint_result_creation(self):
        """Test creating checkpoint evaluation result"""
        metrics = WorkingMemoryMetrics(
            memory_fidelity=MemoryFidelityMetrics(0.1, 0.8, 0.9, 0.85, 0.8),
            contextual_relevance=ContextualRelevanceMetrics(
                0.8, 0.8, 0.8, 0.9, 0.85, 0.83
            ),
            behavioral_integrity=BehavioralIntegrityMetrics(
                0.1, 0.05, 0.03, 0.9, 0.95, 0.85, 0.9, 0.87
            ),
            task_completion_success=True,
        )

        result = CheckpointEvaluationResult(
            checkpoint_id="cp1",
            task_success=True,
            completion_time_ms=5000.0,
            working_memory_metrics=metrics,
            action_count=10,
            error_count=1,
        )

        assert result.checkpoint_id == "cp1"
        assert result.task_success is True
        assert result.completion_time_ms == 5000.0
        assert result.is_valid_for_analysis() is True

    def test_checkpoint_result_failed_task(self):
        """Test checkpoint result for failed task"""
        result = CheckpointEvaluationResult(
            checkpoint_id="cp1",
            task_success=False,  # Failed
            completion_time_ms=3000.0,
            working_memory_metrics=None,  # No metrics for failed task
            action_count=8,
            error_count=3,
        )

        assert result.task_success is False
        assert result.working_memory_metrics is None
        assert result.is_valid_for_analysis() is False


class TestTaskEvaluationResult:
    """Test complete task evaluation result"""

    def create_sample_checkpoint_results(self, count: int = 3) -> list:
        """Create sample checkpoint results for testing"""
        results = []

        for i in range(1, count + 1):
            metrics = WorkingMemoryMetrics(
                memory_fidelity=MemoryFidelityMetrics(0.1, 0.8, 0.9, 0.85, 0.8),
                contextual_relevance=ContextualRelevanceMetrics(
                    0.8, 0.8, 0.8, 0.9, 0.85, 0.83
                ),
                behavioral_integrity=BehavioralIntegrityMetrics(
                    0.1, 0.05, 0.03, 0.9, 0.95, 0.85, 0.9, 0.87
                ),
                task_completion_success=True,
            )

            result = CheckpointEvaluationResult(
                checkpoint_id=f"cp{i}",
                task_success=True,
                completion_time_ms=float(i * 1000),
                working_memory_metrics=metrics,
                action_count=5 + i,
                error_count=i % 2,  # Some errors
            )
            results.append(result)

        return results

    def test_task_result_creation(self):
        """Test creating task evaluation result"""
        checkpoint_results = self.create_sample_checkpoint_results(3)

        result = TaskEvaluationResult(
            task_id="test_task",
            start_timestamp=time.time(),
            end_timestamp=time.time() + 30,
            total_duration_ms=30000.0,
            completed_successfully=True,
            checkpoints_completed=3,
            total_checkpoints=3,
            checkpoint_results=checkpoint_results,
        )

        assert result.task_id == "test_task"
        assert result.completed_successfully is True
        assert result.get_completion_rate() == 1.0
        assert result.aggregated_metrics is not None

    def test_task_statistics_calculation(self):
        """Test task statistics calculation"""
        checkpoint_results = self.create_sample_checkpoint_results(3)

        result = TaskEvaluationResult(
            task_id="test_task",
            start_timestamp=time.time(),
            end_timestamp=time.time() + 30,
            total_duration_ms=30000.0,
            completed_successfully=True,
            checkpoints_completed=3,
            total_checkpoints=3,
            checkpoint_results=checkpoint_results,
        )

        # Total actions: 6 + 7 + 8 = 21
        # Total errors: 1 + 0 + 1 = 2
        assert result.total_actions == 21
        assert result.total_errors == 2
        assert result.overall_error_rate == 2 / 21

    def test_aggregated_metrics_calculation(self):
        """Test aggregated working memory metrics calculation"""
        checkpoint_results = self.create_sample_checkpoint_results(3)

        result = TaskEvaluationResult(
            task_id="test_task",
            start_timestamp=time.time(),
            end_timestamp=time.time() + 30,
            total_duration_ms=30000.0,
            completed_successfully=True,
            checkpoints_completed=3,
            total_checkpoints=3,
            checkpoint_results=checkpoint_results,
        )

        # Should have aggregated metrics
        assert result.aggregated_metrics is not None
        assert result.aggregated_metrics.memory_fidelity.overall_fidelity_score == 0.8
        assert (
            result.aggregated_metrics.contextual_relevance.overall_relevance_score
            == 0.83
        )
        assert (
            result.aggregated_metrics.behavioral_integrity.overall_integrity_score
            == 0.87
        )

    def test_task_result_partial_completion(self):
        """Test task result with partial completion"""
        checkpoint_results = self.create_sample_checkpoint_results(2)
        # Add failed checkpoint
        failed_checkpoint = CheckpointEvaluationResult(
            checkpoint_id="cp3",
            task_success=False,
            completion_time_ms=2000.0,
            action_count=5,
            error_count=3,
        )
        checkpoint_results.append(failed_checkpoint)

        result = TaskEvaluationResult(
            task_id="partial_task",
            start_timestamp=time.time(),
            end_timestamp=time.time() + 20,
            total_duration_ms=20000.0,
            completed_successfully=False,  # Not fully completed
            checkpoints_completed=2,
            total_checkpoints=3,
            checkpoint_results=checkpoint_results,
        )

        assert result.completed_successfully is False
        assert result.get_completion_rate() == 2 / 3
        assert (
            result.aggregated_metrics is None
        )  # No aggregated metrics for incomplete task

    def test_performance_summary(self):
        """Test performance summary generation"""
        checkpoint_results = self.create_sample_checkpoint_results(3)

        result = TaskEvaluationResult(
            task_id="test_task",
            start_timestamp=time.time(),
            end_timestamp=time.time() + 30,
            total_duration_ms=30000.0,
            completed_successfully=True,
            checkpoints_completed=3,
            total_checkpoints=3,
            checkpoint_results=checkpoint_results,
        )

        summary = result.get_performance_summary()

        assert summary["task_id"] == "test_task"
        assert summary["completed_successfully"] is True
        assert summary["completion_rate"] == 1.0
        assert summary["total_duration_minutes"] == 0.5  # 30 seconds
        assert "working_memory_score" in summary
        assert "working_memory_summary" in summary

    def test_task_result_serialization(self):
        """Test task result to dict conversion"""
        checkpoint_results = self.create_sample_checkpoint_results(2)

        result = TaskEvaluationResult(
            task_id="serialize_test",
            start_timestamp=time.time(),
            end_timestamp=time.time() + 15,
            total_duration_ms=15000.0,
            completed_successfully=True,
            checkpoints_completed=2,
            total_checkpoints=2,
            checkpoint_results=checkpoint_results,
        )

        result_dict = result.to_dict()

        assert result_dict["task_id"] == "serialize_test"
        assert result_dict["completed_successfully"] is True
        assert len(result_dict["checkpoint_results"]) == 2
        assert "task_statistics" in result_dict
        assert "performance_summary" in result_dict


class TestEvaluationSession:
    """Test evaluation session with multiple tasks"""

    def create_sample_task_result(
        self, task_id: str, success: bool = True
    ) -> TaskEvaluationResult:
        """Create sample task result for testing"""
        checkpoint_results = []

        for i in range(1, 4):  # 3 checkpoints
            if success or i < 3:  # Fail on last checkpoint if not successful
                metrics = WorkingMemoryMetrics(
                    memory_fidelity=MemoryFidelityMetrics(0.1, 0.8, 0.9, 0.85, 0.8),
                    contextual_relevance=ContextualRelevanceMetrics(
                        0.8, 0.8, 0.8, 0.9, 0.85, 0.83
                    ),
                    behavioral_integrity=BehavioralIntegrityMetrics(
                        0.1, 0.05, 0.03, 0.9, 0.95, 0.85, 0.9, 0.87
                    ),
                    task_completion_success=True,
                )

                result = CheckpointEvaluationResult(
                    checkpoint_id=f"cp{i}",
                    task_success=True,
                    completion_time_ms=float(i * 1000),
                    working_memory_metrics=metrics,
                    action_count=5,
                    error_count=0,
                )
            else:
                result = CheckpointEvaluationResult(
                    checkpoint_id=f"cp{i}",
                    task_success=False,
                    completion_time_ms=float(i * 500),
                    action_count=3,
                    error_count=2,
                )

            checkpoint_results.append(result)

        return TaskEvaluationResult(
            task_id=task_id,
            start_timestamp=time.time(),
            end_timestamp=time.time() + 30,
            total_duration_ms=30000.0,
            completed_successfully=success,
            checkpoints_completed=3 if success else 2,
            total_checkpoints=3,
            checkpoint_results=checkpoint_results,
        )

    def test_evaluation_session_creation(self):
        """Test creating evaluation session"""
        session = EvaluationSession(
            session_id="test_session", start_timestamp=time.time()
        )

        assert session.session_id == "test_session"
        assert session.total_tasks_attempted == 0
        assert session.total_tasks_completed == 0
        assert len(session.task_results) == 0

    def test_adding_task_results(self):
        """Test adding task results to session"""
        session = EvaluationSession(
            session_id="test_session", start_timestamp=time.time()
        )

        # Add successful task
        task1 = self.create_sample_task_result("task1", success=True)
        session.add_task_result(task1)

        # Add failed task
        task2 = self.create_sample_task_result("task2", success=False)
        session.add_task_result(task2)

        assert session.total_tasks_attempted == 2
        assert session.total_tasks_completed == 1
        assert len(session.task_results) == 2

    def test_session_completion(self):
        """Test completing evaluation session"""
        session = EvaluationSession(
            session_id="complete_test", start_timestamp=time.time()
        )

        # Add some tasks
        for i in range(3):
            task = self.create_sample_task_result(
                f"task{i+1}", success=i < 2
            )  # 2 successful, 1 failed
            session.add_task_result(task)

        session.complete_session()

        assert session.end_timestamp is not None
        assert session.session_duration_ms is not None
        assert session.session_duration_ms > 0

    def test_session_summary(self):
        """Test session summary generation"""
        session = EvaluationSession(
            session_id="summary_test", start_timestamp=time.time()
        )

        # Add multiple tasks
        for i in range(4):
            task = self.create_sample_task_result(
                f"task{i+1}", success=i < 3
            )  # 3 successful, 1 failed
            session.add_task_result(task)

        session.complete_session()
        summary = session.get_session_summary()

        assert summary["session_id"] == "summary_test"
        assert summary["total_tasks_attempted"] == 4
        assert summary["total_tasks_completed"] == 3
        assert summary["session_completion_rate"] == 0.75
        assert "average_working_memory_score" in summary
        assert "working_memory_score_std" in summary
        assert "session_duration_minutes" in summary

    def test_empty_session_summary(self):
        """Test session summary with no tasks"""
        session = EvaluationSession(
            session_id="empty_session", start_timestamp=time.time()
        )

        summary = session.get_session_summary()
        assert "message" in summary
        assert "No task results" in summary["message"]


if __name__ == "__main__":
    pytest.main([__file__])
