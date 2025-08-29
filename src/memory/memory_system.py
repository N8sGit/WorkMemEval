"""
WorkMemEval: Plugin-Based Memory System

Abstract interfaces for memory systems that can be plugged into the benchmark.
This allows researchers to bring their own memory implementations while
maintaining consistent evaluation interfaces.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
import time
from dataclasses import dataclass


@dataclass
class PluginCapabilities:
    """Declares what optional features a plugin supports"""
    # Memory system capabilities
    supports_embeddings: bool = False
    supports_persistence: bool = False
    supports_compression: bool = False
    supports_search: bool = False
    supports_introspection: bool = False
    supports_forgetting: bool = False
    supports_consolidation: bool = False
    
    # Agent capabilities  
    supports_planning: bool = False
    supports_debugging: bool = False
    supports_git_operations: bool = False
    supports_docker: bool = False
    
    # Common capabilities
    supports_async: bool = True


class MemorySystem(ABC):
    """
    Abstract base class for memory systems.
    
    This defines the minimal interface that any memory system must implement
    to work with WorkMemEval. Memory systems can be as simple as key-value
    stores or as complex as neural episodic memory architectures.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.created_at = time.time()
        
    @abstractmethod
    def get_capabilities(self) -> PluginCapabilities:
        """
        Return what capabilities this memory system supports.
        
        This allows the benchmark to adapt its evaluation based on
        what the memory system can actually do.
        """
        pass
        
    @abstractmethod
    def store_information(self, key: str, value: Any, context: Dict[str, Any]) -> bool:
        """
        Store information in memory.
        
        Args:
            key: Unique identifier for this piece of information
            value: The actual information to store (can be any type)
            context: Additional context that might influence storage
            
        Returns:
            bool: True if storage was successful, False otherwise
        """
        pass
        
    @abstractmethod
    def retrieve_information(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve information from memory based on a query.
        
        Args:
            query: What to search for
            context: Additional context that might influence retrieval
            
        Returns:
            List of results, each containing:
            - 'key': The original key
            - 'value': The stored value
            - 'relevance_score': How relevant this result is (0.0-1.0)
            - 'metadata': Any additional metadata about this memory
        """
        pass
        
    @abstractmethod
    def get_memory_snapshot(self) -> Dict[str, Any]:
        """
        Get a snapshot of current memory state for WorkMemEval analysis.
        
        This should return information about what's currently in memory
        without revealing the actual stored content (to avoid cheating).
        
        Returns:
            Dict containing memory statistics and metadata
        """
        pass
    
    # Optional methods with default implementations
    def clear_memory(self) -> bool:
        """Clear all stored information. Override if supported."""
        if self.get_capabilities().supports_introspection:
            return False  # Should override if you claim to support this
        raise NotImplementedError("Memory clearing not supported by this system")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get detailed memory usage statistics. Override if supported."""
        if self.get_capabilities().supports_introspection:
            return {}  # Should override if you claim to support this
        raise NotImplementedError("Memory introspection not supported by this system")
    
    def compress_memory(self) -> bool:
        """Trigger memory compression if supported. Override if supported."""
        if self.get_capabilities().supports_compression:
            return False  # Should override if you claim to support this
        raise NotImplementedError("Memory compression not supported by this system")
    
    def forget_information(self, criteria: Dict[str, Any]) -> int:
        """Forget information matching criteria. Override if supported."""
        if self.get_capabilities().supports_forgetting:
            return 0  # Should override if you claim to support this
        raise NotImplementedError("Selective forgetting not supported by this system")
    
    def consolidate_memory(self) -> bool:
        """Trigger memory consolidation if supported. Override if supported."""
        if self.get_capabilities().supports_consolidation:
            return False  # Should override if you claim to support this
        raise NotImplementedError("Memory consolidation not supported by this system")


class NoMemoryBaseline(MemorySystem):
    """
    Baseline system with no memory capability.
    
    This is the true baseline - it stores nothing and recalls nothing.
    Used to measure the impact of any memory system versus no memory.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.operation_count = 0
        
    def get_capabilities(self) -> PluginCapabilities:
        """No capabilities except basic introspection"""
        return PluginCapabilities(
            supports_introspection=True  # We can report our lack of memory
        )
    
    def store_information(self, key: str, value: Any, context: Dict[str, Any]) -> bool:
        """Discard everything immediately"""
        self.operation_count += 1
        return True  # Pretend it worked
        
    def retrieve_information(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Never retrieve anything"""
        self.operation_count += 1
        return []
        
    def get_memory_snapshot(self) -> Dict[str, Any]:
        """Report complete absence of memory"""
        return {
            'total_items': 0,
            'memory_size_bytes': 0,
            'last_accessed': time.time(),
            'operation_count': self.operation_count,
            'memory_type': 'no_memory_baseline',
            'capabilities': self.get_capabilities().__dict__
        }
    
    def clear_memory(self) -> bool:
        """Clear memory - no-op since there's no memory to clear"""
        return True
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Baseline stats showing no memory activity"""
        return {
            'storage_operations': self.operation_count,
            'retrieval_operations': self.operation_count,
            'memory_efficiency': 0.0,
            'recall_success_rate': 0.0,
            'false_positive_rate': 0.0,  # Never returns anything, so no false positives
            'false_negative_rate': 1.0   # Never returns anything, so everything is missed
        }


class MemorySystemInterface:
    """
    Interface wrapper that provides additional functionality around memory systems.
    
    This handles WorkMemEval-specific concerns like metrics collection,
    validation, and standardized logging without constraining the memory
    implementation.
    """
    
    def __init__(self, memory_system: MemorySystem, enable_metrics: bool = True):
        self.memory_system = memory_system
        self.enable_metrics = enable_metrics
        self.metrics = {
            'total_stores': 0,
            'total_retrievals': 0,
            'successful_stores': 0,
            'successful_retrievals': 0,
            'total_query_time': 0.0,
            'total_store_time': 0.0
        } if enable_metrics else {}
        
    def store(self, key: str, value: Any, context: Dict[str, Any] = None) -> bool:
        """Store information with optional metrics collection"""
        if context is None:
            context = {}
            
        start_time = time.time()
        
        try:
            success = self.memory_system.store_information(key, value, context)
            
            if self.enable_metrics:
                self.metrics['total_stores'] += 1
                if success:
                    self.metrics['successful_stores'] += 1
                self.metrics['total_store_time'] += time.time() - start_time
                
            return success
            
        except Exception as e:
            if self.enable_metrics:
                self.metrics['total_stores'] += 1
                self.metrics['total_store_time'] += time.time() - start_time
            raise MemorySystemError(f"Storage failed: {e}") from e
    
    def retrieve(self, query: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Retrieve information with optional metrics collection"""
        if context is None:
            context = {}
            
        start_time = time.time()
        
        try:
            results = self.memory_system.retrieve_information(query, context)
            
            if self.enable_metrics:
                self.metrics['total_retrievals'] += 1
                if results:  # Consider non-empty results as successful
                    self.metrics['successful_retrievals'] += 1
                self.metrics['total_query_time'] += time.time() - start_time
            
            # Validate result format
            if not isinstance(results, list):
                raise MemorySystemError("retrieve_information must return a list")
                
            for result in results:
                if not isinstance(result, dict):
                    raise MemorySystemError("Each result must be a dictionary")
                if 'key' not in result or 'value' not in result:
                    raise MemorySystemError("Results must contain 'key' and 'value' fields")
                    
            return results
            
        except Exception as e:
            if self.enable_metrics:
                self.metrics['total_retrievals'] += 1
                self.metrics['total_query_time'] += time.time() - start_time
            raise MemorySystemError(f"Retrieval failed: {e}") from e
    
    def get_snapshot(self) -> Dict[str, Any]:
        """Get memory snapshot with interface metrics"""
        snapshot = self.memory_system.get_memory_snapshot()
        
        if self.enable_metrics:
            snapshot['interface_metrics'] = self.metrics.copy()
            
        return snapshot
    
    def get_capabilities(self) -> PluginCapabilities:
        """Get memory system capabilities"""
        return self.memory_system.get_capabilities()


class MemorySystemError(Exception):
    """Exception raised by memory system operations"""
    pass


# Factory pattern for creating memory systems
class MemorySystemFactory:
    """Factory for creating memory system instances"""
    
    _registry = {
        'no_memory': NoMemoryBaseline,
    }
    
    @classmethod
    def register_memory_system(cls, name: str, memory_class: type):
        """Register a new memory system type"""
        if not issubclass(memory_class, MemorySystem):
            raise ValueError("Memory system must inherit from MemorySystem")
        cls._registry[name] = memory_class
    
    @classmethod
    def create_memory_system(cls, memory_type: str, config: Dict[str, Any]) -> MemorySystemInterface:
        """Create a memory system instance wrapped in the interface"""
        if memory_type not in cls._registry:
            raise ValueError(f"Unknown memory type: {memory_type}. "
                           f"Available types: {list(cls._registry.keys())}")
        
        memory_system = cls._registry[memory_type](config)
        return MemorySystemInterface(memory_system)
    
    @classmethod
    def list_available_types(cls) -> List[str]:
        """List all registered memory system types"""
        return list(cls._registry.keys())
