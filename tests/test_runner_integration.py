#!/usr/bin/env python3
"""
Integration tests for runner + test execution logging.
"""

import textwrap
from pathlib import Path

import pytest

from src.agents.reference_agent import ReferenceWorkMemAgent
from src.core.action_trace import ActionType
from src.core.task_specification import CheckpointSpecification, TaskSpecification
from src.evaluation.runner import BasicWorkMemEvalRunner
from src.memory.context_memory import ContextMemorySystem


@pytest.mark.asyncio
async def test_runner_logs_test_execution(tmp_path: Path):
    # Arrange a temporary repo with a passing test file
    test_file = tmp_path / "test_ok.py"
    test_file.write_text(
        textwrap.dedent(
            """
            def test_ok():
                assert 2 * 2 == 4
            """
        )
    )

    checkpoints = [
        CheckpointSpecification(
            checkpoint_id="cp1",
            order=1,
            title="CP1",
            stub_file="dummy.py",
            stub_function="foo",
            requirements="noop",
            test_file=str(test_file.name),
            dependencies=[],
        )
    ]
    task_spec = TaskSpecification(
        task_id="tmp_task",
        title="Tmp",
        domain="test",
        description="",
        checkpoints=checkpoints,
        planning_phase=None,
        repository=None,
        memory_challenges=[],
    )

    runner = BasicWorkMemEvalRunner()
    memory = ContextMemorySystem({"max_items": 100})
    agent = ReferenceWorkMemAgent(memory, {"max_iterations": 10})

    # Patch the loader to return our synthetic task
    from unittest.mock import patch

    with patch.object(runner.task_loader, "load_task", return_value=task_spec):
        result = await runner.run_evaluation(
            tmp_path, agent, memory, working_directory=tmp_path
        )

    # Assert TEST_RUN and COMMAND_EXECUTE actions exist
    task_trace = agent.get_behavioral_trace()
    assert len(task_trace.checkpoint_traces) == 1
    cp_trace = task_trace.checkpoint_traces[0]
    actions = cp_trace.actions
    assert any(a.action_type == ActionType.COMMAND_EXECUTE for a in actions)
    assert any(a.action_type == ActionType.TEST_RUN for a in actions)
    # Ensure a ContextSnapshot was logged with delta metadata
    assert len(cp_trace.context_snapshots) >= 1
    snapshot = cp_trace.context_snapshots[-1]
    assert isinstance(snapshot.metadata.get("created"), list)
    assert isinstance(snapshot.metadata.get("modified"), list)
    assert isinstance(snapshot.metadata.get("deleted"), list)

    # Check that checkpoint result reflects pass
    assert result.checkpoint_results[0].tests_passed is True
