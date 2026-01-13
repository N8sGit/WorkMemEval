"""
WorkMemEval: Plugin Loader

Dynamically loads and validates agent implementations and memory systems
from module:ClassName specifications. Provides safe instantiation with
configuration validation and capability checking.
"""

import importlib
import inspect
from dataclasses import dataclass
from typing import Any, Dict, Optional, Type

from .plugin_interfaces import (
    AgentImplementation,
    MemorySystem,
    PluginInfo,
    PluginValidationError,
    validate_agent_implementation,
    validate_memory_system,
)


@dataclass
class PluginConfig:
    """Configuration for loading and instantiating a plugin"""

    class_path: str  # Format: "module.path:ClassName"
    config: Dict[str, Any] = None  # Plugin-specific configuration
    validate_on_load: bool = True  # Whether to validate after instantiation

    def __post_init__(self):
        if self.config is None:
            self.config = {}


class PluginLoadError(Exception):
    """Raised when plugin loading fails"""

    pass


class PluginLoader:
    """
    Loads and validates plugins from class path specifications.

    Supports loading:
    - Memory systems implementing MemorySystem interface
    - Agent implementations implementing AgentImplementation interface

    Example usage:
        loader = PluginLoader()

        # Load memory system
        memory = loader.load_memory_system(PluginConfig(
            class_path="src.memory.reference_implementations:SimpleContextMemory",
            config={"max_items": 1000}
        ))

        # Load agent
        agent = loader.load_agent(PluginConfig(
            class_path="src.agents.simple_agent:SimpleWorkMemAgent",
            config={"llm_provider": "openai"}
        ), memory_system=memory)
    """

    def __init__(self):
        self._loaded_modules = {}  # Cache for loaded modules
        self._plugin_registry = {}  # Registry of loaded plugins

    def parse_class_path(self, class_path: str) -> tuple[str, str]:
        """
        Parse class path into module and class name.

        Args:
            class_path: Format "module.path:ClassName"

        Returns:
            (module_path, class_name) tuple

        Raises:
            PluginLoadError: If class path format is invalid
        """
        if ":" not in class_path:
            raise PluginLoadError(
                f"Invalid class path format: {class_path}. Expected 'module:ClassName'"
            )

        module_path, class_name = class_path.rsplit(":", 1)

        if not module_path or not class_name:
            raise PluginLoadError(
                f"Invalid class path format: {class_path}. Module and class name cannot be empty"
            )

        return module_path, class_name

    def load_class(self, class_path: str) -> Type:
        """
        Dynamically load a class from module path.

        Args:
            class_path: Format "module.path:ClassName"

        Returns:
            The loaded class

        Raises:
            PluginLoadError: If module or class cannot be loaded
        """
        module_path, class_name = self.parse_class_path(class_path)

        try:
            # Try to get from cache first
            if module_path in self._loaded_modules:
                module = self._loaded_modules[module_path]
            else:
                # Import the module
                module = importlib.import_module(module_path)
                self._loaded_modules[module_path] = module

            # Get the class from module
            if not hasattr(module, class_name):
                raise PluginLoadError(
                    f"Class '{class_name}' not found in module '{module_path}'"
                )

            plugin_class = getattr(module, class_name)

            if not inspect.isclass(plugin_class):
                raise PluginLoadError(
                    f"'{class_name}' is not a class in module '{module_path}'"
                )

            return plugin_class

        except ImportError as e:
            raise PluginLoadError(f"Failed to import module '{module_path}': {e}")
        except Exception as e:
            raise PluginLoadError(f"Failed to load class '{class_path}': {e}")

    def validate_constructor(
        self, plugin_class: Type, expected_signature: inspect.Signature
    ) -> bool:
        """
        Validate that plugin constructor has expected signature.

        Args:
            plugin_class: The plugin class to validate
            expected_signature: Expected constructor signature

        Returns:
            True if valid

        Raises:
            PluginValidationError: If constructor signature is invalid
        """
        try:
            constructor_sig = inspect.signature(plugin_class.__init__)

            # Check parameter count (excluding 'self' from both)
            plugin_params = list(constructor_sig.parameters.keys())[1:]  # Skip 'self'
            expected_params = list(expected_signature.parameters.keys())[
                1:
            ]  # Skip 'self'

            if len(plugin_params) < len(expected_params):
                raise PluginValidationError(
                    f"Plugin constructor has {len(plugin_params)} parameters, "
                    f"expected at least {len(expected_params)}: {expected_params}"
                )

            return True

        except Exception as e:
            raise PluginValidationError(f"Constructor validation failed: {e}")

    def load_memory_system(self, plugin_config: PluginConfig) -> MemorySystem:
        """
        Load and instantiate a memory system plugin.

        Args:
            plugin_config: Configuration for the memory system

        Returns:
            Instantiated and validated memory system

        Raises:
            PluginLoadError: If loading fails
            PluginValidationError: If validation fails
        """
        try:
            # Load the class
            memory_class = self.load_class(plugin_config.class_path)

            # Validate it's a MemorySystem subclass
            if not issubclass(memory_class, MemorySystem):
                raise PluginLoadError(
                    f"Class {plugin_config.class_path} does not inherit from MemorySystem"
                )

            # Validate constructor signature
            expected_sig = inspect.signature(MemorySystem.__init__)
            self.validate_constructor(memory_class, expected_sig)

            # Instantiate the memory system
            memory_instance = memory_class(plugin_config.config)

            # Validate the instance if requested
            if plugin_config.validate_on_load:
                validate_memory_system(memory_instance)

            # Register the plugin
            plugin_info = PluginInfo(
                memory_class, *self.parse_class_path(plugin_config.class_path)
            )
            plugin_info.capabilities = memory_instance.get_capabilities()
            self._plugin_registry[plugin_config.class_path] = plugin_info

            return memory_instance

        except Exception as e:
            raise PluginLoadError(
                f"Failed to load memory system '{plugin_config.class_path}': {e}"
            )

    def load_agent(
        self, plugin_config: PluginConfig, memory_system: MemorySystem
    ) -> AgentImplementation:
        """
        Load and instantiate an agent implementation plugin.

        Args:
            plugin_config: Configuration for the agent
            memory_system: Memory system to inject into agent

        Returns:
            Instantiated and validated agent implementation

        Raises:
            PluginLoadError: If loading fails
            PluginValidationError: If validation fails
        """
        try:
            # Load the class
            agent_class = self.load_class(plugin_config.class_path)

            # Validate it's an AgentImplementation subclass
            if not issubclass(agent_class, AgentImplementation):
                raise PluginLoadError(
                    f"Class {plugin_config.class_path} does not inherit from AgentImplementation"
                )

            # Validate constructor signature
            expected_sig = inspect.signature(AgentImplementation.__init__)
            self.validate_constructor(agent_class, expected_sig)

            # Instantiate the agent
            agent_instance = agent_class(memory_system, plugin_config.config)

            # Validate the instance if requested
            if plugin_config.validate_on_load:
                validate_agent_implementation(agent_instance)

            # Register the plugin
            plugin_info = PluginInfo(
                agent_class, *self.parse_class_path(plugin_config.class_path)
            )
            plugin_info.capabilities = agent_instance.get_capabilities()
            self._plugin_registry[plugin_config.class_path] = plugin_info

            return agent_instance

        except Exception as e:
            raise PluginLoadError(
                f"Failed to load agent '{plugin_config.class_path}': {e}"
            )

    def get_plugin_info(self, class_path: str) -> Optional[PluginInfo]:
        """Get information about a loaded plugin"""
        return self._plugin_registry.get(class_path)

    def list_loaded_plugins(self) -> Dict[str, PluginInfo]:
        """Get all loaded plugin information"""
        return self._plugin_registry.copy()

    def clear_cache(self):
        """Clear module cache and plugin registry"""
        self._loaded_modules.clear()
        self._plugin_registry.clear()


# Convenience functions for common loading patterns
def load_memory_from_config(config: Dict[str, Any]) -> MemorySystem:
    """
    Load memory system from configuration dict.

    Expected config format:
    {
        "memory_class": "module.path:ClassName",
        "memory_config": {...}
    }
    """
    loader = PluginLoader()
    plugin_config = PluginConfig(
        class_path=config["memory_class"], config=config.get("memory_config", {})
    )
    return loader.load_memory_system(plugin_config)


def load_agent_from_config(
    config: Dict[str, Any], memory_system: MemorySystem
) -> AgentImplementation:
    """
    Load agent from configuration dict.

    Expected config format:
    {
        "agent_class": "module.path:ClassName",
        "agent_config": {...}
    }
    """
    loader = PluginLoader()
    plugin_config = PluginConfig(
        class_path=config["agent_class"], config=config.get("agent_config", {})
    )
    return loader.load_agent(plugin_config, memory_system)


def load_plugins_from_config(
    config: Dict[str, Any]
) -> tuple[AgentImplementation, MemorySystem]:
    """
    Load both agent and memory system from single config.

    Expected config format:
    {
        "memory_class": "module.path:MemoryClass",
        "memory_config": {...},
        "agent_class": "module.path:AgentClass",
        "agent_config": {...}
    }

    Returns:
        (agent_instance, memory_instance) tuple
    """
    loader = PluginLoader()

    # Load memory system first
    memory_config = PluginConfig(
        class_path=config["memory_class"], config=config.get("memory_config", {})
    )
    memory_system = loader.load_memory_system(memory_config)

    # Load agent with memory system
    agent_config = PluginConfig(
        class_path=config["agent_class"], config=config.get("agent_config", {})
    )
    agent = loader.load_agent(agent_config, memory_system)

    return agent, memory_system
