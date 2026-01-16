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
