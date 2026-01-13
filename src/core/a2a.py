"""
WorkMemEval: Agent-to-Agent (A2A) Protocol Definitions

This module defines the standard message types and protocols for interaction
between the Assessor Agent (Benchmark) and the Assessee Agent (System Under Test).

Based on the AgentBeats A2A specification.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import time
import uuid

class MessageType(Enum):
    # Task Control
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    CHECKPOINT_START = "checkpoint_start"
    CHECKPOINT_COMPLETE = "checkpoint_complete"
    
    # Environment Interaction
    ACTION_REQUEST = "action_request"  # Assessee -> Assessor (Do this)
    ACTION_RESULT = "action_result"    # Assessor -> Assessee (Here is the result)
    
    # Assessment / Probing
    PROBE_INJECTION = "probe_injection" # Assessor -> Assessee (Unexpected event/query)
    PROBE_RESPONSE = "probe_response"   # Assessee -> Assessor (Handling)
    
    # State Updates
    ENVIRONMENT_UPDATE = "environment_update"

@dataclass
class A2AMessage:
    """Standard envelope for Agent-to-Agent communication"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.TASK_START
    source: str = "assessor"
    target: str = "assessee"
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "source": self.source,
            "target": self.target,
            "timestamp": self.timestamp,
            "payload": self.payload
        }

@dataclass
class ActionRequest:
    """Assessee asking to perform an action in the environment"""
    tool_name: str
    arguments: Dict[str, Any]
    request_id: str

@dataclass
class ActionResult:
    """Result of an action performed in the environment"""
    request_id: str
    success: bool
    output: Any
    error: Optional[str] = None
    state_changes: Dict[str, Any] = field(default_factory=dict)
