"""
Tests for Update Robustness (UR) and Resumption Success Rate (RSR)
"""

import time
from unittest.mock import Mock

from src.evaluation.memory_metrics import WorkingMemoryEvaluationEngine
from src.core.action_trace import (
    TaskTrace, CheckpointTrace, ActionTraceEntry, ActionType, ContextSnapshot
)
from src.core.task_specification import (
    TaskSpecification, CheckpointSpecification
)


def _make_task_spec_with_checkpoint(cp_id: str, title: str = "CP") -> TaskSpecification:
    cp = CheckpointSpecification(
        checkpoint_id=cp_id,
        order=1,
        title=title,
        stub_file="main.py",
        stub_function="main",
        requirements="Implement main",
        test_file="test_main.py",
        dependencies=[],
    )
    repo = Mock(**{
        'provided_files': ['main.py'],
        'distractor_files': [],
        'get.return_value': []
    })
    return TaskSpecification(
        task_id=f"task_{cp_id}",
        title="UR/RSR Test Task",
        domain="testing",
        description="Synthetic task for UR/RSR metrics",
        checkpoints=[cp],
        planning_phase=Mock(),
        repository=repo,
        memory_challenges=[],
    )


def test_update_robustness_basic():
    base = time.time() - 1000
    task_trace = TaskTrace(task_id="ur_task", start_timestamp=base)

    # Build checkpoint trace with actions before and after requirement update
    cp = CheckpointTrace(checkpoint_id="cp1", start_timestamp=base)

    # Pre-update actions
    cp.add_action(ActionTraceEntry(
        timestamp=base + 1,
        action_type=ActionType.FILE_READ,
        success=True,
        file_path="main.py",
        metadata={"size_bytes": 120}
    ))
    cp.add_action(ActionTraceEntry(
        timestamp=base + 2,
        action_type=ActionType.FILE_WRITE,
        success=True,
        file_path="main.py",
        metadata={"size_bytes": 240}
    ))

    # Inject requirement update event (memory challenge)
    update_event = ActionTraceEntry(
        timestamp=base + 2.5,
        action_type=ActionType.REQUIREMENT_UPDATE,
        success=True,
        metadata={
            "affected_checkpoint": "cp1",
            "severity": "medium",
            "original_requirements": "old",
            "updated_requirements": "new"
        }
    )
    task_trace.memory_challenge_responses.append(update_event)

    # Post-update: passing tests (compliance signal)
    cp.add_action(ActionTraceEntry(
        timestamp=base + 3,
        action_type=ActionType.TEST_RUN,
        success=True,
        metadata={"test_file": "test_main.py", "exit_code": 0}
    ))

    cp.complete_checkpoint(tests_passed=True)
    task_trace.add_checkpoint_trace(cp)
    task_trace.complete_task(completed_successfully=True)

    # Task spec
    task_spec = _make_task_spec_with_checkpoint("cp1")

    # Evaluate
    engine = WorkingMemoryEvaluationEngine()
    evaluation = engine.evaluate_working_memory(task_trace, task_spec, agent_name="synthetic")
    bi = evaluation.behavioral_integrity

    # Find UR metric
    ur_metric = next((m for m in bi.metrics if m.name == "update_robustness"), None)
    assert ur_metric is not None, "update_robustness metric missing"

    assert 0.0 <= ur_metric.value <= 1.0
    # With immediate test pass after update, should generally be decent
    assert ur_metric.value >= 0.6
    assert isinstance(ur_metric.details, dict)
    assert 'coverage' in ur_metric.details
    assert ur_metric.details['coverage'] >= 1
    assert 'per_challenge' in ur_metric.details
    assert isinstance(ur_metric.details['per_challenge'], list)
    if ur_metric.details['per_challenge']:
        comp = ur_metric.details['per_challenge'][0]['components']
        for key in ['compliance', 'latency', 'stability']:
            assert key in comp


def test_resumption_success_rate_basic():
    base = time.time() - 1000
    task_trace = TaskTrace(task_id="rsr_task", start_timestamp=base)

    cp = CheckpointTrace(checkpoint_id="cp1", start_timestamp=base)

    # Pre-switch context snapshot (so recall/fidelity can be computed)
    pre_snapshot = ContextSnapshot(
        timestamp=base + 1,
        checkpoint_id="cp1",
        files_in_context=["main.py", "utils.py"],
        context_token_count=0,
        working_directory="/tmp",
        metadata={}
    )
    cp.add_context_snapshot(pre_snapshot)

    # Some prior action
    cp.add_action(ActionTraceEntry(
        timestamp=base + 1.2,
        action_type=ActionType.FILE_READ,
        success=True,
        file_path="main.py",
        metadata={"size_bytes": 120}
    ))

    # Context switch start event
    start_event = ActionTraceEntry(
        timestamp=base + 1.5,
        action_type=ActionType.CONTEXT_SWITCH_START,
        success=True,
        metadata={"interruption_task": "doc", "duration_minutes": 5}
    )
    task_trace.memory_challenge_responses.append(start_event)

    # Resume event
    resume_event = ActionTraceEntry(
        timestamp=base + 2.0,
        action_type=ActionType.CONTEXT_SWITCH_RESUME,
        success=True,
        metadata={"resumed_successfully": True}
    )
    task_trace.memory_challenge_responses.append(resume_event)

    # Post-resume actions: first productive action, then a few touches to pre fileset
    cp.add_action(ActionTraceEntry(
        timestamp=base + 2.1,
        action_type=ActionType.FILE_WRITE,
        success=True,
        file_path="main.py",
        metadata={"size_bytes": 200}
    ))
    cp.add_action(ActionTraceEntry(
        timestamp=base + 2.15,
        action_type=ActionType.FILE_READ,
        success=True,
        file_path="utils.py",
        metadata={"size_bytes": 80}
    ))

    cp.complete_checkpoint(tests_passed=True)
    task_trace.add_checkpoint_trace(cp)
    task_trace.complete_task(completed_successfully=True)

    task_spec = _make_task_spec_with_checkpoint("cp1")

    engine = WorkingMemoryEvaluationEngine()
    evaluation = engine.evaluate_working_memory(task_trace, task_spec, agent_name="synthetic")
    bi = evaluation.behavioral_integrity

    rsr_metric = next((m for m in bi.metrics if m.name == "resumption_success_rate"), None)
    assert rsr_metric is not None, "resumption_success_rate metric missing"

    assert 0.0 <= rsr_metric.value <= 1.0
    assert 'coverage' in rsr_metric.details
    assert rsr_metric.details['coverage'] >= 1

    # Check component presence
    per = rsr_metric.details['per_challenge'][0]
    comps = per['components']
    for key in ['latency', 'overhead']:
        assert key in comps

    # Since we returned to touching pre-switch files quickly, expect decent score
    assert rsr_metric.value >= 0.5

