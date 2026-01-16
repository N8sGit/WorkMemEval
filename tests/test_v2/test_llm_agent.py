import pytest

from src.v2.llm_agent import OpenRouterAgent


@pytest.mark.asyncio
async def test_openrouter_agent_prunes_messages_keeps_system(tmp_path, monkeypatch):
    agent = OpenRouterAgent(
        api_key="test-key",
        model="test-model",
        max_context_messages=5,
    )

    async def fake_call_llm():
        return "```workpad\n## Notes\n- ok\n```"

    monkeypatch.setattr(agent, "_call_llm", fake_call_llm)

    for i in range(6):
        await agent.execute(f"Checkpoint {i}", tmp_path)

    assert agent.messages[0]["role"] == "system"
    assert len(agent.messages) <= 5


@pytest.mark.asyncio
async def test_openrouter_agent_prunes_by_char_budget(tmp_path, monkeypatch):
    agent = OpenRouterAgent(
        api_key="test-key",
        model="test-model",
        max_context_chars=300,
    )

    async def fake_call_llm():
        return "```workpad\n## Notes\n- ok\n```"

    monkeypatch.setattr(agent, "_call_llm", fake_call_llm)

    for i in range(10):
        await agent.execute("X" * 200, tmp_path)

    assert agent.messages[0]["role"] == "system"
    total_chars = sum(len(m.get("content", "")) for m in agent.messages[1:])
    assert total_chars <= 300


def test_openrouter_agent_build_prompt_includes_default_history(tmp_path):
    agent = OpenRouterAgent(
        api_key="test-key",
        model="test-model",
    )

    (tmp_path / "HISTORY.json").write_text(
        """
[
  {"role": "user", "content": "hello"},
  {"role": "assistant", "content": "world"}
]
""".strip()
    )

    prompt = agent._build_prompt("CP", tmp_path, include_history=True)
    assert "--- CONVERSATION HISTORY ---" in prompt
    assert "[user]: hello" in prompt
    assert "[assistant]: world" in prompt
    assert "--- END HISTORY ---" in prompt


def test_openrouter_agent_history_context_hook_overrides_history(tmp_path):
    (tmp_path / "HISTORY.json").write_text(
        """
[
  {"role": "user", "content": "hello"},
  {"role": "assistant", "content": "world"}
]
""".strip()
    )

    calls = {"count": 0, "last": None}

    def hook(history, include_last_n, truncate_chars_per_msg, working_dir):
        calls["count"] += 1
        calls["last"] = (len(history), include_last_n, truncate_chars_per_msg, working_dir)
        return "\n--- HOOKED HISTORY ---\nOK\n--- END HOOKED HISTORY ---\n\n"

    agent = OpenRouterAgent(
        api_key="test-key",
        model="test-model",
        history_context_hook=hook,
    )

    prompt = agent._build_prompt("CP", tmp_path, include_history=True)
    assert "--- HOOKED HISTORY ---" in prompt
    assert "--- CONVERSATION HISTORY ---" not in prompt
    assert calls["count"] == 1
    assert calls["last"][0] == 2
