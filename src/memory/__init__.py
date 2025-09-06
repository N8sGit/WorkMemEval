"""
WorkMemEval Memory Systems

This module provides the plugin-based memory system architecture for WorkMemEval.
"""

from .memory_system import (
    PluginCapabilities,
    MemorySystem,
    NoMemoryBaseline,
    MemorySystemInterface,
    MemorySystemFactory,
    MemorySystemError
)

from .reference_implementations import (
    ExampleKeyValueMemory,
    SimpleContextMemory
)

from .context_memory import (
    NoMemory,
    ContextMemorySystem
)

__all__ = [
    'PluginCapabilities',
    'MemorySystem',
    'NoMemoryBaseline',
    'MemorySystemInterface',
    'MemorySystemFactory',
    'MemorySystemError',
    'ExampleKeyValueMemory',
    'SimpleContextMemory',
    'NoMemory',
    'ContextMemorySystem'
]
