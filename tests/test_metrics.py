#!/usr/bin/env python3
"""
Unit tests for metrics: memory fidelity, contextual relevance, and plan compliance.
"""

import time
from pathlib import Path

import pytest

from src.core.action_trace import ActionType, ActionTraceEntry, CheckpointTrace, TaskTrace, ContextSnapshot
from src.core.task_specification import TaskSpecification, CheckpointSpecification


def make_checkpoint_trace(checkpoint_id: str, actions: list[ActionTraceEntry]) -> CheckpointTrace:
    cp = CheckpointTrace(checkpoint_id=checkpoint_id, start_timestamp=time.time())
    for a in actions:
        cp.add_action(a)
    cp.complete_checkpoint(True)
    return cp


class _RepoMock:
    def __init__(self, provided=None, distractors=None):
        self.provided_files = provided or []
        self.distractor_files = distractors or []
    def get(self, key, default=None):
        if key == 'provided_files':
            return self.provided_files
        if key == 'distractor_files':
            return self.distractor_files
        return default

def make_task_spec(required_pairs: list[tuple[str, str]]) -> TaskSpecification:
    cps: list[CheckpointSpecification] = []
    for i, (stub, test) in enumerate(required_pairs, start=1):
        cps.append(
            CheckpointSpecification(
                checkpoint_id=f"cp{i}",
                order=i,
                title=f"CP{i}",
                stub_file=stub,
                stub_function="f",
                requirements="",
                test_file=test,
                dependencies=[],
            )
        )
    # Minimal repository mock so evaluators that rely on repository.get() work
    repo = _RepoMock(provided=[], distractors=[])
    return TaskSpecification(
        task_id="metrics_task",
        title="Metrics",
        domain="test",
        description="",
        checkpoints=cps,
        planning_phase=None,
        repository=repo,
        memory_challenges=[],
    )


@pytest.mark.parametrize("accesses, expected_rate", [
    (["a.py", "b.py", "a.py"], 1/3),   # 3 accesses, 2 unique => rereads 1/3
    (["a.py"], 0.0),
    ([], 0.0),
])
def test_memory_fidelity_reread_rate(accesses, expected_rate):
    # Build task trace
    cp = CheckpointTrace(checkpoint_id="cp1", start_timestamp=time.time())
    t0 = time.time()
    for i, f in enumerate(accesses):
        cp.add_action(ActionTraceEntry(
            timestamp=t0 + i,
            action_type=ActionType.FILE_READ,
            success=True,
            file_path=f,
        ))
    tt = TaskTrace(task_id="t", start_timestamp=time.time())
    tt.add_checkpoint_trace(cp)

    # Use three-pillar helper for reread rate
    from src.evaluation.memory_metrics import calculate_context_reread_rate
    rate = calculate_context_reread_rate(tt)
    assert pytest.approx(rate, rel=1e-6) == expected_rate


def test_contextual_relevance_precision_recall_f1():
    # Required files: a.py, b.py
    task_spec = make_task_spec([("a.py", "ta.py"), ("b.py", "tb.py")])

    # Accessed files: a.py, c.py
    base = time.time()
    actions = [
        ActionTraceEntry(timestamp=base, action_type=ActionType.FILE_READ, success=True, file_path="/abs/x/a.py"),
        ActionTraceEntry(timestamp=base+1, action_type=ActionType.FILE_WRITE, success=True, file_path="c.py"),
    ]
    cp = make_checkpoint_trace("cp1", actions)
    tt = TaskTrace(task_id="t", start_timestamp=time.time())
    tt.add_checkpoint_trace(cp)

    from src.evaluation.memory_metrics import ContextualRelevanceEvaluator
    cre = ContextualRelevanceEvaluator()
    results = cre.evaluate(tt, task_spec)
    prec = next(m for m in results if m.name == "file_access_precision")
    rec = next(m for m in results if m.name == "file_access_recall")
    f1 = next(m for m in results if m.name == "relevance_f1_score")
    assert pytest.approx(prec.value, rel=1e-6) == 0.5  # 1 / 2
    # Recall uses total relevant files (stub + test) => 1 / 4
    assert pytest.approx(rec.value, rel=1e-6) == 0.25
    # F1 = 2 * (0.5 * 0.25) / (0.5 + 0.25) = 1/3
    assert pytest.approx(f1.value, rel=1e-6) == pytest.approx(1/3, rel=1e-6)


def test_plan_compliance_full_and_ordered():
    # Plan: read a.py, implement
    plan_steps = [
        {"action": "read_file", "file_path": "a.py"},
        {"action": "implement"},
    ]
    base = time.time()
    actions = [
        ActionTraceEntry(timestamp=base, action_type=ActionType.PLANNING, success=True, metadata={"plan": plan_steps}),
        ActionTraceEntry(timestamp=base+1, action_type=ActionType.FILE_READ, success=True, file_path="/abs/a.py"),
        ActionTraceEntry(timestamp=base+2, action_type=ActionType.LLM_CALL, success=True),
    ]
    cp = make_checkpoint_trace("cp1", actions)
    tt = TaskTrace(task_id="t", start_timestamp=time.time())
    tt.add_checkpoint_trace(cp)

    from src.evaluation.memory_metrics import BehavioralIntegrityEvaluator
    bie = BehavioralIntegrityEvaluator()
    results = bie.evaluate(tt, make_task_spec([("a.py","t.py")]))
    pc = next(m for m in results if m.name == "plan_compliance")
    assert pytest.approx(pc.details["plan_coverage"], rel=1e-6) == 1.0
    assert pytest.approx(pc.details["plan_order_score"], rel=1e-6) == 1.0
    assert pytest.approx(pc.details["on_plan_action_ratio"], rel=1e-6) == 1.0
    assert pytest.approx(pc.details["time_on_plan_ratio"], rel=1e-6) == 1.0
    assert pc.details["replan_count"] == 0


def test_plan_compliance_out_of_order_and_offplan():
    # Plan: read a.py, write a.py
    plan_steps = [
        {"action": "read_file", "file_path": "a.py"},
        {"action": "edit_file", "file_path": "a.py"},
    ]
    base = time.time()
    actions = [
        ActionTraceEntry(timestamp=base, action_type=ActionType.PLANNING, success=True, metadata={"plan": plan_steps}),
        # Off-plan read of z.py consuming time
        ActionTraceEntry(timestamp=base+1, action_type=ActionType.FILE_READ, success=True, file_path="z.py"),
        # Execute write before read (out of order)
        ActionTraceEntry(timestamp=base+2, action_type=ActionType.FILE_WRITE, success=True, file_path="/work/a.py"),
        ActionTraceEntry(timestamp=base+3, action_type=ActionType.FILE_READ, success=True, file_path="a.py"),
    ]
    cp = make_checkpoint_trace("cp1", actions)
    tt = TaskTrace(task_id="t", start_timestamp=time.time())
    tt.add_checkpoint_trace(cp)

    from src.evaluation.memory_metrics import BehavioralIntegrityEvaluator
    bie = BehavioralIntegrityEvaluator()
    results = bie.evaluate(tt, make_task_spec([("a.py","t.py")]))
    pc = next(m for m in results if m.name == "plan_compliance")
    # Coverage should be 1.0 (both steps present), but order < 1.0, on-plan ratio < 1.0, time-on-plan < 1.0
    assert pytest.approx(pc.details["plan_coverage"], rel=1e-6) == 1.0
    assert pc.details["plan_order_score"] < 1.0
    assert pc.details["on_plan_action_ratio"] < 1.0
    assert pc.details["time_on_plan_ratio"] < 1.0


def test_update_robustness_binary_success_and_details():
    # Build a task with one checkpoint and a requirement update followed by a passing test
    task_spec = make_task_spec([("a.py", "tests/test_a.py")])

    base = time.time()
    actions = [
        ActionTraceEntry(timestamp=base, action_type=ActionType.FILE_READ, success=True, file_path="a.py"),
        # After update, agent writes and then runs tests successfully
        ActionTraceEntry(timestamp=base+3, action_type=ActionType.FILE_WRITE, success=True, file_path="a.py"),
        ActionTraceEntry(timestamp=base+4, action_type=ActionType.TEST_RUN, success=True),
    ]
    cp = make_checkpoint_trace("cp1", actions)
    tt = TaskTrace(task_id="t", start_timestamp=time.time())
    tt.add_checkpoint_trace(cp)

    # Inject requirement update challenge before the test run
    update_event = ActionTraceEntry(
        timestamp=base+1,
        action_type=ActionType.REQUIREMENT_UPDATE,
        success=True,
        metadata={"affected_checkpoint": "cp1", "severity": "medium"},
    )
    tt.memory_challenge_responses.append(update_event)

    from src.evaluation.memory_metrics import BehavioralIntegrityEvaluator
    bie = BehavioralIntegrityEvaluator()
    results = bie.evaluate(tt, task_spec)
    ur = next(m for m in results if m.name == "update_robustness")

    assert ur.details.get("coverage", 0) == 1
    assert ur.details.get("binary_success_rate", 0.0) == pytest.approx(1.0, rel=1e-6)
    assert ur.details.get("per_challenge")[0]["binary_success"] == 1
    # Score should be reasonably high given passing tests quickly after update
    assert ur.value >= 0.7


def test_resumption_success_rate_with_pre_snapshot_and_binary_success():
    # Build a task with one checkpoint, a context switch, and successful resume
    task_spec = make_task_spec([("a.py", "tests/test_a.py")])

    base = time.time()
    cp = CheckpointTrace(checkpoint_id="cp1", start_timestamp=base)
    # Pre-switch context snapshot
    pre_snapshot_time = base + 0.5
    cp.add_context_snapshot(
        ContextSnapshot(
            timestamp=pre_snapshot_time,
            checkpoint_id="cp1",
            files_in_context=["a.py"],
            context_token_count=100,
        )
    )
    # Actions after resume: touch same file, productive write
    cp.add_action(ActionTraceEntry(timestamp=base+3, action_type=ActionType.FILE_READ, success=True, file_path="a.py"))
    cp.add_action(ActionTraceEntry(timestamp=base+4, action_type=ActionType.FILE_WRITE, success=True, file_path="a.py"))
    cp.complete_checkpoint(True)

    tt = TaskTrace(task_id="t", start_timestamp=time.time())
    tt.add_checkpoint_trace(cp)

    # Inject context switch start and resume
    start_event = ActionTraceEntry(
        timestamp=base+1,
        action_type=ActionType.CONTEXT_SWITCH_START,
        success=True,
        metadata={"severity": "medium"},
    )
    resume_event = ActionTraceEntry(
        timestamp=base+2,
        action_type=ActionType.CONTEXT_SWITCH_RESUME,
        success=True,
        metadata={"severity": "medium"},
    )
    tt.memory_challenge_responses.extend([start_event, resume_event])

    from src.evaluation.memory_metrics import BehavioralIntegrityEvaluator
    bie = BehavioralIntegrityEvaluator()
    results = bie.evaluate(tt, task_spec)
    rsr = next(m for m in results if m.name == "resumption_success_rate")

    assert rsr.details.get("coverage", 0) == 1
    assert rsr.details.get("binary_success_rate", 0.0) == pytest.approx(1.0, rel=1e-6)
    assert rsr.details.get("per_challenge")[0]["binary_success"] == 1
    # Score should be reasonably high given quick productive action on same file
    assert rsr.value >= 0.6


def test_update_robustness_no_passing_tests_binary_zero():
    # Update event occurs, but no passing TEST_RUN afterwards; only a file write
    task_spec = make_task_spec([("a.py", "tests/test_a.py")])

    base = time.time()
    actions = [
        ActionTraceEntry(timestamp=base, action_type=ActionType.FILE_READ, success=True, file_path="a.py"),
        # After update, only write without passing tests
        ActionTraceEntry(timestamp=base+3, action_type=ActionType.FILE_WRITE, success=True, file_path="a.py"),
    ]
    cp = make_checkpoint_trace("cp1", actions)
    tt = TaskTrace(task_id="t", start_timestamp=time.time())
    tt.add_checkpoint_trace(cp)

    update_event = ActionTraceEntry(
        timestamp=base+1,
        action_type=ActionType.REQUIREMENT_UPDATE,
        success=True,
        metadata={"affected_checkpoint": "cp1", "severity": "medium"},
    )
    tt.memory_challenge_responses.append(update_event)

    from src.evaluation.memory_metrics import BehavioralIntegrityEvaluator
    bie = BehavioralIntegrityEvaluator()
    results = bie.evaluate(tt, task_spec)
    ur = next(m for m in results if m.name == "update_robustness")

    assert ur.details.get("coverage", 0) == 1
    assert ur.details.get("binary_success_rate", 1.0) == pytest.approx(0.0, rel=1e-6)
    assert ur.details.get("per_challenge")[0]["binary_success"] == 0
    # Score should be meaningfully lower than a passing-tests scenario
    assert ur.value < 0.8


def test_resumption_success_rate_resume_failure_binary_zero():
    # Context switch resume event marked unsuccessful
    task_spec = make_task_spec([("a.py", "tests/test_a.py")])

    base = time.time()
    cp = CheckpointTrace(checkpoint_id="cp1", start_timestamp=base)
    # Minimal actions after resume (not critical for binary check)
    cp.add_action(ActionTraceEntry(timestamp=base+3, action_type=ActionType.FILE_READ, success=True, file_path="a.py"))
    cp.complete_checkpoint(False)

    tt = TaskTrace(task_id="t", start_timestamp=time.time())
    tt.add_checkpoint_trace(cp)

    start_event = ActionTraceEntry(
        timestamp=base+1,
        action_type=ActionType.CONTEXT_SWITCH_START,
        success=True,
        metadata={"severity": "medium"},
    )
    resume_event = ActionTraceEntry(
        timestamp=base+2,
        action_type=ActionType.CONTEXT_SWITCH_RESUME,
        success=False,  # explicit failure
        metadata={"severity": "medium"},
    )
    tt.memory_challenge_responses.extend([start_event, resume_event])

    from src.evaluation.memory_metrics import BehavioralIntegrityEvaluator
    bie = BehavioralIntegrityEvaluator()
    results = bie.evaluate(tt, task_spec)
    rsr = next(m for m in results if m.name == "resumption_success_rate")

    assert rsr.details.get("coverage", 0) == 1
    assert rsr.details.get("binary_success_rate", 1.0) == pytest.approx(0.0, rel=1e-6)
    assert rsr.details.get("per_challenge")[0]["binary_success"] == 0
    # Score should be lower than in the successful case
    assert rsr.value < 0.7

