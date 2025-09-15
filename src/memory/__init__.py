"""
WorkMemEval Memory Systems

This module provides the plugin-based memory system architecture for WorkMemEval.
"""

from .context_memory import ContextMemorySystem, NoMemory
from .memory_system import (
    MemorySystem,
    MemorySystemError,
    MemorySystemFactory,
    MemorySystemInterface,
    NoMemoryBaseline,
    PluginCapabilities,
)
from .reference_implementations import ExampleKeyValueMemory, SimpleContextMemory

__all__ = [
    "PluginCapabilities",
    "MemorySystem",
    "NoMemoryBaseline",
    "MemorySystemInterface",
    "MemorySystemFactory",
    "MemorySystemError",
    "ExampleKeyValueMemory",
    "SimpleContextMemory",
    "NoMemory",
    "ContextMemorySystem",
]
