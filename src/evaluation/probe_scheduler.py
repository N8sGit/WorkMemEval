"""
WorkMemEval: Probe Scheduler

This module provides memory probe scheduling and injection capabilities
for enhanced evaluation, including optimal timing calculation and natural
integration within the task flow.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from ..core.task_specification import (
    MemoryProbe, ProbeType, MemoryPillar, TaskSpecification, 
    CheckpointSpecification
)
from ..core.plugin_interfaces import AgentImplementation
from ..core.action_trace import ActionTracer, ActionType


class ProbeInjectionTiming(Enum):
    """Timing strategies for probe injection"""
    CHECKPOINT_START = "checkpoint_start"
    MID_CHECKPOINT = "mid_checkpoint"
    CHECKPOINT_END = "checkpoint_end"
    MEMORY_PRESSURE_PEAK = "memory_pressure_peak"


@dataclass
class ProbeInjectionPoint:
    """Represents an optimal point for probe injection"""
    checkpoint_id: str
    timing: ProbeInjectionTiming
    memory_pressure_score: float
    pillar_stress_level: float
    injection_order: int


@dataclass
class ProbeResponse:
    """Captures agent response to a memory probe"""
    probe_id: str
    response_text: str
    response_time_seconds: float
    success: bool
    score: float
    metadata: Dict[str, Any]


class ProbeScheduler:
    """
    Schedules and manages memory probe injection during task execution.
    
    Provides intelligent probe scheduling based on:
    - Memory pressure detection
    - Pillar-specific stress points
    - Natural integration opportunities
    - Probe independence validation
    """
    
    def __init__(self):
        self.scheduled_probes: Dict[str, List[MemoryProbe]] = {}
        self.injection_points: Dict[str, ProbeInjectionPoint] = {}
        self.probe_responses: List[ProbeResponse] = []
        self.probe_interference_matrix: Dict[Tuple[str, str], float] = {}
        
    def schedule_probes(self, probes: List[MemoryProbe], 
                       task_spec: Optional[TaskSpecification] = None) -> Dict[str, List[MemoryProbe]]:
        """
        Schedule memory probes for injection at optimal points.
        
        Args:
            probes: List of memory probes to schedule
            task_spec: Task specification for context analysis
            
        Returns:
            Dictionary mapping checkpoint IDs to lists of probes
        """
        if not probes:
            return {}
        
        # Calculate optimal injection points
        injection_points = self._calculate_optimal_injection_points(probes, task_spec)
        
        # Validate probe independence
        validated_schedule = self._validate_probe_independence(probes, injection_points)
        
        # Group probes by checkpoint
        scheduled = {}
        for probe in validated_schedule:
            checkpoint_id = probe.target_checkpoint
            if checkpoint_id not in scheduled:
                scheduled[checkpoint_id] = []
            scheduled[checkpoint_id].append(probe)
        
        # Sort probes within each checkpoint by injection order
        for checkpoint_id, checkpoint_probes in scheduled.items():
            checkpoint_probes.sort(key=lambda p: self.injection_points.get(p.probe_id, ProbeInjectionPoint(
                checkpoint_id, ProbeInjectionTiming.CHECKPOINT_START, 0, 0, 0
            )).injection_order)
        
        self.scheduled_probes = scheduled
        print(f"Scheduled {len(probes)} probes across {len(scheduled)} checkpoints")
        
        return scheduled
    
    def _calculate_optimal_injection_points(self, probes: List[MemoryProbe], 
                                          task_spec: Optional[TaskSpecification]) -> Dict[str, ProbeInjectionPoint]:
        """Calculate optimal injection points for each probe"""
        injection_points = {}
        
        for i, probe in enumerate(probes):
            # Calculate memory pressure score for target checkpoint
            memory_pressure = self._calculate_memory_pressure_score(probe, task_spec)
            
            # Calculate pillar-specific stress level
            pillar_stress = self._calculate_pillar_stress_level(probe, task_spec)
            
            # Determine optimal timing within checkpoint
            timing = self._determine_optimal_timing(probe, memory_pressure, pillar_stress)
            
            injection_point = ProbeInjectionPoint(
                checkpoint_id=probe.target_checkpoint,
                timing=timing,
                memory_pressure_score=memory_pressure,
                pillar_stress_level=pillar_stress,
                injection_order=i
            )
            
            injection_points[probe.probe_id] = injection_point
        
        self.injection_points = injection_points
        return injection_points
    
    def _calculate_memory_pressure_score(self, probe: MemoryProbe, 
                                       task_spec: Optional[TaskSpecification]) -> float:
        """Calculate memory pressure score for probe injection timing"""
        if not task_spec:
            return 0.5  # Default moderate pressure
        
        # Find target checkpoint
        target_checkpoint = None
        for cp in task_spec.checkpoints:
            if cp.checkpoint_id == probe.target_checkpoint:
                target_checkpoint = cp
                break
        
        if not target_checkpoint:
            return 0.5
        
        # Calculate pressure based on checkpoint position and complexity
        checkpoint_position = target_checkpoint.order / len(task_spec.checkpoints)
        complexity_factor = min(target_checkpoint.estimated_tokens / 500.0, 1.0)
        dependency_factor = min(len(target_checkpoint.dependencies) / 3.0, 1.0)
        
        # Memory pressure increases with position, complexity, and dependencies
        pressure_score = (checkpoint_position * 0.4) + (complexity_factor * 0.3) + (dependency_factor * 0.3)
        
        return min(pressure_score, 1.0)
    
    def _calculate_pillar_stress_level(self, probe: MemoryProbe, 
                                     task_spec: Optional[TaskSpecification]) -> float:
        """Calculate pillar-specific stress level for probe timing"""
        if not task_spec or not hasattr(task_spec, 'enhanced_complexity'):
            return 0.5  # Default moderate stress
        
        enhanced_complexity = task_spec.enhanced_complexity
        if not enhanced_complexity:
            return 0.5
        
        # Get pillar stress score from complexity analysis
        pillar_scores = enhanced_complexity.pillar_stress_scores
        return pillar_scores.get(probe.pillar, 0.5)
    
    def _determine_optimal_timing(self, probe: MemoryProbe, 
                                memory_pressure: float, pillar_stress: float) -> ProbeInjectionTiming:
        """Determine optimal timing for probe injection within checkpoint"""
        
        # Different probe types have different optimal timings
        if probe.probe_type in [ProbeType.N_BACK_INTEGRATION, ProbeType.UPDATE_ROBUSTNESS]:
            # These probes work best mid-checkpoint when context is loaded
            return ProbeInjectionTiming.MID_CHECKPOINT
        elif probe.probe_type in [ProbeType.COMPRESSION_STRESS, ProbeType.CONTEXT_SWITCH]:
            # These probes work best at memory pressure peaks
            return ProbeInjectionTiming.MEMORY_PRESSURE_PEAK
        elif probe.probe_type in [ProbeType.DISTRACTOR_INJECTION, ProbeType.CHANGE_DETECTION]:
            # These probes work best at checkpoint start when focus is being established
            return ProbeInjectionTiming.CHECKPOINT_START
        else:
            # Default to mid-checkpoint
            return ProbeInjectionTiming.MID_CHECKPOINT
    
    def _validate_probe_independence(self, probes: List[MemoryProbe], 
                                   injection_points: Dict[str, ProbeInjectionPoint]) -> List[MemoryProbe]:
        """Validate that probes don't interfere with each other"""
        validated_probes = []
        
        # Build interference matrix
        self._build_probe_interference_matrix(probes)
        
        # Check for conflicts and resolve them
        for probe in probes:
            conflicts = self._detect_probe_conflicts(probe, validated_probes, injection_points)
            
            if not conflicts:
                validated_probes.append(probe)
            else:
                # Try to resolve conflicts by adjusting timing or skipping
                resolved_probe = self._resolve_probe_conflicts(probe, conflicts, injection_points)
                if resolved_probe:
                    validated_probes.append(resolved_probe)
                else:
                    print(f"Warning: Skipping probe {probe.probe_id} due to unresolvable conflicts")
        
        return validated_probes
    
    def _build_probe_interference_matrix(self, probes: List[MemoryProbe]):
        """Build matrix of probe interference scores"""
        for i, probe1 in enumerate(probes):
            for j, probe2 in enumerate(probes):
                if i != j:
                    interference_score = self._calculate_probe_interference(probe1, probe2)
                    self.probe_interference_matrix[(probe1.probe_id, probe2.probe_id)] = interference_score
    
    def _calculate_probe_interference(self, probe1: MemoryProbe, probe2: MemoryProbe) -> float:
        """Calculate interference score between two probes (0.0 = no interference, 1.0 = high interference)"""
        
        # Same checkpoint = potential interference
        if probe1.target_checkpoint == probe2.target_checkpoint:
            base_interference = 0.5
        else:
            base_interference = 0.0
        
        # Same pillar = higher interference
        if probe1.pillar == probe2.pillar:
            base_interference += 0.3
        
        # Same probe type = very high interference
        if probe1.probe_type == probe2.probe_type:
            base_interference += 0.4
        
        return min(base_interference, 1.0)
    
    def _detect_probe_conflicts(self, probe: MemoryProbe, existing_probes: List[MemoryProbe], 
                              injection_points: Dict[str, ProbeInjectionPoint]) -> List[str]:
        """Detect conflicts between a probe and existing scheduled probes"""
        conflicts = []
        
        for existing_probe in existing_probes:
            interference = self.probe_interference_matrix.get((probe.probe_id, existing_probe.probe_id), 0.0)
            
            if interference > 0.7:  # High interference threshold
                conflicts.append(existing_probe.probe_id)
        
        return conflicts
    
    def _resolve_probe_conflicts(self, probe: MemoryProbe, conflicts: List[str], 
                               injection_points: Dict[str, ProbeInjectionPoint]) -> Optional[MemoryProbe]:
        """Attempt to resolve probe conflicts by adjusting timing or parameters"""
        
        # For now, simple resolution: skip high-conflict probes
        # In full implementation, this could adjust timing, parameters, or checkpoint assignment
        
        if len(conflicts) > 2:  # Too many conflicts
            return None
        
        # Try adjusting injection order to reduce conflicts
        if probe.probe_id in injection_points:
            injection_points[probe.probe_id].injection_order += len(conflicts)
        
        return probe
    
    async def inject_probe_at_checkpoint(self, probe: MemoryProbe, agent: AgentImplementation, 
                                       action_tracer: ActionTracer, 
                                       checkpoint: CheckpointSpecification) -> ProbeResponse:
        """
        Inject a memory probe during checkpoint execution.
        
        Args:
            probe: Memory probe to inject
            agent: Agent implementation
            action_tracer: Action tracer for logging
            checkpoint: Current checkpoint context
            
        Returns:
            Probe response with scoring
        """
        injection_start = time.time()
        
        # Log probe injection start
        action_tracer.log_action(
            ActionType.PROBE_INJECTION,
            success=True,
            probe_id=probe.probe_id,
            probe_type=probe.probe_type.value,
            pillar=probe.pillar.value,
            target_checkpoint=probe.target_checkpoint
        )
        
        print(f"Injecting {probe.pillar.value} probe: {probe.probe_id}")
        
        try:
            # Generate probe challenge based on type
            challenge = self._generate_probe_challenge(probe, checkpoint)
            
            # Present challenge to agent and collect response
            response_text = await self._present_probe_to_agent(probe, challenge, agent)
            
            # Score the response
            score, success = self._score_probe_response(probe, response_text, checkpoint)
            
            response_time = time.time() - injection_start
            
            # Create probe response record
            probe_response = ProbeResponse(
                probe_id=probe.probe_id,
                response_text=response_text,
                response_time_seconds=response_time,
                success=success,
                score=score,
                metadata={
                    "probe_type": probe.probe_type.value,
                    "pillar": probe.pillar.value,
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "challenge": challenge
                }
            )
            
            self.probe_responses.append(probe_response)
            
            # Log probe completion
            action_tracer.log_action(
                ActionType.PROBE_RESPONSE,
                success=success,
                probe_id=probe.probe_id,
                score=score,
                response_time_ms=int(response_time * 1000)
            )
            
            action_tracer.log_action(
                ActionType.MEMORY_PROBE_SCORE,
                success=True,
                probe_id=probe.probe_id,
                pillar=probe.pillar.value,
                score=score,
                binary_success=success
            )
            
            print(f"Probe {probe.probe_id} completed: {'PASS' if success else 'FAIL'} (score: {score:.2f})")
            
            return probe_response
            
        except Exception as e:
            # Handle probe injection errors
            error_response = ProbeResponse(
                probe_id=probe.probe_id,
                response_text="",
                response_time_seconds=time.time() - injection_start,
                success=False,
                score=0.0,
                metadata={"error": str(e)}
            )
            
            action_tracer.log_action(
                ActionType.ERROR_ENCOUNTERED,
                success=False,
                probe_id=probe.probe_id,
                error_message=str(e)
            )
            
            print(f"Probe {probe.probe_id} failed with error: {e}")
            return error_response
    
    def _generate_probe_challenge(self, probe: MemoryProbe, checkpoint: CheckpointSpecification) -> str:
        """Generate probe-specific challenge based on probe type"""
        
        if probe.probe_type == ProbeType.N_BACK_INTEGRATION:
            n_back = probe.n_back_distance or 2
            return f"Integrate current component with specifications from {n_back} checkpoints ago. Use exact specifications without re-reading files."
        
        elif probe.probe_type == ProbeType.COMPRESSION_STRESS:
            return "Context limit reached. Summarize key information and continue implementation without losing critical details."
        
        elif probe.probe_type == ProbeType.DISTRACTOR_INJECTION:
            return f"Multiple similar requirements provided. Identify and implement only the relevant specifications for {checkpoint.checkpoint_id}."
        
        elif probe.probe_type == ProbeType.CHANGE_DETECTION:
            return "Specification has been updated. Identify what changed and update your implementation accordingly."
        
        elif probe.probe_type == ProbeType.UPDATE_ROBUSTNESS:
            return f"Core requirement for {checkpoint.checkpoint_id} has changed. Propagate changes to all affected components."
        
        elif probe.probe_type == ProbeType.CONTEXT_SWITCH:
            return "Task interrupted. Debug this unrelated issue, then resume your original implementation."
        
        else:
            return f"Memory challenge: {probe.description}"
    
    async def _present_probe_to_agent(self, probe: MemoryProbe, challenge: str, 
                                    agent: AgentImplementation) -> str:
        """Present probe challenge to agent and collect response"""
        
        # In a full implementation, this would integrate with the agent's
        # natural interaction flow. For now, we simulate the interaction.
        
        if hasattr(agent, 'handle_memory_probe'):
            # Agent has explicit probe handling
            return await agent.handle_memory_probe(probe, challenge)
        elif hasattr(agent, 'process_requirement'):
            # Present as natural requirement
            return await agent.process_requirement(challenge)
        else:
            # Fallback: simulate response based on probe type
            return self._simulate_agent_response(probe, challenge)
    
    def _simulate_agent_response(self, probe: MemoryProbe, challenge: str) -> str:
        """Simulate agent response for testing purposes"""
        
        # This is a placeholder for testing. In production, agents would
        # provide actual responses to probe challenges.
        
        responses = {
            ProbeType.N_BACK_INTEGRATION: "Integrating with previous specifications as requested.",
            ProbeType.COMPRESSION_STRESS: "Summarizing context and continuing with implementation.",
            ProbeType.DISTRACTOR_INJECTION: "Filtering relevant requirements and focusing on target specifications.",
            ProbeType.CHANGE_DETECTION: "Analyzing changes and updating implementation accordingly.",
            ProbeType.UPDATE_ROBUSTNESS: "Propagating requirement changes to affected components.",
            ProbeType.CONTEXT_SWITCH: "Handling interruption and resuming original task."
        }
        
        return responses.get(probe.probe_type, "Handling memory challenge as requested.")
    
    def _score_probe_response(self, probe: MemoryProbe, response: str, 
                            checkpoint: CheckpointSpecification) -> Tuple[float, bool]:
        """Score probe response objectively"""
        
        # Simplified scoring for demonstration
        # In full implementation, this would use sophisticated scoring algorithms
        
        if not response or len(response.strip()) < 10:
            return 0.0, False
        
        # Basic scoring based on response content
        score = 0.5  # Base score
        
        # Check for probe-specific indicators
        if probe.probe_type == ProbeType.N_BACK_INTEGRATION:
            if "integrat" in response.lower() and "previous" in response.lower():
                score += 0.3
        elif probe.probe_type == ProbeType.DISTRACTOR_INJECTION:
            if "filter" in response.lower() or "relevant" in response.lower():
                score += 0.3
        elif probe.probe_type == ProbeType.CHANGE_DETECTION:
            if "chang" in response.lower() or "updat" in response.lower():
                score += 0.3
        
        # Length bonus (up to 0.2)
        length_bonus = min(len(response) / 500.0, 0.2)
        score += length_bonus
        
        # Binary success threshold
        success = score >= 0.6
        
        return min(score, 1.0), success
    
    def get_probe_results_summary(self) -> Dict[str, Any]:
        """Get summary of probe injection results"""
        
        if not self.probe_responses:
            return {"error": "No probe responses available"}
        
        # Calculate overall metrics
        total_probes = len(self.probe_responses)
        successful_probes = sum(1 for r in self.probe_responses if r.success)
        avg_score = sum(r.score for r in self.probe_responses) / total_probes
        avg_response_time = sum(r.response_time_seconds for r in self.probe_responses) / total_probes
        
        # Group by pillar
        pillar_results = {}
        for response in self.probe_responses:
            pillar = response.metadata.get("pillar", "unknown")
            if pillar not in pillar_results:
                pillar_results[pillar] = {"total": 0, "successful": 0, "scores": []}
            
            pillar_results[pillar]["total"] += 1
            if response.success:
                pillar_results[pillar]["successful"] += 1
            pillar_results[pillar]["scores"].append(response.score)
        
        # Calculate pillar-specific metrics
        for pillar, results in pillar_results.items():
            results["success_rate"] = results["successful"] / results["total"]
            results["avg_score"] = sum(results["scores"]) / len(results["scores"])
        
        return {
            "total_probes": total_probes,
            "successful_probes": successful_probes,
            "overall_success_rate": successful_probes / total_probes,
            "average_score": avg_score,
            "average_response_time": avg_response_time,
            "pillar_results": pillar_results,
            "scheduled_checkpoints": len(self.scheduled_probes)
        }