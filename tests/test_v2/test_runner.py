"""
Integration tests for V2 Runner.

Tests the full evaluation flow with mock agents.
"""

import pytest
import asyncio
from pathlib import Path
from typing import Optional

from src.v2.runner import V2Runner
from src.v2.task_loader import load_task_from_string
from src.v2.models import Task


class MockAgent:
    """
    Mock agent that writes predetermined content to WORKPAD.md.
    
    Used for testing the runner without needing a real LLM.
    """
    
    def __init__(self, responses: dict[str, str]):
        """
        Args:
            responses: Map of checkpoint_id -> workpad content to write
        """
        self.responses = responses
        self.executed_checkpoints = []
        self._current_checkpoint_id: Optional[str] = None
    
    async def execute(self, prompt: str, working_dir: Path) -> None:
        """Write predetermined response to workpad."""
        # Extract checkpoint ID from prompt (hacky but works for testing)
        for cp_id in self.responses:
            if cp_id in prompt or any(cp_id in line for line in prompt.split('\n')):
                self._current_checkpoint_id = cp_id
                break
        
        # If we couldn't determine checkpoint, use the next unexecuted one
        if self._current_checkpoint_id is None:
            for cp_id in self.responses:
                if cp_id not in self.executed_checkpoints:
                    self._current_checkpoint_id = cp_id
                    break
        
        if self._current_checkpoint_id and self._current_checkpoint_id in self.responses:
            content = self.responses[self._current_checkpoint_id]
            workpad = working_dir / "WORKPAD.md"
            
            # Append to existing content
            existing = workpad.read_text() if workpad.exists() else ""
            workpad.write_text(existing + "\n" + content)
            
            self.executed_checkpoints.append(self._current_checkpoint_id)
            self._current_checkpoint_id = None


class TestRunnerBasic:
    """Basic runner functionality tests."""
    
    @pytest.mark.asyncio
    async def test_single_checkpoint_pass(self, tmp_path):
        task = load_task_from_string("""
task_id: test
title: Test
checkpoints:
  - id: cp1
    prompt: "Record that the answer is 42"
    checks:
      - pillar: fidelity
        must_contain: ["42"]
""")
        
        agent = MockAgent({"cp1": "The answer is 42."})
        runner = V2Runner(output_dir=tmp_path / "results")
        
        result = await runner.run(task, agent, working_dir=tmp_path / "workspace")
        
        assert result.task_id == "test"
        assert result.pillar_scores["fidelity"] == 1.0
        assert len(result.checkpoint_results) == 1
    
    @pytest.mark.asyncio
    async def test_single_checkpoint_fail(self, tmp_path):
        task = load_task_from_string("""
task_id: test
title: Test
checkpoints:
  - id: cp1
    prompt: "Record that the answer is 42"
    checks:
      - pillar: fidelity
        must_contain: ["42", "answer"]
""")
        
        agent = MockAgent({"cp1": "I don't know the answer."})
        runner = V2Runner(output_dir=tmp_path / "results")
        
        result = await runner.run(task, agent, working_dir=tmp_path / "workspace")
        
        # "answer" is present but not "42"
        assert result.pillar_scores["fidelity"] == 0.5
    
    @pytest.mark.asyncio
    async def test_multiple_checkpoints(self, tmp_path):
        task = load_task_from_string("""
task_id: test
title: Test
checkpoints:
  - id: cp1
    prompt: "cp1: Record fact A"
    checks:
      - pillar: fidelity
        must_contain: ["fact A"]
  - id: cp2
    prompt: "cp2: Record fact B"
    checks:
      - pillar: fidelity
        must_contain: ["fact B"]
""")
        
        agent = MockAgent({
            "cp1": "## Checkpoint 1\nfact A is recorded",
            "cp2": "## Checkpoint 2\nfact B is recorded",
        })
        runner = V2Runner(output_dir=tmp_path / "results")
        
        result = await runner.run(task, agent, working_dir=tmp_path / "workspace")
        
        assert len(result.checkpoint_results) == 2
        assert result.pillar_scores["fidelity"] == 1.0


class TestRunnerPillars:
    """Tests for pillar-specific evaluation."""
    
    @pytest.mark.asyncio
    async def test_all_three_pillars(self, tmp_path):
        task = load_task_from_string("""
task_id: test
title: Test
checkpoints:
  - id: cp1
    prompt: "cp1: Test fidelity"
    checks:
      - pillar: fidelity
        must_contain: ["remembered"]
  - id: cp2
    prompt: "cp2: Test relevance"
    checks:
      - pillar: relevance
        must_contain_one_of: ["reject", "ignore"]
        must_not_contain: ["accept"]
  - id: cp3
    prompt: "cp3: Test integrity"
    checks:
      - pillar: integrity
        must_contain: ["updated", "new value"]
""")
        
        agent = MockAgent({
            "cp1": "I remembered the important facts",
            "cp2": "I reject this distractor suggestion",
            "cp3": "I updated to reflect new value",
        })
        runner = V2Runner(output_dir=tmp_path / "results")
        
        result = await runner.run(task, agent, working_dir=tmp_path / "workspace")
        
        assert result.pillar_scores["fidelity"] == 1.0
        assert result.pillar_scores["relevance"] == 1.0
        assert result.pillar_scores["integrity"] == 1.0
    
    @pytest.mark.asyncio
    async def test_relevance_failure(self, tmp_path):
        task = load_task_from_string("""
task_id: test
title: Test
checkpoints:
  - id: cp1
    prompt: "cp1: Evaluate suggestion"
    checks:
      - pillar: relevance
        must_contain_one_of: ["reject", "ignore"]
        must_not_contain: ["great idea", "will implement"]
""")
        
        # Agent accepts the distractor
        agent = MockAgent({
            "cp1": "Great idea! I will implement this suggestion."
        })
        runner = V2Runner(output_dir=tmp_path / "results")
        
        result = await runner.run(task, agent, working_dir=tmp_path / "workspace")
        
        # Failed both checks
        assert result.pillar_scores["relevance"] == 0.0


class TestRunnerInjectedFiles:
    """Tests for checkpoint file injection."""
    
    @pytest.mark.asyncio
    async def test_inject_files(self, tmp_path):
        task = load_task_from_string("""
task_id: test
title: Test
checkpoints:
  - id: cp1
    prompt: "cp1: Check the suggestion.md file"
    inject_files:
      suggestion.md: |
        Bad suggestion: do the wrong thing
    checks:
      - pillar: relevance
        must_contain_one_of: ["reject"]
""")
        
        agent = MockAgent({"cp1": "I reject this bad suggestion"})
        runner = V2Runner(output_dir=tmp_path / "results")
        workspace = tmp_path / "workspace"
        
        await runner.run(task, agent, working_dir=workspace)
        
        # Verify file was injected
        assert (workspace / "suggestion.md").exists()
        assert "Bad suggestion" in (workspace / "suggestion.md").read_text()


class TestRunnerResults:
    """Tests for result generation and output."""
    
    @pytest.mark.asyncio
    async def test_result_structure(self, tmp_path):
        task = load_task_from_string("""
task_id: test_result
title: Result Test
checkpoints:
  - id: cp1
    prompt: "cp1: Do something"
    checks:
      - pillar: fidelity
        must_contain: ["done"]
""")
        
        agent = MockAgent({"cp1": "Task done successfully"})
        runner = V2Runner(output_dir=tmp_path / "results")
        
        result = await runner.run(task, agent, working_dir=tmp_path / "workspace")
        
        assert result.task_id == "test_result"
        assert result.agent_name == "MockAgent"
        assert result.execution_time_seconds > 0
        assert result.timestamp > 0
        assert "done" in result.final_workpad.lower()
    
    @pytest.mark.asyncio
    async def test_result_to_dict(self, tmp_path):
        task = load_task_from_string("""
task_id: test
title: Test
checkpoints:
  - id: cp1
    prompt: "cp1: Record"
    checks:
      - pillar: fidelity
        must_contain: ["recorded"]
""")
        
        agent = MockAgent({"cp1": "Data recorded"})
        runner = V2Runner(output_dir=tmp_path / "results")
        
        result = await runner.run(task, agent, working_dir=tmp_path / "workspace")
        result_dict = result.to_dict()
        
        assert "task_id" in result_dict
        assert "pillar_scores" in result_dict
        assert "checkpoint_results" in result_dict
        assert result_dict["pillar_scores"]["fidelity"] == 1.0
    
    @pytest.mark.asyncio
    async def test_results_saved_to_file(self, tmp_path):
        task = load_task_from_string("""
task_id: save_test
title: Test
checkpoints:
  - id: cp1
    prompt: "cp1: Save"
    checks:
      - pillar: fidelity
        must_contain: ["saved"]
""")
        
        agent = MockAgent({"cp1": "Data saved"})
        results_dir = tmp_path / "results"
        runner = V2Runner(output_dir=results_dir)
        
        await runner.run(task, agent, working_dir=tmp_path / "workspace")
        
        # Check results were saved
        task_results = results_dir / "save_test"
        assert task_results.exists()
        result_files = list(task_results.glob("*.json"))
        assert len(result_files) == 1


class TestShopMindScenario:
    """
    Integration test simulating the ShopMind evaluation scenario.
    
    Tests all three pillars with realistic workpad content.
    """
    
    @pytest.mark.asyncio
    async def test_shopmind_like_task(self, tmp_path):
        task = load_task_from_string("""
task_id: shopmind_test
title: ShopMind-like Test
checkpoints:
  - id: cp1_recall
    prompt: "cp1_recall: Recall business rules"
    checks:
      - pillar: fidelity
        must_contain: ["75", "100 points"]
        
  - id: cp2_distractor
    prompt: "cp2_distractor: Evaluate colleague suggestion"
    checks:
      - pillar: relevance
        must_contain_one_of: ["reject", "contradicts", "ignore"]
        must_not_contain: ["great idea", "will implement"]
        
  - id: cp3_update
    prompt: "cp3_update: Apply policy update"
    checks:
      - pillar: integrity
        must_contain: ["45 days", "90 days"]
        must_not_contain: ["30 days"]
""")
        
        agent = MockAgent({
            "cp1_recall": """
## Business Rules Recalled
- Free shipping threshold: $75
- Loyalty conversion: 100 points = $1
- Discounts don't stack (take better deal)
""",
            "cp2_distractor": """
## Decision on Colleague Suggestion
I reject this suggestion as it contradicts our established 
architecture where discounts don't stack.
""",
            "cp3_update": """
## Policy Update Applied
New return windows:
- Standard: 45 days (was 30)
- VIP: 90 days (was 60)
- Digital: 14 days (new)
""",
        })
        
        runner = V2Runner(output_dir=tmp_path / "results")
        result = await runner.run(task, agent, working_dir=tmp_path / "workspace")
        
        # All pillars should pass
        assert result.pillar_scores["fidelity"] == 1.0
        assert result.pillar_scores["relevance"] == 1.0
        assert result.pillar_scores["integrity"] == 1.0
        
        # Check individual checkpoints
        assert result.checkpoint_results[0].pillar_scores["fidelity"] == 1.0
        assert result.checkpoint_results[1].pillar_scores["relevance"] == 1.0
        assert result.checkpoint_results[2].pillar_scores["integrity"] == 1.0
