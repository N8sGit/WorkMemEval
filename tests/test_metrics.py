#!/usr/bin/env python3
"""
Unit tests for metrics: memory fidelity, contextual relevance, and plan compliance.
"""

import time

import pytest

from src.core.action_trace import (
    ActionTraceEntry,
    ActionType,
    CheckpointTrace,
    TaskTrace,
)
from src.core.task_specification import CheckpointSpecification, TaskSpecification


def make_checkpoint_trace(
    checkpoint_id: str, actions: list[ActionTraceEntry]
) -> CheckpointTrace:
    cp = CheckpointTrace(checkpoint_id=checkpoint_id, start_timestamp=time.time())
    for a in actions:
        cp.add_action(a)
    cp.complete_checkpoint(True)
    return cp


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
    return TaskSpecification(
        task_id="metrics_task",
        title="Metrics",
        domain="test",
        description="",
        checkpoints=cps,
        planning_phase=None,
        repository=None,
        memory_challenges=[],
    )


@pytest.mark.parametrize(
    "accesses, expected_rate",
    [
        (["a.py", "b.py", "a.py"], 1 / 3),  # 3 accesses, 2 unique => rereads 1/3
        (["a.py"], 0.0),
        ([], 0.0),
    ],
)
def test_memory_fidelity_reread_rate(accesses, expected_rate):
    # Build task trace
    cp = CheckpointTrace(checkpoint_id="cp1", start_timestamp=time.time())
    t0 = time.time()
    for i, f in enumerate(accesses):
        cp.add_action(
            ActionTraceEntry(
                timestamp=t0 + i,
                action_type=ActionType.FILE_READ,
                success=True,
                file_path=f,
            )
        )
    tt = TaskTrace(task_id="t", start_timestamp=time.time())
    tt.add_checkpoint_trace(cp)

    # Import here to avoid circular import during test discovery
    from src.evaluation import metrics

    m = metrics.compute_memory_fidelity(tt)
    assert pytest.approx(m["context_reread_rate"], rel=1e-6) == expected_rate


def test_contextual_relevance_precision_recall_f1():
    # Required files: a.py, b.py
    task_spec = make_task_spec([("a.py", "ta.py"), ("b.py", "tb.py")])

    # Accessed files: a.py, c.py
    base = time.time()
    actions = [
        ActionTraceEntry(
            timestamp=base,
            action_type=ActionType.FILE_READ,
            success=True,
            file_path="/abs/x/a.py",
        ),
        ActionTraceEntry(
            timestamp=base + 1,
            action_type=ActionType.FILE_WRITE,
            success=True,
            file_path="c.py",
        ),
    ]
    cp = make_checkpoint_trace("cp1", actions)
    tt = TaskTrace(task_id="t", start_timestamp=time.time())
    tt.add_checkpoint_trace(cp)

    from src.evaluation import metrics

    m = metrics.compute_contextual_relevance(task_spec, tt)
    assert pytest.approx(m["relevance_precision"], rel=1e-6) == 0.5  # 1 / 2
    assert pytest.approx(m["relevance_recall"], rel=1e-6) == 0.5  # 1 / 2
    assert pytest.approx(m["relevance_f1"], rel=1e-6) == 0.5


def test_plan_compliance_full_and_ordered():
    # Plan: read a.py, implement
    plan_steps = [
        {"action": "read_file", "file_path": "a.py"},
        {"action": "implement"},
    ]
    base = time.time()
    actions = [
        ActionTraceEntry(
            timestamp=base,
            action_type=ActionType.PLANNING,
            success=True,
            metadata={"plan": plan_steps},
        ),
        ActionTraceEntry(
            timestamp=base + 1,
            action_type=ActionType.FILE_READ,
            success=True,
            file_path="/abs/a.py",
        ),
        ActionTraceEntry(
            timestamp=base + 2, action_type=ActionType.LLM_CALL, success=True
        ),
    ]
    cp = make_checkpoint_trace("cp1", actions)
    tt = TaskTrace(task_id="t", start_timestamp=time.time())
    tt.add_checkpoint_trace(cp)

    from src.evaluation import metrics

    m = metrics.compute_plan_compliance(make_task_spec([("a.py", "t.py")]), tt)
    assert pytest.approx(m["plan_coverage"], rel=1e-6) == 1.0
    assert pytest.approx(m["plan_order_score"], rel=1e-6) == 1.0
    assert pytest.approx(m["on_plan_action_ratio"], rel=1e-6) == 1.0
    assert pytest.approx(m["time_on_plan_ratio"], rel=1e-6) == 1.0
    assert m["replan_count"] == 0


def test_plan_compliance_out_of_order_and_offplan():
    # Plan: read a.py, write a.py
    plan_steps = [
        {"action": "read_file", "file_path": "a.py"},
        {"action": "edit_file", "file_path": "a.py"},
    ]
    base = time.time()
    actions = [
        ActionTraceEntry(
            timestamp=base,
            action_type=ActionType.PLANNING,
            success=True,
            metadata={"plan": plan_steps},
        ),
        # Off-plan read of z.py consuming time
        ActionTraceEntry(
            timestamp=base + 1,
            action_type=ActionType.FILE_READ,
            success=True,
            file_path="z.py",
        ),
        # Execute write before read (out of order)
        ActionTraceEntry(
            timestamp=base + 2,
            action_type=ActionType.FILE_WRITE,
            success=True,
            file_path="/work/a.py",
        ),
        ActionTraceEntry(
            timestamp=base + 3,
            action_type=ActionType.FILE_READ,
            success=True,
            file_path="a.py",
        ),
    ]
    cp = make_checkpoint_trace("cp1", actions)
    tt = TaskTrace(task_id="t", start_timestamp=time.time())
    tt.add_checkpoint_trace(cp)

    from src.evaluation import metrics

    m = metrics.compute_plan_compliance(make_task_spec([("a.py", "t.py")]), tt)
    # Coverage should be 1.0 (both steps present), but order < 1.0, on_plan_ratio < 1.0, time_on_plan < 1.0
    assert pytest.approx(m["plan_coverage"], rel=1e-6) == 1.0
    assert m["plan_order_score"] < 1.0
    assert m["on_plan_action_ratio"] < 1.0
    assert m["time_on_plan_ratio"] < 1.0
