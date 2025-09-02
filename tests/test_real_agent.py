#!/usr/bin/env python3
"""
Test script for real agent integration
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from src.agents.real_agent import RealAgent
from src.memory.reference_implementations import SimpleContextMemory
from src.core.task_specification import CheckpointSpecification


def test_real_agent():
    """Test real agent with simple checkpoint"""
    
    # Load environment variables
    load_dotenv()
    
    # Check API key
    api_key = os.getenv('LLM_API_KEY')
    if not api_key:
        print("❌ LLM_API_KEY not found in environment")
        print("Please add your OpenRouter API key to .env file:")
        print("LLM_API_KEY=your_key_here")
        return False
    
    print("✅ API key loaded from environment")
    
    # Create memory system
    memory_system = SimpleContextMemory(config={})
    
    # Create real agent
    agent_config = {
        'model': 'moonshotai/kimi-k2',
        'temperature': 0.1,
        'max_tokens': 4000
    }
    
    agent = RealAgent(memory_system, agent_config)
    print("✅ Real agent created successfully")
    
    # Test agent capabilities
    capabilities = agent.get_capabilities()
    print(f"✅ Agent capabilities: {capabilities}")
    
    # Test with a simple checkpoint
    test_checkpoint = CheckpointSpecification(
        checkpoint_id="test_add_function",
        order=1,
        title="Test Addition Function",
        stub_file="test_calculator.py",
        stub_function="add",
        requirements="Implement an add(a, b) function that returns the sum of two numbers",
        test_file="tests/test_simple.py"
    )
    
    print("🚀 Testing real agent with checkpoint...")
    
    try:
        # Run async test
        result = asyncio.run(agent.execute_checkpoint(test_checkpoint))
        print(f"✅ Checkpoint execution result: {result}")
        
        # Get statistics
        stats = agent.get_agent_stats()
        print(f"📊 Agent stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False


if __name__ == "__main__":
    success = test_real_agent()
    if success:
        print("\n🎉 Real agent integration test completed successfully!")
    else:
        print("\n💥 Real agent integration test failed!")
