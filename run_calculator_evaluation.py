#!/usr/bin/env python3
"""
Direct End-to-End WorkMemEval Test

Shows how to run a complete evaluation using the evaluation runner directly.
This demonstrates the typical usage pattern for evaluating agents.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import os

from src.agents.reference_agent import ReferenceWorkMemAgent
from src.evaluation.runner import BasicWorkMemEvalRunner
from src.memory.context_memory import ContextMemorySystem


async def main():
    """Run a complete evaluation using the evaluation runner"""

    print("🧪 WorkMemEval Direct End-to-End Test")
    print("=" * 50)

    # Check if we have OpenRouter API key
    has_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))

    if has_openrouter:
        print("🔑 OpenRouter API key detected - using real LLM!")
        llm_config = {
            "provider": "openrouter",
            "model": "gpt-3.5-turbo",  # Cost-effective for testing
            "temperature": 0.1,
            "max_tokens": 1000,
            "timeout_seconds": 60,
        }
        provider_name = "OpenRouter (gpt-3.5-turbo)"
    else:
        print("🎭 No OpenRouter API key - using mock test provider")
        print("💡 Set OPENROUTER_API_KEY environment variable to test with real LLM")
        llm_config = {"provider": "mock", "model": "test-calculator-model"}
        provider_name = "Mock Test Provider"

    print(f"🤖 Provider: {provider_name}")

    # Create components
    print("\n⚙️ Setting up evaluation components...")

    # Memory system
    memory = ContextMemorySystem({"max_items": 100})
    print(f"✅ Memory system: {memory.__class__.__name__}")

    # Agent configuration
    agent_config = {
        "max_iterations": 10,
        "memory_context_limit": 5,
        "llm_config": llm_config,
        "use_secure_file_ops": True,
    }

    # Create agent
    agent = ReferenceWorkMemAgent(memory, agent_config)
    print(f"✅ Agent: {agent.__class__.__name__}")
    print(f"   LLM: {agent.llm.__class__.__name__}")
    print(f"   Model: {agent.llm.config.model}")

    # Create runner
    runner = BasicWorkMemEvalRunner()
    print(f"✅ Runner: {runner.__class__.__name__}")

    # Run evaluation
    print("\n🚀 Starting evaluation...")
    print("-" * 30)

    try:
        result = await runner.run_evaluation(
            task_path=Path("tasks/calculator_demo.json"),
            agent=agent,
            memory_system=memory,
            working_directory=Path("evaluation_workspace/direct_test"),
        )

        print("\n📊 EVALUATION COMPLETE!")
        print("=" * 30)

        # Print comprehensive results
        print(f"✅ Task Success: {result.task_completed_successfully}")
        print(f"⏱️ Total Time: {result.execution_time_seconds:.1f}s")
        print(f"📝 Task ID: {result.task_id}")
        print(f"🤖 Agent: {result.agent_name}")
        print(f"🧠 Memory System: {result.memory_system_name}")

        # Checkpoint breakdown
        print("\n📍 CHECKPOINT BREAKDOWN:")
        for i, cp_result in enumerate(result.checkpoint_results, 1):
            status = "✅" if cp_result.completed_successfully else "❌"
            test_status = "🧪✅" if cp_result.tests_passed else "🧪❌"
            print(f"{i}. {cp_result.checkpoint_id}")
            print(f"   Status: {status} {test_status}")
            print(f"   Time: {cp_result.execution_time_seconds:.1f}s")
            print(f"   Actions: {cp_result.actions_taken}")
            if cp_result.files_accessed:
                print(f"   Files: {len(cp_result.files_accessed)}")
            if cp_result.errors_encountered:
                print(f"   Errors: {len(cp_result.errors_encountered)}")

        # Working memory metrics
        print("\n🧠 WORKING MEMORY METRICS:")
        if result.working_memory_metrics:
            for metric, value in result.working_memory_metrics.items():
                print(f"   {metric}: {value:.3f}")
        else:
            print("   (No metrics available)")

        # LLM usage analysis (if available)
        if hasattr(agent.llm, "get_provider_info"):
            info = agent.llm.get_provider_info()
            print("\n🤖 LLM USAGE ANALYSIS:")
            print(f"   Provider: {info.get('provider', 'unknown')}")
            print(f"   Model: {info.get('model', 'unknown')}")
            print(f"   Total Calls: {info.get('total_calls', 0)}")
            if "total_tokens" in info:
                print(f"   Total Tokens: {info['total_tokens']}")
            if "total_cost_usd" in info and info["total_cost_usd"] > 0:
                print(f"   Total Cost: ${info['total_cost_usd']:.6f}")

        # Success analysis
        success_rate = sum(
            1 for cp in result.checkpoint_results if cp.tests_passed
        ) / len(result.checkpoint_results)
        print("\n🎯 SUCCESS ANALYSIS:")
        print(f"   Checkpoint Success Rate: {success_rate * 100:.1f}%")
        print(f"   Test Pass Rate: {success_rate * 100:.1f}%")

        if result.task_completed_successfully:
            print("\n🎉 EVALUATION SUCCESSFUL!")
            if has_openrouter:
                print(
                    "   The agent successfully completed the task using real LLM capabilities!"
                )
            else:
                print(
                    "   The evaluation system is working perfectly with mock test provider!"
                )
                print("   Ready for real LLM evaluation when API keys are available.")
        else:
            print("\n⚠️ EVALUATION ISSUES DETECTED")
            failed = [
                cp.checkpoint_id
                for cp in result.checkpoint_results
                if not cp.tests_passed
            ]
            if failed:
                print(f"   Failed checkpoints: {', '.join(failed)}")

        # File analysis
        print("\n📁 FILE ANALYSIS:")
        try:
            # Check what files were created
            workspace = Path("evaluation_workspace/direct_test")
            if workspace.exists():
                py_files = list(workspace.glob("*.py"))
                test_files = list(workspace.glob("tests/*.py"))
                print(f"   Python files created: {len(py_files)}")
                print(f"   Test files available: {len(test_files)}")

                # Show the implemented calculator
                calc_file = workspace / "calculator.py"
                if calc_file.exists():
                    print("\n📄 Generated calculator.py:")
                    print("-" * 40)
                    with open(calc_file, "r") as f:
                        content = f.read()
                    # Show first 20 lines
                    lines = content.split("\n")[:20]
                    for i, line in enumerate(lines, 1):
                        print(f"{i:2}: {line}")
                    if len(content.split("\n")) > 20:
                        print("    ... (truncated)")

        except Exception as e:
            print(f"   Error analyzing files: {e}")

        return result

    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        import traceback

        traceback.print_exc()
        return None

    finally:
        # Cleanup
        if hasattr(agent.llm, "close"):
            await agent.llm.close()


if __name__ == "__main__":
    asyncio.run(main())
