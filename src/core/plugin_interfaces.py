"""
WorkMemEval: Plugin Interfaces

Defines the core plugin contracts for agents and memory systems.
These interfaces are minimal, stable, and capability-driven to support
a wide range of implementations without assumptions.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
import time

# Import the new memory system architecture
from ..memory.memory_system import MemorySystem, PluginCapabilities, MemorySystemInterface


# Re-export PluginCapabilities from memory_system for backward compatibility
# This will be deprecated in future versions


# MemorySystem is now imported from memory_system module
# This reference is kept for backward compatibility
# In future versions, this will be completely moved to the memory module


class AgentImplementation(ABC):
    """
    Pluggable agent implementation interface.
    
    This interface makes NO assumptions about agent architecture:
    - Could be simple LLM + tools
    - Could be sophisticated planning agents
    - Could be external process wrappers (like Aider)
    - Could be multi-agent systems
    
    The only requirement is behavioral trace output for evaluation.
    """
    
    def __init__(self, memory_system: MemorySystem, config: Dict[str, Any]):
        self.memory_system = memory_system
        self.config = config
        self.capabilities = self.get_capabilities()
        self._agent_id = f"{self.__class__.__name__}_{int(time.time())}"
    
    @abstractmethod
    def get_capabilities(self) -> PluginCapabilities:
        """Return what optional capabilities this agent supports"""
        pass
    
    @abstractmethod
    async def execute_checkpoint(self, checkpoint: 'CheckpointSpecification') -> bool:
        """
        Execute a checkpoint and return success status.
        
        Args:
            checkpoint: The checkpoint specification to execute
            
        Returns:
            True if checkpoint completed successfully, False otherwise
            
        The agent should:
        1. Use the memory_system to retrieve relevant information
        2. Execute the checkpoint requirements
        3. Store new information in memory_system  
        4. Generate behavioral trace data for evaluation
        """
        pass
        
    @abstractmethod
    def get_behavioral_trace(self) -> 'TaskTrace':
        """
        Get complete behavioral trace for evaluation.
        
        Returns:
            TaskTrace containing all agent behavior for working memory analysis
        """
        pass
        
    def get_agent_id(self) -> str:
        """Get unique identifier for this agent instance"""
        return self._agent_id
        
    def reset_agent_state(self) -> bool:
        """Reset agent to initial state (optional, for testing)"""
        return True
        
    def get_agent_stats(self) -> Dict[str, Any]:
        """Get agent performance statistics (optional capability)"""
        return {}


class PluginInfo:
    """Metadata about a loaded plugin"""
    
    def __init__(self, plugin_class: type, module_path: str, class_name: str):
        self.plugin_class = plugin_class
        self.module_path = module_path
        self.class_name = class_name
        self.capabilities = None  # Set when instantiated
        
    def __repr__(self):
        return f"PluginInfo({self.module_path}:{self.class_name})"


class PluginValidationError(Exception):
    """Raised when plugin fails validation"""
    pass


def validate_plugin_interface(plugin_instance, expected_interface: type) -> bool:
    """
    Validate that a plugin instance implements the expected interface.
    
    Args:
        plugin_instance: The plugin instance to validate
        expected_interface: The interface class it should implement
        
    Returns:
        True if valid, raises PluginValidationError if not
    """
    if not isinstance(plugin_instance, expected_interface):
        raise PluginValidationError(
            f"Plugin {plugin_instance.__class__} does not implement {expected_interface}"
        )
    
    # Check required methods exist and are callable
    required_methods = [method for method in dir(expected_interface) 
                       if not method.startswith('_') and callable(getattr(expected_interface, method, None))]
    
    for method_name in required_methods:
        if not hasattr(plugin_instance, method_name):
            raise PluginValidationError(
                f"Plugin {plugin_instance.__class__} missing required method: {method_name}"
            )
        
        method = getattr(plugin_instance, method_name)
        if not callable(method):
            raise PluginValidationError(
                f"Plugin {plugin_instance.__class__} method {method_name} is not callable"
            )
    
    return True


def validate_memory_system(memory_system: MemorySystem) -> bool:
    """Validate memory system implementation"""
    validate_plugin_interface(memory_system, MemorySystem)
    
    # Test basic functionality
    try:
        # Test capabilities
        capabilities = memory_system.get_capabilities()
        if not isinstance(capabilities, PluginCapabilities):
            raise PluginValidationError("get_capabilities() must return PluginCapabilities instance")
        
        # Test snapshot format
        snapshot = memory_system.get_memory_snapshot()
        required_keys = {'total_items', 'memory_size_bytes', 'last_accessed'}
        if not all(key in snapshot for key in required_keys):
            raise PluginValidationError(f"Memory snapshot missing required keys: {required_keys}")
            
        # Test store/retrieve cycle
        test_stored = memory_system.store_information(
            "test_key", 
            "test_value", 
            {"validation": True}
        )
        if not isinstance(test_stored, bool):
            raise PluginValidationError("store_information() must return bool")
            
    except Exception as e:
        raise PluginValidationError(f"Memory system validation failed: {e}")
    
    return True


def validate_agent_implementation(agent: AgentImplementation) -> bool:
    """Validate agent implementation"""
    validate_plugin_interface(agent, AgentImplementation)
    
    # Test basic functionality  
    try:
        # Test capabilities
        capabilities = agent.get_capabilities()
        if not isinstance(capabilities, PluginCapabilities):
            raise PluginValidationError("get_capabilities() must return PluginCapabilities instance")
            
        # Test agent ID
        agent_id = agent.get_agent_id()
        if not isinstance(agent_id, str) or not agent_id:
            raise PluginValidationError("get_agent_id() must return non-empty string")
            
    except Exception as e:
        raise PluginValidationError(f"Agent validation failed: {e}")
    
    return True
