"""
WorkMemEval: Context Window Management

This module provides context window management capabilities for enhanced evaluation,
including standardized, native, and overflow conditions.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from ..core.plugin_interfaces import AgentImplementation, MemorySystem
from ..core.task_specification import CheckpointSpecification, ContextConditionType, ContextWindowCondition
from ..core.action_trace import ActionTracer, ActionType


class ContextState(Enum):
    """Current state of context window usage"""
    NORMAL = "normal"
    APPROACHING_LIMIT = "approaching_limit"
    OVERFLOW = "overflow"
    COMPRESSED = "compressed"


@dataclass
class ContextUsageMetrics:
    """Metrics for context window usage analysis"""
    current_tokens: int
    token_limit: int
    utilization_percentage: float
    relevant_tokens: int
    irrelevant_tokens: int
    redundant_tokens: int
    efficiency_score: float
    state: ContextState


@dataclass
class ContextEfficiencyMetrics:
    """Context efficiency analysis results"""
    relevance_precision: float  # Percentage of context that's task-relevant
    information_density: float  # Task-relevant information per token
    redundancy_rate: float     # Repeated information access patterns
    compression_effectiveness: float  # Information retention after compression


class ContextWindowManager:
    """
    Manages context window conditions and monitoring for enhanced evaluation.
    
    Provides three evaluation conditions:
    - Standardized: Fixed context window for fair comparison
    - Native: Agent's natural context capacity
    - Overflow: Forced context overflow to stress memory systems
    """
    
    def __init__(self):
        self.current_condition: Optional[ContextWindowCondition] = None
        self.context_history: List[ContextUsageMetrics] = []
        self.compression_events: List[Dict[str, Any]] = []
        self.native_capacity_cache: Dict[str, int] = {}
        
    def configure_condition(self, condition: str, agent: Optional[AgentImplementation] = None):
        """
        Configure the context window condition for evaluation.
        
        Args:
            condition: Condition name ("standardized", "native", "overflow")
            agent: Agent implementation for native capacity detection
        """
        if condition == "standardized":
            self.current_condition = ContextWindowCondition(
                condition_name="standardized",
                condition_type=ContextConditionType.STANDARDIZED,
                token_limit=8192,
                description="Standardized 8K context window for fair comparison"
            )
        elif condition == "native" and agent:
            native_capacity = self.detect_native_capacity(agent)
            self.current_condition = ContextWindowCondition(
                condition_name="native",
                condition_type=ContextConditionType.NATIVE,
                token_limit=native_capacity,
                description=f"Agent's native context capacity ({native_capacity} tokens)"
            )
        elif condition == "overflow" and agent:
            native_capacity = self.detect_native_capacity(agent)
            overflow_limit = int(native_capacity * 2.0)  # 2x native capacity
            self.current_condition = ContextWindowCondition(
                condition_name="overflow",
                condition_type=ContextConditionType.OVERFLOW,
                token_limit=overflow_limit,
                overflow_multiplier=2.0,
                description=f"Forced overflow condition ({overflow_limit} tokens, 2x native)"
            )
        else:
            raise ValueError(f"Invalid condition '{condition}' or missing agent for capacity detection")
        
        print(f"Context window condition configured: {self.current_condition.condition_name} "
              f"({self.current_condition.token_limit} tokens)")
    
    def detect_native_capacity(self, agent: AgentImplementation) -> int:
        """
        Detect the agent's native context window capacity.
        
        Args:
            agent: Agent implementation to analyze
            
        Returns:
            Native context window capacity in tokens
        """
        agent_class = agent.__class__.__name__
        
        # Check cache first
        if agent_class in self.native_capacity_cache:
            return self.native_capacity_cache[agent_class]
        
        # Try to detect from agent configuration
        native_capacity = 8192  # Default fallback
        
        if hasattr(agent, 'context_window_size'):
            native_capacity = agent.context_window_size
        elif hasattr(agent, 'max_tokens'):
            native_capacity = agent.max_tokens
        elif hasattr(agent, 'model_config'):
            # Try to extract from model configuration
            config = getattr(agent, 'model_config', {})
            native_capacity = config.get('context_window', config.get('max_tokens', 8192))
        
        # Cache the result
        self.native_capacity_cache[agent_class] = native_capacity
        return native_capacity
    
    def monitor_context_usage(self, agent: AgentImplementation, 
                            checkpoint: Optional[CheckpointSpecification] = None) -> ContextUsageMetrics:
        """
        Monitor current context window usage and calculate efficiency metrics.
        
        Args:
            agent: Agent implementation being monitored
            checkpoint: Current checkpoint for relevance analysis
            
        Returns:
            Context usage metrics
        """
        if not self.current_condition:
            raise ValueError("Context condition not configured")
        
        # Estimate current context usage
        current_tokens = self._estimate_context_tokens(agent)
        token_limit = self.current_condition.token_limit
        utilization = (current_tokens / token_limit) * 100 if token_limit > 0 else 0
        
        # Analyze context relevance if checkpoint provided
        relevant_tokens = current_tokens  # Default: assume all relevant
        irrelevant_tokens = 0
        redundant_tokens = 0
        
        if checkpoint:
            relevance_analysis = self._analyze_context_relevance(agent, checkpoint)
            relevant_tokens = relevance_analysis['relevant_tokens']
            irrelevant_tokens = relevance_analysis['irrelevant_tokens']
            redundant_tokens = relevance_analysis['redundant_tokens']
        
        # Calculate efficiency score
        efficiency_score = self._calculate_efficiency_score(
            relevant_tokens, irrelevant_tokens, redundant_tokens, current_tokens
        )
        
        # Determine context state
        state = self._determine_context_state(utilization, self.current_condition.condition_type)
        
        metrics = ContextUsageMetrics(
            current_tokens=current_tokens,
            token_limit=token_limit,
            utilization_percentage=utilization,
            relevant_tokens=relevant_tokens,
            irrelevant_tokens=irrelevant_tokens,
            redundant_tokens=redundant_tokens,
            efficiency_score=efficiency_score,
            state=state
        )
        
        # Store in history
        self.context_history.append(metrics)
        
        return metrics
    
    def _estimate_context_tokens(self, agent: AgentImplementation) -> int:
        """
        Estimate current context window token usage.
        
        This is a simplified estimation. In a full implementation,
        this would integrate with the agent's actual context tracking.
        """
        # Try to get actual context from agent
        if hasattr(agent, 'get_context_size'):
            return agent.get_context_size()
        elif hasattr(agent, 'current_context_tokens'):
            return agent.current_context_tokens
        
        # Fallback: estimate based on action trace
        if hasattr(agent, 'action_tracer') and agent.action_tracer:
            trace = agent.get_behavioral_trace()
            if trace and trace.checkpoints:
                # Rough estimation: 100 tokens per action + 500 per checkpoint
                total_actions = sum(len(cp.actions) for cp in trace.checkpoints.values())
                return (total_actions * 100) + (len(trace.checkpoints) * 500)
        
        # Very rough fallback
        return 2000
    
    def _analyze_context_relevance(self, agent: AgentImplementation, 
                                 checkpoint: CheckpointSpecification) -> Dict[str, int]:
        """
        Analyze the relevance of current context content.
        
        This is a simplified analysis. Full implementation would use
        sophisticated relevance calculation algorithms.
        """
        current_tokens = self._estimate_context_tokens(agent)
        
        # Simplified relevance analysis
        # In practice, this would analyze actual context content
        relevant_ratio = 0.7  # Assume 70% relevant by default
        redundant_ratio = 0.1  # Assume 10% redundant
        
        relevant_tokens = int(current_tokens * relevant_ratio)
        redundant_tokens = int(current_tokens * redundant_ratio)
        irrelevant_tokens = current_tokens - relevant_tokens - redundant_tokens
        
        return {
            'relevant_tokens': relevant_tokens,
            'irrelevant_tokens': irrelevant_tokens,
            'redundant_tokens': redundant_tokens
        }
    
    def _calculate_efficiency_score(self, relevant: int, irrelevant: int, 
                                  redundant: int, total: int) -> float:
        """Calculate context efficiency score (0.0 to 1.0)"""
        if total == 0:
            return 1.0
        
        # Efficiency = (relevant tokens) / (total tokens) - penalty for redundancy
        base_efficiency = relevant / total
        redundancy_penalty = (redundant / total) * 0.5  # 50% penalty for redundancy
        
        return max(0.0, base_efficiency - redundancy_penalty)
    
    def _determine_context_state(self, utilization: float, 
                               condition_type: ContextConditionType) -> ContextState:
        """Determine current context state based on utilization"""
        if utilization < 70:
            return ContextState.NORMAL
        elif utilization < 90:
            return ContextState.APPROACHING_LIMIT
        elif condition_type == ContextConditionType.OVERFLOW:
            return ContextState.OVERFLOW
        else:
            return ContextState.OVERFLOW
    
    def trigger_compression_event(self, agent: AgentImplementation, 
                                memory_system: MemorySystem,
                                action_tracer: Optional[ActionTracer] = None) -> Dict[str, Any]:
        """
        Trigger a context compression event when limits are reached.
        
        Args:
            agent: Agent implementation
            memory_system: Memory system to handle compression
            action_tracer: Optional action tracer for logging
            
        Returns:
            Compression event results
        """
        compression_start = time.time()
        
        # Capture pre-compression state
        pre_compression_metrics = self.monitor_context_usage(agent)
        
        # Log compression start
        if action_tracer:
            action_tracer.log_action(
                ActionType.MEMORY_COMPRESSION,
                success=True,
                pre_compression_tokens=pre_compression_metrics.current_tokens,
                compression_trigger="context_overflow"
            )
        
        # Perform compression (delegate to memory system)
        compression_result = {"success": True, "compression_ratio": 0.5}
        if hasattr(memory_system, 'compress_context'):
            compression_result = memory_system.compress_context()
        
        # Capture post-compression state
        post_compression_metrics = self.monitor_context_usage(agent)
        
        # Calculate compression effectiveness
        token_reduction = pre_compression_metrics.current_tokens - post_compression_metrics.current_tokens
        compression_ratio = token_reduction / pre_compression_metrics.current_tokens if pre_compression_metrics.current_tokens > 0 else 0
        
        compression_event = {
            "timestamp": compression_start,
            "pre_compression_tokens": pre_compression_metrics.current_tokens,
            "post_compression_tokens": post_compression_metrics.current_tokens,
            "token_reduction": token_reduction,
            "compression_ratio": compression_ratio,
            "efficiency_change": post_compression_metrics.efficiency_score - pre_compression_metrics.efficiency_score,
            "duration_seconds": time.time() - compression_start,
            "success": compression_result.get("success", True)
        }
        
        self.compression_events.append(compression_event)
        
        # Log compression completion
        if action_tracer:
            action_tracer.log_action(
                ActionType.MEMORY_COMPRESSION,
                success=compression_event["success"],
                post_compression_tokens=post_compression_metrics.current_tokens,
                compression_ratio=compression_ratio,
                duration_ms=int(compression_event["duration_seconds"] * 1000)
            )
        
        print(f"Context compression completed: {token_reduction} tokens reduced "
              f"({compression_ratio:.2%} compression ratio)")
        
        return compression_event
    
    def calculate_context_efficiency(self, agent: AgentImplementation, 
                                   checkpoint: CheckpointSpecification) -> ContextEfficiencyMetrics:
        """
        Calculate comprehensive context efficiency metrics.
        
        Args:
            agent: Agent implementation
            checkpoint: Current checkpoint for analysis
            
        Returns:
            Context efficiency metrics
        """
        current_metrics = self.monitor_context_usage(agent, checkpoint)
        
        # Calculate relevance precision
        total_tokens = current_metrics.current_tokens
        relevance_precision = (current_metrics.relevant_tokens / total_tokens) if total_tokens > 0 else 1.0
        
        # Calculate information density
        information_density = relevance_precision * current_metrics.efficiency_score
        
        # Calculate redundancy rate
        redundancy_rate = (current_metrics.redundant_tokens / total_tokens) if total_tokens > 0 else 0.0
        
        # Calculate compression effectiveness from recent events
        compression_effectiveness = 1.0
        if self.compression_events:
            recent_compressions = [e for e in self.compression_events if time.time() - e["timestamp"] < 3600]  # Last hour
            if recent_compressions:
                avg_efficiency_change = sum(e["efficiency_change"] for e in recent_compressions) / len(recent_compressions)
                compression_effectiveness = max(0.0, 1.0 + avg_efficiency_change)
        
        return ContextEfficiencyMetrics(
            relevance_precision=relevance_precision,
            information_density=information_density,
            redundancy_rate=redundancy_rate,
            compression_effectiveness=compression_effectiveness
        )
    
    def force_overflow_at_checkpoint(self, checkpoint_order: int, 
                                   target_overflow: float = 1.5) -> Dict[str, Any]:
        """
        Force context window overflow at a specific checkpoint.
        
        Args:
            checkpoint_order: Checkpoint number to force overflow
            target_overflow: Target overflow multiplier (e.g., 1.5 = 150% of limit)
            
        Returns:
            Overflow event configuration
        """
        if not self.current_condition:
            raise ValueError("Context condition not configured")
        
        target_tokens = int(self.current_condition.token_limit * target_overflow)
        
        overflow_config = {
            "checkpoint_order": checkpoint_order,
            "target_tokens": target_tokens,
            "target_overflow": target_overflow,
            "original_limit": self.current_condition.token_limit,
            "forced_overflow": True
        }
        
        print(f"Configured forced overflow at checkpoint {checkpoint_order}: "
              f"{target_tokens} tokens ({target_overflow:.1%} of limit)")
        
        return overflow_config
    
    def detect_context_rereading(self, agent: AgentImplementation) -> List[Dict[str, Any]]:
        """
        Detect context re-reading patterns that indicate memory system inefficiency.
        
        Args:
            agent: Agent implementation to analyze
            
        Returns:
            List of detected re-reading events
        """
        reread_events = []
        
        # Analyze action trace for repeated file access patterns
        if hasattr(agent, 'get_behavioral_trace'):
            trace = agent.get_behavioral_trace()
            if trace and trace.checkpoints:
                for checkpoint_id, checkpoint_trace in trace.checkpoints.items():
                    file_accesses = {}
                    
                    for action in checkpoint_trace.actions:
                        if action.action_type in [ActionType.FILE_READ, ActionType.FILE_WRITE]:
                            file_path = action.metadata.get('file_path', '')
                            if file_path:
                                if file_path not in file_accesses:
                                    file_accesses[file_path] = []
                                file_accesses[file_path].append(action.timestamp)
                    
                    # Detect repeated accesses (more than 2 times to same file)
                    for file_path, timestamps in file_accesses.items():
                        if len(timestamps) > 2:
                            reread_events.append({
                                "checkpoint_id": checkpoint_id,
                                "file_path": file_path,
                                "access_count": len(timestamps),
                                "timestamps": timestamps,
                                "redundancy_score": len(timestamps) - 1  # Penalty score
                            })
        
        return reread_events
    
    def get_context_usage_summary(self) -> Dict[str, Any]:
        """Get summary of context usage across the evaluation"""
        if not self.context_history:
            return {"error": "No context usage data available"}
        
        # Calculate averages and trends
        avg_utilization = sum(m.utilization_percentage for m in self.context_history) / len(self.context_history)
        avg_efficiency = sum(m.efficiency_score for m in self.context_history) / len(self.context_history)
        
        # Count state transitions
        state_counts = {}
        for metrics in self.context_history:
            state = metrics.state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        
        return {
            "condition": self.current_condition.condition_name if self.current_condition else "none",
            "token_limit": self.current_condition.token_limit if self.current_condition else 0,
            "measurements": len(self.context_history),
            "average_utilization": avg_utilization,
            "average_efficiency": avg_efficiency,
            "state_distribution": state_counts,
            "compression_events": len(self.compression_events),
            "total_token_reduction": sum(e["token_reduction"] for e in self.compression_events)
        }