"""
WorkMemEval: Context Memory Systems

Context-based memory system implementations for comparison and testing.
These provide reference implementations of the MemorySystem interface
with different memory management strategies.
"""

import time
from typing import Any, Dict, List

from .memory_system import MemorySystem, PluginCapabilities


class NoMemory(MemorySystem):
    """
    No-memory baseline system.

    Discards all information immediately and never recalls anything.
    Useful as a baseline to measure the impact of memory systems
    on agent performance.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_count = 0
        self.last_accessed = time.time()

    def get_capabilities(self) -> PluginCapabilities:
        """Return capabilities - no optional features supported"""
        return PluginCapabilities(
            supports_embeddings=False,
            supports_persistence=False,
            supports_compression=False,
            supports_search=False,
            supports_introspection=True,  # We can report that we have no memory
        )

    def store_information(self, key: str, value: Any, context: Dict[str, Any]) -> bool:
        """Pretend to store but actually discard everything"""
        self.last_accessed = time.time()
        self.access_count += 1
        # Always report success, but don't actually store anything
        return True

    def retrieve_information(
        self, query: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Never recall anything"""
        self.last_accessed = time.time()
        self.access_count += 1
        # Always return empty results
        return []

    def get_memory_snapshot(self) -> Dict[str, Any]:
        """Return snapshot showing no memory"""
        return {
            "total_items": 0,
            "memory_size_estimate": 0,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "memory_type": "no_memory",
        }

    def clear_memory(self) -> bool:
        """Nothing to clear"""
        return True

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "total_stores": self.access_count,
            "total_retrievals": self.access_count,
            "memory_efficiency": 0.0,  # No memory = no efficiency
            "recall_accuracy": 0.0,  # Never recalls anything
        }


class ContextMemorySystem(MemorySystem):
    """
    Context-based memory system.

    Uses list-based storage with keyword matching for retrieval.
    Provides a practical baseline for memory-guided agent evaluation.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.items = []
        self.last_accessed = time.time()

        # Configuration
        self.max_items = config.get("max_items", 1000)
        self.max_memory_size = config.get("max_memory_size", 100000)  # chars
        self.relevance_threshold = config.get("relevance_threshold", 0.1)

        # Statistics
        self.store_count = 0
        self.retrieve_count = 0

    def get_capabilities(self) -> PluginCapabilities:
        """Return capabilities - basic search and introspection"""
        return PluginCapabilities(
            supports_embeddings=False,
            supports_persistence=False,
            supports_compression=False,
            supports_search=True,  # Basic keyword search
            supports_introspection=True,
        )

    def store_information(self, key: str, value: Any, context: Dict[str, Any]) -> bool:
        """Store information with simple overflow management"""
        try:
            self.last_accessed = time.time()
            self.store_count += 1

            # Create memory item
            memory_item = {
                "key": key,
                "value": value,
                "context": context,
                "timestamp": time.time(),
                "access_count": 0,
            }

            # Check for existing key and update
            for i, item in enumerate(self.items):
                if item["key"] == key:
                    self.items[i] = memory_item
                    return True

            # Add new item
            self.items.append(memory_item)

            # Simple overflow management - remove oldest items if needed
            self._manage_memory_overflow()

            return True

        except Exception:
            return False

    def retrieve_information(
        self, query: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Retrieve information using naive keyword matching"""
        self.last_accessed = time.time()
        self.retrieve_count += 1

        if not query or not self.items:
            return []

        results = []
        query_lower = query.lower()

        for item in self.items:
            # Simple keyword matching (before incrementing access count)
            relevance_score = self._calculate_relevance(query_lower, item)

            if relevance_score > self.relevance_threshold:
                # Only increment access count for items that meet threshold
                item["access_count"] += 1

                results.append(
                    {
                        "key": item["key"],
                        "value": item["value"],
                        "relevance_score": relevance_score,
                        "metadata": {
                            "timestamp": item["timestamp"],
                            "access_count": item["access_count"],
                            "context": item["context"],
                        },
                    }
                )

        # Sort by relevance score (highest first)
        results.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Limit results to prevent overwhelming the agent
        max_results = context.get("max_results", 10)
        return results[:max_results]

    def get_memory_snapshot(self) -> Dict[str, Any]:
        """Get current memory state snapshot"""
        total_size = sum(len(str(item)) for item in self.items)

        return {
            "total_items": len(self.items),
            "memory_size_estimate": total_size,
            "last_accessed": self.last_accessed,
            "memory_type": "simple_context",
            "config": {
                "max_items": self.max_items,
                "max_memory_size": self.max_memory_size,
                "relevance_threshold": self.relevance_threshold,
            },
            "statistics": {
                "store_count": self.store_count,
                "retrieve_count": self.retrieve_count,
                "avg_access_count": self._calculate_avg_access_count(),
            },
            "recent_items": [
                {
                    "key": item["key"],
                    "timestamp": item["timestamp"],
                    "access_count": item["access_count"],
                }
                for item in self.items[-5:]  # Last 5 items
            ],
        }

    def clear_memory(self) -> bool:
        """Clear all stored information"""
        self.items.clear()
        self.store_count = 0
        self.retrieve_count = 0
        return True

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get detailed memory statistics"""
        if not self.items:
            return {
                "memory_efficiency": 0.0,
                "recall_frequency": 0.0,
                "memory_utilization": 0.0,
            }

        total_accesses = sum(item["access_count"] for item in self.items)
        total_size = sum(len(str(item)) for item in self.items)

        return {
            "memory_efficiency": total_accesses / len(self.items)
            if self.items
            else 0.0,
            "recall_frequency": self.retrieve_count / max(1, self.store_count),
            "memory_utilization": total_size / self.max_memory_size,
            "average_item_size": total_size / len(self.items) if self.items else 0,
            "most_accessed_items": self._get_most_accessed_items(5),
        }

    def _calculate_relevance(self, query: str, item: Dict[str, Any]) -> float:
        """Calculate naive relevance score based on keyword matching"""
        # Convert item value and context to searchable text
        searchable_text = ""

        # Add value text
        if isinstance(item["value"], str):
            searchable_text += item["value"].lower()
        else:
            searchable_text += str(item["value"]).lower()

        # Add context text
        if item["context"]:
            for key, value in item["context"].items():
                searchable_text += f" {key} {str(value)}".lower()

        # Count keyword matches
        query_words = query.split()
        matches = 0
        total_words = len(query_words)

        if total_words == 0:
            return 0.0

        for word in query_words:
            if word in searchable_text:
                matches += 1

        # Base relevance on match ratio (cap at 0.8 to leave room for boosts)
        base_relevance = min(0.8, matches / total_words)

        # More significant boost for access count
        access_boost = min(item["access_count"] * 0.05, 0.4)

        # Time decay - more recent items get slight boost
        time_since_store = time.time() - item["timestamp"]
        time_boost = max(0, (3600 - time_since_store) / 3600 * 0.05)  # 1 hour decay

        return min(1.0, base_relevance + access_boost + time_boost)

    def _manage_memory_overflow(self):
        """Simple memory overflow management"""
        # Remove oldest items if over max_items
        while len(self.items) > self.max_items:
            # Remove least recently stored item
            oldest_idx = min(
                range(len(self.items)), key=lambda i: self.items[i]["timestamp"]
            )
            self.items.pop(oldest_idx)

        # Remove items if over memory size limit
        while self._calculate_memory_size() > self.max_memory_size and self.items:
            # Remove least accessed item
            least_accessed_idx = min(
                range(len(self.items)), key=lambda i: self.items[i]["access_count"]
            )
            self.items.pop(least_accessed_idx)

    def _calculate_memory_size(self) -> int:
        """Calculate approximate memory usage in characters"""
        return sum(len(str(item)) for item in self.items)

    def _calculate_avg_access_count(self) -> float:
        """Calculate average access count across all items"""
        if not self.items:
            return 0.0
        return sum(item["access_count"] for item in self.items) / len(self.items)

    def _get_most_accessed_items(self, count: int) -> List[Dict[str, Any]]:
        """Get most frequently accessed items"""
        if not self.items:
            return []

        sorted_items = sorted(self.items, key=lambda x: x["access_count"], reverse=True)

        return [
            {
                "key": item["key"],
                "access_count": item["access_count"],
                "timestamp": item["timestamp"],
            }
            for item in sorted_items[:count]
        ]


class CompressedMemory(MemorySystem):
    """
    Simple memory compression system.

    Demonstrates basic memory compression by storing summarized versions
    of information after a certain threshold. This is a stepping stone
    toward more sophisticated memory management.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.items = []
        self.compressed_items = []
        self.last_accessed = time.time()

        # Configuration
        self.max_uncompressed = config.get("max_uncompressed", 100)
        self.compression_ratio = config.get(
            "compression_ratio", 0.3
        )  # 30% of original size

        # Statistics
        self.compression_count = 0
        self.store_count = 0
        self.retrieve_count = 0

    def get_capabilities(self) -> PluginCapabilities:
        """Return capabilities - supports basic compression"""
        return PluginCapabilities(
            supports_embeddings=False,
            supports_persistence=False,
            supports_compression=True,
            supports_search=True,
            supports_introspection=True,
        )

    def store_information(self, key: str, value: Any, context: Dict[str, Any]) -> bool:
        """Store information with automatic compression"""
        try:
            self.last_accessed = time.time()
            self.store_count += 1

            memory_item = {
                "key": key,
                "value": value,
                "context": context,
                "timestamp": time.time(),
                "access_count": 0,
            }

            self.items.append(memory_item)

            # Trigger compression if needed
            if len(self.items) > self.max_uncompressed:
                self._compress_oldest_items()

            return True

        except Exception:
            return False

    def retrieve_information(
        self, query: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Retrieve from both regular and compressed memory"""
        self.last_accessed = time.time()
        self.retrieve_count += 1

        results = []

        # Search regular items
        results.extend(self._search_items(query, self.items, compressed=False))

        # Search compressed items (with lower relevance)
        compressed_results = self._search_items(
            query, self.compressed_items, compressed=True
        )
        for result in compressed_results:
            result["relevance_score"] *= 0.7  # Penalty for compressed items
        results.extend(compressed_results)

        # Sort and limit results
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:10]

    def get_memory_snapshot(self) -> Dict[str, Any]:
        """Get memory snapshot including compression stats"""
        return {
            "total_items": len(self.items) + len(self.compressed_items),
            "memory_size_estimate": self._calculate_total_size(),
            "last_accessed": self.last_accessed,
            "memory_type": "compressed",
            "compression_stats": {
                "uncompressed_items": len(self.items),
                "compressed_items": len(self.compressed_items),
                "compression_count": self.compression_count,
                "compression_ratio": self.compression_ratio,
            },
        }

    def _compress_oldest_items(self):
        """Compress oldest items to make space"""
        if len(self.items) <= self.max_uncompressed:
            return

        # Sort by timestamp and compress oldest
        self.items.sort(key=lambda x: x["timestamp"])
        items_to_compress = self.items[: len(self.items) - self.max_uncompressed]
        self.items = self.items[len(self.items) - self.max_uncompressed :]

        for item in items_to_compress:
            compressed = self._compress_item(item)
            self.compressed_items.append(compressed)

        self.compression_count += len(items_to_compress)

    def _compress_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Simple compression - truncate value to specified ratio"""
        value_str = str(item["value"])
        target_length = int(len(value_str) * self.compression_ratio)

        # Simple truncation with ellipsis
        if target_length < len(value_str):
            compressed_value = value_str[:target_length] + "..."
        else:
            compressed_value = value_str

        return {
            "key": item["key"],
            "value": compressed_value,
            "context": item["context"],
            "timestamp": item["timestamp"],
            "access_count": item["access_count"],
            "compressed": True,
            "original_size": len(value_str),
            "compressed_size": len(compressed_value),
        }

    def _search_items(
        self, query: str, items: List[Dict[str, Any]], compressed: bool
    ) -> List[Dict[str, Any]]:
        """Search items with basic keyword matching"""
        results = []
        query_lower = query.lower()

        for item in items:
            if query_lower in str(item["value"]).lower():
                results.append(
                    {
                        "key": item["key"],
                        "value": item["value"],
                        "relevance_score": 0.8 if not compressed else 0.5,
                        "metadata": {
                            "compressed": compressed,
                            "timestamp": item["timestamp"],
                            "access_count": item["access_count"],
                        },
                    }
                )

        return results

    def _calculate_total_size(self) -> int:
        """Calculate total memory usage"""
        regular_size = sum(len(str(item)) for item in self.items)
        compressed_size = sum(len(str(item)) for item in self.compressed_items)
        return regular_size + compressed_size
