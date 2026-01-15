import pytest

from src.v2.runner import V2Runner
from src.v2.task_loader import load_task_from_string


class ContextReportingAgent:
    def __init__(self):
        self.messages = [{"role": "system", "content": "sys"}]
        self.max_context_messages = 10
        self.max_context_chars = 500

    async def execute(self, prompt, working_dir):
        self.messages.append({"role": "user", "content": prompt})
        (working_dir / "WORKPAD.md").write_text("ok")


@pytest.mark.asyncio
async def test_runner_records_context_metrics(tmp_path):
    task = load_task_from_string(
        """
 task_id: test
 title: Test
 checkpoints:
   - id: cp1
     prompt: "hello"
     checks:
       - pillar: fidelity
         must_contain: ["ok"]
 """
    )

    runner = V2Runner(output_dir=tmp_path / "results")
    agent = ContextReportingAgent()

    result = await runner.run(task, agent, working_dir=tmp_path / "ws")

    assert result.checkpoint_results[0].context_metrics["message_count"] >= 2
    assert result.checkpoint_results[0].context_metrics["max_context_messages"] == 10
    assert result.checkpoint_results[0].context_metrics["max_context_chars"] == 500
