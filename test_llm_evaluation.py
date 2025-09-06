#!/usr/bin/env python3
"""
Test script for LLM-enabled WorkMemEval evaluation

This script runs the simple_calculator task with the new LLM integration
and provides detailed analysis of the results.
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Dict, Any

from src.evaluation.runner import BasicWorkMemEvalRunner, TaskSpecificationLoader
from src.agents.simple_agent import SimpleWorkMemAgent
from src.memory.simple_memory import SimpleContextMemory
from src.core.action_trace import ActionTracer


async def run_llm_evaluation(use_real_llm: bool = False):
    """Run evaluation with LLM integration"""
    
    print("🧪 WorkMemEval LLM Integration Test")
    print("=" * 50)
    
    # Configuration
    task_file = Path("tasks/simple_calculator.json")
    workspace_dir = Path("evaluation_workspace/llm_test")
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure LLM
    if use_real_llm and os.getenv('OPENAI_API_KEY'):
        print("🤖 Using OpenAI GPT-4o-mini")
        llm_config = {
            'provider': 'openai',
            'model': 'gpt-4o-mini',
            'temperature': 0.1,
            'max_tokens': 4000
        }
    else:
        print("🎭 Using MockProvider (no API key required)")
        llm_config = {
            'provider': 'mock',
            'model': 'test-calculator-model',
            'response_delay': 0.1  # Small delay for realism
        }
    
    # Create memory system
    memory_config = {
        'max_items': 100,
        'max_memory_size': 50000,
        'relevance_threshold': 0.1
    }
    memory_system = SimpleContextMemory(memory_config)
    
    # Create agent with LLM integration
    agent_config = {
        'max_iterations': 10,
        'memory_context_limit': 5,
        'use_secure_file_ops': True,   # Enable real file operations
        'working_directory': str(workspace_dir),
        'llm_config': llm_config
    }
    agent = SimpleWorkMemAgent(memory_system, agent_config)
    
    print(f"💭 Agent LLM: {type(agent.llm).__name__}")
    print(f"🧠 Memory System: {type(memory_system).__name__}")
    print(f"📁 Workspace: {workspace_dir}")
    print()
    
    # Run evaluation
    print("🚀 Starting evaluation...")
    start_time = time.time()
    
    try:
        runner = BasicWorkMemEvalRunner()
        
        # Load task
        loader = TaskSpecificationLoader()
        task_spec = loader.load_task(task_file)
        
        print(f"📋 Task: {task_spec.title}")
        print(f"🎯 Checkpoints: {len(task_spec.checkpoints)}")
        for i, cp in enumerate(task_spec.checkpoints, 1):
            print(f"   {i}. {cp.title} ({cp.checkpoint_id})")
        print()
        
        # Execute the evaluation
        result = await runner.run_evaluation(
            task_path=task_file,
            agent=agent,
            memory_system=memory_system,
            working_directory=workspace_dir
        )
        
        elapsed = time.time() - start_time
        print(f"⏱️ Evaluation completed in {elapsed:.1f}s")
        print()
        
        return result, agent, elapsed
        
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return None, agent, time.time() - start_time


def analyze_results(result, agent, elapsed_time):
    """Analyze and display evaluation results"""
    
    print("📊 EVALUATION ANALYSIS")
    print("=" * 50)
    
    if result is None:
        print("❌ No results to analyze - evaluation failed")
        return
    
    # Overall results
    print(f"✅ Task Success: {result.task_completed_successfully}")
    print(f"⏱️ Total Time: {elapsed_time:.1f}s")
    print(f"📝 Task ID: {result.task_id}")
    print()
    
    # Checkpoint results
    print("📍 CHECKPOINT RESULTS:")
    print("-" * 30)
    for i, cp_result in enumerate(result.checkpoint_results, 1):
        status = "✅" if cp_result.completed_successfully else "❌"
        tests = "🧪✅" if cp_result.tests_passed else "🧪❌"
        print(f"{i}. {cp_result.checkpoint_id} {status} {tests}")
        print(f"   Time: {cp_result.execution_time_seconds:.1f}s")
        print(f"   Actions: {cp_result.actions_taken}")
        print(f"   Files: {len(cp_result.files_accessed)}")
        if cp_result.errors_encountered:
            print(f"   Errors: {len(cp_result.errors_encountered)}")
        print()
    
    # LLM Usage Analysis
    print("🤖 LLM USAGE ANALYSIS:")
    print("-" * 30)
    if hasattr(agent.llm, 'get_usage_metrics'):
        try:
            metrics = agent.llm.get_usage_metrics()
            print(f"Total Requests: {metrics.total_requests}")
            print(f"Input Tokens: {metrics.total_tokens_input}")
            print(f"Output Tokens: {metrics.total_tokens_output}")
            print(f"Total Tokens: {metrics.total_tokens_input + metrics.total_tokens_output}")
            print(f"Average Latency: {metrics.average_latency_ms:.1f}ms")
            print(f"Total Cost: ${metrics.total_cost_usd:.4f}")
            print(f"Errors: {metrics.error_count}")
        except Exception as e:
            print(f"Could not get usage metrics: {e}")
    
    provider_info = agent.llm.get_provider_info()
    print(f"Provider: {provider_info.get('provider', 'unknown')}")
    print(f"Model: {provider_info.get('model', 'unknown')}")
    if 'total_calls' in provider_info:
        print(f"Total Calls: {provider_info['total_calls']}")
    print()
    
    # Memory System Analysis
    print("🧠 MEMORY SYSTEM ANALYSIS:")
    print("-" * 30)
    memory_snapshot = agent.memory_system.get_memory_snapshot()
    print(f"Items Stored: {memory_snapshot.get('total_items', 0)}")
    print(f"Memory Size: {memory_snapshot.get('memory_size_bytes', 0)} bytes")
    if 'statistics' in memory_snapshot:
        stats = memory_snapshot['statistics']
        print(f"Store Operations: {stats.get('store_count', 0)}")
        print(f"Retrieve Operations: {stats.get('retrieve_count', 0)}")
    print()
    
    # Task Trace Analysis
    if hasattr(result, 'task_trace') and result.task_trace:
        print("📈 BEHAVIORAL TRACE ANALYSIS:")
        print("-" * 30)
        trace = result.task_trace
        duration = getattr(trace, 'total_duration_ms', None)
        if duration is not None:
            print(f"Total Duration: {duration/1000:.1f}s")
        else:
            print("Total Duration: N/A")
        
        # Count action types
        action_counts = {}
        total_actions = 0
        for cp_trace in trace.checkpoint_traces:
            for action in cp_trace.actions:
                action_type = str(action.action_type)
                action_counts[action_type] = action_counts.get(action_type, 0) + 1
                total_actions += 1
        
        print(f"Total Actions: {total_actions}")
        print("Action Breakdown:")
        for action_type, count in sorted(action_counts.items()):
            print(f"  {action_type}: {count}")
        
        print()
    
    # Working Memory Metrics (if available)
    if hasattr(result, 'working_memory_metrics') and result.working_memory_metrics:
        print("🧠 WORKING MEMORY METRICS:")
        print("-" * 30)
        wm_metrics = result.working_memory_metrics
        for key, value in wm_metrics.items():
            if isinstance(value, float):
                print(f"{key}: {value:.3f}")
            else:
                print(f"{key}: {value}")
        print()
    
    # Success/Failure Analysis
    print("🎯 SUCCESS ANALYSIS:")
    print("-" * 30)
    success_rate = sum(1 for cp in result.checkpoint_results if cp.completed_successfully) / len(result.checkpoint_results)
    test_pass_rate = sum(1 for cp in result.checkpoint_results if cp.tests_passed) / len(result.checkpoint_results)
    
    print(f"Checkpoint Success Rate: {success_rate:.1%}")
    print(f"Test Pass Rate: {test_pass_rate:.1%}")
    
    if result.task_completed_successfully:
        print("🎉 EVALUATION SUCCESSFUL!")
        print("The agent successfully completed the calculator task using LLM integration.")
    else:
        print("⚠️ EVALUATION ISSUES DETECTED")
        failed_checkpoints = [cp.checkpoint_id for cp in result.checkpoint_results if not cp.completed_successfully]
        if failed_checkpoints:
            print(f"Failed checkpoints: {', '.join(failed_checkpoints)}")
    
    print()


async def main():
    """Main execution function"""
    print("Starting WorkMemEval LLM Integration Test...")
    
    # Check for API keys
    has_openai = bool(os.getenv('OPENAI_API_KEY'))
    has_openrouter = bool(os.getenv('OPENROUTER_API_KEY'))
    
    if has_openai:
        print("🔑 OpenAI API key detected - can run with real LLM")
        use_real_llm = True
    elif has_openrouter:
        print("🔑 OpenRouter API key detected - can run with real LLM")
        use_real_llm = True
    else:
        print("🎭 No API keys detected - will use MockProvider")
        use_real_llm = False
    
    print()
    
    # Run the evaluation
    result, agent, elapsed = await run_llm_evaluation(use_real_llm)
    
    # Analyze results
    analyze_results(result, agent, elapsed)


if __name__ == "__main__":
    asyncio.run(main())
