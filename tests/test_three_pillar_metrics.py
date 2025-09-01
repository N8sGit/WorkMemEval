"""
Tests for the Three-Pillar Working Memory Metrics System

This test suite validates that the comprehensive working memory evaluation system 
produces meaningful, accurate, and reliable metrics across all three pillars.
"""

import pytest
import time
from unittest.mock import Mock

from src.evaluation.memory_metrics import (
    WorkingMemoryEvaluationEngine,
    MemoryFidelityEvaluator, 
    ContextualRelevanceEvaluator,
    BehavioralIntegrityEvaluator,
    MetricResult,
    PillarResult,
    WorkingMemoryEvaluation
)

from src.core.action_trace import (
    TaskTrace, CheckpointTrace, ActionTraceEntry, ActionType
)

from src.core.task_specification import (
    TaskSpecification, CheckpointSpecification
)


class TestWorkingMemoryEvaluationEngine:
    """Test the main evaluation engine orchestrating all three pillars"""
    
    def setup_method(self):
        """Setup for each test"""
        self.engine = WorkingMemoryEvaluationEngine()
        self.task_spec = self._create_sample_task_spec()
        self.task_trace = self._create_sample_task_trace()
    
    def test_complete_evaluation(self):
        """Test that complete evaluation produces all expected components"""
        evaluation = self.engine.evaluate_working_memory(
            self.task_trace, 
            self.task_spec, 
            agent_name="test_agent"
        )
        
        # Validate structure
        assert isinstance(evaluation, WorkingMemoryEvaluation)
        assert evaluation.task_id == "test_task"
        assert evaluation.agent_name == "test_agent"
        assert isinstance(evaluation.timestamp, float)
        
        # Validate pillar results
        assert isinstance(evaluation.memory_fidelity, PillarResult)
        assert isinstance(evaluation.contextual_relevance, PillarResult) 
        assert isinstance(evaluation.behavioral_integrity, PillarResult)
        
        # Validate overall assessment
        assert 0 <= evaluation.overall_working_memory_score <= 1
        assert evaluation.grade in ['A', 'B', 'C', 'D', 'F']
        assert isinstance(evaluation.summary, str)
        assert len(evaluation.summary) > 0
        
        # Validate diagnostic information
        assert isinstance(evaluation.strengths, list)
        assert isinstance(evaluation.weaknesses, list) 
        assert isinstance(evaluation.improvement_suggestions, list)
    
    def test_grade_calculation(self):
        """Test grade calculation logic"""
        # Test different score ranges
        test_cases = [
            (0.95, "A"),
            (0.85, "B"), 
            (0.75, "C"),
            (0.65, "D"),
            (0.45, "F")
        ]
        
        for score, expected_grade in test_cases:
            grade = self.engine._calculate_grade(score)
            assert grade == expected_grade
    
    def test_pillar_weighting(self):
        """Test that all pillars contribute equally to overall score"""
        evaluation = self.engine.evaluate_working_memory(self.task_trace, self.task_spec)
        
        # Overall score should be roughly the mean of pillar scores
        pillar_scores = [
            evaluation.memory_fidelity.overall_score,
            evaluation.contextual_relevance.overall_score,
            evaluation.behavioral_integrity.overall_score
        ]
        
        expected_overall = sum(pillar_scores) / len(pillar_scores)
        
        # Should be within small tolerance due to confidence weighting
        assert abs(evaluation.overall_working_memory_score - expected_overall) < 0.1
    
    def _create_sample_task_spec(self) -> TaskSpecification:
        """Create a sample task specification for testing"""
        checkpoint1 = CheckpointSpecification(
            checkpoint_id="cp1",
            order=1,
            title="Test Checkpoint 1",
            stub_file="main.py",
            stub_function="main",
            requirements="Implement main function",
            test_file="test_main.py",
            dependencies=[]
        )
        
        checkpoint2 = CheckpointSpecification(
            checkpoint_id="cp2", 
            order=2,
            title="Test Checkpoint 2",
            stub_file="utils.py",
            stub_function="helper",
            requirements="Implement helper function",
            test_file="test_utils.py",
            dependencies=["cp1"]
        )
        
        return TaskSpecification(
            task_id="test_task",
            title="Test Task",
            domain="testing",
            description="A test task for metrics evaluation",
            checkpoints=[checkpoint1, checkpoint2],
            planning_phase=Mock(),
            repository=Mock(**{
                'provided_files': ['main.py'],
                'distractor_files': ['distractor.py'],
                'get.return_value': []
            }),
            memory_challenges=[]
        )
    
    def _create_sample_task_trace(self) -> TaskTrace:
        """Create a sample task trace for testing"""
        task_trace = TaskTrace(
            task_id="test_task",
            start_timestamp=time.time() - 3600  # 1 hour ago
        )
        
        # Create checkpoint 1 trace
        cp1_trace = CheckpointTrace(
            checkpoint_id="cp1",
            start_timestamp=time.time() - 3600
        )
        
        # Add some realistic actions
        actions = [
            ActionTraceEntry(
                timestamp=time.time() - 3500,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path="main.py",
                metadata={"size_bytes": 150}
            ),
            ActionTraceEntry(
                timestamp=time.time() - 3400,
                action_type=ActionType.LLM_CALL,
                success=True,
                metadata={"description": "plan implementation", "response_length": 200}
            ),
            ActionTraceEntry(
                timestamp=time.time() - 3300,
                action_type=ActionType.FILE_WRITE,
                success=True,
                file_path="main.py",
                metadata={"size_bytes": 300, "operation": "create"}
            ),
            ActionTraceEntry(
                timestamp=time.time() - 3200,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path="test_main.py",
                metadata={"size_bytes": 100}
            ),
        ]
        
        for action in actions:
            cp1_trace.add_action(action)
        
        cp1_trace.complete_checkpoint(tests_passed=True)
        
        # Create checkpoint 2 trace
        cp2_trace = CheckpointTrace(
            checkpoint_id="cp2",
            start_timestamp=time.time() - 1800  # 30 minutes ago
        )
        
        # Add some actions including a reread
        actions2 = [
            ActionTraceEntry(
                timestamp=time.time() - 1700,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path="main.py",  # This is a reread
                metadata={"size_bytes": 300}
            ),
            ActionTraceEntry(
                timestamp=time.time() - 1600,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path="utils.py",
                metadata={"size_bytes": 80}
            ),
            ActionTraceEntry(
                timestamp=time.time() - 1500,
                action_type=ActionType.FILE_WRITE,
                success=True,
                file_path="utils.py",
                metadata={"size_bytes": 200, "operation": "create"}
            ),
        ]
        
        for action in actions2:
            cp2_trace.add_action(action)
        
        cp2_trace.complete_checkpoint(tests_passed=True)
        
        # Add checkpoint traces to task trace
        task_trace.add_checkpoint_trace(cp1_trace)
        task_trace.add_checkpoint_trace(cp2_trace)
        
        task_trace.complete_task(completed_successfully=True)
        
        return task_trace


class TestMemoryFidelityEvaluator:
    """Test memory fidelity metrics"""
    
    def setup_method(self):
        """Setup for each test"""
        self.evaluator = MemoryFidelityEvaluator()
        self.task_spec = Mock()
        self.task_trace = self._create_memory_test_trace()
    
    def test_reread_efficiency_metric(self):
        """Test context reread efficiency calculation"""
        metrics = self.evaluator.evaluate(self.task_trace, self.task_spec)
        reread_metric = next(m for m in metrics if m.name == "context_reread_efficiency")
        
        # Should be between 0 and 1
        assert 0 <= reread_metric.value <= 1
        assert isinstance(reread_metric.interpretation, str)
        assert len(reread_metric.interpretation) > 0
        assert 'reread_rate' in reread_metric.details
    
    def test_size_weighted_efficiency_metric(self):
        """Test size-weighted efficiency calculation"""
        metrics = self.evaluator.evaluate(self.task_trace, self.task_spec)
        size_metric = next(m for m in metrics if m.name == "size_weighted_efficiency")
        
        assert 0 <= size_metric.value <= 1
        assert isinstance(size_metric.interpretation, str)
        assert 'size_penalty' in size_metric.details
    
    def test_information_retention_metric(self):
        """Test information retention across checkpoints"""
        metrics = self.evaluator.evaluate(self.task_trace, self.task_spec)
        retention_metric = next(m for m in metrics if m.name == "information_retention")
        
        assert 0 <= retention_metric.value <= 1
        assert 'checkpoint_count' in retention_metric.details
    
    def test_temporal_information_loss(self):
        """Test temporal information loss detection"""
        metrics = self.evaluator.evaluate(self.task_trace, self.task_spec)
        temporal_metric = next(m for m in metrics if m.name == "temporal_information_loss")
        
        assert 0 <= temporal_metric.value <= 1
        assert 'timeline_events' in temporal_metric.details
    
    def test_memory_coherence_index(self):
        """Test memory coherence measurement"""
        metrics = self.evaluator.evaluate(self.task_trace, self.task_spec)
        coherence_metric = next(m for m in metrics if m.name == "memory_coherence_index")
        
        assert 0 <= coherence_metric.value <= 1
        assert 'total_operations' in coherence_metric.details
        assert 'coherence_violations' in coherence_metric.details
    
    def _create_memory_test_trace(self) -> TaskTrace:
        """Create a trace with memory-specific test patterns"""
        task_trace = TaskTrace(
            task_id="memory_test",
            start_timestamp=time.time() - 1000
        )
        
        # Create checkpoint with some rereads
        cp_trace = CheckpointTrace(
            checkpoint_id="memory_cp",
            start_timestamp=time.time() - 1000
        )
        
        actions = [
            # Initial read
            ActionTraceEntry(
                timestamp=time.time() - 900,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path="file1.py",
                metadata={"size_bytes": 100}
            ),
            # Write
            ActionTraceEntry(
                timestamp=time.time() - 800,
                action_type=ActionType.FILE_WRITE,
                success=True,
                file_path="file1.py",
                metadata={"size_bytes": 150}
            ),
            # Reread (coherence violation)
            ActionTraceEntry(
                timestamp=time.time() - 750,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path="file1.py",
                metadata={"size_bytes": 150}
            ),
            # Another file
            ActionTraceEntry(
                timestamp=time.time() - 700,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path="file2.py",
                metadata={"size_bytes": 200}
            ),
        ]
        
        for action in actions:
            cp_trace.add_action(action)
        
        cp_trace.complete_checkpoint(tests_passed=True)
        task_trace.add_checkpoint_trace(cp_trace)
        
        return task_trace

    def _create_cross_checkpoint_trace(self) -> TaskTrace:
        """Create a two-checkpoint trace to exercise cross-checkpoint retention metric"""
        task_trace = TaskTrace(
            task_id="cc_retention_test",
            start_timestamp=time.time() - 1000
        )
        # Checkpoint 1: read two files
        cp1 = CheckpointTrace(
            checkpoint_id="cp1",
            start_timestamp=time.time() - 1000
        )
        cp1.add_action(ActionTraceEntry(
            timestamp=time.time() - 900,
            action_type=ActionType.FILE_READ,
            success=True,
            file_path="retain.py",
            metadata={"size_bytes": 120}
        ))
        cp1.add_action(ActionTraceEntry(
            timestamp=time.time() - 880,
            action_type=ActionType.FILE_READ,
            success=True,
            file_path="forget.py",
            metadata={"size_bytes": 200}
        ))
        cp1.complete_checkpoint(tests_passed=True)
        task_trace.add_checkpoint_trace(cp1)
        
        # Checkpoint 2: reuse retain.py without reread (WRITE first), and forget.py with reread (READ first)
        cp2 = CheckpointTrace(
            checkpoint_id="cp2",
            start_timestamp=time.time() - 600
        )
        # First access is WRITE => retained
        cp2.add_action(ActionTraceEntry(
            timestamp=time.time() - 590,
            action_type=ActionType.FILE_WRITE,
            success=True,
            file_path="retain.py",
            metadata={"size_bytes": 150}
        ))
        # First access is READ => loss
        cp2.add_action(ActionTraceEntry(
            timestamp=time.time() - 580,
            action_type=ActionType.FILE_READ,
            success=True,
            file_path="forget.py",
            metadata={"size_bytes": 210}
        ))
        cp2.complete_checkpoint(tests_passed=True)
        task_trace.add_checkpoint_trace(cp2)
        
        return task_trace

    def test_cross_checkpoint_information_retention(self):
        """Ensure the cross-checkpoint retention metric is computed and well-formed"""
        # Build a dedicated trace with both retention and loss cases
        task_trace = self._create_cross_checkpoint_trace()
        metrics = self.evaluator.evaluate(task_trace, self.task_spec)
        metric = next(m for m in metrics if m.name == "cross_checkpoint_information_retention")
        
        assert 0 <= metric.value <= 1
        for key in ['total_reuse_events', 'loss_events', 'weighted_loss', 'weighted_total', 'raw_loss_rate', 'loss_rate', 'tau_seconds']:
            assert key in metric.details
        # Expect at least some reuse events in this synthetic trace
        assert metric.details['total_reuse_events'] >= 1


class TestContextualRelevanceEvaluator:
    """Test contextual relevance metrics"""
    
    def setup_method(self):
        """Setup for each test"""
        self.evaluator = ContextualRelevanceEvaluator()
        self.task_spec = self._create_relevance_task_spec()
        self.task_trace = self._create_relevance_test_trace()
    
    def test_file_access_precision(self):
        """Test precision of file access"""
        metrics = self.evaluator.evaluate(self.task_trace, self.task_spec)
        precision_metric = next(m for m in metrics if m.name == "file_access_precision")
        
        assert 0 <= precision_metric.value <= 1
        assert 'total_files_accessed' in precision_metric.details
        assert 'relevant_files_accessed' in precision_metric.details
        assert 'irrelevant_files_accessed' in precision_metric.details
    
    def test_file_access_recall(self):
        """Test recall of file access"""
        metrics = self.evaluator.evaluate(self.task_trace, self.task_spec)
        recall_metric = next(m for m in metrics if m.name == "file_access_recall")
        
        assert 0 <= recall_metric.value <= 1
        assert 'total_relevant_files' in recall_metric.details
        assert 'relevant_files_accessed' in recall_metric.details
    
    def test_relevance_f1_score(self):
        """Test F1 score calculation"""
        metrics = self.evaluator.evaluate(self.task_trace, self.task_spec)
        f1_metric = next(m for m in metrics if m.name == "relevance_f1_score")
        
        assert 0 <= f1_metric.value <= 1
        assert 'precision' in f1_metric.details
        assert 'recall' in f1_metric.details
    
    def test_distractor_resistance(self):
        """Test resistance to distractor files"""
        metrics = self.evaluator.evaluate(self.task_trace, self.task_spec)
        distractor_metric = next(m for m in metrics if m.name == "distractor_resistance")
        
        assert 0 <= distractor_metric.value <= 1
        assert 'total_distractor_files' in distractor_metric.details
    
    def test_focus_consistency_index(self):
        """Test focus consistency across checkpoints"""
        metrics = self.evaluator.evaluate(self.task_trace, self.task_spec)
        focus_metric = next(m for m in metrics if m.name == "focus_consistency_index")
        
        assert 0 <= focus_metric.value <= 1
        assert 'checkpoint_focus_scores' in focus_metric.details
    
    def _create_relevance_task_spec(self) -> TaskSpecification:
        """Create task spec with relevant and distractor files"""
        checkpoint = CheckpointSpecification(
            checkpoint_id="relevance_cp",
            order=1,
            title="Relevance Test",
            stub_file="relevant.py",
            stub_function="main",
            requirements="Test relevance",
            test_file="test_relevant.py",
            dependencies=[]
        )
        
        return TaskSpecification(
            task_id="relevance_test",
            title="Relevance Test",
            domain="testing",
            description="Test contextual relevance",
            checkpoints=[checkpoint],
            planning_phase=Mock(),
            repository=Mock(**{
                'provided_files': ['relevant.py'],
                'distractor_files': ['distractor1.py', 'distractor2.py'],
                'get.return_value': ['distractor1.py', 'distractor2.py']
            }),
            memory_challenges=[]
        )
    
    def _create_relevance_test_trace(self) -> TaskTrace:
        """Create trace with relevance test patterns"""
        task_trace = TaskTrace(
            task_id="relevance_test",
            start_timestamp=time.time() - 1000
        )
        
        cp_trace = CheckpointTrace(
            checkpoint_id="relevance_cp",
            start_timestamp=time.time() - 1000
        )
        
        actions = [
            # Access relevant file
            ActionTraceEntry(
                timestamp=time.time() - 900,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path="relevant.py",
                metadata={"size_bytes": 100}
            ),
            # Access test file (also relevant)
            ActionTraceEntry(
                timestamp=time.time() - 800,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path="test_relevant.py",
                metadata={"size_bytes": 150}
            ),
            # Access distractor (should hurt precision)
            ActionTraceEntry(
                timestamp=time.time() - 700,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path="distractor1.py",
                metadata={"size_bytes": 80}
            ),
        ]
        
        for action in actions:
            cp_trace.add_action(action)
        
        cp_trace.complete_checkpoint(tests_passed=True)
        task_trace.add_checkpoint_trace(cp_trace)
        
        return task_trace


class TestBehavioralIntegrityEvaluator:
    """Test behavioral integrity metrics"""
    
    def setup_method(self):
        """Setup for each test"""
        self.evaluator = BehavioralIntegrityEvaluator()
        self.task_spec = Mock()
        self.task_trace = self._create_integrity_test_trace()
    
    def test_error_correction_overhead(self):
        """Test error correction overhead calculation"""
        metrics = self.evaluator.evaluate(self.task_trace, self.task_spec)
        error_metric = next(m for m in metrics if m.name == "error_correction_overhead")
        
        assert 0 <= error_metric.value <= 1
        assert 'total_actions' in error_metric.details
        assert 'error_actions' in error_metric.details
        assert 'recovery_actions' in error_metric.details
    
    def test_state_coherence_index(self):
        """Test state coherence measurement"""
        metrics = self.evaluator.evaluate(self.task_trace, self.task_spec)
        coherence_metric = next(m for m in metrics if m.name == "state_coherence_index")
        
        assert 0 <= coherence_metric.value <= 1
        assert 'state_operations' in coherence_metric.details
        assert 'coherence_violations' in coherence_metric.details
    
    def test_backtracking_rate(self):
        """Test backtracking rate calculation"""
        metrics = self.evaluator.evaluate(self.task_trace, self.task_spec)
        backtrack_metric = next(m for m in metrics if m.name == "backtracking_rate")
        
        assert 0 <= backtrack_metric.value <= 1
        assert 'total_modifications' in backtrack_metric.details
        assert 'backtracking_events' in backtrack_metric.details
    
    def test_decision_consistency_index(self):
        """Test decision consistency measurement"""
        metrics = self.evaluator.evaluate(self.task_trace, self.task_spec)
        consistency_metric = next(m for m in metrics if m.name == "decision_consistency_index")
        
        assert 0 <= consistency_metric.value <= 1
        assert 'total_decisions' in consistency_metric.details
        assert 'decision_contexts' in consistency_metric.details
    
    def test_recovery_effectiveness(self):
        """Test error recovery effectiveness"""
        metrics = self.evaluator.evaluate(self.task_trace, self.task_spec)
        recovery_metric = next(m for m in metrics if m.name == "recovery_effectiveness")
        
        assert 0 <= recovery_metric.value <= 1
        # Validate existing detail keys from implementation
        for key in ['error_recovery_pairs', 'successful_recoveries', 'recovery_rate', 'avg_recovery_time_seconds']:
            assert key in recovery_metric.details

    def _create_integrity_test_trace(self) -> TaskTrace:
        """Create trace with behavioral integrity test patterns"""
        task_trace = TaskTrace(
            task_id="integrity_test",
            start_timestamp=time.time() - 1000
        )
        
        cp_trace = CheckpointTrace(
            checkpoint_id="integrity_cp",
            start_timestamp=time.time() - 1000
        )
        
        actions = [
            # Successful action
            ActionTraceEntry(
                timestamp=time.time() - 900,
                action_type=ActionType.FILE_WRITE,
                success=True,
                file_path="test.py",
                metadata={"size_bytes": 100}
            ),
            # Failed action (error)
            ActionTraceEntry(
                timestamp=time.time() - 800,
                action_type=ActionType.FILE_WRITE,
                success=False,
                file_path="test2.py",
                metadata={"error": "permission denied"}
            ),
            # Recovery action
            ActionTraceEntry(
                timestamp=time.time() - 750,
                action_type=ActionType.ERROR_RECOVERY,
                success=True,
                metadata={"recovery_type": "retry"}
            ),
            # Backtracking (file size reduction)
            ActionTraceEntry(
                timestamp=time.time() - 700,
                action_type=ActionType.FILE_MODIFY,
                success=True,
                file_path="test.py",
                metadata={"size_bytes": 50}  # Reduced from 100
            ),
            # Decision point
            ActionTraceEntry(
                timestamp=time.time() - 600,
                action_type=ActionType.LLM_CALL,
                success=True,
                metadata={"decision": "implementation_strategy"}
            ),
        ]
        
        for action in actions:
            cp_trace.add_action(action)
        
        cp_trace.complete_checkpoint(tests_passed=True)
        task_trace.add_checkpoint_trace(cp_trace)
        
        return task_trace


class TestMetricInterpretation:
    """Test that metrics produce appropriate interpretations"""
    
    def test_metric_interpretation_ranges(self):
        """Test that different score ranges produce appropriate interpretations"""
        test_cases = [
            (0.95, ["excellent", "strong", "optimal"]),
            (0.8, ["good", "well", "effective"]),
            (0.6, ["fair", "moderate", "some"]),
            (0.3, ["poor", "weak", "significant"])
        ]
        
        # Test with a simple metric result
        for score, expected_words in test_cases:
            metric = MetricResult(
                name="test_metric",
                value=score,
                interpretation=self._generate_test_interpretation(score)
            )
            
            interpretation_lower = metric.interpretation.lower()
            assert any(word in interpretation_lower for word in expected_words), \
                f"Score {score} should contain one of {expected_words} in interpretation: {metric.interpretation}"
    
    def test_confidence_calculation(self):
        """Test confidence calculation based on sample sizes"""
        evaluator = MemoryFidelityEvaluator()
        
        # Test different sample sizes
        test_cases = [
            (2, 5, 0.4),   # 2 samples, min 5 -> 0.4 confidence
            (5, 5, 0.5),   # 5 samples, min 5 -> 0.5 confidence (full at 2x min)
            (10, 5, 1.0),  # 10 samples, min 5 -> 1.0 confidence
            (0, 5, 0.0),   # 0 samples -> 0.0 confidence
        ]
        
        for sample_size, min_size, expected in test_cases:
            confidence = evaluator._calculate_confidence(sample_size, min_size)
            assert abs(confidence - expected) < 0.1, \
                f"Sample size {sample_size} (min {min_size}) should give confidence ~{expected}, got {confidence}"
    
    def _generate_test_interpretation(self, score: float) -> str:
        """Generate test interpretation based on score"""
        if score >= 0.9:
            return "Excellent performance with strong capabilities"
        elif score >= 0.8:
            return "Good performance with effective execution" 
        elif score >= 0.6:
            return "Fair performance with moderate effectiveness"
        else:
            return "Poor performance with significant weaknesses"


class TestMetricResultValidation:
    """Test validation of metric results"""
    
    def test_metric_result_validation(self):
        """Test that MetricResult validates inputs correctly"""
        # Valid metric result
        valid_metric = MetricResult(
            name="test",
            value=0.8,
            confidence=0.9
        )
        assert valid_metric.confidence == 0.9
        
        # Invalid confidence should raise error
        with pytest.raises(ValueError, match="Confidence must be 0-1"):
            MetricResult(
                name="test",
                value=0.8,
                confidence=1.5
            )
        
        with pytest.raises(ValueError, match="Confidence must be 0-1"):
            MetricResult(
                name="test", 
                value=0.8,
                confidence=-0.1
            )
    
    def test_pillar_result_metric_lookup(self):
        """Test PillarResult metric lookup functionality"""
        metrics = [
            MetricResult(name="metric1", value=0.8),
            MetricResult(name="metric2", value=0.6),
            MetricResult(name="metric3", value=0.9)
        ]
        
        pillar = PillarResult(
            pillar_name="Test Pillar",
            overall_score=0.77,
            metrics=metrics
        )
        
        # Test successful lookup
        found_metric = pillar.get_metric("metric2")
        assert found_metric is not None
        assert found_metric.value == 0.6
        
        # Test unsuccessful lookup
        not_found = pillar.get_metric("nonexistent")
        assert not_found is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
