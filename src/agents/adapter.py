"""
WorkMemEval: Assessee Adapter

This module provides the "Bridge" between the Assessor (Game Master) and 
legacy/plugin agents (Players). It allows standard Python agent implementations
to function within the event-driven A2A architecture without rewriting them.

Key Concepts:
1. Protocol Translation: Converts A2A messages -> Method calls on Agent.
2. Environment Proxy: Intercepts Agent I/O -> A2A ACTION_REQUESTs.
3. Execution Management: Runs the agent in a controlled way.
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, Optional, List, Callable
from pathlib import Path

from ..core.a2a import A2AMessage, MessageType, ActionResult
from ..core.plugin_interfaces import AgentImplementation
from ..core.task_specification import CheckpointSpecification
from .secure_file_ops import SecureFileOperations, SecurityViolationError

# Mock objects to inject into legacy agents
class NetworkedFileOps:
    """
    A proxy for SecureFileOps that sends requests to the Assessor
    instead of touching the disk directly.
    """
    def __init__(self, adapter: 'AssesseeAdapter'):
        self.adapter = adapter
        
    def read_file(self, path: str) -> str:
        """Synchronous blocking call that waits for async response via adapter"""
        return self.adapter.sync_execute_tool("read_file", {"path": str(path)})
        
    def write_file(self, path: str, content: str, append: bool = False) -> None:
        self.adapter.sync_execute_tool("write_file", {
            "path": str(path), 
            "content": content,
            "append": append
        })
        
    def list_files(self, path: str = ".") -> List[str]:
        return self.adapter.sync_execute_tool("list_files", {"path": str(path)})

    def file_exists(self, path: str) -> bool:
        return self.adapter.sync_execute_tool("file_exists", {"path": str(path)})

class AssesseeAdapter:
    """
    Wraps an AgentImplementation instance to make it speak A2A protocol.
    """
    def __init__(self, agent: AgentImplementation, agent_name: str = "Assessee"):
        self.agent = agent
        self.name = agent_name
        self.logger = logging.getLogger(f"Adapter[{agent_name}]")
        
        # Communication channels
        self.outbox: asyncio.Queue[A2AMessage] = asyncio.Queue()
        # Map request_id -> concurrent.futures.Future (thread-safe)
        self.pending_requests: Dict[str, Any] = {}
        
        # Capture the main event loop (where the adapter lives)
        self.main_loop = asyncio.get_running_loop()
        
        # Inject the NetworkedFileOps if the agent supports it
        # This is a bit of a hack for the ReferenceAgent, but necessary for the bridge
        if hasattr(self.agent, 'secure_file_ops'):
            self.logger.info("Injecting NetworkedFileOps into agent")
            self.agent.secure_file_ops = NetworkedFileOps(self)
            
        # State
        self.current_task_context = None

    async def process_message(self, message: A2AMessage) -> Optional[A2AMessage]:
        """
        Main entry point for incoming messages from Assessor.
        Returns an immediate response if applicable, or None (responses sent via outbox).
        """
        self.logger.debug(f"Received: {message.type}")
        
        if message.type == MessageType.TASK_START:
            # Prepare the agent for the task
            self.logger.info("Task Start received. Spinning up execution...")
            
            # Handle working history (pre-existing context)
            working_history = message.payload.get("working_history", [])
            if working_history and hasattr(self.agent, 'initialize_working_history'):
                self.logger.info(f"Initializing agent with {len(working_history)} history items")
                self.agent.initialize_working_history(working_history)
            
            # Check if task start includes a checkpoint (legacy/simple mode)
            if "first_checkpoint" in message.payload and message.payload["first_checkpoint"]:
                self._run_agent_execution(message.payload["first_checkpoint"])
            
            return None # Async execution started
            
        elif message.type == MessageType.CHECKPOINT_START:
            self.logger.info(f"Checkpoint Start received: {message.payload.get('checkpoint_id')}")
            self._run_agent_execution(message.payload)
            return None # Async execution started

        elif message.type == MessageType.ACTION_RESULT:
            # Complete a pending request
            req_id = message.payload.get("request_id")
            if req_id in self.pending_requests:
                future = self.pending_requests.pop(req_id)
                # Set result on the thread-safe future
                if not future.done():
                    future.set_result(message.payload)
            return None
            
        elif message.type == MessageType.PROBE_INJECTION:
            # Route probe to agent
            # If the agent has a 'handle_memory_probe' method, call it
            # NOTE: If agent is running in another thread/loop, we technically need to 
            # bridge this too. For now, assuming handle_memory_probe might be safe 
            # or we accept the race condition for the demo. 
            # Ideally, we queue this into the agent's loop.
            if hasattr(self.agent, 'handle_memory_probe'):
                # TODO: This awaits in the MAIN loop. If agent shares state, it's risky.
                # But ReferenceAgent.handle_memory_probe is usually stateless/async-safe.
                response = await self.agent.handle_memory_probe(
                    SimpleProbe(message.payload), # Wrap payload to look like Probe object
                    message.payload.get("challenge", "")
                )
                return A2AMessage(
                    type=MessageType.PROBE_RESPONSE,
                    source="assessee",
                    target="assessor",
                    payload={
                        "probe_id": message.payload.get("probe_id"),
                        "response": response
                    }
                )
            return A2AMessage(
                type=MessageType.PROBE_RESPONSE, 
                source="assessee",
                target="assessor",
                payload={"error": "Agent does not support probes"}
            )
            
        return None

    def _run_agent_execution(self, checkpoint_data: Dict[str, Any]):
        """
        Runs the agent's logic in a background THREAD with its own event loop.
        This allows blocking calls (like NetworkedFileOps) to wait for the main loop.
        """
        import threading
        
        if not checkpoint_data:
             return 

        checkpoint = SimpleCheckpoint(checkpoint_data)
        
        def agent_thread_target():
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                self.logger.info(f"Executing checkpoint in agent thread: {checkpoint.checkpoint_id}")
                # Run the async execution in this loop
                success = loop.run_until_complete(self.agent.execute_checkpoint(checkpoint))
                
                self.logger.info(f"Checkpoint execution complete. Success: {success}")
                # Signal completion to main loop
                self._send_to_main_loop(A2AMessage(
                    type=MessageType.CHECKPOINT_COMPLETE,
                    source="assessee",
                    target="assessor",
                    payload={
                        "checkpoint_id": checkpoint.checkpoint_id,
                        "status": "success" if success else "failure"
                    }
                ))
            except Exception as e:
                self.logger.error(f"Execution failed in thread: {e}", exc_info=True)
                self._send_to_main_loop(A2AMessage(
                    type=MessageType.ENVIRONMENT_UPDATE,
                    source="assessee",
                    target="assessor",
                    payload={"status": "error", "error": str(e)}
                ))
            finally:
                loop.close()

        # Start the thread
        t = threading.Thread(target=agent_thread_target, name=f"AgentThread-{self.name}-{checkpoint.checkpoint_id}")
        t.daemon = True
        self.logger.info(f"DEBUG: Starting thread {t.name}")
        t.start()

    def _send_to_main_loop(self, msg: A2AMessage):
        """Helper to safely put message in outbox from another thread"""
        self.logger.info(f"DEBUG: Enqueuing message {msg.type} from {msg.source} to {msg.target} (Payload: {str(msg.payload)[:50]}...)")
        self.main_loop.call_soon_threadsafe(self.outbox.put_nowait, msg)

    def sync_execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        Called by the synchronous NetworkedFileOps in the Agent Thread.
        Bridges to Main Thread to send message, then blocks waiting for response.
        """
        import concurrent.futures
        
        req_id = str(uuid.uuid4())
        # Use a thread-safe future
        future = concurrent.futures.Future()
        self.pending_requests[req_id] = future
        
        msg = A2AMessage(
            type=MessageType.ACTION_REQUEST,
            source="assessee",
            target="assessor",
            payload={
                "request_id": req_id,
                "tool_name": tool_name,
                "arguments": args
            }
        )
        
        # Send request to main loop
        self._send_to_main_loop(msg)
        
        # Block this thread until the main loop processes the result and sets the future
        try:
            # Wait up to 60 seconds
            result_payload = future.result(timeout=60)
            
            if result_payload.get("error"):
                raise RuntimeError(f"Tool execution failed: {result_payload.get('error')}")
                
            return result_payload.get("output")
            
        except Exception as e:
            self.logger.error(f"Tool execution error: {e}")
            # Clean up if needed
            if req_id in self.pending_requests:
                del self.pending_requests[req_id]
            raise


class SimpleProbe:
    def __init__(self, data):
        self.probe_type = data.get("probe_type", "general")
        self.probe_id = data.get("probe_id", "unknown")

class SimpleCheckpoint:
    def __init__(self, data):
        self.checkpoint_id = data.get("checkpoint_id", "cp_0")
        self.requirements = data.get("requirements", "")
        self.stub_file = data.get("stub_file")
        self.test_file = data.get("test_file")
        self.dependencies = data.get("dependencies", [])
        self.title = data.get("title", "")
        self.order = data.get("order", 0)
