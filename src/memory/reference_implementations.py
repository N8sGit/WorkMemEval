"""
WorkMemEval: Reference Memory System Implementations

This module provides example implementations of the MemorySystem interface
to demonstrate how researchers can build their own memory systems.
"""

import time
from typing import Dict, Any, List
from .memory_system import MemorySystem, PluginCapabilities, MemorySystemFactory


class ExampleKeyValueMemory(MemorySystem):
    """
    Example implementation showing how to create a simple memory system.
    
    This is just a reference - real implementations would be much more sophisticated.
    Users should create their own memory systems inheriting from MemorySystem.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._storage = {}  # Simple dict storage
        self._metadata = {}  # Metadata for each stored item
        self.last_accessed = time.time()
        
    def get_capabilities(self) -> PluginCapabilities:
        """This simple system supports basic operations"""
        return PluginCapabilities(
            supports_search=True,
            supports_introspection=True,
            supports_forgetting=True
        )
    
    def store_information(self, key: str, value: Any, context: Dict[str, Any]) -> bool:
        """Store in simple dictionary"""
        try:
            self._storage[key] = value
            self._metadata[key] = {
                'stored_at': time.time(),
                'context': context,
                'access_count': 0
            }
            return True
        except Exception:
            return False
    
    def retrieve_information(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Simple substring search"""
        results = []
        
        for key, value in self._storage.items():
            # Naive search - check if query appears in key or value
            searchable_text = f"{key} {str(value)}".lower()
            if query.lower() in searchable_text:
                self._metadata[key]['access_count'] += 1
                results.append({
                    'key': key,
                    'value': value,
                    'relevance_score': 0.5,  # Naive scoring
                    'metadata': self._metadata[key].copy()
                })
        
        return results
    
    def get_memory_snapshot(self) -> Dict[str, Any]:
        """Simple snapshot of storage state"""
        return {
            'total_items': len(self._storage),
            'memory_size_bytes': len(str(self._storage)),
            'last_accessed': self.last_accessed,
            'memory_type': 'example_key_value',
            'sample_keys': list(self._storage.keys())[:5],  # Don't expose all data
            'capabilities': self.get_capabilities().__dict__
        }
    
    def clear_memory(self) -> bool:
        """Clear all storage"""
        self._storage.clear()
        self._metadata.clear()
        return True
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get basic statistics"""
        if not self._storage:
            return {
                'total_items': 0,
                'average_access_count': 0.0,
                'memory_utilization': 0.0
            }
        
        total_accesses = sum(meta['access_count'] for meta in self._metadata.values())
        
        return {
            'total_items': len(self._storage),
            'average_access_count': total_accesses / len(self._storage),
            'memory_utilization': len(str(self._storage)) / 10000,  # Arbitrary scale
            'most_accessed': max(self._metadata.items(), key=lambda x: x[1]['access_count'])[0]
                             if self._metadata else None
        }
    
    def forget_information(self, criteria: Dict[str, Any]) -> int:
        """Example of selective forgetting"""
        keys_to_remove = []
        
        # Simple criteria matching
        if 'older_than' in criteria:
            cutoff_time = criteria['older_than']
            for key, metadata in self._metadata.items():
                if metadata['stored_at'] < cutoff_time:
                    keys_to_remove.append(key)
        
        # Remove matched items
        for key in keys_to_remove:
            del self._storage[key]
            del self._metadata[key]
        
        return len(keys_to_remove)


class SimpleContextMemory(MemorySystem):
    """
    Improved version of the original SimpleContextMemory with better interface compliance.
    
    Uses basic list-based storage with naive keyword matching for retrieval.
    Demonstrates how to migrate existing memory systems to the new interface.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.items = []
        self.last_accessed = time.time()
        
        # Configuration
        self.max_items = config.get('max_items', 1000)
        self.max_memory_size = config.get('max_memory_size', 100000)  # chars
        self.relevance_threshold = config.get('relevance_threshold', 0.1)
        
        # Statistics
        self.store_count = 0
        self.retrieve_count = 0
        
    def get_capabilities(self) -> PluginCapabilities:
        """Return capabilities - basic search and introspection"""
        return PluginCapabilities(
            supports_search=True,
            supports_introspection=True,
            supports_forgetting=True
        )
    
    def store_information(self, key: str, value: Any, context: Dict[str, Any]) -> bool:
        """Store information with simple overflow management"""
        try:
            self.last_accessed = time.time()
            self.store_count += 1
            
            # Create memory item
            memory_item = {
                'key': key,
                'value': value,
                'context': context,
                'timestamp': time.time(),
                'access_count': 0
            }
            
            # Check for existing key and update
            for i, item in enumerate(self.items):
                if item['key'] == key:
                    self.items[i] = memory_item
                    return True
            
            # Add new item
            self.items.append(memory_item)
            
            # Simple overflow management - remove oldest items if needed
            self._manage_memory_overflow()
            
            return True
            
        except Exception:
            return False
    
    def retrieve_information(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Retrieve information using naive keyword matching"""
        self.last_accessed = time.time()
        self.retrieve_count += 1
        
        if not query or not self.items:
            return []
        
        results = []
        query_lower = query.lower()
        
        for item in self.items:
            # Simple keyword matching
            relevance_score = self._calculate_relevance(query_lower, item)
            
            if relevance_score > self.relevance_threshold:
                # Only increment access count for items that meet threshold
                item['access_count'] += 1
                
                results.append({
                    'key': item['key'],
                    'value': item['value'],
                    'relevance_score': relevance_score,
                    'metadata': {
                        'timestamp': item['timestamp'],
                        'access_count': item['access_count'],
                        'context': item['context']
                    }
                })
        
        # Sort by relevance score (highest first)
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Limit results to prevent overwhelming the agent
        max_results = context.get('max_results', 10)
        return results[:max_results]
    
    def get_memory_snapshot(self) -> Dict[str, Any]:
        """Get current memory state snapshot"""
        total_size = sum(len(str(item)) for item in self.items)
        
        return {
            'total_items': len(self.items),
            'memory_size_bytes': total_size,
            'last_accessed': self.last_accessed,
            'memory_type': 'simple_context_memory',
            'capabilities': self.get_capabilities().__dict__,
            'config': {
                'max_items': self.max_items,
                'max_memory_size': self.max_memory_size,
                'relevance_threshold': self.relevance_threshold
            },
            'statistics': {
                'store_count': self.store_count,
                'retrieve_count': self.retrieve_count,
                'avg_access_count': self._calculate_avg_access_count()
            }
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
                'memory_efficiency': 0.0,
                'recall_frequency': 0.0,
                'memory_utilization': 0.0
            }
        
        total_accesses = sum(item['access_count'] for item in self.items)
        total_size = sum(len(str(item)) for item in self.items)
        
        return {
            'memory_efficiency': total_accesses / len(self.items) if self.items else 0.0,
            'recall_frequency': self.retrieve_count / max(1, self.store_count),
            'memory_utilization': total_size / self.max_memory_size,
            'average_item_size': total_size / len(self.items) if self.items else 0,
            'most_accessed_items': self._get_most_accessed_items(5)
        }
    
    def forget_information(self, criteria: Dict[str, Any]) -> int:
        """Forget items based on criteria"""
        initial_count = len(self.items)
        
        if 'older_than' in criteria:
            cutoff_time = criteria['older_than']
            self.items = [item for item in self.items if item['timestamp'] >= cutoff_time]
        
        if 'least_accessed' in criteria:
            min_access_count = criteria['least_accessed']
            self.items = [item for item in self.items if item['access_count'] >= min_access_count]
        
        return initial_count - len(self.items)
    
    def _calculate_relevance(self, query: str, item: Dict[str, Any]) -> float:
        """Calculate naive relevance score based on keyword matching"""
        # Convert item value and context to searchable text
        searchable_text = ""
        
        # Add value text
        if isinstance(item['value'], str):
            searchable_text += item['value'].lower()
        else:
            searchable_text += str(item['value']).lower()
        
        # Add context text
        if item['context']:
            for key, value in item['context'].items():
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
        
        # Access count boost
        access_boost = min(item['access_count'] * 0.05, 0.4)
        
        # Time decay - more recent items get slight boost
        time_since_store = time.time() - item['timestamp']
        time_boost = max(0, (3600 - time_since_store) / 3600 * 0.05)  # 1 hour decay
        
        return min(1.0, base_relevance + access_boost + time_boost)
    
    def _manage_memory_overflow(self):
        """Simple memory overflow management"""
        # Remove oldest items if over max_items
        while len(self.items) > self.max_items:
            # Remove least recently stored item
            oldest_idx = min(range(len(self.items)), key=lambda i: self.items[i]['timestamp'])
            self.items.pop(oldest_idx)
        
        # Remove items if over memory size limit
        while self._calculate_memory_size() > self.max_memory_size and self.items:
            # Remove least accessed item
            least_accessed_idx = min(range(len(self.items)), key=lambda i: self.items[i]['access_count'])
            self.items.pop(least_accessed_idx)
    
    def _calculate_memory_size(self) -> int:
        """Calculate approximate memory usage in characters"""
        return sum(len(str(item)) for item in self.items)
    
    def _calculate_avg_access_count(self) -> float:
        """Calculate average access count across all items"""
        if not self.items:
            return 0.0
        return sum(item['access_count'] for item in self.items) / len(self.items)
    
    def _get_most_accessed_items(self, count: int) -> List[Dict[str, Any]]:
        """Get most frequently accessed items"""
        if not self.items:
            return []
        
        sorted_items = sorted(self.items, key=lambda x: x['access_count'], reverse=True)
        
        return [
            {
                'key': item['key'],
                'access_count': item['access_count'],
                'timestamp': item['timestamp']
            }
            for item in sorted_items[:count]
        ]


# Register the reference implementations with the factory
MemorySystemFactory.register_memory_system('example_kv', ExampleKeyValueMemory)
MemorySystemFactory.register_memory_system('simple_context', SimpleContextMemory)
