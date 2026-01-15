# Memory Probe Framework

## Overview

The Memory Probe Framework provides systematic evaluation of working memory capabilities through controlled challenges that test specific aspects of memory performance. Probes are designed to integrate naturally within task execution while providing objective, measurable assessments of memory system effectiveness.

## Theoretical Foundation

### Three-Pillar Memory Model

The framework is built on a three-pillar model of working memory evaluation:

#### Memory Fidelity
**Definition**: The ability to accurately retain and recall information over time
**Key Aspects**:
- Information compression without loss of critical details
- Accurate recall of specifications from previous contexts
- Resistance to information degradation over time
- Effective summarization and abstraction

#### Contextual Relevance  
**Definition**: The ability to filter signal from noise and maintain focus on task-relevant information
**Key Aspects**:
- Filtering irrelevant or distracting information
- Detecting changes in requirements or specifications
- Maintaining attention on current task objectives
- Prioritizing information based on task relevance

#### Behavioral Integrity
**Definition**: The ability to maintain coherent behavior and state across context changes and interruptions
**Key Aspects**:
- Consistent behavior across checkpoint transitions
- Robust recovery from task interruptions
- Proper propagation of requirement changes
- Integration consistency across dependent components

### Probe Design Principles

#### Natural Integration
Probes are designed to appear as natural task requirements rather than artificial tests:
```python
# Probe challenge appears as normal requirement
"Integrate current component with specifications from 2 checkpoints ago. 
Use exact specifications without re-reading files."

# Rather than artificial test
"Memory Test: Recall the API specification from checkpoint 1"
```

#### Objective Scoring
Probe responses are scored through objective criteria rather than subjective assessment:
```python
def score_n_back_integration(response: str, target_specs: List[str]) -> float:
    # Objective scoring based on specification accuracy
    mentioned_specs = extract_specifications(response)
    accuracy = calculate_specification_accuracy(mentioned_specs, target_specs)
    return accuracy
```

#### Minimal Interference
Probes are scheduled to minimize interference with natural task progression:
```python
# Probe interference matrix prevents conflicting probes
interference_score = calculate_probe_interference(probe1, probe2)
if interference_score > 0.7:  # High interference threshold
    reschedule_or_skip_probe(probe2)
```

## Probe Types and Implementation

### Memory Fidelity Probes

#### N-Back Integration Probe
**Purpose**: Test recall of specifications from N checkpoints ago
**Implementation**:
```python
class NBackIntegrationProbe(MemoryProbe):
    def __init__(self, n_back_distance: int = 2):
        super().__init__(
            probe_type=ProbeType.N_BACK_INTEGRATION,
            pillar=MemoryPillar.MEMORY_FIDELITY,
            n_back_distance=n_back_distance
        )
    
    def generate_challenge(self, current_checkpoint: CheckpointSpecification,
                          task_history: List[CheckpointSpecification]) -> str:
        target_checkpoint = task_history[-self.n_back_distance]
        return f"Integrate current component with specifications from " \
               f"{target_checkpoint.title}. Use exact specifications " \
               f"without re-reading files."
    
    def score_response(self, response: str, target_specs: List[str]) -> Tuple[float, bool]:
        # Extract mentioned specifications from response
        mentioned_specs = self._extract_specifications(response)
        
        # Calculate accuracy based on correct specification usage
        correct_specs = sum(1 for spec in target_specs if spec in mentioned_specs)
        accuracy = correct_specs / len(target_specs) if target_specs else 0
        
        # Binary success threshold
        success = accuracy >= 0.7
        return accuracy, success
```

**Scoring Criteria**:
- Specification accuracy (70% threshold for success)
- Implementation correctness
- No file re-reading detected
- Integration completeness

#### Compression Stress Probe
**Purpose**: Test information retention after context compression
**Implementation**:
```python
class CompressionStressProbe(MemoryProbe):
    def generate_challenge(self, context: EvaluationContext) -> str:
        # Trigger compression event
        context.memory_system.compress_context()
        
        return "Context limit reached. Summarize key information and " \
               "continue implementation without losing critical details."
    
    def score_response(self, response: str, pre_compression_state: Dict) -> Tuple[float, bool]:
        # Evaluate information retention after compression
        retained_info = self._extract_key_information(response)
        critical_info = pre_compression_state["critical_information"]
        
        retention_rate = len(retained_info & critical_info) / len(critical_info)
        success = retention_rate >= 0.8
        return retention_rate, success
```

### Contextual Relevance Probes

#### Distractor Injection Probe
**Purpose**: Test filtering of relevant vs. irrelevant information
**Implementation**:
```python
class DistractorInjectionProbe(MemoryProbe):
    def __init__(self, distractor_ratio: float = 0.3):
        super().__init__(
            probe_type=ProbeType.DISTRACTOR_INJECTION,
            pillar=MemoryPillar.CONTEXTUAL_RELEVANCE,
            distractor_ratio=distractor_ratio
        )
    
    def generate_challenge(self, checkpoint: CheckpointSpecification) -> str:
        # Inject distractor requirements alongside real ones
        real_requirements = checkpoint.requirements
        distractor_requirements = self._generate_distractors(real_requirements)
        
        combined_requirements = self._mix_requirements(
            real_requirements, distractor_requirements, self.distractor_ratio
        )
        
        return f"Multiple requirements provided below. Identify and implement " \
               f"only the relevant specifications for {checkpoint.checkpoint_id}:\n\n" \
               f"{combined_requirements}"
    
    def score_response(self, response: str, real_requirements: List[str],
                      distractor_requirements: List[str]) -> Tuple[float, bool]:
        # Analyze which requirements were addressed
        addressed_real = sum(1 for req in real_requirements if req in response)
        addressed_distractors = sum(1 for req in distractor_requirements if req in response)
        
        # Calculate precision and recall
        precision = addressed_real / (addressed_real + addressed_distractors) if (addressed_real + addressed_distractors) > 0 else 0
        recall = addressed_real / len(real_requirements) if real_requirements else 0
        
        # F1 score as overall measure
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        success = f1_score >= 0.75
        
        return f1_score, success
```

#### Change Detection Probe
**Purpose**: Test detection of critical specification changes
**Implementation**:
```python
class ChangeDetectionProbe(MemoryProbe):
    def __init__(self, change_percentage: float = 0.01):  # 1% change
        super().__init__(
            probe_type=ProbeType.CHANGE_DETECTION,
            pillar=MemoryPillar.CONTEXTUAL_RELEVANCE,
            change_percentage=change_percentage
        )
    
    def generate_challenge(self, original_spec: str) -> Tuple[str, List[str]]:
        # Make subtle but critical changes to specification
        modified_spec, changes = self._introduce_subtle_changes(
            original_spec, self.change_percentage
        )
        
        challenge = f"Specification has been updated. Identify what changed " \
                   f"and update your implementation accordingly:\n\n{modified_spec}"
        
        return challenge, changes
    
    def score_response(self, response: str, actual_changes: List[str]) -> Tuple[float, bool]:
        # Detect which changes were identified
        identified_changes = self._extract_identified_changes(response)
        
        # Calculate change detection accuracy
        correct_detections = sum(1 for change in actual_changes 
                               if self._change_mentioned(change, identified_changes))
        detection_rate = correct_detections / len(actual_changes) if actual_changes else 0
        
        # Penalize false positives
        false_positives = len(identified_changes) - correct_detections
        false_positive_penalty = min(false_positives * 0.1, 0.3)
        
        final_score = max(0, detection_rate - false_positive_penalty)
        success = final_score >= 0.6
        
        return final_score, success
```

### Behavioral Integrity Probes

#### Update Robustness Probe
**Purpose**: Test propagation of requirement changes across components
**Implementation**:
```python
class UpdateRobustnessProbe(MemoryProbe):
    def generate_challenge(self, checkpoint: CheckpointSpecification,
                          dependent_checkpoints: List[CheckpointSpecification]) -> str:
        # Identify core requirement that affects multiple components
        core_requirement = self._identify_core_requirement(checkpoint, dependent_checkpoints)
        updated_requirement = self._modify_requirement(core_requirement)
        
        return f"Core requirement for {checkpoint.checkpoint_id} has changed: " \
               f"{updated_requirement}. Propagate changes to all affected components."
    
    def score_response(self, response: str, affected_components: List[str]) -> Tuple[float, bool]:
        # Check if all affected components were updated
        updated_components = self._extract_updated_components(response)
        
        propagation_completeness = len(updated_components & set(affected_components)) / len(affected_components)
        consistency_score = self._evaluate_update_consistency(response, updated_components)
        
        overall_score = (propagation_completeness + consistency_score) / 2
        success = overall_score >= 0.75
        
        return overall_score, success
```

#### Context Switch Probe
**Purpose**: Test resumption after task interruption
**Implementation**:
```python
class ContextSwitchProbe(MemoryProbe):
    def __init__(self, interruption_duration: int = 5):
        super().__init__(
            probe_type=ProbeType.CONTEXT_SWITCH,
            pillar=MemoryPillar.BEHAVIORAL_INTEGRITY,
            interruption_duration=interruption_duration
        )
    
    async def inject_interruption(self, agent: AgentImplementation) -> Dict[str, Any]:
        # Capture pre-interruption state
        pre_state = self._capture_agent_state(agent)
        
        # Present unrelated debugging task
        interruption_task = self._generate_interruption_task()
        await agent.process_requirement(f"URGENT: Debug this unrelated issue: {interruption_task}")
        
        # Wait for interruption duration
        await asyncio.sleep(self.interruption_duration)
        
        return {"pre_state": pre_state, "interruption_task": interruption_task}
    
    def generate_challenge(self, original_task_context: str) -> str:
        return f"Interruption resolved. Resume your original implementation: {original_task_context}"
    
    def score_response(self, response: str, pre_interruption_state: Dict,
                      original_context: str) -> Tuple[float, bool]:
        # Evaluate resumption quality
        context_recovery = self._evaluate_context_recovery(response, original_context)
        state_consistency = self._evaluate_state_consistency(response, pre_interruption_state)
        task_continuation = self._evaluate_task_continuation(response, original_context)
        
        recovery_score = (context_recovery + state_consistency + task_continuation) / 3
        success = recovery_score >= 0.7
        
        return recovery_score, success
```

## Probe Scheduling and Injection

### Intelligent Scheduling Algorithm

```python
class ProbeScheduler:
    def schedule_probes(self, probes: List[MemoryProbe], 
                       task_spec: TaskSpecification) -> Dict[str, List[MemoryProbe]]:
        """
        Intelligent probe scheduling based on:
        1. Memory pressure analysis
        2. Pillar-specific stress points
        3. Natural integration opportunities
        4. Probe independence validation
        """
        
        # Step 1: Calculate optimal injection points
        injection_points = {}
        for probe in probes:
            memory_pressure = self._calculate_memory_pressure(probe, task_spec)
            pillar_stress = self._calculate_pillar_stress(probe, task_spec)
            optimal_timing = self._determine_optimal_timing(probe, memory_pressure, pillar_stress)
            
            injection_points[probe.probe_id] = ProbeInjectionPoint(
                checkpoint_id=probe.target_checkpoint,
                timing=optimal_timing,
                memory_pressure_score=memory_pressure,
                pillar_stress_level=pillar_stress
            )
        
        # Step 2: Validate probe independence
        validated_probes = self._validate_probe_independence(probes, injection_points)
        
        # Step 3: Group by checkpoint and sort by injection order
        scheduled = {}
        for probe in validated_probes:
            checkpoint_id = probe.target_checkpoint
            if checkpoint_id not in scheduled:
                scheduled[checkpoint_id] = []
            scheduled[checkpoint_id].append(probe)
        
        # Sort probes within each checkpoint
        for checkpoint_probes in scheduled.values():
            checkpoint_probes.sort(key=lambda p: injection_points[p.probe_id].injection_order)
        
        return scheduled
```

### Memory Pressure Calculation

```python
def _calculate_memory_pressure(self, probe: MemoryProbe, 
                              task_spec: TaskSpecification) -> float:
    """Calculate memory pressure score for optimal probe timing"""
    
    # Find target checkpoint
    target_checkpoint = task_spec.get_checkpoint_by_id(probe.target_checkpoint)
    if not target_checkpoint:
        return 0.5  # Default moderate pressure
    
    # Factors contributing to memory pressure
    checkpoint_position = target_checkpoint.order / len(task_spec.checkpoints)
    complexity_factor = min(target_checkpoint.estimated_tokens / 500.0, 1.0)
    dependency_factor = min(len(target_checkpoint.dependencies) / 3.0, 1.0)
    
    # Cumulative context factor (more context = more pressure)
    cumulative_context = sum(cp.estimated_tokens for cp in task_spec.checkpoints 
                           if cp.order <= target_checkpoint.order)
    context_factor = min(cumulative_context / 4000.0, 1.0)
    
    # Weighted combination
    pressure_score = (
        checkpoint_position * 0.3 +    # Later checkpoints have more pressure
        complexity_factor * 0.25 +     # Complex checkpoints increase pressure
        dependency_factor * 0.2 +      # Dependencies increase pressure
        context_factor * 0.25          # Cumulative context increases pressure
    )
    
    return min(pressure_score, 1.0)
```

### Probe Independence Validation

```python
def _validate_probe_independence(self, probes: List[MemoryProbe], 
                               injection_points: Dict[str, ProbeInjectionPoint]) -> List[MemoryProbe]:
    """Ensure probes don't interfere with each other"""
    
    # Build interference matrix
    interference_matrix = {}
    for i, probe1 in enumerate(probes):
        for j, probe2 in enumerate(probes):
            if i != j:
                interference = self._calculate_probe_interference(probe1, probe2)
                interference_matrix[(probe1.probe_id, probe2.probe_id)] = interference
    
    # Resolve conflicts using greedy algorithm
    validated_probes = []
    for probe in sorted(probes, key=lambda p: injection_points[p.probe_id].memory_pressure_score, reverse=True):
        # Check for high interference with already scheduled probes
        conflicts = [existing.probe_id for existing in validated_probes 
                    if interference_matrix.get((probe.probe_id, existing.probe_id), 0) > 0.7]
        
        if len(conflicts) <= 1:  # Allow low-level conflicts
            validated_probes.append(probe)
        else:
            print(f"Skipping probe {probe.probe_id} due to interference with {conflicts}")
    
    return validated_probes
```

## Probe Response Analysis

### Objective Scoring Framework

```python
class ProbeResponseAnalyzer:
    def score_probe_response(self, probe: MemoryProbe, response: str, 
                           context: EvaluationContext) -> ProbeResponse:
        """Objective scoring of probe responses"""
        
        # Probe-type specific scoring
        if probe.probe_type == ProbeType.N_BACK_INTEGRATION:
            score, success = self._score_n_back_integration(probe, response, context)
        elif probe.probe_type == ProbeType.DISTRACTOR_INJECTION:
            score, success = self._score_distractor_filtering(probe, response, context)
        elif probe.probe_type == ProbeType.CONTEXT_SWITCH:
            score, success = self._score_context_switch_recovery(probe, response, context)
        # ... other probe types
        
        # Create response record
        return ProbeResponse(
            probe_id=probe.probe_id,
            response_text=response,
            response_time_seconds=context.response_time,
            success=success,
            score=score,
            metadata={
                "probe_type": probe.probe_type.value,
                "pillar": probe.pillar.value,
                "scoring_criteria": self._get_scoring_criteria(probe),
                "detailed_analysis": self._generate_detailed_analysis(probe, response, score)
            }
        )
```

### Scoring Criteria by Probe Type

#### N-Back Integration Scoring
```python
def _score_n_back_integration(self, probe: MemoryProbe, response: str, 
                             context: EvaluationContext) -> Tuple[float, bool]:
    """Score N-back integration probe response"""
    
    # Extract target specifications from N checkpoints ago
    n_back_distance = probe.n_back_distance or 2
    target_checkpoint = context.get_checkpoint_n_back(n_back_distance)
    target_specs = self._extract_specifications(target_checkpoint.requirements)
    
    # Analyze response for specification usage
    mentioned_specs = self._extract_specifications_from_response(response)
    
    # Calculate specification accuracy
    correct_specs = sum(1 for spec in target_specs 
                       if self._specification_correctly_used(spec, mentioned_specs))
    specification_accuracy = correct_specs / len(target_specs) if target_specs else 0
    
    # Check for file re-reading (penalty)
    file_reread_penalty = 0.2 if self._detect_file_rereading(response) else 0
    
    # Implementation quality assessment
    implementation_quality = self._assess_implementation_quality(response, target_specs)
    
    # Final score calculation
    final_score = max(0, (specification_accuracy * 0.5 + implementation_quality * 0.5) - file_reread_penalty)
    success = final_score >= 0.7
    
    return final_score, success
```

#### Distractor Filtering Scoring
```python
def _score_distractor_filtering(self, probe: MemoryProbe, response: str,
                               context: EvaluationContext) -> Tuple[float, bool]:
    """Score distractor injection probe response"""
    
    # Get real vs. distractor requirements
    real_requirements = context.real_requirements
    distractor_requirements = context.distractor_requirements
    
    # Analyze which requirements were addressed
    addressed_requirements = self._extract_addressed_requirements(response)
    
    # Calculate precision (% of addressed requirements that are real)
    real_addressed = sum(1 for req in addressed_requirements if req in real_requirements)
    precision = real_addressed / len(addressed_requirements) if addressed_requirements else 0
    
    # Calculate recall (% of real requirements that were addressed)
    recall = real_addressed / len(real_requirements) if real_requirements else 0
    
    # F1 score as balanced measure
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    # Bonus for explicit distractor rejection
    distractor_rejection_bonus = 0.1 if self._detect_explicit_distractor_rejection(response) else 0
    
    final_score = min(1.0, f1_score + distractor_rejection_bonus)
    success = final_score >= 0.75
    
    return final_score, success
```

## Integration with Enhanced Evaluation

### Probe Injection During Evaluation

```python
async def _execute_enhanced_checkpoint(self, checkpoint: CheckpointSpecification,
                                     scheduled_probes: List[MemoryProbe],
                                     agent: AgentImplementation,
                                     action_tracer: ActionTracer) -> List[ProbeResponse]:
    """Execute checkpoint with probe injection"""
    
    probe_responses = []
    
    for probe in scheduled_probes:
        # Determine injection timing
        injection_point = self.probe_scheduler.injection_points[probe.probe_id]
        
        if injection_point.timing == ProbeInjectionTiming.CHECKPOINT_START:
            # Inject before checkpoint execution
            response = await self.probe_scheduler.inject_probe_at_checkpoint(
                probe, agent, action_tracer, checkpoint
            )
            probe_responses.append(response)
        
        elif injection_point.timing == ProbeInjectionTiming.MID_CHECKPOINT:
            # Inject during checkpoint execution (requires agent cooperation)
            await self._schedule_mid_checkpoint_injection(probe, agent, action_tracer)
        
        elif injection_point.timing == ProbeInjectionTiming.MEMORY_PRESSURE_PEAK:
            # Inject when memory pressure is detected
            if self._detect_memory_pressure_peak(agent):
                response = await self.probe_scheduler.inject_probe_at_checkpoint(
                    probe, agent, action_tracer, checkpoint
                )
                probe_responses.append(response)
    
    return probe_responses
```

### Results Integration

```python
def _integrate_probe_results(self, checkpoint_result: CheckpointResult,
                           probe_responses: List[ProbeResponse]) -> CheckpointResult:
    """Integrate probe results into checkpoint results"""
    
    if not probe_responses:
        return checkpoint_result
    
    # Add probe-specific metrics
    probe_metrics = {
        "probe_responses": [
            {
                "probe_id": response.probe_id,
                "success": response.success,
                "score": response.score,
                "pillar": response.metadata["pillar"],
                "response_time": response.response_time_seconds
            }
            for response in probe_responses
        ],
        "probe_summary": {
            "total_probes": len(probe_responses),
            "successful_probes": sum(1 for r in probe_responses if r.success),
            "average_score": sum(r.score for r in probe_responses) / len(probe_responses),
            "pillar_breakdown": self._calculate_pillar_breakdown(probe_responses)
        }
    }
    
    # Merge with existing metadata
    if checkpoint_result.metadata:
        checkpoint_result.metadata.update(probe_metrics)
    else:
        checkpoint_result.metadata = probe_metrics
    
    return checkpoint_result
```

## Future Extensions

### Custom Probe Development

```python
class CustomMemoryProbe(MemoryProbe):
    """Base class for custom probe development"""
    
    def __init__(self, probe_id: str, pillar: MemoryPillar, **kwargs):
        super().__init__(
            probe_id=probe_id,
            probe_type=ProbeType.CUSTOM,
            pillar=pillar,
            **kwargs
        )
    
    @abstractmethod
    def generate_challenge(self, context: EvaluationContext) -> str:
        """Generate probe-specific challenge"""
        pass
    
    @abstractmethod
    def score_response(self, response: str, context: EvaluationContext) -> Tuple[float, bool]:
        """Score probe response objectively"""
        pass
    
    def get_injection_timing(self, memory_pressure: float, pillar_stress: float) -> ProbeInjectionTiming:
        """Determine optimal injection timing (override for custom logic)"""
        return ProbeInjectionTiming.MID_CHECKPOINT
```

### Adaptive Probe Scheduling

```python
class AdaptiveProbeScheduler(ProbeScheduler):
    """Adaptive probe scheduling based on agent performance"""
    
    def adapt_probe_difficulty(self, agent_performance: Dict[str, float],
                              probe: MemoryProbe) -> MemoryProbe:
        """Adapt probe difficulty based on agent's demonstrated capabilities"""
        
        pillar_performance = agent_performance.get(probe.pillar.value, 0.5)
        
        if pillar_performance > 0.8:
            # Increase difficulty for high-performing agents
            return self._increase_probe_difficulty(probe)
        elif pillar_performance < 0.4:
            # Decrease difficulty for struggling agents
            return self._decrease_probe_difficulty(probe)
        else:
            return probe
```

The Memory Probe Framework provides a comprehensive, scientifically grounded approach to evaluating working memory capabilities in AI agents. Through natural integration, objective scoring, and intelligent scheduling, it enables precise measurement of memory system performance across the three critical pillars of memory evaluation.