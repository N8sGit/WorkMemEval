"""
Unit tests for WorkMemEval action trace module.

Tests action trace data structures, behavioral capture, and metric calculations
following TDD principles with comprehensive coverage.
"""

import tempfile
import time
from pathlib import Path
from typing import List

import pytest

from src.core.action_trace import (
    ActionTraceEntry,
    ActionTracer,
    ActionType,
    CheckpointTrace,
    ContextSnapshot,
    TaskTrace,
)


class TestActionTraceEntry:
    """Test ActionTraceEntry data structure"""

    def test_valid_action_creation(self):
        """Test creating a valid action trace entry"""
        timestamp = time.time()
        action = ActionTraceEntry(
            timestamp=timestamp,
            action_type=ActionType.FILE_READ,
            success=True,
            file_path="src/models/user.py",
            function_name="User",
            context_size_tokens=150,
        )

        assert action.timestamp == timestamp
        assert action.action_type == ActionType.FILE_READ
        assert action.success is True
        assert action.file_path == "src/models/user.py"
        assert action.function_name == "User"
        assert action.context_size_tokens == 150
        assert action.metadata == {}

    def test_action_with_metadata(self):
        """Test action trace entry with metadata"""
        action = ActionTraceEntry(
            timestamp=time.time(),
            action_type=ActionType.LLM_CALL,
            success=True,
            duration_ms=250.5,
            metadata={"model": "gpt-4", "prompt_tokens": 100, "completion_tokens": 50},
        )

        assert action.action_type == ActionType.LLM_CALL
        assert action.duration_ms == 250.5
        assert action.metadata["model"] == "gpt-4"
        assert action.metadata["prompt_tokens"] == 100

    def test_action_validation_positive_timestamp(self):
        """Test action validation fails with non-positive timestamp"""
        with pytest.raises(ValueError, match="Timestamp must be positive"):
            ActionTraceEntry(
                timestamp=0, action_type=ActionType.FILE_READ, success=True
            )

    def test_action_validation_negative_duration(self):
        """Test action validation fails with negative duration"""
        with pytest.raises(ValueError, match="Duration cannot be negative"):
            ActionTraceEntry(
                timestamp=time.time(),
                action_type=ActionType.FILE_READ,
                success=True,
                duration_ms=-10.0,
            )


class TestContextSnapshot:
    """Test ContextSnapshot data structure"""

    def test_valid_snapshot_creation(self):
        """Test creating a valid context snapshot"""
        timestamp = time.time()
        snapshot = ContextSnapshot(
            timestamp=timestamp,
            checkpoint_id="cp1",
            files_in_context=["file1.py", "file2.py"],
            context_token_count=500,
            working_directory="/workspace",
            metadata={"note": "checkpoint start"},
        )

        assert snapshot.timestamp == timestamp
        assert snapshot.checkpoint_id == "cp1"
        assert len(snapshot.files_in_context) == 2
        assert snapshot.context_token_count == 500
        assert snapshot.working_directory == "/workspace"
        assert snapshot.metadata["note"] == "checkpoint start"

    def test_snapshot_methods(self):
        """Test context snapshot utility methods"""
        snapshot = ContextSnapshot(
            timestamp=time.time(),
            checkpoint_id="cp1",
            files_in_context=["file1.py", "file2.py", "file3.py"],
            context_token_count=750,
        )

        assert snapshot.get_context_size() == 750
        assert snapshot.get_file_count() == 3


class TestCheckpointTrace:
    """Test CheckpointTrace functionality"""

    def create_sample_actions(
        self, checkpoint_id: str = "cp1"
    ) -> List[ActionTraceEntry]:
        """Create sample actions for testing"""
        base_time = time.time()
        return [
            ActionTraceEntry(
                timestamp=base_time,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path="src/models/user.py",
                checkpoint_id=checkpoint_id,
            ),
            ActionTraceEntry(
                timestamp=base_time + 1,
                action_type=ActionType.FILE_WRITE,
                success=True,
                file_path="src/models/user.py",
                checkpoint_id=checkpoint_id,
            ),
            ActionTraceEntry(
                timestamp=base_time + 2,
                action_type=ActionType.TEST_RUN,
                success=False,  # Failed test
                file_path="tests/test_user.py",
                checkpoint_id=checkpoint_id,
            ),
            ActionTraceEntry(
                timestamp=base_time + 3,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path="src/models/user.py",  # Re-read same file
                checkpoint_id=checkpoint_id,
            ),
        ]

    def test_checkpoint_trace_creation(self):
        """Test creating checkpoint trace"""
        checkpoint_trace = CheckpointTrace(
            checkpoint_id="cp1", start_timestamp=time.time()
        )

        assert checkpoint_trace.checkpoint_id == "cp1"
        assert checkpoint_trace.end_timestamp is None
        assert checkpoint_trace.tests_passed is False
        assert len(checkpoint_trace.actions) == 0
        assert len(checkpoint_trace.context_snapshots) == 0

    def test_add_actions_to_checkpoint(self):
        """Test adding actions to checkpoint trace"""
        checkpoint_trace = CheckpointTrace(
            checkpoint_id="cp1", start_timestamp=time.time()
        )

        actions = self.create_sample_actions("cp1")

        for action in actions:
            checkpoint_trace.add_action(action)

        assert len(checkpoint_trace.actions) == 4
        assert len(checkpoint_trace.errors_encountered) == 1  # One failed test
        assert checkpoint_trace.errors_encountered[0].action_type == ActionType.TEST_RUN

    def test_add_action_checkpoint_id_mismatch(self):
        """Test that adding action with wrong checkpoint ID fails"""
        checkpoint_trace = CheckpointTrace(
            checkpoint_id="cp1", start_timestamp=time.time()
        )

        action = ActionTraceEntry(
            timestamp=time.time(),
            action_type=ActionType.FILE_READ,
            success=True,
            checkpoint_id="cp2",  # Wrong checkpoint ID
        )

        with pytest.raises(ValueError, match="doesn't match trace checkpoint_id"):
            checkpoint_trace.add_action(action)

    def test_complete_checkpoint(self):
        """Test completing checkpoint trace"""
        start_time = time.time()
        checkpoint_trace = CheckpointTrace(
            checkpoint_id="cp1", start_timestamp=start_time
        )

        # Add some actions
        for action in self.create_sample_actions("cp1"):
            checkpoint_trace.add_action(action)

        # Complete checkpoint
        checkpoint_trace.complete_checkpoint(True)

        assert checkpoint_trace.tests_passed is True
        assert checkpoint_trace.end_timestamp is not None
        assert checkpoint_trace.completion_duration_ms is not None
        assert checkpoint_trace.completion_duration_ms > 0

    def test_file_access_pattern_analysis(self):
        """Test file access pattern analysis"""
        checkpoint_trace = CheckpointTrace(
            checkpoint_id="cp1", start_timestamp=time.time()
        )

        actions = self.create_sample_actions("cp1")
        for action in actions:
            checkpoint_trace.add_action(action)

        file_pattern = checkpoint_trace.get_file_access_pattern()

        # Should have 3 accesses to user.py (read, write, read)
        # TEST_RUN actions are not tracked as file access patterns
        assert "src/models/user.py" in file_pattern
        assert len(file_pattern["src/models/user.py"]) == 3  # Read, write, read again
        assert (
            "tests/test_user.py" not in file_pattern
        )  # TEST_RUN actions don't count as file access

    def test_error_rate_calculation(self):
        """Test error rate calculation"""
        checkpoint_trace = CheckpointTrace(
            checkpoint_id="cp1", start_timestamp=time.time()
        )

        actions = self.create_sample_actions("cp1")
        for action in actions:
            checkpoint_trace.add_action(action)

        # 1 error out of 4 actions = 25%
        error_rate = checkpoint_trace.get_error_rate()
        assert error_rate == 0.25


class TestTaskTrace:
    """Test TaskTrace functionality"""

    def create_sample_checkpoint_traces(self) -> List[CheckpointTrace]:
        """Create sample checkpoint traces for testing"""
        traces = []

        for i in range(1, 4):  # cp1, cp2, cp3
            checkpoint_id = f"cp{i}"
            trace = CheckpointTrace(
                checkpoint_id=checkpoint_id, start_timestamp=time.time() + i * 10
            )

            # Add some actions
            for j in range(3):
                action = ActionTraceEntry(
                    timestamp=time.time() + i * 10 + j,
                    action_type=ActionType.FILE_READ,
                    success=j != 1,  # Make second action fail
                    file_path=f"src/{checkpoint_id}_file.py",
                    checkpoint_id=checkpoint_id,
                )
                trace.add_action(action)

            trace.complete_checkpoint(True)
            traces.append(trace)

        return traces

    def test_task_trace_creation(self):
        """Test creating task trace"""
        task_trace = TaskTrace(task_id="test_task", start_timestamp=time.time())

        assert task_trace.task_id == "test_task"
        assert task_trace.end_timestamp is None
        assert task_trace.completed_successfully is False
        assert len(task_trace.checkpoint_traces) == 0
        assert task_trace.total_actions == 0
        assert task_trace.total_errors == 0

    def test_add_checkpoint_traces(self):
        """Test adding checkpoint traces to task"""
        task_trace = TaskTrace(task_id="test_task", start_timestamp=time.time())

        checkpoint_traces = self.create_sample_checkpoint_traces()

        for trace in checkpoint_traces:
            task_trace.add_checkpoint_trace(trace)

        assert len(task_trace.checkpoint_traces) == 3
        assert task_trace.total_actions == 9  # 3 checkpoints × 3 actions each
        assert task_trace.total_errors == 3  # 1 error per checkpoint

    def test_complete_task(self):
        """Test completing task trace"""
        start_time = time.time()
        task_trace = TaskTrace(task_id="test_task", start_timestamp=start_time)

        # Add checkpoint traces
        for trace in self.create_sample_checkpoint_traces():
            task_trace.add_checkpoint_trace(trace)

        # Complete task
        task_trace.complete_task(True)

        assert task_trace.completed_successfully is True
        assert task_trace.end_timestamp is not None
        assert task_trace.total_duration_ms is not None
        assert task_trace.total_duration_ms > 0

    def test_get_checkpoint_trace(self):
        """Test retrieving specific checkpoint trace"""
        task_trace = TaskTrace(task_id="test_task", start_timestamp=time.time())

        checkpoint_traces = self.create_sample_checkpoint_traces()
        for trace in checkpoint_traces:
            task_trace.add_checkpoint_trace(trace)

        cp2_trace = task_trace.get_checkpoint_trace("cp2")
        assert cp2_trace is not None
        assert cp2_trace.checkpoint_id == "cp2"

        nonexistent_trace = task_trace.get_checkpoint_trace("cp99")
        assert nonexistent_trace is None

    def test_file_reread_statistics(self):
        """Test file reread statistics calculation"""
        task_trace = TaskTrace(task_id="test_task", start_timestamp=time.time())

        # Create checkpoint trace with file rereads
        checkpoint_trace = CheckpointTrace(
            checkpoint_id="cp1", start_timestamp=time.time()
        )

        # Add actions that reread the same file
        base_time = time.time()
        actions = [
            ActionTraceEntry(
                timestamp=base_time,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path="file1.py",
            ),
            ActionTraceEntry(
                timestamp=base_time + 1,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path="file2.py",
            ),
            ActionTraceEntry(
                timestamp=base_time + 2,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path="file1.py",  # Reread
            ),
        ]

        for action in actions:
            checkpoint_trace.add_action(action)

        task_trace.add_checkpoint_trace(checkpoint_trace)

        stats = task_trace.get_file_reread_statistics()

        assert stats["total_file_accesses"] == 3
        assert stats["unique_files_accessed"] == 2
        assert stats["unnecessary_rereads"] == 1
        assert stats["reread_rate"] == 1 / 3  # 33.33%
        assert "file1.py" in stats["files_with_multiple_accesses"]
        assert stats["files_with_multiple_accesses"]["file1.py"] == 2


class TestTaskTraceSerialization:
    """Test TaskTrace serialization and deserialization"""

    def create_comprehensive_task_trace(self) -> TaskTrace:
        """Create a comprehensive task trace for serialization testing"""
        task_trace = TaskTrace(
            task_id="comprehensive_test", start_timestamp=time.time()
        )

        # Add a checkpoint trace with various actions and snapshots
        checkpoint_trace = CheckpointTrace(
            checkpoint_id="cp1", start_timestamp=time.time()
        )

        # Add actions
        actions = [
            ActionTraceEntry(
                timestamp=time.time(),
                action_type=ActionType.FILE_READ,
                success=True,
                file_path="src/models/user.py",
                function_name="User",
                duration_ms=50.5,
                context_size_tokens=200,
                metadata={"operation": "initial_read"},
            ),
            ActionTraceEntry(
                timestamp=time.time() + 1,
                action_type=ActionType.LLM_CALL,
                success=True,
                duration_ms=1250.0,
                context_size_tokens=1500,
                metadata={
                    "model": "gpt-4",
                    "prompt_tokens": 1200,
                    "completion_tokens": 300,
                },
            ),
        ]

        for action in actions:
            checkpoint_trace.add_action(action)

        # Add context snapshots
        snapshot = ContextSnapshot(
            timestamp=time.time(),
            checkpoint_id="cp1",
            files_in_context=["src/models/user.py", "tests/test_user.py"],
            context_token_count=1000,
            working_directory="/workspace/project",
            metadata={"phase": "implementation"},
        )
        checkpoint_trace.add_context_snapshot(snapshot)

        checkpoint_trace.complete_checkpoint(True)
        task_trace.add_checkpoint_trace(checkpoint_trace)
        task_trace.complete_task(True)

        return task_trace

    def test_task_trace_to_dict(self):
        """Test converting task trace to dictionary"""
        task_trace = self.create_comprehensive_task_trace()
        trace_dict = task_trace.to_dict()

        # Check basic fields
        assert trace_dict["task_id"] == "comprehensive_test"
        assert trace_dict["completed_successfully"] is True
        assert trace_dict["total_duration_ms"] is not None

        # Check checkpoint traces
        assert len(trace_dict["checkpoint_traces"]) == 1
        cp_dict = trace_dict["checkpoint_traces"][0]
        assert cp_dict["checkpoint_id"] == "cp1"
        assert cp_dict["tests_passed"] is True

        # Check actions
        assert len(cp_dict["actions"]) == 2
        action_dict = cp_dict["actions"][0]
        assert action_dict["action_type"] == "file_read"
        assert action_dict["file_path"] == "src/models/user.py"
        assert action_dict["metadata"]["operation"] == "initial_read"

        # Check context snapshots
        assert len(cp_dict["context_snapshots"]) == 1
        snapshot_dict = cp_dict["context_snapshots"][0]
        assert len(snapshot_dict["files_in_context"]) == 2
        assert snapshot_dict["context_token_count"] == 1000

        # Check summary statistics
        stats = trace_dict["summary_statistics"]
        assert stats["total_actions"] == 2
        assert stats["unique_files_accessed"] == 1

    def test_task_trace_from_dict(self):
        """Test creating task trace from dictionary"""
        original_trace = self.create_comprehensive_task_trace()
        trace_dict = original_trace.to_dict()
        reconstructed_trace = TaskTrace.from_dict(trace_dict)

        # Check basic equality
        assert reconstructed_trace.task_id == original_trace.task_id
        assert (
            reconstructed_trace.completed_successfully
            == original_trace.completed_successfully
        )

        # Check checkpoint traces
        assert len(reconstructed_trace.checkpoint_traces) == len(
            original_trace.checkpoint_traces
        )
        orig_cp = original_trace.checkpoint_traces[0]
        recon_cp = reconstructed_trace.checkpoint_traces[0]

        assert orig_cp.checkpoint_id == recon_cp.checkpoint_id
        assert orig_cp.tests_passed == recon_cp.tests_passed
        assert len(orig_cp.actions) == len(recon_cp.actions)
        assert len(orig_cp.context_snapshots) == len(recon_cp.context_snapshots)

        # Check action details
        orig_action = orig_cp.actions[0]
        recon_action = recon_cp.actions[0]
        assert orig_action.action_type == recon_action.action_type
        assert orig_action.file_path == recon_action.file_path
        assert orig_action.metadata == recon_action.metadata

    def test_roundtrip_serialization(self):
        """Test full roundtrip serialization"""
        original_trace = self.create_comprehensive_task_trace()

        # Convert to dict and back
        trace_dict = original_trace.to_dict()
        reconstructed_trace = TaskTrace.from_dict(trace_dict)

        # Should be functionally identical
        assert original_trace.task_id == reconstructed_trace.task_id
        assert original_trace.total_actions == reconstructed_trace.total_actions
        assert (
            original_trace.completed_successfully
            == reconstructed_trace.completed_successfully
        )

        # Check statistics calculation works the same
        orig_stats = original_trace.get_file_reread_statistics()
        recon_stats = reconstructed_trace.get_file_reread_statistics()
        assert orig_stats["reread_rate"] == recon_stats["reread_rate"]


class TestActionTracer:
    """Test ActionTracer functionality"""

    def test_action_tracer_creation(self):
        """Test creating action tracer"""
        tracer = ActionTracer("test_task")

        assert tracer.task_id == "test_task"
        assert tracer.task_trace.task_id == "test_task"
        assert tracer.current_checkpoint_trace is None

    def test_checkpoint_lifecycle(self):
        """Test complete checkpoint lifecycle"""
        tracer = ActionTracer("test_task")

        # Start checkpoint
        tracer.start_checkpoint("cp1")
        assert tracer.current_checkpoint_trace is not None
        assert tracer.current_checkpoint_trace.checkpoint_id == "cp1"

        # Log some actions
        action1 = tracer.log_action(
            ActionType.FILE_READ, success=True, file_path="file1.py"
        )
        assert action1.checkpoint_id == "cp1"

        action2 = tracer.log_action(
            ActionType.TEST_RUN, success=False, file_path="test_file.py"
        )
        assert action2.success is False

        # Log context snapshot
        snapshot = tracer.log_context_snapshot(
            files_in_context=["file1.py", "file2.py"], context_token_count=500
        )
        assert snapshot.checkpoint_id == "cp1"

        # Complete checkpoint
        completed_trace = tracer.complete_checkpoint(True)
        assert completed_trace is not None
        assert completed_trace.tests_passed is True
        assert len(completed_trace.actions) == 2
        assert len(completed_trace.context_snapshots) == 1
        assert tracer.current_checkpoint_trace is None

        # Check task trace was updated
        assert len(tracer.task_trace.checkpoint_traces) == 1

    def test_multiple_checkpoints(self):
        """Test multiple checkpoint handling"""
        tracer = ActionTracer("multi_checkpoint_task")

        # First checkpoint
        tracer.start_checkpoint("cp1")
        tracer.log_action(ActionType.FILE_READ, file_path="file1.py")
        tracer.complete_checkpoint(True)

        # Second checkpoint
        tracer.start_checkpoint("cp2")
        tracer.log_action(ActionType.FILE_WRITE, file_path="file2.py")
        tracer.log_action(ActionType.TEST_RUN, success=False)
        tracer.complete_checkpoint(False)

        # Check both checkpoints are in task trace
        task_trace = tracer.get_task_trace()
        assert len(task_trace.checkpoint_traces) == 2
        assert task_trace.checkpoint_traces[0].checkpoint_id == "cp1"
        assert task_trace.checkpoint_traces[1].checkpoint_id == "cp2"
        assert task_trace.checkpoint_traces[0].tests_passed is True
        assert task_trace.checkpoint_traces[1].tests_passed is False

    def test_automatic_checkpoint_completion(self):
        """Test automatic completion when starting new checkpoint"""
        tracer = ActionTracer("auto_complete_task")

        # Start first checkpoint but don't complete it
        tracer.start_checkpoint("cp1")
        tracer.log_action(ActionType.FILE_READ, file_path="file1.py")

        # Start second checkpoint - should auto-complete first
        tracer.start_checkpoint("cp2")

        # First checkpoint should be completed with failure
        task_trace = tracer.get_task_trace()
        assert len(task_trace.checkpoint_traces) == 1
        assert task_trace.checkpoint_traces[0].checkpoint_id == "cp1"
        assert task_trace.checkpoint_traces[0].tests_passed is False

        # Current checkpoint should be cp2
        assert tracer.current_checkpoint_trace.checkpoint_id == "cp2"

    def test_complete_task(self):
        """Test completing entire task"""
        tracer = ActionTracer("complete_task_test")

        # Add some checkpoints
        tracer.start_checkpoint("cp1")
        tracer.log_action(ActionType.FILE_READ, file_path="file1.py")
        tracer.complete_checkpoint(True)

        tracer.start_checkpoint("cp2")
        tracer.log_action(ActionType.FILE_WRITE, file_path="file2.py")
        tracer.complete_checkpoint(True)

        # Complete task
        final_trace = tracer.complete_task(True)

        assert final_trace.completed_successfully is True
        assert final_trace.end_timestamp is not None
        assert final_trace.total_duration_ms is not None
        assert len(final_trace.checkpoint_traces) == 2

    def test_save_and_load_trace(self):
        """Test saving and loading trace from file"""
        tracer = ActionTracer("save_load_test")

        # Create some trace data
        tracer.start_checkpoint("cp1")
        tracer.log_action(ActionType.FILE_READ, file_path="test.py")
        tracer.log_context_snapshot(["test.py"], context_token_count=100)
        tracer.complete_checkpoint(True)
        tracer.complete_task(True)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            # Save trace
            tracer.save_trace(temp_path)

            # Load trace
            loaded_trace = ActionTracer.load_trace(temp_path)

            # Should be identical
            assert loaded_trace.task_id == tracer.task_trace.task_id
            assert (
                loaded_trace.completed_successfully
                == tracer.task_trace.completed_successfully
            )
            assert len(loaded_trace.checkpoint_traces) == len(
                tracer.task_trace.checkpoint_traces
            )

        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__])
