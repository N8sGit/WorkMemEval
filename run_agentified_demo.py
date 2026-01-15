"""
WorkMemEval: Agentified Evaluation Harness

This script demonstrates the "Assessor Agent" architecture.
It bootstraps the multi-agent loop:
1. Initializes the Assessor (The Benchmark)
2. Initializes the Assessee (The Candidate) via the AssesseeAdapter
3. Orchestrates the A2A message passing loop until task completion.
"""

import asyncio
import argparse
import logging
from pathlib import Path
import shutil
import time

from src.core.a2a import MessageType, A2AMessage
from src.core.task_specification import TaskSpecification
from src.core.action_trace import ActionTracer
from src.agents.assessor import AssessorAgent
from src.agents.adapter import AssesseeAdapter
from src.agents.reference_agent import ReferenceWorkMemAgent
from src.memory.context_memory import ContextMemorySystem
from src.evaluation.runner import TaskSpecificationLoader

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(message)s')
logger = logging.getLogger("Harness")

async def run_evaluation(task_path: str, workspace: str):
    workspace_path = Path(workspace)
    if workspace_path.exists():
        shutil.rmtree(workspace_path)
    workspace_path.mkdir(parents=True)
    
    # 1. Load Task
    loader = TaskSpecificationLoader()
    task_spec = loader.load_task(Path(task_path))
    
    # 2. Initialize Agents
    tracer = ActionTracer(task_id=task_spec.task_id)
    assessor = AssessorAgent(task_spec, workspace_path)
    
    # Initialize the User's Agent (Reference Agent with Mock LLM)
    logger.info("Initializing User Agent (ReferenceWorkMemAgent)...")
    memory_system = ContextMemorySystem({"max_items": 50})
    agent_config = {
        "llm_config": {
            "provider": "mock", 
            "model": "test-model",
            "temperature": 0.0
        },
        "use_secure_file_ops": True,
        "working_directory": str(workspace_path) # Configuration only
    }
    user_agent = ReferenceWorkMemAgent(memory_system, agent_config)
    
    # Wrap it in the Adapter to speak A2A
    logger.info("Wrapping User Agent in AssesseeAdapter...")
    assessee = AssesseeAdapter(user_agent, agent_name="RefAgent")
    
    # 3. Start Session
    logger.info("--- STARTING AGENTIFIED EVALUATION ---")
    current_message = assessor.initialize_session(tracer)
    
    # 4. Message Loop
    max_turns = 20 # Increased for real agent interaction
    turn = 0
    
    while turn < max_turns:
        turn += 1
        
        # Send Assessor message to Assessee
        response = await assessee.process_message(current_message)
        
        if response:
            # Immediate response from Adapter (e.g. Probe Response or confirmation)
            current_message = assessor.process_message(response)
        else:
            # No immediate response, check outbox (Async action requests)
            # We drain the outbox one by one
            if not assessee.outbox.empty():
                msg_from_assessee = await assessee.outbox.get()
                current_message = assessor.process_message(msg_from_assessee)
            else:
                # Wait for agent to think/act
                await asyncio.sleep(0.1)
                continue
        
        if current_message.type == MessageType.TASK_COMPLETE:
            logger.info("Assessor declared task complete.")
            break
            
        await asyncio.sleep(0.01) 
        
    logger.info("--- EVALUATION COMPLETE ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default="tasks/shopmind.yaml")
    parser.add_argument("--workspace", default="workspace_test")
    args = parser.parse_args()
    
    asyncio.run(run_evaluation(args.task, args.workspace))
