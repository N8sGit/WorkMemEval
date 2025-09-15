"""
Unit tests for the new plugin-based memory system architecture.

Tests cover:
- Abstract base classes
- Reference implementations
- Factory pattern
- Interface wrapper
- Error handling
"""

import time
from unittest.mock import Mock

import pytest

from src.memory.memory_system import (
    MemorySystem,
    MemorySystemError,
    MemorySystemFactory,
    MemorySystemInterface,
    NoMemoryBaseline,
    PluginCapabilities,
)
from src.memory.reference_implementations import (
    ExampleKeyValueMemory,
    SimpleContextMemory,
)


class TestPluginCapabilities:
    """Test the PluginCapabilities dataclass"""

    def test_default_capabilities(self):
        """Test default capability values are all False except where specified"""
        caps = PluginCapabilities()

        assert caps.supports_embeddings is False
        assert caps.supports_persistence is False
        assert caps.supports_compression is False
        assert caps.supports_search is False
        assert caps.supports_introspection is False
        assert caps.supports_forgetting is False
        assert caps.supports_consolidation is False

    def test_custom_capabilities(self):
        """Test setting custom capability values"""
        caps = PluginCapabilities(
            supports_search=True, supports_introspection=True, supports_forgetting=True
        )

        assert caps.supports_search is True
        assert caps.supports_introspection is True
        assert caps.supports_forgetting is True
        assert caps.supports_embeddings is False  # Still default


class TestMemorySystemAbstract:
    """Test abstract base class behavior"""

    def test_abstract_methods_cannot_be_instantiated(self):
        """Test that MemorySystem cannot be instantiated directly"""
        with pytest.raises(TypeError):
            MemorySystem({})

    def test_optional_methods_raise_not_implemented_by_default(self):
        """Test that optional methods raise NotImplementedError when capabilities don't match"""

        # Create a minimal concrete implementation
        class MinimalMemory(MemorySystem):
            def get_capabilities(self):
                return PluginCapabilities()  # No capabilities

            def store_information(self, key, value, context):
                return True

            def retrieve_information(self, query, context):
                return []

            def get_memory_snapshot(self):
                return {
                    "total_items": 0,
                    "memory_size_bytes": 0,
                    "last_accessed": time.time(),
                }

        memory = MinimalMemory({})

        # Should raise NotImplementedError since capabilities don't claim support
        with pytest.raises(NotImplementedError, match="Memory clearing not supported"):
            memory.clear_memory()

        with pytest.raises(
            NotImplementedError, match="Memory introspection not supported"
        ):
            memory.get_memory_stats()

        with pytest.raises(
            NotImplementedError, match="Memory compression not supported"
        ):
            memory.compress_memory()


class TestNoMemoryBaseline:
    """Test the no-memory baseline implementation"""

    def test_initialization(self):
        """Test NoMemoryBaseline initialization"""
        config = {"test_param": "test_value"}
        memory = NoMemoryBaseline(config)

        assert memory.config == config
        assert memory.operation_count == 0
        assert isinstance(memory.created_at, float)

    def test_capabilities(self):
        """Test that NoMemoryBaseline reports correct capabilities"""
        memory = NoMemoryBaseline({})
        caps = memory.get_capabilities()

        assert caps.supports_introspection is True
        assert caps.supports_search is False
        assert caps.supports_persistence is False

    def test_store_information_discards_everything(self):
        """Test that store_information discards everything but returns success"""
        memory = NoMemoryBaseline({})

        result = memory.store_information("test_key", "test_value", {"context": "test"})

        assert result is True
        assert memory.operation_count == 1

        # Verify nothing is actually stored by checking snapshot
        snapshot = memory.get_memory_snapshot()
        assert snapshot["total_items"] == 0

    def test_retrieve_information_returns_empty(self):
        """Test that retrieve_information always returns empty list"""
        memory = NoMemoryBaseline({})

        # Store something first
        memory.store_information("test_key", "test_value", {})

        # Try to retrieve
        results = memory.retrieve_information("test_value", {})

        assert results == []
        assert memory.operation_count == 2  # One store, one retrieve

    def test_memory_snapshot(self):
        """Test memory snapshot format and content"""
        memory = NoMemoryBaseline({})
        memory.store_information("key", "value", {})  # This should be discarded

        snapshot = memory.get_memory_snapshot()

        assert snapshot["total_items"] == 0
        assert snapshot["memory_size_bytes"] == 0
        assert snapshot["memory_type"] == "no_memory_baseline"
        assert snapshot["operation_count"] == 1
        assert "capabilities" in snapshot
        assert isinstance(snapshot["last_accessed"], float)

    def test_memory_stats(self):
        """Test memory statistics"""
        memory = NoMemoryBaseline({})
        memory.store_information("key", "value", {})
        memory.retrieve_information("query", {})

        stats = memory.get_memory_stats()

        assert stats["memory_efficiency"] == 0.0
        assert stats["recall_success_rate"] == 0.0
        assert stats["false_positive_rate"] == 0.0
        assert stats["false_negative_rate"] == 1.0


class TestExampleKeyValueMemory:
    """Test the example key-value memory implementation"""

    def test_initialization(self):
        """Test ExampleKeyValueMemory initialization"""
        config = {"max_size": 1000}
        memory = ExampleKeyValueMemory(config)

        assert memory.config == config
        assert memory._storage == {}
        assert memory._metadata == {}

    def test_capabilities(self):
        """Test capabilities reporting"""
        memory = ExampleKeyValueMemory({})
        caps = memory.get_capabilities()

        assert caps.supports_search is True
        assert caps.supports_introspection is True
        assert caps.supports_forgetting is True

    def test_store_and_retrieve_basic(self):
        """Test basic store and retrieve functionality"""
        memory = ExampleKeyValueMemory({})

        # Store information
        result = memory.store_information("test_key", "test_value", {"source": "test"})
        assert result is True

        # Retrieve information
        results = memory.retrieve_information("test_value", {})

        assert len(results) == 1
        assert results[0]["key"] == "test_key"
        assert results[0]["value"] == "test_value"
        assert results[0]["relevance_score"] == 0.5
        assert "metadata" in results[0]
        assert results[0]["metadata"]["access_count"] == 1

    def test_search_functionality(self):
        """Test search across multiple items"""
        memory = ExampleKeyValueMemory({})

        # Store multiple items
        memory.store_information("key1", "apple fruit", {"type": "food"})
        memory.store_information("key2", "banana fruit", {"type": "food"})
        memory.store_information("key3", "carrot vegetable", {"type": "food"})

        # Search for fruit
        results = memory.retrieve_information("fruit", {})
        assert len(results) == 2

        # Search for something not there
        results = memory.retrieve_information("meat", {})
        assert len(results) == 0

    def test_access_count_tracking(self):
        """Test that access counts are tracked correctly"""
        memory = ExampleKeyValueMemory({})

        memory.store_information("key1", "test value", {})

        # First retrieval
        results = memory.retrieve_information("test", {})
        assert results[0]["metadata"]["access_count"] == 1

        # Second retrieval
        results = memory.retrieve_information("test", {})
        assert results[0]["metadata"]["access_count"] == 2

    def test_clear_memory(self):
        """Test memory clearing functionality"""
        memory = ExampleKeyValueMemory({})

        # Store some data
        memory.store_information("key1", "value1", {})
        memory.store_information("key2", "value2", {})

        # Verify data exists
        snapshot = memory.get_memory_snapshot()
        assert snapshot["total_items"] == 2

        # Clear memory
        result = memory.clear_memory()
        assert result is True

        # Verify data is gone
        snapshot = memory.get_memory_snapshot()
        assert snapshot["total_items"] == 0
        assert len(memory._storage) == 0
        assert len(memory._metadata) == 0

    def test_forget_information(self):
        """Test selective forgetting functionality"""
        memory = ExampleKeyValueMemory({})

        # Store items with different timestamps
        old_time = time.time() - 3600  # 1 hour ago
        memory.store_information("old_key", "old_value", {})
        memory._metadata["old_key"]["stored_at"] = old_time

        memory.store_information("new_key", "new_value", {})

        # Forget old items
        cutoff_time = time.time() - 1800  # 30 minutes ago
        forgotten_count = memory.forget_information({"older_than": cutoff_time})

        assert forgotten_count == 1
        assert "old_key" not in memory._storage
        assert "new_key" in memory._storage


class TestSimpleContextMemory:
    """Test the SimpleContextMemory implementation"""

    def test_initialization_with_config(self):
        """Test initialization with custom configuration"""
        config = {
            "max_items": 500,
            "max_memory_size": 50000,
            "relevance_threshold": 0.2,
        }
        memory = SimpleContextMemory(config)

        assert memory.max_items == 500
        assert memory.max_memory_size == 50000
        assert memory.relevance_threshold == 0.2

    def test_relevance_calculation(self):
        """Test relevance score calculation"""
        memory = SimpleContextMemory({})

        # Store an item
        memory.store_information(
            "key1", "artificial intelligence machine learning", {"topic": "AI"}
        )

        # Test exact match
        results = memory.retrieve_information("artificial intelligence", {})
        assert len(results) > 0
        assert results[0]["relevance_score"] > 0.5

        # Test partial match
        results = memory.retrieve_information("machine", {})
        assert len(results) > 0
        assert 0 < results[0]["relevance_score"] <= 1.0

    def test_memory_overflow_management(self):
        """Test memory overflow handling"""
        config = {"max_items": 3, "max_memory_size": 1000000}  # Only item limit
        memory = SimpleContextMemory(config)

        # Store more items than the limit
        for i in range(5):
            memory.store_information(f"key{i}", f"value{i}", {})

        # Should only keep 3 items
        snapshot = memory.get_memory_snapshot()
        assert snapshot["total_items"] == 3

    def test_context_search(self):
        """Test searching through context information"""
        memory = SimpleContextMemory({})

        memory.store_information(
            "doc1", "python code", {"language": "python", "type": "code"}
        )
        memory.store_information(
            "doc2", "java program", {"language": "java", "type": "code"}
        )

        # Search by context should work through the searchable text
        results = memory.retrieve_information("python", {})
        assert len(results) >= 1


class TestMemorySystemInterface:
    """Test the MemorySystemInterface wrapper"""

    def test_initialization_with_metrics(self):
        """Test interface wrapper initialization with metrics enabled"""
        mock_memory = Mock(spec=MemorySystem)
        interface = MemorySystemInterface(mock_memory, enable_metrics=True)

        assert interface.memory_system == mock_memory
        assert interface.enable_metrics is True
        assert "total_stores" in interface.metrics
        assert "total_retrievals" in interface.metrics

    def test_initialization_without_metrics(self):
        """Test interface wrapper initialization with metrics disabled"""
        mock_memory = Mock(spec=MemorySystem)
        interface = MemorySystemInterface(mock_memory, enable_metrics=False)

        assert interface.enable_metrics is False
        assert interface.metrics == {}

    def test_store_with_metrics_collection(self):
        """Test store operation with metrics collection"""
        mock_memory = Mock(spec=MemorySystem)
        mock_memory.store_information.return_value = True

        interface = MemorySystemInterface(mock_memory, enable_metrics=True)

        result = interface.store("key", "value", {"context": "test"})

        assert result is True
        assert interface.metrics["total_stores"] == 1
        assert interface.metrics["successful_stores"] == 1
        assert interface.metrics["total_store_time"] > 0
        mock_memory.store_information.assert_called_once_with(
            "key", "value", {"context": "test"}
        )

    def test_store_with_failure(self):
        """Test store operation when underlying memory fails"""
        mock_memory = Mock(spec=MemorySystem)
        mock_memory.store_information.return_value = False

        interface = MemorySystemInterface(mock_memory, enable_metrics=True)

        result = interface.store("key", "value")

        assert result is False
        assert interface.metrics["total_stores"] == 1
        assert interface.metrics["successful_stores"] == 0

    def test_retrieve_with_validation(self):
        """Test retrieve operation with result validation"""
        mock_memory = Mock(spec=MemorySystem)
        mock_memory.retrieve_information.return_value = [
            {"key": "test_key", "value": "test_value", "relevance_score": 0.8}
        ]

        interface = MemorySystemInterface(mock_memory, enable_metrics=True)

        results = interface.retrieve("query", {"context": "test"})

        assert len(results) == 1
        assert interface.metrics["total_retrievals"] == 1
        assert interface.metrics["successful_retrievals"] == 1

    def test_retrieve_validation_error(self):
        """Test retrieve validation catches malformed results"""
        mock_memory = Mock(spec=MemorySystem)
        mock_memory.retrieve_information.return_value = [
            {"key": "test_key"}  # Missing 'value' field
        ]

        interface = MemorySystemInterface(mock_memory, enable_metrics=True)

        with pytest.raises(
            MemorySystemError, match="Results must contain 'key' and 'value' fields"
        ):
            interface.retrieve("query")

    def test_retrieve_non_list_error(self):
        """Test retrieve validation catches non-list returns"""
        mock_memory = Mock(spec=MemorySystem)
        mock_memory.retrieve_information.return_value = "not a list"

        interface = MemorySystemInterface(mock_memory)

        with pytest.raises(
            MemorySystemError, match="retrieve_information must return a list"
        ):
            interface.retrieve("query")

    def test_get_snapshot_with_interface_metrics(self):
        """Test snapshot includes interface metrics"""
        mock_memory = Mock(spec=MemorySystem)
        mock_memory.get_memory_snapshot.return_value = {"total_items": 5}

        interface = MemorySystemInterface(mock_memory, enable_metrics=True)
        interface.store("key", "value")  # Generate some metrics

        snapshot = interface.get_snapshot()

        assert snapshot["total_items"] == 5
        assert "interface_metrics" in snapshot
        assert snapshot["interface_metrics"]["total_stores"] == 1

    def test_exception_handling_in_store(self):
        """Test exception handling in store operation"""
        mock_memory = Mock(spec=MemorySystem)
        mock_memory.store_information.side_effect = Exception("Storage error")

        interface = MemorySystemInterface(mock_memory, enable_metrics=True)

        with pytest.raises(MemorySystemError, match="Storage failed"):
            interface.store("key", "value")

        # Metrics should still be updated
        assert interface.metrics["total_stores"] == 1
        assert interface.metrics["successful_stores"] == 0


class TestMemorySystemFactory:
    """Test the MemorySystemFactory"""

    def test_default_registry(self):
        """Test that factory has default registrations"""
        types = MemorySystemFactory.list_available_types()

        assert "no_memory" in types
        assert "example_kv" in types  # From reference_implementations
        assert "simple_context" in types  # From reference_implementations

    def test_register_memory_system(self):
        """Test registering a new memory system"""

        class CustomMemory(MemorySystem):
            def get_capabilities(self):
                return PluginCapabilities()

            def store_information(self, key, value, context):
                return True

            def retrieve_information(self, query, context):
                return []

            def get_memory_snapshot(self):
                return {
                    "total_items": 0,
                    "memory_size_bytes": 0,
                    "last_accessed": time.time(),
                }

        MemorySystemFactory.register_memory_system("custom", CustomMemory)

        types = MemorySystemFactory.list_available_types()
        assert "custom" in types

    def test_register_invalid_memory_system(self):
        """Test that registering invalid memory system raises error"""

        class NotAMemorySystem:
            pass

        with pytest.raises(
            ValueError, match="Memory system must inherit from MemorySystem"
        ):
            MemorySystemFactory.register_memory_system("invalid", NotAMemorySystem)

    def test_create_memory_system_success(self):
        """Test successful memory system creation"""
        config = {"test_param": "test_value"}

        interface = MemorySystemFactory.create_memory_system("no_memory", config)

        assert isinstance(interface, MemorySystemInterface)
        assert isinstance(interface.memory_system, NoMemoryBaseline)
        assert interface.memory_system.config == config

    def test_create_unknown_memory_system(self):
        """Test creating unknown memory system raises error"""

        with pytest.raises(ValueError, match="Unknown memory type: nonexistent"):
            MemorySystemFactory.create_memory_system("nonexistent", {})

    def test_factory_creates_wrapped_instances(self):
        """Test that factory creates MemorySystemInterface-wrapped instances"""
        interface = MemorySystemFactory.create_memory_system("example_kv", {})

        assert isinstance(interface, MemorySystemInterface)
        assert isinstance(interface.memory_system, ExampleKeyValueMemory)

    def test_integration_store_retrieve_cycle(self):
        """Integration test: create system via factory and test full cycle"""
        interface = MemorySystemFactory.create_memory_system("example_kv", {})

        # Store information
        success = interface.store(
            "integration_test", "test data for integration", {"test": True}
        )
        assert success is True

        # Retrieve information
        results = interface.retrieve("integration", {})
        assert len(results) == 1
        assert results[0]["key"] == "integration_test"
        assert results[0]["value"] == "test data for integration"

        # Check snapshot
        snapshot = interface.get_snapshot()
        assert snapshot["total_items"] == 1
        assert "interface_metrics" in snapshot


if __name__ == "__main__":
    pytest.main([__file__])
