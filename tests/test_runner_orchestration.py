#!/usr/bin/env python3
"""
Tests for proper async orchestration in the evaluation runner.

These tests validate that the runner properly orchestrates checkpoint execution
with correct async flow and tracing.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.agents.reference_agent import ReferenceWorkMemAgent
from src.core.action_trace import ActionType
from src.core.task_specification import CheckpointSpecification, TaskSpecification
from src.evaluation.runner import BasicWorkMemEvalRunner
from src.memory.context_memory import ContextMemorySystem


class TestRunnerOrchestration:
    """Test proper orchestration of checkpoint execution"""

    @pytest.fixture
    def mock_task_spec(self):
        """Create a mock task specification with multiple checkpoints"""
        checkpoints = [
            CheckpointSpecification(
                checkpoint_id="cp1",
                order=1,
                title="First Checkpoint",
                stub_file="test1.py",
                stub_function="func1",
                requirements="Implement func1",
                test_file="test_func1.py",
                dependencies=[],
            ),
            CheckpointSpecification(
                checkpoint_id="cp2",
                order=2,
                title="Second Checkpoint",
                stub_file="test2.py",
                stub_function="func2",
                requirements="Implement func2",
                test_file="test_func2.py",
                dependencies=["cp1"],
            ),
        ]

        return TaskSpecification(
            task_id="test_task",
            title="Test Task",
            domain="test",
            description="Test task for orchestration",
            checkpoints=checkpoints,
            planning_phase=Mock(),
            repository=Mock(),
            memory_challenges=[],
        )

    @pytest.fixture
    def runner(self):
        """Create a runner instance"""
        return BasicWorkMemEvalRunner()

    @pytest.fixture
    def agent_and_memory(self):
        """Create agent and memory system"""
        memory = ContextMemorySystem({"max_items": 50})
        agent = ReferenceWorkMemAgent(
            memory,
            {
                "max_iterations": 5,
                "memory_context_limit": 3,
                "llm_config": {"response_delay": 0.01},
            },
        )
        return agent, memory

    @pytest.mark.asyncio
    async def test_checkpoint_orchestration_flow(
        self, runner, mock_task_spec, agent_and_memory
    ):
        """Test that runner orchestrates checkpoints properly with async flow"""
        agent, memory = agent_and_memory

        # Mock the task loader to return our test task
        with patch.object(runner.task_loader, "load_task", return_value=mock_task_spec):
            # This should NOT raise RuntimeWarning about coroutines
            result = await runner.run_evaluation(
                Path("dummy_task.json"),
                agent,
                memory,
                working_directory=Path("/tmp/test_workspace"),
            )

            # The task should complete without async errors
            assert result is not None
            assert result.task_id == "test_task"

            # Should have processed both checkpoints
            task_trace = agent.get_behavioral_trace()
            assert len(task_trace.checkpoint_traces) == 2
            assert task_trace.checkpoint_traces[0].checkpoint_id == "cp1"
            assert task_trace.checkpoint_traces[1].checkpoint_id == "cp2"

    @pytest.mark.asyncio
    async def test_checkpoint_start_complete_tracing(
        self, runner, mock_task_spec, agent_and_memory
    ):
        """Test that CHECKPOINT_START and CHECKPOINT_COMPLETE actions are logged"""
        agent, memory = agent_and_memory

        with patch.object(runner.task_loader, "load_task", return_value=mock_task_spec):
            await runner.run_evaluation(
                Path("dummy_task.json"),
                agent,
                memory,
                working_directory=Path("/tmp/test_workspace"),
            )

            # Check that checkpoint start/complete actions were logged
            task_trace = agent.get_behavioral_trace()
            all_actions = []
            for cp_trace in task_trace.checkpoint_traces:
                all_actions.extend(cp_trace.actions)

            # Should have CHECKPOINT_START and CHECKPOINT_COMPLETE actions
            start_actions = [
                a for a in all_actions if a.action_type == ActionType.CHECKPOINT_START
            ]
            complete_actions = [
                a
                for a in all_actions
                if a.action_type == ActionType.CHECKPOINT_COMPLETE
            ]

            assert len(start_actions) == 2  # One for each checkpoint
            assert len(complete_actions) == 2  # One for each checkpoint

    @pytest.mark.asyncio
    async def test_no_nested_asyncio_run(
        self, runner, mock_task_spec, agent_and_memory
    ):
        """Test that no nested asyncio.run calls are made"""
        agent, memory = agent_and_memory

        # Patch asyncio.run to detect if it's called
        run_calls = []

        def mock_run(*args, **kwargs):
            run_calls.append((args, kwargs))
            # This would normally raise RuntimeError in nested context
            raise RuntimeError(
                "asyncio.run() cannot be called from a running event loop"
            )

        with patch.object(runner.task_loader, "load_task", return_value=mock_task_spec):
            with patch("asyncio.run", side_effect=mock_run):
                # This should complete without calling asyncio.run
                await runner.run_evaluation(
                    Path("dummy_task.json"),
                    agent,
                    memory,
                    working_directory=Path("/tmp/test_workspace"),
                )

                # Should not have made any asyncio.run calls
                assert len(run_calls) == 0, f"Unexpected asyncio.run calls: {run_calls}"

    @pytest.mark.asyncio
    async def test_checkpoint_execution_order(
        self, runner, mock_task_spec, agent_and_memory
    ):
        """Test that checkpoints are executed in correct order"""
        agent, memory = agent_and_memory

        checkpoint_execution_order = []

        # Mock execute_checkpoint to track execution order
        original_execute = agent.execute_checkpoint

        async def track_execution(checkpoint):
            checkpoint_execution_order.append(checkpoint.checkpoint_id)
            return await original_execute(checkpoint)

        agent.execute_checkpoint = track_execution

        with patch.object(runner.task_loader, "load_task", return_value=mock_task_spec):
            await runner.run_evaluation(
                Path("dummy_task.json"),
                agent,
                memory,
                working_directory=Path("/tmp/test_workspace"),
            )

            # Checkpoints should be executed in order
            assert checkpoint_execution_order == ["cp1", "cp2"]
