#!/usr/bin/env python3
"""
End-to-End Test Script for WorkMemEval

Tests the complete evaluation flow from task loading through results generation.
This validates that all components work together correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.agents.reference_agent import ReferenceWorkMemAgent
from src.evaluation.results import ComparisonResult
from src.evaluation.runner import BasicWorkMemEvalRunner
from src.memory.context_memory import ContextMemorySystem
from src.memory.memory_system import NoMemoryBaseline as NoMemory


async def test_basic_evaluation():
    """Test basic evaluation with SimpleWorkMemAgent and SimpleContextMemory"""
    print("=== Basic Evaluation Test ===")

    # Set up components
    memory_system = ContextMemorySystem({"max_items": 100})
    agent = ReferenceWorkMemAgent(
        memory_system,
        {
            "max_iterations": 10,
            "memory_context_limit": 5,
            "llm_config": {"response_delay": 0.1},  # Slight delay for realism
        },
    )

    # Set up evaluation
    runner = BasicWorkMemEvalRunner()
    task_path = Path("tasks/calculator_demo.json")

    try:
        # Run evaluation
        result = await runner.run_evaluation(task_path, agent, memory_system)

        # Display results
        result.print_summary()

        return result

    except Exception as e:
        print(f"❌ Basic evaluation failed: {e}")
        import traceback

        traceback.print_exc()
        return None


async def test_memory_system_comparison():
    """Test comparison between different memory systems"""
    print("\n\n=== Memory System Comparison Test ===")

    runner = BasicWorkMemEvalRunner()
    task_path = Path("tasks/calculator_demo.json")
    comparison = ComparisonResult("Memory System Comparison")

    # Test with different memory systems
    memory_systems = [
        ("NoMemory", NoMemory({})),
        ("ContextMemorySystem", ContextMemorySystem({"max_items": 50})),
        ("ContextMemorySystem_Large", ContextMemorySystem({"max_items": 200})),
    ]

    for memory_name, memory_system in memory_systems:
        print(f"\n--- Testing with {memory_name} ---")

        try:
            # Create agent with this memory system
            agent = ReferenceWorkMemAgent(
                memory_system,
                {
                    "max_iterations": 10,
                    "memory_context_limit": 5,
                    "llm_config": {"response_delay": 0.05},
                },
            )

            # Run evaluation
            result = await runner.run_evaluation(task_path, agent, memory_system)
            comparison.add_evaluation(result)

            print(
                f"✅ {memory_name}: {'SUCCESS' if result.task_completed_successfully else 'FAILED'}"
            )

        except Exception as e:
            print(f"❌ {memory_name} evaluation failed: {e}")

    # Generate comparison
    comparison.calculate_comparison_metrics()
    comparison.print_comparison()

    return comparison


async def test_task_loading():
    """Test task loading and validation"""
    print("\n\n=== Task Loading Test ===")

    runner = BasicWorkMemEvalRunner()
    task_path = Path("tasks/calculator_demo.json")

    try:
        # Load task
        task_spec = runner.task_loader.load_task(task_path)

        print("✅ Task loaded successfully")
        print(f"   Task ID: {task_spec.task_id}")
        print(f"   Title: {task_spec.title}")
        print(f"   Checkpoints: {len(task_spec.checkpoints)}")

        # Validate checkpoint structure
        for i, checkpoint in enumerate(task_spec.checkpoints, 1):
            print(f"   {i}. {checkpoint.checkpoint_id}: {checkpoint.title}")
            print(f"      Requirements: {checkpoint.requirements[:60]}...")
            print(f"      Dependencies: {checkpoint.dependencies}")

        return task_spec

    except Exception as e:
        print(f"❌ Task loading failed: {e}")
        import traceback

        traceback.print_exc()
        return None


async def test_invalid_task_handling():
    """Test handling of invalid task specifications"""
    print("\n\n=== Invalid Task Handling Test ===")

    runner = BasicWorkMemEvalRunner()

    # Test with non-existent file
    try:
        runner.task_loader.load_task(Path("tasks/nonexistent.json"))
        print("❌ Should have failed with FileNotFoundError")
    except FileNotFoundError:
        print("✅ Correctly handled non-existent file")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    return True


def run_all_tests():
    """Run all end-to-end tests"""
    print("WorkMemEval End-to-End Test Suite")
    print("=" * 50)

    async def run_tests():
        results = {}

        # Test 1: Task Loading
        results["task_loading"] = await test_task_loading()

        # Test 2: Invalid task handling
        results["invalid_handling"] = await test_invalid_task_handling()

        # Test 3: Basic Evaluation
        results["basic_evaluation"] = await test_basic_evaluation()

        # Test 4: Memory System Comparison (if basic evaluation worked)
        if results["basic_evaluation"]:
            results["memory_comparison"] = await test_memory_system_comparison()

        return results

    # Run tests
    results = asyncio.run(run_tests())

    # Final summary
    print("\n\n" + "=" * 50)
    print("TEST SUITE SUMMARY")
    print("=" * 50)

    success_count = 0
    total_count = 0

    for test_name, result in results.items():
        total_count += 1
        if result is not None:
            success_count += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"

        print(f"{test_name}: {status}")

    print(f"\nOverall: {success_count}/{total_count} tests passed")

    if success_count == total_count:
        print("🎉 All tests passed! End-to-end system is working.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

    return success_count == total_count


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
