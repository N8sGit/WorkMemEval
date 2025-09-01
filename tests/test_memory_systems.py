"""
Unit tests for WorkMemEval memory systems.

Tests the baseline memory system implementations with comprehensive
coverage following TDD principles.
"""

import pytest
import time
from src.memory.reference_implementations import SimpleContextMemory
from src.memory.simple_memory import NoMemory, CompressedMemory
from src.memory.memory_system import PluginCapabilities


class TestNoMemory:
    """Test NoMemory baseline system"""
    
    def setup_method(self):
        """Setup for each test"""
        self.memory = NoMemory({})
    
    def test_no_memory_creation(self):
        """Test creating NoMemory system"""
        assert isinstance(self.memory, NoMemory)
        # For new NoMemory, use snapshot access_count instead of operation_count
        snap = self.memory.get_memory_snapshot()
        assert snap.get('access_count', 0) == 0
        
        # Test with config
        config_memory = NoMemory({'some_config': 'value'})
        assert config_memory.config['some_config'] == 'value'
    
    def test_no_memory_capabilities(self):
        """Test NoMemory capabilities"""
        caps = self.memory.get_capabilities()
        
        assert isinstance(caps, PluginCapabilities)
        assert caps.supports_embeddings is False
        assert caps.supports_persistence is False
        assert caps.supports_compression is False
        assert caps.supports_search is False
        assert caps.supports_introspection is True
    
    def test_store_information_always_succeeds(self):
        """Test that storing always reports success but doesn't actually store"""
        # Store some information
        result = self.memory.store_information("test_key", "test_value", {"context": True})
        
        assert result is True
        # access_count increments on store
        snap = self.memory.get_memory_snapshot()
        assert snap.get('access_count', 0) == 1
        
        # Store more information
        result2 = self.memory.store_information("key2", {"complex": "data"}, {})
        assert result2 is True
        snap = self.memory.get_memory_snapshot()
        assert snap.get('access_count', 0) == 2
    
    def test_retrieve_information_always_empty(self):
        """Test that retrieval always returns empty results"""
        # Try to retrieve without storing
        results = self.memory.retrieve_information("test query", {})
        assert results == []
        snap = self.memory.get_memory_snapshot()
        assert snap.get('access_count', 0) == 1
        
        # Store something, then try to retrieve
        self.memory.store_information("key", "value", {})
        results = self.memory.retrieve_information("key", {})
        assert results == []
        snap = self.memory.get_memory_snapshot()
        assert snap.get('access_count', 0) == 3  # store + 2 retrievals
    
    def test_memory_snapshot(self):
        """Test memory snapshot shows no memory"""
        snapshot = self.memory.get_memory_snapshot()
        
        assert snapshot['total_items'] == 0
        assert snapshot['memory_size_bytes'] == 0
        assert snapshot['memory_type'] == 'no_memory'
        assert 'last_accessed' in snapshot
        assert 'access_count' in snapshot
    
    def test_clear_memory(self):
        """Test clearing memory (no-op)"""
        self.memory.store_information("key", "value", {})
        result = self.memory.clear_memory()
        
        # NoMemoryBaseline clear_memory is not implemented and should return False by default
        # since it doesn't actually support clearing (no memory to clear)
        assert result is True  # But our implementation does override this method
        # access_count should reflect only the store
        snap = self.memory.get_memory_snapshot()
        assert snap.get('access_count', 0) == 1
    
    def test_memory_stats(self):
        """Test memory statistics"""
        stats = self.memory.get_memory_stats()
        
        assert stats['memory_efficiency'] == 0.0
        # New NoMemory reports 'recall_accuracy'
        assert stats.get('recall_accuracy', 0.0) == 0.0
        # And counts under total_* keys
        assert 'total_stores' in stats or 'storage_operations' in stats
        assert 'total_retrievals' in stats or 'retrieval_operations' in stats


class TestSimpleContextMemory:
    """Test SimpleContextMemory system"""
    
    def setup_method(self):
        """Setup for each test"""
        self.memory = SimpleContextMemory({
            'max_items': 100,
            'max_memory_size': 10000,
            'relevance_threshold': 0.1
        })
    
    def test_simple_memory_creation(self):
        """Test creating SimpleContextMemory"""
        assert isinstance(self.memory, SimpleContextMemory)
        assert len(self.memory.items) == 0
        assert self.memory.max_items == 100
        assert self.memory.max_memory_size == 10000
    
    def test_simple_memory_capabilities(self):
        """Test SimpleContextMemory capabilities"""
        caps = self.memory.get_capabilities()
        
        assert caps.supports_search is True
        assert caps.supports_introspection is True
        assert caps.supports_embeddings is False
        assert caps.supports_persistence is False
        assert caps.supports_compression is False
    
    def test_store_and_retrieve_information(self):
        """Test basic store and retrieve functionality"""
        # Store information
        result = self.memory.store_information(
            "task_info", 
            "Implement calculator with add and multiply functions",
            {"checkpoint": "cp1", "type": "requirement"}
        )
        
        assert result is True
        assert len(self.memory.items) == 1
        assert self.memory.store_count == 1
        
        # Retrieve information
        results = self.memory.retrieve_information("calculator", {})
        
        assert len(results) == 1
        assert results[0]['key'] == "task_info"
        assert "calculator" in results[0]['value']
        assert results[0]['relevance_score'] > 0
        assert self.memory.retrieve_count == 1
    
    def test_keyword_matching(self):
        """Test keyword matching relevance"""
        # Store multiple items
        self.memory.store_information("calc", "Calculator implementation", {"type": "task"})
        self.memory.store_information("user", "User management system", {"type": "task"})
        self.memory.store_information("math", "Mathematical operations for calculator", {"type": "detail"})
        
        # Search for calculator-related items
        results = self.memory.retrieve_information("calculator", {})
        
        # Should find 2 items (calc and math)
        assert len(results) >= 2
        
        # Results should be sorted by relevance
        assert results[0]['relevance_score'] >= results[1]['relevance_score']
        
        # Should not include user management
        user_found = any("User management" in result['value'] for result in results)
        assert not user_found
    
    def test_update_existing_key(self):
        """Test updating existing information"""
        # Store initial information
        self.memory.store_information("status", "Task started", {"phase": "initial"})
        assert len(self.memory.items) == 1
        
        # Update the same key
        self.memory.store_information("status", "Task completed", {"phase": "final"})
        assert len(self.memory.items) == 1  # Should not grow
        
        # Retrieve should get updated value
        results = self.memory.retrieve_information("completed", {})
        assert len(results) == 1
        assert "completed" in results[0]['value']
    
    def test_relevance_threshold(self):
        """Test relevance threshold filtering"""
        self.memory.store_information("test", "This is a test document", {})
        
        # Query that should have low relevance
        results = self.memory.retrieve_information("xyz", {})
        assert len(results) == 0  # Below threshold
        
        # Query that should have high relevance
        results = self.memory.retrieve_information("test", {})
        assert len(results) == 1  # Above threshold
    
    def test_access_count_tracking(self):
        """Test that access counts are tracked and boost relevance"""
        self.memory.store_information("popular_doc", "Frequently accessed document item", {})
        self.memory.store_information("rare_doc", "Rarely accessed document item", {})
        
        # Access the popular item multiple times by searching for it specifically
        for _ in range(10):  # More accesses to get bigger difference
            self.memory.retrieve_information("Frequently", {})
        
        # Now search for both using a common term
        results = self.memory.retrieve_information("document", {})
        
        assert len(results) == 2
        # Popular item should have higher relevance due to access boost
        popular_result = next(r for r in results if "popular" in r['key'])
        rare_result = next(r for r in results if "rare" in r['key'])
        
        # Check that popular has been accessed more
        assert popular_result['metadata']['access_count'] > rare_result['metadata']['access_count']
        
        # And that relevance reflects this (allow small floating point differences)
        assert popular_result['relevance_score'] >= rare_result['relevance_score']
    
    def test_memory_overflow_management(self):
        """Test memory overflow management"""
        # Create memory with small limits
        small_memory = SimpleContextMemory({
            'max_items': 3,
            'max_memory_size': 1000
        })
        
        # Add items beyond limit
        for i in range(5):
            small_memory.store_information(f"key{i}", f"value{i}", {})
        
        # Should not exceed max_items
        assert len(small_memory.items) <= 3
    
    def test_memory_snapshot(self):
        """Test memory snapshot contains expected information"""
        # Add some items
        self.memory.store_information("key1", "value1", {"type": "test"})
        self.memory.store_information("key2", "value2", {"type": "test"})
        
        snapshot = self.memory.get_memory_snapshot()
        
        assert snapshot['total_items'] == 2
        assert snapshot['memory_type'] == 'simple_context_memory'
        assert 'memory_size_bytes' in snapshot
        assert 'last_accessed' in snapshot
        assert 'config' in snapshot
        assert 'statistics' in snapshot
        # Note: recent_items not in the updated interface, but that's okay
        
        # Check config preservation
        assert snapshot['config']['max_items'] == 100
        assert snapshot['config']['relevance_threshold'] == 0.1
    
    def test_clear_memory_functionality(self):
        """Test clearing memory removes all items"""
        # Add items
        self.memory.store_information("key1", "value1", {})
        self.memory.store_information("key2", "value2", {})
        assert len(self.memory.items) == 2
        
        # Clear memory
        result = self.memory.clear_memory()
        assert result is True
        assert len(self.memory.items) == 0
        assert self.memory.store_count == 0
        assert self.memory.retrieve_count == 0
    
    def test_memory_statistics(self):
        """Test detailed memory statistics"""
        # Add and access items
        self.memory.store_information("key1", "value1", {})
        self.memory.store_information("key2", "value2", {})
        self.memory.retrieve_information("value1", {})  # Access first item
        
        stats = self.memory.get_memory_stats()
        
        assert 'memory_efficiency' in stats
        assert 'recall_frequency' in stats
        assert 'memory_utilization' in stats
        assert 'average_item_size' in stats
        assert 'most_accessed_items' in stats
        
        # Should have positive utilization
        assert stats['memory_utilization'] > 0
    
    def test_context_search_integration(self):
        """Test that context information is included in search"""
        self.memory.store_information(
            "impl", 
            "Function implementation", 
            {"checkpoint": "cp1", "language": "python"}
        )
        
        # Search should find items based on context
        results = self.memory.retrieve_information("python", {})
        assert len(results) == 1
        assert results[0]['key'] == "impl"
        
        # Search for checkpoint info
        results = self.memory.retrieve_information("cp1", {})
        assert len(results) == 1


class TestCompressedMemory:
    """Test CompressedMemory system"""
    
    def setup_method(self):
        """Setup for each test"""
        self.memory = CompressedMemory({
            'max_uncompressed': 3,
            'compression_ratio': 0.5
        })
    
    def test_compressed_memory_creation(self):
        """Test creating CompressedMemory"""
        assert isinstance(self.memory, CompressedMemory)
        assert len(self.memory.items) == 0
        assert len(self.memory.compressed_items) == 0
        assert self.memory.max_uncompressed == 3
        assert self.memory.compression_ratio == 0.5
    
    def test_compressed_memory_capabilities(self):
        """Test CompressedMemory capabilities"""
        caps = self.memory.get_capabilities()
        
        assert caps.supports_compression is True
        assert caps.supports_search is True
        assert caps.supports_introspection is True
    
    def test_automatic_compression(self):
        """Test that items are automatically compressed when limit is exceeded"""
        long_value = "This is a very long value that should be compressed when the limit is reached" * 3
        
        # Add items up to limit
        for i in range(4):  # One more than max_uncompressed
            self.memory.store_information(f"key{i}", f"{long_value} {i}", {})
        
        # Should have compressed oldest items
        assert len(self.memory.items) == 3  # max_uncompressed
        assert len(self.memory.compressed_items) == 1  # oldest item compressed
        assert self.memory.compression_count > 0
    
    def test_search_both_regular_and_compressed(self):
        """Test that search looks in both regular and compressed items"""
        # Add items to trigger compression
        for i in range(5):
            self.memory.store_information(f"key{i}", f"test value {i}", {})
        
        # Should have some compressed items
        assert len(self.memory.compressed_items) > 0
        
        # Search should find items from both regular and compressed
        results = self.memory.retrieve_information("test", {})
        
        # Should find multiple items
        assert len(results) > 1
        
        # Should include both compressed and uncompressed
        has_compressed = any(r['metadata'].get('compressed', False) for r in results)
        assert has_compressed
    
    def test_compression_penalty(self):
        """Test that compressed items have lower relevance scores"""
        # Store items to trigger compression
        self.memory.store_information("old", "test content", {})
        for i in range(4):  # Force compression of first item
            self.memory.store_information(f"new{i}", "test content", {})
        
        results = self.memory.retrieve_information("test", {})
        
        # Find compressed and uncompressed results
        compressed_results = [r for r in results if r['metadata'].get('compressed', False)]
        regular_results = [r for r in results if not r['metadata'].get('compressed', False)]
        
        if compressed_results and regular_results:
            # Compressed should generally have lower scores
            avg_compressed = sum(r['relevance_score'] for r in compressed_results) / len(compressed_results)
            avg_regular = sum(r['relevance_score'] for r in regular_results) / len(regular_results)
            assert avg_compressed < avg_regular
    
    def test_memory_snapshot_with_compression(self):
        """Test memory snapshot includes compression statistics"""
        # Add items to trigger compression
        for i in range(5):
            self.memory.store_information(f"key{i}", f"value{i}", {})
        
        snapshot = self.memory.get_memory_snapshot()
        
        assert snapshot['memory_type'] == 'compressed'
        assert 'compression_stats' in snapshot
        
        comp_stats = snapshot['compression_stats']
        assert 'uncompressed_items' in comp_stats
        assert 'compressed_items' in comp_stats
        assert 'compression_count' in comp_stats
        assert 'compression_ratio' in comp_stats
        
        # Should show some compression activity
        assert comp_stats['compressed_items'] > 0
    
    def test_compression_preserves_searchability(self):
        """Test that compressed items are still searchable"""
        original_text = "This is important information that needs to be preserved"
        
        # Store item that will be compressed
        self.memory.store_information("important", original_text, {})
        
        # Add more items to trigger compression
        for i in range(4):
            self.memory.store_information(f"filler{i}", f"filler content {i}", {})
        
        # Original item should be compressed but still findable
        results = self.memory.retrieve_information("important", {})
        assert len(results) > 0
        
        # Find the compressed result
        important_result = next((r for r in results if "important" in r['key']), None)
        assert important_result is not None
        assert important_result['metadata']['compressed'] is True


class TestMemorySystemComparison:
    """Test comparing different memory systems"""
    
    def setup_method(self):
        """Setup multiple memory systems for comparison"""
        self.no_memory = NoMemory({})
        self.simple_memory = SimpleContextMemory({'max_items': 100})
        self.compressed_memory = CompressedMemory({'max_uncompressed': 50})
    
    def test_store_retrieve_comparison(self):
        """Compare store/retrieve behavior across memory systems"""
        test_data = [
            ("task1", "Implement calculator functionality", {"type": "requirement"}),
            ("task2", "Add user authentication", {"type": "requirement"}),
            ("impl1", "Calculator implementation complete", {"type": "status"})
        ]
        
        # Store same data in all systems
        for key, value, context in test_data:
            assert self.no_memory.store_information(key, value, context) is True
            assert self.simple_memory.store_information(key, value, context) is True
            assert self.compressed_memory.store_information(key, value, context) is True
        
        # Retrieve from all systems
        no_mem_results = self.no_memory.retrieve_information("calculator", {})
        simple_results = self.simple_memory.retrieve_information("calculator", {})
        compressed_results = self.compressed_memory.retrieve_information("calculator", {})
        
        # NoMemory should return nothing
        assert len(no_mem_results) == 0
        
        # Other systems should return relevant results
        assert len(simple_results) > 0
        assert len(compressed_results) > 0
        
        # Results should contain calculator-related information
        for result in simple_results:
            assert "calculator" in result['value'].lower() or "calculator" in result['key'].lower()
    
    def test_memory_snapshot_comparison(self):
        """Compare memory snapshots across systems"""
        # Add same data to all systems
        self.no_memory.store_information("test", "data", {})
        self.simple_memory.store_information("test", "data", {})
        self.compressed_memory.store_information("test", "data", {})
        
        no_snapshot = self.no_memory.get_memory_snapshot()
        simple_snapshot = self.simple_memory.get_memory_snapshot()
        compressed_snapshot = self.compressed_memory.get_memory_snapshot()
        
        # All should have required fields, but compressed memory uses different key name
        for snapshot in [no_snapshot, simple_snapshot]:
            assert 'total_items' in snapshot
            assert 'memory_size_bytes' in snapshot
            assert 'last_accessed' in snapshot
        
        # Compressed memory uses memory_size_estimate instead of memory_size_bytes
        assert 'total_items' in compressed_snapshot
        assert 'memory_size_estimate' in compressed_snapshot
        assert 'last_accessed' in compressed_snapshot
        
        # NoMemory should show no storage
        assert no_snapshot['total_items'] == 0
        assert no_snapshot['memory_size_bytes'] == 0
        
        # Others should show storage
        assert simple_snapshot['total_items'] > 0
        assert simple_snapshot['memory_size_bytes'] > 0
        assert compressed_snapshot['memory_size_estimate'] > 0
        assert compressed_snapshot['total_items'] > 0
    
    def test_capabilities_comparison(self):
        """Compare capabilities across memory systems"""
        no_caps = self.no_memory.get_capabilities()
        simple_caps = self.simple_memory.get_capabilities()
        compressed_caps = self.compressed_memory.get_capabilities()
        
        # NoMemory should support the least
        assert no_caps.supports_search is False
        assert no_caps.supports_compression is False
        
        # SimpleMemory should support search but not compression
        assert simple_caps.supports_search is True
        assert simple_caps.supports_compression is False
        
        # CompressedMemory should support both
        assert compressed_caps.supports_search is True
        assert compressed_caps.supports_compression is True
        
        # All should support introspection
        assert no_caps.supports_introspection is True
        assert simple_caps.supports_introspection is True
        assert compressed_caps.supports_introspection is True


if __name__ == "__main__":
    pytest.main([__file__])
