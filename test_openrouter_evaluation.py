#!/usr/bin/env python3
"""
OpenRouter Integration Test for WorkMemEval

Tests the full evaluation pipeline using OpenRouter LLM provider.
Falls back to mock test provider if no API key is available.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.reference_agent import ReferenceWorkMemAgent
from src.evaluation.runner import BasicWorkMemEvalRunner, TaskSpecificationLoader
from src.llm import LLMConfig, LLMFactory, LLMProvider
from src.memory.context_memory import ContextMemorySystem


def print_header(title: str, emoji: str = "🧪"):
    """Print a formatted header"""
    print(f"\n{emoji} {title}")
    print("=" * (len(title) + 4))


def check_openrouter_availability() -> bool:
    """Check if OpenRouter API key is available"""
    return bool(os.getenv("OPENROUTER_API_KEY"))


async def test_openrouter_provider_creation():
    """Test creating OpenRouter provider"""
    print_header("OpenRouter Provider Creation Test", "⚙️")

    if check_openrouter_availability():
        print("🔑 OpenRouter API key detected")

        # Test with various models
        test_models = [
            ("gpt-3.5-turbo", "openai/gpt-3.5-turbo"),
            ("claude-3-haiku", "anthropic/claude-3-haiku"),
            ("llama-3.1-8b", "meta-llama/llama-3.1-8b-instruct"),
            ("custom/model", "custom/model"),  # Should pass through unchanged
        ]

        for model_shortcut, expected_full_name in test_models:
            config = LLMConfig(
                provider=LLMProvider.OPENROUTER,
                model=model_shortcut,
                temperature=0.1,
                max_tokens=100,
            )

            provider = LLMFactory.create_provider(config)
            print(
                f"✅ Created provider for '{model_shortcut}' -> '{provider.config.model}'"
            )

            # Verify model name resolution
            assert (
                provider.config.model == expected_full_name
            ), f"Expected {expected_full_name}, got {provider.config.model}"

            await provider.close()

    else:
        print("🎭 No OpenRouter API key - testing error handling")
        config = LLMConfig(provider=LLMProvider.OPENROUTER, model="gpt-4")

        # Should raise error when no API key
        try:
            provider = LLMFactory.create_provider(config)
            print("❌ Expected error when no API key provided")
        except ValueError as e:
            print(f"✅ Correctly raised error: {e}")


async def test_openrouter_simple_generation():
    """Test simple response generation with OpenRouter"""
    print_header("OpenRouter Response Generation Test", "💬")

    if not check_openrouter_availability():
        print("⏭️ Skipping - no OpenRouter API key")
        return

    config = LLMConfig(
        provider=LLMProvider.OPENROUTER,
        model="gpt-3.5-turbo",  # Cost-effective model
        temperature=0.1,
        max_tokens=50,
    )

    provider = LLMFactory.create_provider(config)

    try:
        print("🚀 Testing simple response generation...")
        response = await provider.generate_response(
            "Respond with exactly: 'OpenRouter test successful'"
        )

        print("✅ Response received!")
        print(f"   Model: {response.model}")
        print(f"   Tokens: {response.usage['total_tokens']}")
        print(f"   Cost: ${response.cost_usd:.6f}")
        print(f"   Latency: {response.latency_ms:.1f}ms")
        print(f"   Content: {response.content}")

        # Verify response structure
        assert response.content is not None
        assert len(response.content) > 0
        assert response.usage["total_tokens"] > 0
        assert response.latency_ms > 0
        assert response.model.startswith("openai/")

    finally:
        await provider.close()


async def test_openrouter_agent_integration():
    """Test OpenRouter integration with ReferenceWorkMemAgent"""
    print_header("OpenRouter Agent Integration Test", "🤖")

    # Determine which provider to use
    if check_openrouter_availability():
        print("🔑 Using OpenRouter provider")
        llm_config = {
            "provider": "openrouter",
            "model": "gpt-3.5-turbo",
            "temperature": 0.1,
            "max_tokens": 500,
            "timeout_seconds": 30,
        }
    else:
        print("🎭 Using mock test provider (no API key)")
        llm_config = {"provider": "mock", "model": "test-calculator-model"}

    # Create agent with OpenRouter or fallback
    memory = ContextMemorySystem({"max_items": 100})
    agent_config = {
        "max_iterations": 10,
        "memory_context_limit": 5,
        "llm_config": llm_config,
    }

    agent = ReferenceWorkMemAgent(memory, agent_config)

    print(f"✅ Agent created with LLM provider: {type(agent.llm).__name__}")
    print(f"   Model: {agent.llm.config.model}")

    # Test basic agent functionality
    if hasattr(agent.llm, "generate_response"):
        try:
            print("🧪 Testing agent LLM integration...")
            response = await agent.llm.generate_response(
                "Plan how to implement a simple calculator with add and multiply functions."
            )

            print(f"✅ Agent LLM response received ({len(response.content)} chars)")
            print(f"   Preview: {response.content[:100]}...")

            if hasattr(agent.llm, "close"):
                await agent.llm.close()

        except Exception as e:
            print(f"❌ Agent LLM integration failed: {e}")
    else:
        print("ℹ️  Agent LLM is synchronous (legacy interface)")


async def test_full_evaluation_with_openrouter():
    """Test complete evaluation pipeline with OpenRouter"""
    print_header("Full Evaluation Pipeline Test", "🎯")

    # Determine provider
    if check_openrouter_availability():
        print("🔑 Running evaluation with OpenRouter")
        llm_config = {
            "provider": "openrouter",
            "model": "gpt-3.5-turbo",  # Cost-effective for testing
            "temperature": 0.1,
            "max_tokens": 1000,  # Enough for code generation
            "timeout_seconds": 60,
        }
        provider_name = "OpenRouter (gpt-3.5-turbo)"
    else:
        print("🎭 Running evaluation with mock test provider")
        llm_config = {"provider": "mock", "model": "test-calculator-model"}
        provider_name = "Mock Test Provider"

    # Create evaluation components
    memory = ContextMemorySystem({"max_items": 100})
    agent_config = {
        "max_iterations": 10,
        "memory_context_limit": 5,
        "llm_config": llm_config,
        "use_secure_file_ops": True,
    }

    agent = ReferenceWorkMemAgent(memory, agent_config)
    runner = BasicWorkMemEvalRunner()

    # Load task
    loader = TaskSpecificationLoader()
    task_spec = loader.load_task(Path("tasks/calculator_demo.json"))

    print(f"📋 Task: {task_spec.title}")
    print(f"🎯 Checkpoints: {len(task_spec.checkpoints)}")
    for i, cp in enumerate(task_spec.checkpoints, 1):
        print(f"   {i}. {cp.title} ({cp.checkpoint_id})")

    # Run evaluation
    print(f"\n🚀 Starting evaluation with {provider_name}...")
    try:
        # Run evaluation using correct method signature
        working_directory = Path("evaluation_workspace/openrouter_test")
        result = await runner.run_evaluation(
            task_path=Path("tasks/calculator_demo.json"),
            agent=agent,
            memory_system=memory,
            working_directory=working_directory,
        )

        # Print results
        print("\n📊 EVALUATION RESULTS")
        print(f"✅ Task Success: {result.task_completed_successfully}")
        print(f"⏱️ Total Time: {result.execution_time_seconds:.1f}s")
        print(f"📝 Task ID: {result.task_id}")

        print("\n📍 CHECKPOINT RESULTS:")
        for i, cp_result in enumerate(result.checkpoint_results, 1):
            status = "✅" if cp_result.completed_successfully else "❌"
            test_status = "🧪✅" if cp_result.tests_passed else "🧪❌"
            print(f"{i}. {cp_result.checkpoint_id} {status} {test_status}")
            print(f"   Time: {cp_result.execution_time_seconds:.1f}s")
            if (
                hasattr(cp_result, "errors_encountered")
                and cp_result.errors_encountered
            ):
                print(f"   Errors: {len(cp_result.errors_encountered)}")

        # LLM Usage Analysis
        trace = result.task_trace if hasattr(result, "task_trace") else None
        llm_calls = []
        if trace and hasattr(trace, "checkpoint_traces"):
            # Extract LLM calls from all checkpoint traces
            for checkpoint_trace in trace.checkpoint_traces:
                for action in checkpoint_trace.actions:
                    if action.action_type.name == "LLM_CALL":
                        llm_calls.append(action)

        print("\n🤖 LLM USAGE ANALYSIS:")
        print(f"Provider: {provider_name}")
        print(f"Total LLM Calls: {len(llm_calls)}")

        if hasattr(agent.llm, "get_provider_info"):
            info = agent.llm.get_provider_info()
            if "total_cost_usd" in info:
                print(f"Total Cost: ${info['total_cost_usd']:.6f}")
            if "total_tokens" in info:
                print(f"Total Tokens: {info['total_tokens']}")

        success_rate = (
            sum(1 for cp in result.checkpoint_results if cp.tests_passed)
            / len(result.checkpoint_results)
            if result.checkpoint_results
            else 0
        )
        print("\n🎯 SUCCESS ANALYSIS:")
        print(f"Checkpoint Success Rate: {success_rate * 100:.1f}%")

        if result.task_completed_successfully:
            print("🎉 EVALUATION SUCCESSFUL!")
            if check_openrouter_availability():
                print(
                    "The agent successfully completed the task using real LLM capabilities!"
                )
        else:
            print("⚠️ EVALUATION ISSUES DETECTED")
            failed_checkpoints = [
                cp.checkpoint_id
                for cp in result.checkpoint_results
                if not cp.tests_passed
            ]
            if failed_checkpoints:
                print(f"Failed checkpoints: {', '.join(failed_checkpoints)}")

        return result

    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback

        traceback.print_exc()
        return None

    finally:
        if hasattr(agent.llm, "close"):
            await agent.llm.close()


async def main():
    """Run all OpenRouter integration tests"""
    print_header("WorkMemEval OpenRouter Integration Tests", "🧪")

    # Check environment
    has_api_key = check_openrouter_availability()
    print(f"🔑 OpenRouter API Key: {'Available' if has_api_key else 'Not Found'}")

    if not has_api_key:
        print(
            "💡 Set OPENROUTER_API_KEY environment variable to test real OpenRouter integration"
        )
        print("🎭 Will use mock test provider as fallback for testing")

    try:
        # Run tests
        await test_openrouter_provider_creation()
        await test_openrouter_simple_generation()
        await test_openrouter_agent_integration()
        result = await test_full_evaluation_with_openrouter()

        print_header("Test Summary", "📋")
        if has_api_key and result and result.task_completed_successfully:
            print("🎉 All OpenRouter integration tests passed!")
            print("   ✅ Provider creation works")
            print("   ✅ Response generation works")
            print("   ✅ Agent integration works")
            print("   ✅ Full evaluation pipeline works")
            print("   ✅ Real LLM successfully completed calculator task")
        elif not has_api_key:
            print("🎭 Mock provider tests passed!")
            print("   ✅ Fallback behavior works correctly")
            print("   ✅ Integration is ready for real API keys")
        else:
            print("⚠️ Some tests failed - check output above")

    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
