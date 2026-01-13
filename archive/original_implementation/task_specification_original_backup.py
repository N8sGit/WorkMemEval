"""
WorkMemEval: Task Specification Core Data Structures

This module defines the foundational data structures for WorkMemEval task specifications,
following the hybrid task structure design that combines controlled checkpoints with
architectural freedom zones.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class CheckpointType(Enum):
    """Types of checkpoints in WorkMemEval tasks"""

    IMPLEMENTATION = "implementation"  # Core functionality development
    INTEGRATION = "integration"  # Component combination and coordination
    EXTENSION = "extension"  # Feature addition to existing system


class MemoryChallengeType(Enum):
    """Types of working memory challenges"""

    REQUIREMENT_UPDATE = "requirement_update"  # Mid-task specification changes
    CONTEXT_SWITCH = "context_switch"  # Task interruption and resumption
    INFORMATION_OVERLOAD = "information_overload"  # Distractor files and complexity
    INTEGRATION_CONSTRAINT = "integration_constraint"  # Cross-checkpoint dependencies


class MemoryPillar(Enum):
    """Three pillars of working memory evaluation"""

    MEMORY_FIDELITY = "memory_fidelity"  # Information retention and compression
    CONTEXTUAL_RELEVANCE = "contextual_relevance"  # Signal vs noise filtering
    BEHAVIORAL_INTEGRITY = "behavioral_integrity"  # State coherence and robustness


class ProbeType(Enum):
    """Types of memory probes for pillar testing"""

    N_BACK_INTEGRATION = "n_back_integration"  # Memory Fidelity
    COMPRESSION_STRESS = "compression_stress"  # Memory Fidelity
    DISTRACTOR_INJECTION = "distractor_injection"  # Contextual Relevance
    CHANGE_DETECTION = "change_detection"  # Contextual Relevance
    UPDATE_ROBUSTNESS = "update_robustness"  # Behavioral Integrity
    CONTEXT_SWITCH = "context_switch"  # Behavioral Integrity


class ContextConditionType(Enum):
    """Context window evaluation conditions"""

    STANDARDIZED = "standardized"  # Fixed context window for fair comparison
    NATIVE = "native"  # Agent's natural context capacity
    OVERFLOW = "overflow"  # Forced context overflow to stress memory systems


class EvaluationMode(Enum):
    """Evaluation complexity tiers for progressive disclosure"""

    SIMPLE = "simple"  # Tier 1: Basic evaluation (existing functionality)
    RESEARCH = "research"  # Tier 2: Enhanced evaluation with smart defaults
    ADVANCED = "advanced"  # Tier 3: Full framework control


@dataclass
class ResearchTemplate:
    """
    Pre-configured research pattern template.

    Provides ready-to-use configurations for common memory research
    patterns, hiding implementation complexity behind research intent.
    """

    template_id: str
    name: str
    description: str
    research_focus: MemoryPillar

    # Pre-configured components
    probe_configuration: List[Dict[str, Any]] = field(default_factory=list)
    context_conditions: List[Dict[str, Any]] = field(default_factory=list)
    complexity_targets: Dict[str, Any] = field(default_factory=dict)
    evaluation_metrics: List[str] = field(default_factory=list)

    # Template metadata
    difficulty_level: str = "moderate"
    estimated_duration_minutes: int = 120
    required_checkpoints: int = 5
    tags: List[str] = field(default_factory=list)

    def apply_to_task(self, task_spec: "TaskSpecification") -> "TaskSpecification":
        """Apply research template configuration to a task specification"""
        # Create memory probes from template
        memory_probes = []
        for i, probe_config in enumerate(self.probe_configuration):
            # Find suitable checkpoint for probe injection
            target_checkpoint = self._select_target_checkpoint(task_spec.checkpoints, i)
            if target_checkpoint:
                probe = MemoryProbe(
                    probe_id=f"{self.template_id}_probe_{i + 1}",
                    probe_type=ProbeType(probe_config["probe_type"]),
                    pillar=self.research_focus,
                    target_checkpoint=target_checkpoint.checkpoint_id,
                    description=probe_config["description"],
                    **{
                        k: v
                        for k, v in probe_config.items()
                        if k not in ["probe_type", "description"]
                    },
                )
                memory_probes.append(probe)

        # Create context conditions from template
        context_conditions = []
        for cond_config in self.context_conditions:
            context_conditions.append(
                ContextWindowCondition(
                    condition_name=cond_config["condition_name"],
                    condition_type=ContextConditionType(cond_config["condition_type"]),
                    token_limit=cond_config.get("token_limit"),
                    overflow_multiplier=cond_config.get("overflow_multiplier"),
                    description=cond_config.get("description", ""),
                )
            )

        # Create three-dimensional complexity
        complexity_profile = ComplexityProfile.from_task_specification(task_spec)
        three_d_complexity = ThreeDimensionalComplexity(
            length_dimension=complexity_profile.length_dimension,
            depth_dimension=complexity_profile.depth_dimension,
            composition_dimension=complexity_profile.composition_metrics.composition_score,
            primary_stress_pillar=self.research_focus,
            secondary_stress_pillars=[],
            suggested_probe_density=len(self.probe_configuration),
            complexity_tier=self.difficulty_level,
        )

        # Apply template to task
        return TaskSpecification(
            task_id=task_spec.task_id,
            title=task_spec.title,
            domain=task_spec.domain,
            description=task_spec.description,
            checkpoints=task_spec.checkpoints,
            planning_phase=task_spec.planning_phase,
            repository=task_spec.repository,
            memory_challenges=task_spec.memory_challenges,
            complexity=task_spec.complexity,
            evaluation_config=task_spec.evaluation_config,
            enhanced_evaluation=True,
            memory_probes=memory_probes,
            context_conditions=context_conditions,
            three_dimensional_complexity=three_d_complexity,
            difficulty=self.difficulty_level,
            estimated_duration_minutes=self.estimated_duration_minutes,
            created_by=task_spec.created_by,
            version=task_spec.version,
            tags=task_spec.tags + self.tags + [f"template_{self.template_id}"],
        )

    def _select_target_checkpoint(
        self, checkpoints: List["CheckpointSpecification"], probe_index: int
    ) -> Optional["CheckpointSpecification"]:
        """Select appropriate checkpoint for probe injection"""
        if not checkpoints:
            return None

        # Avoid first checkpoint, distribute evenly
        available_checkpoints = checkpoints[1:] if len(checkpoints) > 1 else checkpoints

        if probe_index < len(available_checkpoints):
            step = max(1, len(available_checkpoints) // len(self.probe_configuration))
            target_index = min(probe_index * step, len(available_checkpoints) - 1)
            return available_checkpoints[target_index]

        return available_checkpoints[-1] if available_checkpoints else checkpoints[0]


@dataclass
class ConfigurationProfile:
    """
    Intelligent auto-configuration system for enhanced evaluation.

    Analyzes task characteristics and automatically configures
    appropriate enhanced evaluation features with smart defaults.
    """

    profile_id: str
    evaluation_mode: EvaluationMode
    auto_configure_probes: bool = True
    auto_configure_context: bool = True
    auto_configure_complexity: bool = True

    # Configuration preferences
    preferred_probe_density: Optional[int] = None
    preferred_context_conditions: List[ContextConditionType] = field(
        default_factory=list
    )
    complexity_bias: Optional[MemoryPillar] = None  # Bias toward specific pillar

    # Smart defaults
    enable_feature_flags: bool = True
    backward_compatibility_mode: bool = True
    progressive_disclosure_level: int = 2  # 1=simple, 2=research, 3=advanced

    def configure_task(self, task_spec: "TaskSpecification") -> "TaskSpecification":
        """Apply intelligent auto-configuration to task specification"""
        if task_spec.enhanced_evaluation and not self._should_reconfigure(task_spec):
            return task_spec  # Already configured appropriately

        # Analyze task characteristics
        complexity_profile = ComplexityProfile.from_task_specification(task_spec)

        # Configure based on evaluation mode
        if self.evaluation_mode == EvaluationMode.SIMPLE:
            return self._configure_simple_mode(task_spec)
        elif self.evaluation_mode == EvaluationMode.RESEARCH:
            return self._configure_research_mode(task_spec, complexity_profile)
        else:  # ADVANCED
            return self._configure_advanced_mode(task_spec, complexity_profile)

    def _should_reconfigure(self, task_spec: "TaskSpecification") -> bool:
        """Determine if task should be reconfigured"""
        # Reconfigure if mode doesn't match current configuration
        current_complexity = len(task_spec.get_all_probes())

        if self.evaluation_mode == EvaluationMode.SIMPLE and current_complexity > 0:
            return True
        elif (
            self.evaluation_mode == EvaluationMode.RESEARCH and current_complexity == 0
        ):
            return True
        elif self.evaluation_mode == EvaluationMode.ADVANCED and current_complexity < 3:
            return True

        return False

    def _configure_simple_mode(
        self, task_spec: "TaskSpecification"
    ) -> "TaskSpecification":
        """Configure for simple evaluation mode (Tier 1)"""
        # Simple mode = existing functionality, no enhanced features
        return TaskSpecification(
            task_id=task_spec.task_id,
            title=task_spec.title,
            domain=task_spec.domain,
            description=task_spec.description,
            checkpoints=task_spec.checkpoints,
            planning_phase=task_spec.planning_phase,
            repository=task_spec.repository,
            memory_challenges=task_spec.memory_challenges,
            complexity=task_spec.complexity,
            evaluation_config=task_spec.evaluation_config,
            enhanced_evaluation=False,  # Disable enhanced features
            memory_probes=[],
            context_conditions=[],
            three_dimensional_complexity=None,
            difficulty=task_spec.difficulty,
            estimated_duration_minutes=task_spec.estimated_duration_minutes,
            created_by=task_spec.created_by,
            version=task_spec.version,
            tags=task_spec.tags + ["simple_mode"],
        )

    def _configure_research_mode(
        self, task_spec: "TaskSpecification", complexity_profile: "ComplexityProfile"
    ) -> "TaskSpecification":
        """Configure for research evaluation mode (Tier 2)"""
        # Auto-configure probes based on complexity analysis
        memory_probes = []
        if self.auto_configure_probes:
            probe_density = (
                self.preferred_probe_density or complexity_profile.optimal_probe_density
            )
            probe_density = min(probe_density, 3)  # Limit for research mode

            # Select probes based on primary pillar or bias
            target_pillar = (
                self.complexity_bias or complexity_profile.primary_stress_pillar
            )
            probe_types = self._get_pillar_probe_types(target_pillar)[:probe_density]

            memory_probes = self._create_probes_for_types(
                probe_types, task_spec.checkpoints
            )

        # Auto-configure context conditions
        context_conditions = []
        if self.auto_configure_context:
            default_conditions = self.preferred_context_conditions or [
                ContextConditionType.STANDARDIZED,
                ContextConditionType.NATIVE,
            ]

            for cond_type in default_conditions:
                if cond_type == ContextConditionType.STANDARDIZED:
                    context_conditions.append(
                        ContextWindowCondition(
                            condition_name="standardized",
                            condition_type=cond_type,
                            token_limit=8192,
                            description="Standardized 8K context for fair comparison",
                        )
                    )
                elif cond_type == ContextConditionType.NATIVE:
                    context_conditions.append(
                        ContextWindowCondition(
                            condition_name="native",
                            condition_type=cond_type,
                            description="Agent's native context capacity",
                        )
                    )

        # Create three-dimensional complexity
        three_d_complexity = None
        if self.auto_configure_complexity:
            three_d_complexity = ThreeDimensionalComplexity(
                length_dimension=complexity_profile.length_dimension,
                depth_dimension=complexity_profile.depth_dimension,
                composition_dimension=complexity_profile.composition_metrics.composition_score,
                primary_stress_pillar=self.complexity_bias
                or complexity_profile.primary_stress_pillar,
                secondary_stress_pillars=complexity_profile.secondary_stress_pillars[
                    :1
                ],  # Limit for research mode
                suggested_probe_density=len(memory_probes),
                complexity_tier=complexity_profile.complexity_tier,
            )

        return TaskSpecification(
            task_id=task_spec.task_id,
            title=task_spec.title,
            domain=task_spec.domain,
            description=task_spec.description,
            checkpoints=task_spec.checkpoints,
            planning_phase=task_spec.planning_phase,
            repository=task_spec.repository,
            memory_challenges=task_spec.memory_challenges,
            complexity=task_spec.complexity,
            evaluation_config=task_spec.evaluation_config,
            enhanced_evaluation=True,
            memory_probes=memory_probes,
            context_conditions=context_conditions,
            three_dimensional_complexity=three_d_complexity,
            difficulty=task_spec.difficulty,
            estimated_duration_minutes=task_spec.estimated_duration_minutes,
            created_by=task_spec.created_by,
            version=task_spec.version,
            tags=task_spec.tags + ["research_mode", "auto_configured"],
        )

    def _configure_advanced_mode(
        self, task_spec: "TaskSpecification", complexity_profile: "ComplexityProfile"
    ) -> "TaskSpecification":
        """Configure for advanced evaluation mode (Tier 3)"""
        # Advanced mode provides full framework capabilities
        memory_probes = complexity_profile.auto_configure_probes_for_checkpoints(
            task_spec.checkpoints
        )

        # Full context condition set
        context_conditions = [
            ContextWindowCondition(
                condition_name="standardized",
                condition_type=ContextConditionType.STANDARDIZED,
                token_limit=8192,
                description="Standardized 8K context for fair comparison",
            ),
            ContextWindowCondition(
                condition_name="native",
                condition_type=ContextConditionType.NATIVE,
                description="Agent's native context capacity",
            ),
            ContextWindowCondition(
                condition_name="overflow",
                condition_type=ContextConditionType.OVERFLOW,
                overflow_multiplier=2.0,
                description="Forced context overflow to stress memory systems",
            ),
        ]

        # Full three-dimensional complexity
        three_d_complexity = ThreeDimensionalComplexity(
            length_dimension=complexity_profile.length_dimension,
            depth_dimension=complexity_profile.depth_dimension,
            composition_dimension=complexity_profile.composition_metrics.composition_score,
            primary_stress_pillar=complexity_profile.primary_stress_pillar,
            secondary_stress_pillars=complexity_profile.secondary_stress_pillars,
            suggested_probe_density=complexity_profile.optimal_probe_density,
            complexity_tier=complexity_profile.complexity_tier,
        )

        return TaskSpecification(
            task_id=task_spec.task_id,
            title=task_spec.title,
            domain=task_spec.domain,
            description=task_spec.description,
            checkpoints=task_spec.checkpoints,
            planning_phase=task_spec.planning_phase,
            repository=task_spec.repository,
            memory_challenges=task_spec.memory_challenges,
            complexity=task_spec.complexity,
            evaluation_config=task_spec.evaluation_config,
            enhanced_evaluation=True,
            memory_probes=memory_probes,
            context_conditions=context_conditions,
            three_dimensional_complexity=three_d_complexity,
            difficulty=task_spec.difficulty,
            estimated_duration_minutes=task_spec.estimated_duration_minutes,
            created_by=task_spec.created_by,
            version=task_spec.version,
            tags=task_spec.tags + ["advanced_mode", "full_framework"],
        )

    def _get_pillar_probe_types(self, pillar: MemoryPillar) -> List[ProbeType]:
        """Get probe types for specific memory pillar"""
        if pillar == MemoryPillar.MEMORY_FIDELITY:
            return [ProbeType.N_BACK_INTEGRATION, ProbeType.COMPRESSION_STRESS]
        elif pillar == MemoryPillar.CONTEXTUAL_RELEVANCE:
            return [ProbeType.DISTRACTOR_INJECTION, ProbeType.CHANGE_DETECTION]
        elif pillar == MemoryPillar.BEHAVIORAL_INTEGRITY:
            return [ProbeType.UPDATE_ROBUSTNESS, ProbeType.CONTEXT_SWITCH]
        else:
            return [ProbeType.N_BACK_INTEGRATION]

    def _create_probes_for_types(
        self, probe_types: List[ProbeType], checkpoints: List["CheckpointSpecification"]
    ) -> List[MemoryProbe]:
        """Create memory probes for specified types"""
        probes = []

        # Select target checkpoints
        available_checkpoints = checkpoints[1:] if len(checkpoints) > 1 else checkpoints

        for i, probe_type in enumerate(probe_types):
            if i < len(available_checkpoints):
                checkpoint = available_checkpoints[i]
                probe = self._create_probe(probe_type, checkpoint.checkpoint_id, i + 1)
                probes.append(probe)

        return probes

    def _create_probe(
        self, probe_type: ProbeType, checkpoint_id: str, probe_number: int
    ) -> MemoryProbe:
        """Create a memory probe of specified type"""
        pillar_map = {
            ProbeType.N_BACK_INTEGRATION: MemoryPillar.MEMORY_FIDELITY,
            ProbeType.COMPRESSION_STRESS: MemoryPillar.MEMORY_FIDELITY,
            ProbeType.DISTRACTOR_INJECTION: MemoryPillar.CONTEXTUAL_RELEVANCE,
            ProbeType.CHANGE_DETECTION: MemoryPillar.CONTEXTUAL_RELEVANCE,
            ProbeType.UPDATE_ROBUSTNESS: MemoryPillar.BEHAVIORAL_INTEGRITY,
            ProbeType.CONTEXT_SWITCH: MemoryPillar.BEHAVIORAL_INTEGRITY,
        }

        descriptions = {
            ProbeType.N_BACK_INTEGRATION: "Test recall of specifications from previous checkpoints",
            ProbeType.COMPRESSION_STRESS: "Test information retention after context compression",
            ProbeType.DISTRACTOR_INJECTION: "Test filtering of relevant vs irrelevant information",
            ProbeType.CHANGE_DETECTION: "Test detection of critical specification changes",
            ProbeType.UPDATE_ROBUSTNESS: "Test propagation of requirement changes",
            ProbeType.CONTEXT_SWITCH: "Test resumption after task interruption",
        }

        # Configure probe-specific parameters
        probe_config = {}
        if probe_type == ProbeType.N_BACK_INTEGRATION:
            probe_config["n_back_distance"] = min(3, probe_number)
        elif probe_type == ProbeType.DISTRACTOR_INJECTION:
            probe_config["distractor_ratio"] = 0.3
        elif probe_type == ProbeType.CHANGE_DETECTION:
            probe_config["change_percentage"] = 0.01
        elif probe_type == ProbeType.CONTEXT_SWITCH:
            probe_config["interruption_duration"] = 5

        return MemoryProbe(
            probe_id=f"config_probe_{probe_number}_{probe_type.value}",
            probe_type=probe_type,
            pillar=pillar_map[probe_type],
            target_checkpoint=checkpoint_id,
            description=descriptions[probe_type],
            **probe_config,
        )


@dataclass
class MemoryProbe:
    """
    Memory probe specification for pillar-specific testing.

    Represents a controlled memory challenge that tests specific aspects
    of working memory performance at strategic points in task execution.
    """

    probe_id: str
    probe_type: ProbeType
    pillar: MemoryPillar
    target_checkpoint: str  # Checkpoint where probe is injected
    description: str

    # Probe-specific configuration
    n_back_distance: Optional[int] = None  # For N-back integration probes
    distractor_ratio: Optional[float] = None  # For distractor injection probes
    change_percentage: Optional[float] = None  # For change detection probes
    interruption_duration: Optional[int] = None  # For context switch probes

    # Scoring configuration
    binary_scoring: bool = True  # Use binary pass/fail scoring
    timeout_seconds: int = 300  # Maximum time for probe response
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate probe configuration"""
        if not self.probe_id or not self.target_checkpoint:
            raise ValueError("probe_id and target_checkpoint are required")


@dataclass
class ContextWindowCondition:
    """
    Context window experimental condition specification.

    Defines how context window constraints are applied during evaluation
    to enable controlled comparison across different memory system capabilities.
    """

    condition_name: str
    condition_type: ContextConditionType
    token_limit: Optional[int] = None  # Fixed limit for standardized conditions
    overflow_multiplier: Optional[
        float
    ] = None  # For overflow conditions (e.g., 2.0 = 2x native)
    description: str = ""

    def __post_init__(self):
        """Validate context condition configuration"""
        if (
            self.condition_type == ContextConditionType.STANDARDIZED
            and not self.token_limit
        ):
            raise ValueError("Standardized conditions require token_limit")
        if (
            self.condition_type == ContextConditionType.OVERFLOW
            and not self.overflow_multiplier
        ):
            raise ValueError("Overflow conditions require overflow_multiplier")


@dataclass
class ThreeDimensionalComplexity:
    """
    Enhanced three-dimensional complexity specification.

    Extends the existing complexity framework with enhanced pillar mapping
    and automatic probe configuration capabilities.
    """

    length_dimension: int  # Temporal complexity (checkpoint count)
    depth_dimension: int  # Informational complexity (tokens per checkpoint)
    composition_dimension: float  # Structural complexity (components × integration)

    # Enhanced pillar mapping
    primary_stress_pillar: MemoryPillar
    secondary_stress_pillars: List[MemoryPillar] = field(default_factory=list)

    # Automatic probe configuration
    suggested_probe_density: int = 3  # Probes per pillar
    complexity_tier: str = "medium"  # low, medium, high, extreme

    def calculate_difficulty_score(self) -> float:
        """Calculate overall difficulty score from three dimensions"""
        length_factor = min(self.length_dimension / 10.0, 1.0)
        depth_factor = min(self.depth_dimension / 500.0, 1.0)
        composition_factor = min(self.composition_dimension / 15.0, 1.0)

        return length_factor * depth_factor * composition_factor

    def get_recommended_probes(self) -> List[ProbeType]:
        """Get recommended probe types based on complexity profile"""
        probes = []

        # Primary pillar gets more probes
        if self.primary_stress_pillar == MemoryPillar.MEMORY_FIDELITY:
            probes.extend([ProbeType.N_BACK_INTEGRATION, ProbeType.COMPRESSION_STRESS])
        elif self.primary_stress_pillar == MemoryPillar.CONTEXTUAL_RELEVANCE:
            probes.extend([ProbeType.DISTRACTOR_INJECTION, ProbeType.CHANGE_DETECTION])
        elif self.primary_stress_pillar == MemoryPillar.BEHAVIORAL_INTEGRITY:
            probes.extend([ProbeType.UPDATE_ROBUSTNESS, ProbeType.CONTEXT_SWITCH])

        # Add secondary pillar probes
        for pillar in self.secondary_stress_pillars:
            if (
                pillar == MemoryPillar.MEMORY_FIDELITY
                and ProbeType.N_BACK_INTEGRATION not in probes
            ):
                probes.append(ProbeType.N_BACK_INTEGRATION)
            elif (
                pillar == MemoryPillar.CONTEXTUAL_RELEVANCE
                and ProbeType.DISTRACTOR_INJECTION not in probes
            ):
                probes.append(ProbeType.DISTRACTOR_INJECTION)
            elif (
                pillar == MemoryPillar.BEHAVIORAL_INTEGRITY
                and ProbeType.UPDATE_ROBUSTNESS not in probes
            ):
                probes.append(ProbeType.UPDATE_ROBUSTNESS)

        return probes


@dataclass
class CheckpointSpecification:
    """
    Individual checkpoint within a WorkMemEval task.

    Represents a controlled measurement point with specific requirements,
    test criteria, and dependency relationships. Enhanced with optional
    memory probe support for backward compatibility.
    """

    checkpoint_id: str
    order: int
    title: str
    stub_file: str  # File where implementation is required
    stub_function: str  # Function/class to implement
    requirements: str  # Natural language requirements
    test_file: str  # Pytest file that must pass
    dependencies: List[str] = field(default_factory=list)  # Other checkpoint IDs
    checkpoint_type: CheckpointType = CheckpointType.IMPLEMENTATION
    estimated_tokens: int = 200  # Estimated complexity (depth dimension)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Enhanced evaluation fields (optional for backward compatibility)
    embedded_probes: List[MemoryProbe] = field(default_factory=list)
    context_conditions: List[ContextWindowCondition] = field(default_factory=list)
    pillar_stress_target: Optional[MemoryPillar] = None

    def __post_init__(self):
        """Validate checkpoint specification"""
        if not self.checkpoint_id:
            raise ValueError("checkpoint_id cannot be empty")
        if not self.stub_file or not self.test_file:
            raise ValueError("stub_file and test_file are required")
        if self.order < 1:
            raise ValueError("order must be >= 1")


@dataclass
class MemoryChallenge:
    """
    Working memory challenge injection point.

    Represents controlled stress testing of working memory through
    requirement changes, interruptions, or information overload.
    """

    challenge_id: str
    challenge_type: MemoryChallengeType
    at_checkpoint: str  # Checkpoint ID where challenge occurs
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Type-specific fields
    affects: List[str] = field(default_factory=list)  # For requirement updates
    interruption_task: Optional[str] = None  # For context switches
    duration_minutes: Optional[int] = None  # For context switches
    distractor_files: List[str] = field(
        default_factory=list
    )  # For information overload


@dataclass
class PlanningPhase:
    """
    Planning phase configuration for establishing baseline plan.

    The planning phase captures the agent's initial approach strategy
    for later compliance tracking during execution.
    """

    overview_prompt: str
    planning_deliverables: Dict[str, str] = field(default_factory=dict)
    planning_capture: Dict[str, Any] = field(default_factory=dict)
    max_planning_time_minutes: int = 15
    required_sections: List[str] = field(default_factory=list)


@dataclass
class RepositoryTemplate:
    """
    Repository template configuration defining the starting codebase.

    Includes provided files, distractor files for testing contextual relevance,
    and organizational structure.
    """

    template_name: str
    provided_files: List[str] = field(default_factory=list)
    distractor_files: List[str] = field(default_factory=list)  # For relevance testing
    directory_structure: Dict[str, List[str]] = field(default_factory=dict)
    setup_commands: List[str] = field(default_factory=list)


@dataclass
class CompositionMetrics:
    """
    Detailed composition complexity measurement.

    Provides granular analysis of structural complexity through
    component count and integration density calculation.
    """

    component_count: int
    integration_density: float
    composition_score: float

    # Detailed component analysis
    semantic_components: List[str] = field(default_factory=list)
    component_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    integration_interfaces: List[str] = field(default_factory=list)

    @classmethod
    def from_checkpoint_structure(
        cls, checkpoints: List["CheckpointSpecification"]
    ) -> "CompositionMetrics":
        """Calculate composition metrics from checkpoint structure"""
        if not checkpoints:
            return cls(0, 0.0, 0.0)

        # Extract semantic components from checkpoints
        components = []
        dependencies = {}
        interfaces = []

        for cp in checkpoints:
            component_name = cp.title
            components.append(component_name)
            dependencies[component_name] = cp.dependencies

            # Extract integration interfaces from requirements
            if (
                "integrate" in cp.requirements.lower()
                or "interface" in cp.requirements.lower()
            ):
                interfaces.append(f"{component_name}_interface")

        # Calculate metrics
        component_count = len(components)
        total_deps = sum(len(deps) for deps in dependencies.values())
        integration_density = (
            total_deps / component_count if component_count > 0 else 0.0
        )
        composition_score = component_count * integration_density

        return cls(
            component_count=component_count,
            integration_density=integration_density,
            composition_score=composition_score,
            semantic_components=components,
            component_dependencies=dependencies,
            integration_interfaces=interfaces,
        )

    def get_complexity_tier(self) -> str:
        """Determine complexity tier based on composition score"""
        if self.composition_score < 5:
            return "simple"
        elif self.composition_score < 10:
            return "moderate"
        elif self.composition_score < 20:
            return "complex"
        else:
            return "highly_complex"

    def get_primary_stress_pillar(self) -> MemoryPillar:
        """Determine which pillar is primarily stressed by composition complexity"""
        if self.integration_density > 2.0:
            return MemoryPillar.BEHAVIORAL_INTEGRITY  # High integration stress
        elif self.component_count > 8:
            return MemoryPillar.CONTEXTUAL_RELEVANCE  # Many components to track
        else:
            return MemoryPillar.MEMORY_FIDELITY  # Default to fidelity


@dataclass
class TaskComplexityMetrics:
    """
    Three-dimensional task complexity measurement.

    Implements the Length × Depth × Composition complexity space
    for systematic difficulty scaling.
    """

    length: int  # Number of sequential checkpoints
    depth: float  # Average tokens per checkpoint specification
    composition: float  # Component count × integration density

    # Component analysis
    semantic_components: List[str] = field(default_factory=list)
    component_dependencies: Dict[str, List[str]] = field(default_factory=dict)

    def calculate_composition_score(self) -> float:
        """Calculate composition complexity score (C × I)"""
        if not self.semantic_components:
            return 0

        if not self.component_dependencies:
            return len(self.semantic_components)

        total_dependencies = sum(
            len(deps) for deps in self.component_dependencies.values()
        )

        # If no dependencies exist at all (all empty lists), return component count
        if total_dependencies == 0:
            return len(self.semantic_components)

        integration_density = total_dependencies / len(self.semantic_components)
        return len(self.semantic_components) * integration_density

    def __post_init__(self):
        """Auto-calculate composition if component data provided"""
        if self.semantic_components and self.component_dependencies:
            self.composition = self.calculate_composition_score()


@dataclass
class ComplexityProfile:
    """
    Enhanced complexity profile that extends TaskComplexityMetrics.

    Provides comprehensive complexity analysis with pillar mapping
    and automatic probe configuration capabilities.
    """

    # Core three-dimensional metrics
    length_dimension: int  # Temporal complexity
    depth_dimension: int  # Informational complexity
    composition_metrics: CompositionMetrics  # Structural complexity

    # Enhanced analysis
    overall_difficulty_score: float
    complexity_tier: str  # simple, moderate, complex, highly_complex

    # Pillar mapping
    primary_stress_pillar: MemoryPillar
    secondary_stress_pillars: List[MemoryPillar] = field(default_factory=list)
    pillar_stress_scores: Dict[MemoryPillar, float] = field(default_factory=dict)

    # Probe configuration
    recommended_probe_types: List[ProbeType] = field(default_factory=list)
    optimal_probe_density: int = 3
    probe_injection_points: List[int] = field(default_factory=list)  # Checkpoint orders

    @classmethod
    def from_task_specification(
        cls, task_spec: "TaskSpecification"
    ) -> "ComplexityProfile":
        """Create complexity profile from task specification"""
        checkpoints = task_spec.checkpoints

        # Calculate dimensions
        length_dim = len(checkpoints)
        depth_dim = (
            int(sum(cp.estimated_tokens for cp in checkpoints) / len(checkpoints))
            if checkpoints
            else 200
        )
        composition_metrics = CompositionMetrics.from_checkpoint_structure(checkpoints)

        # Calculate overall difficulty
        length_factor = min(length_dim / 10.0, 1.0)
        depth_factor = min(depth_dim / 500.0, 1.0)
        composition_factor = min(composition_metrics.composition_score / 15.0, 1.0)
        difficulty_score = length_factor * depth_factor * composition_factor

        # Determine complexity tier
        if difficulty_score < 0.3:
            tier = "simple"
        elif difficulty_score < 0.6:
            tier = "moderate"
        elif difficulty_score < 0.9:
            tier = "complex"
        else:
            tier = "highly_complex"

        # Calculate pillar stress scores
        pillar_scores = cls._calculate_pillar_stress_scores(
            length_dim, depth_dim, composition_metrics
        )

        # Determine primary and secondary pillars
        sorted_pillars = sorted(pillar_scores.items(), key=lambda x: x[1], reverse=True)
        primary_pillar = sorted_pillars[0][0]
        secondary_pillars = [
            pillar for pillar, score in sorted_pillars[1:] if score > 0.3
        ]

        # Generate probe recommendations
        recommended_probes = cls._recommend_probe_types(
            primary_pillar, secondary_pillars, tier
        )
        probe_density = cls._calculate_optimal_probe_density(length_dim, tier)
        injection_points = cls._calculate_probe_injection_points(
            length_dim, probe_density
        )

        return cls(
            length_dimension=length_dim,
            depth_dimension=depth_dim,
            composition_metrics=composition_metrics,
            overall_difficulty_score=difficulty_score,
            complexity_tier=tier,
            primary_stress_pillar=primary_pillar,
            secondary_stress_pillars=secondary_pillars,
            pillar_stress_scores=pillar_scores,
            recommended_probe_types=recommended_probes,
            optimal_probe_density=probe_density,
            probe_injection_points=injection_points,
        )

    @staticmethod
    def _calculate_pillar_stress_scores(
        length: int, depth: int, composition: CompositionMetrics
    ) -> Dict[MemoryPillar, float]:
        """Calculate stress scores for each memory pillar"""
        # Memory Fidelity: stressed by length (temporal demands)
        fidelity_score = min(length / 10.0, 1.0)

        # Contextual Relevance: stressed by depth (information filtering)
        relevance_score = min(depth / 500.0, 1.0)

        # Behavioral Integrity: stressed by composition (coordination demands)
        integrity_score = min(composition.composition_score / 15.0, 1.0)

        return {
            MemoryPillar.MEMORY_FIDELITY: fidelity_score,
            MemoryPillar.CONTEXTUAL_RELEVANCE: relevance_score,
            MemoryPillar.BEHAVIORAL_INTEGRITY: integrity_score,
        }

    @staticmethod
    def _recommend_probe_types(
        primary_pillar: MemoryPillar,
        secondary_pillars: List[MemoryPillar],
        complexity_tier: str,
    ) -> List[ProbeType]:
        """Recommend probe types based on pillar stress analysis"""
        probes = []

        # Primary pillar gets 2 probe types
        if primary_pillar == MemoryPillar.MEMORY_FIDELITY:
            probes.extend([ProbeType.N_BACK_INTEGRATION, ProbeType.COMPRESSION_STRESS])
        elif primary_pillar == MemoryPillar.CONTEXTUAL_RELEVANCE:
            probes.extend([ProbeType.DISTRACTOR_INJECTION, ProbeType.CHANGE_DETECTION])
        elif primary_pillar == MemoryPillar.BEHAVIORAL_INTEGRITY:
            probes.extend([ProbeType.UPDATE_ROBUSTNESS, ProbeType.CONTEXT_SWITCH])

        # Secondary pillars get 1 probe type each
        for pillar in secondary_pillars:
            if (
                pillar == MemoryPillar.MEMORY_FIDELITY
                and ProbeType.N_BACK_INTEGRATION not in probes
            ):
                probes.append(ProbeType.N_BACK_INTEGRATION)
            elif (
                pillar == MemoryPillar.CONTEXTUAL_RELEVANCE
                and ProbeType.DISTRACTOR_INJECTION not in probes
            ):
                probes.append(ProbeType.DISTRACTOR_INJECTION)
            elif (
                pillar == MemoryPillar.BEHAVIORAL_INTEGRITY
                and ProbeType.UPDATE_ROBUSTNESS not in probes
            ):
                probes.append(ProbeType.UPDATE_ROBUSTNESS)

        # Limit probes based on complexity tier
        max_probes = {"simple": 2, "moderate": 3, "complex": 4, "highly_complex": 6}
        return probes[: max_probes.get(complexity_tier, 3)]

    @staticmethod
    def _calculate_optimal_probe_density(length: int, complexity_tier: str) -> int:
        """Calculate optimal number of probes for task length and complexity"""
        base_density = {"simple": 1, "moderate": 2, "complex": 3, "highly_complex": 4}
        base = base_density.get(complexity_tier, 2)

        # Adjust for task length
        if length < 5:
            return max(1, base - 1)
        elif length > 10:
            return min(6, base + 1)
        else:
            return base

    @staticmethod
    def _calculate_probe_injection_points(length: int, probe_density: int) -> List[int]:
        """Calculate optimal checkpoint orders for probe injection"""
        if probe_density >= length:
            return list(range(1, length + 1))

        # Avoid first checkpoint, distribute evenly
        available_points = list(range(2, length + 1)) if length > 1 else [1]
        step = max(1, len(available_points) // probe_density)

        injection_points = []
        for i in range(0, len(available_points), step):
            if len(injection_points) < probe_density:
                injection_points.append(available_points[i])

        return injection_points

    def get_complexity_to_pillar_mapping(self) -> Dict[str, MemoryPillar]:
        """Get mapping from complexity dimensions to primary stress pillars"""
        return {
            "length": MemoryPillar.MEMORY_FIDELITY,
            "depth": MemoryPillar.CONTEXTUAL_RELEVANCE,
            "composition": MemoryPillar.BEHAVIORAL_INTEGRITY,
        }

    def auto_configure_probes_for_checkpoints(
        self, checkpoints: List["CheckpointSpecification"]
    ) -> List[MemoryProbe]:
        """Auto-configure memory probes for specific checkpoints"""
        probes = []

        # Select checkpoints for probe injection
        target_checkpoints = []
        for order in self.probe_injection_points:
            checkpoint = next((cp for cp in checkpoints if cp.order == order), None)
            if checkpoint:
                target_checkpoints.append(checkpoint)

        # Create probes
        for i, probe_type in enumerate(self.recommended_probe_types):
            if i < len(target_checkpoints):
                checkpoint = target_checkpoints[i]
                probe = self._create_auto_probe(
                    probe_type, checkpoint.checkpoint_id, i + 1
                )
                probes.append(probe)

        return probes

    def _create_auto_probe(
        self, probe_type: ProbeType, checkpoint_id: str, probe_number: int
    ) -> MemoryProbe:
        """Create an automatically configured probe"""
        pillar_map = {
            ProbeType.N_BACK_INTEGRATION: MemoryPillar.MEMORY_FIDELITY,
            ProbeType.COMPRESSION_STRESS: MemoryPillar.MEMORY_FIDELITY,
            ProbeType.DISTRACTOR_INJECTION: MemoryPillar.CONTEXTUAL_RELEVANCE,
            ProbeType.CHANGE_DETECTION: MemoryPillar.CONTEXTUAL_RELEVANCE,
            ProbeType.UPDATE_ROBUSTNESS: MemoryPillar.BEHAVIORAL_INTEGRITY,
            ProbeType.CONTEXT_SWITCH: MemoryPillar.BEHAVIORAL_INTEGRITY,
        }

        descriptions = {
            ProbeType.N_BACK_INTEGRATION: f"Recall specifications from {min(3, probe_number)} checkpoints prior",
            ProbeType.COMPRESSION_STRESS: "Maintain functionality after context compression",
            ProbeType.DISTRACTOR_INJECTION: "Filter relevant from irrelevant requirements",
            ProbeType.CHANGE_DETECTION: "Detect critical specification changes",
            ProbeType.UPDATE_ROBUSTNESS: "Propagate requirement changes to dependent components",
            ProbeType.CONTEXT_SWITCH: "Resume task after interruption",
        }

        # Configure probe-specific parameters
        probe_config = {}
        if probe_type == ProbeType.N_BACK_INTEGRATION:
            probe_config["n_back_distance"] = min(3, max(1, self.length_dimension // 3))
        elif probe_type == ProbeType.DISTRACTOR_INJECTION:
            probe_config["distractor_ratio"] = (
                0.3 if self.complexity_tier in ["simple", "moderate"] else 0.5
            )
        elif probe_type == ProbeType.CHANGE_DETECTION:
            probe_config["change_percentage"] = 0.01  # 1% critical changes
        elif probe_type == ProbeType.CONTEXT_SWITCH:
            probe_config["interruption_duration"] = (
                5 if self.complexity_tier in ["simple", "moderate"] else 10
            )

        return MemoryProbe(
            probe_id=f"auto_{probe_type.value}_{probe_number}",
            probe_type=probe_type,
            pillar=pillar_map[probe_type],
            target_checkpoint=checkpoint_id,
            description=descriptions[probe_type],
            **probe_config,
        )


@dataclass
class EvaluationConfiguration:
    """
    Configuration for evaluation behavior and metric calculation.
    """

    memory_checkpoint_frequency: int = 3  # Memory snapshots every N checkpoints
    planning_compliance_tracking: bool = True
    trace_capture_level: str = "detailed"  # basic, detailed, comprehensive
    success_criteria: Dict[str, bool] = field(
        default_factory=lambda: {
            "all_tests_pass": True,
            "no_breaking_changes": True,
            "integration_functional": True,
            "planning_phase_completed": True,
        }
    )
    timeout_minutes: int = 180
    enable_memory_challenges: bool = True


@dataclass
class TaskSpecification:
    """
    Complete WorkMemEval task specification.

    Represents a full task including metadata, checkpoints, memory challenges,
    complexity metrics, and evaluation configuration. Enhanced with optional
    memory probe support while maintaining full backward compatibility.
    """

    task_id: str
    title: str
    domain: str  # e.g., "api_service", "data_processing"
    description: str

    # Core task structure
    checkpoints: List[CheckpointSpecification]
    planning_phase: PlanningPhase
    repository: RepositoryTemplate

    # Working memory challenges
    memory_challenges: List[MemoryChallenge] = field(default_factory=list)

    # Complexity and evaluation
    complexity: TaskComplexityMetrics = field(default=None)
    evaluation_config: EvaluationConfiguration = field(
        default_factory=EvaluationConfiguration
    )

    # Enhanced evaluation fields (optional for backward compatibility)
    enhanced_evaluation: bool = False
    memory_probes: List[MemoryProbe] = field(default_factory=list)
    context_conditions: List[ContextWindowCondition] = field(default_factory=list)
    three_dimensional_complexity: Optional[ThreeDimensionalComplexity] = None

    # Metadata
    difficulty: str = "medium"  # beginner, intermediate, advanced, expert
    estimated_duration_minutes: int = 90
    created_by: str = ""
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate task specification and auto-calculate complexity"""
        if not self.task_id or not self.title:
            raise ValueError("task_id and title are required")

        if not self.checkpoints:
            raise ValueError("Task must have at least one checkpoint")

        # Auto-detect enhanced evaluation features
        self._detect_enhanced_features()

        # Auto-calculate complexity metrics if not provided
        if self.complexity is None:
            self.complexity = self._calculate_complexity()

        # Validate checkpoint order and dependencies
        self._validate_checkpoint_dependencies()

    def _calculate_complexity(self) -> TaskComplexityMetrics:
        """Auto-calculate task complexity from checkpoint structure"""
        length = len(self.checkpoints)
        depth = (
            sum(cp.estimated_tokens for cp in self.checkpoints) / length
            if self.checkpoints
            else 0
        )

        # Extract semantic components from checkpoint titles and dependencies
        components = []
        dependencies = {}

        for cp in self.checkpoints:
            component_name = cp.title
            components.append(component_name)
            dependencies[component_name] = cp.dependencies

        return TaskComplexityMetrics(
            length=length,
            depth=depth,
            composition=0,  # Will be calculated in __post_init__
            semantic_components=components,
            component_dependencies=dependencies,
        )

    def get_enhanced_complexity_profile(self) -> ComplexityProfile:
        """Get enhanced complexity profile with pillar mapping and probe recommendations"""
        return ComplexityProfile.from_task_specification(self)

    def auto_configure_enhanced_features(self) -> "TaskSpecification":
        """Auto-configure enhanced evaluation features based on complexity analysis"""
        if self.enhanced_evaluation:
            return self  # Already configured

        # Get complexity profile
        complexity_profile = self.get_enhanced_complexity_profile()

        # Create three-dimensional complexity
        three_d_complexity = ThreeDimensionalComplexity(
            length_dimension=complexity_profile.length_dimension,
            depth_dimension=complexity_profile.depth_dimension,
            composition_dimension=complexity_profile.composition_metrics.composition_score,
            primary_stress_pillar=complexity_profile.primary_stress_pillar,
            secondary_stress_pillars=complexity_profile.secondary_stress_pillars,
            suggested_probe_density=complexity_profile.optimal_probe_density,
            complexity_tier=complexity_profile.complexity_tier,
        )

        # Auto-configure probes
        memory_probes = complexity_profile.auto_configure_probes_for_checkpoints(
            self.checkpoints
        )

        # Create default context conditions
        context_conditions = [
            ContextWindowCondition(
                condition_name="standardized",
                condition_type=ContextConditionType.STANDARDIZED,
                token_limit=8192,
                description="Standardized 8K context window for fair comparison",
            ),
            ContextWindowCondition(
                condition_name="native",
                condition_type=ContextConditionType.NATIVE,
                description="Agent's native context window capacity",
            ),
        ]

        # Create enhanced task
        return TaskSpecification(
            task_id=self.task_id,
            title=self.title,
            domain=self.domain,
            description=self.description,
            checkpoints=self.checkpoints,
            planning_phase=self.planning_phase,
            repository=self.repository,
            memory_challenges=self.memory_challenges,
            complexity=self.complexity,
            evaluation_config=self.evaluation_config,
            enhanced_evaluation=True,
            memory_probes=memory_probes,
            context_conditions=context_conditions,
            three_dimensional_complexity=three_d_complexity,
            difficulty=self.difficulty,
            estimated_duration_minutes=self.estimated_duration_minutes,
            created_by=self.created_by,
            version=self.version,
            tags=self.tags + ["auto_configured"],
        )

    def _detect_enhanced_features(self):
        """Auto-detect if task uses enhanced evaluation features"""
        has_probes = bool(self.memory_probes) or any(
            cp.embedded_probes for cp in self.checkpoints
        )
        has_context_conditions = bool(self.context_conditions) or any(
            cp.context_conditions for cp in self.checkpoints
        )
        has_three_d_complexity = self.three_dimensional_complexity is not None
        has_pillar_targets = any(cp.pillar_stress_target for cp in self.checkpoints)

        if (
            has_probes
            or has_context_conditions
            or has_three_d_complexity
            or has_pillar_targets
        ):
            self.enhanced_evaluation = True

    def _validate_checkpoint_dependencies(self):
        """Validate that all checkpoint dependencies exist and form valid DAG"""
        checkpoint_ids = {cp.checkpoint_id for cp in self.checkpoints}

        for cp in self.checkpoints:
            for dep_id in cp.dependencies:
                if dep_id not in checkpoint_ids:
                    raise ValueError(
                        f"Checkpoint {cp.checkpoint_id} depends on non-existent checkpoint {dep_id}"
                    )

        # TODO: Add cycle detection for dependency graph

    def is_enhanced_evaluation(self) -> bool:
        """Check if task uses enhanced evaluation features"""
        return self.enhanced_evaluation

    def get_all_probes(self) -> List[MemoryProbe]:
        """Get all memory probes from task and checkpoints"""
        all_probes = list(self.memory_probes)
        for checkpoint in self.checkpoints:
            all_probes.extend(checkpoint.embedded_probes)
        return all_probes

    def get_probes_for_checkpoint(self, checkpoint_id: str) -> List[MemoryProbe]:
        """Get all probes that target a specific checkpoint"""
        probes = []

        # Task-level probes targeting this checkpoint
        for probe in self.memory_probes:
            if probe.target_checkpoint == checkpoint_id:
                probes.append(probe)

        # Embedded probes in this checkpoint
        checkpoint = self.get_checkpoint_by_id(checkpoint_id)
        if checkpoint:
            probes.extend(checkpoint.embedded_probes)

        return probes

    def get_checkpoint_by_id(
        self, checkpoint_id: str
    ) -> Optional[CheckpointSpecification]:
        """Get checkpoint by ID"""
        return next(
            (cp for cp in self.checkpoints if cp.checkpoint_id == checkpoint_id), None
        )

    def get_required_files_for_checkpoint(self, checkpoint_id: str) -> set:
        """
        Calculate which files are required for a given checkpoint.

        This is crucial for contextual relevance metric calculation.
        """
        checkpoint = self.get_checkpoint_by_id(checkpoint_id)
        if not checkpoint:
            return set()

        required = set()

        # Direct checkpoint files
        required.add(checkpoint.stub_file)
        required.add(checkpoint.test_file)

        # Dependency checkpoint files
        for dep_id in checkpoint.dependencies:
            dep_checkpoint = self.get_checkpoint_by_id(dep_id)
            if dep_checkpoint:
                required.add(dep_checkpoint.stub_file)

        # Common files
        required.update(["requirements.txt", "README.md"])

        return required

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization with backward compatibility"""
        result = {
            "task_id": self.task_id,
            "title": self.title,
            "domain": self.domain,
            "description": self.description,
            "difficulty": self.difficulty,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "checkpoints": [
                {
                    "checkpoint_id": cp.checkpoint_id,
                    "order": cp.order,
                    "title": cp.title,
                    "stub_file": cp.stub_file,
                    "stub_function": cp.stub_function,
                    "requirements": cp.requirements,
                    "test_file": cp.test_file,
                    "dependencies": cp.dependencies,
                    "checkpoint_type": cp.checkpoint_type.value,
                    "estimated_tokens": cp.estimated_tokens,
                    "metadata": cp.metadata,
                    # Enhanced fields (only include if present)
                    **(
                        {
                            "embedded_probes": [
                                {
                                    "probe_id": probe.probe_id,
                                    "probe_type": probe.probe_type.value,
                                    "pillar": probe.pillar.value,
                                    "target_checkpoint": probe.target_checkpoint,
                                    "description": probe.description,
                                    "n_back_distance": probe.n_back_distance,
                                    "distractor_ratio": probe.distractor_ratio,
                                    "change_percentage": probe.change_percentage,
                                    "interruption_duration": probe.interruption_duration,
                                    "binary_scoring": probe.binary_scoring,
                                    "timeout_seconds": probe.timeout_seconds,
                                    "metadata": probe.metadata,
                                }
                                for probe in cp.embedded_probes
                            ]
                        }
                        if cp.embedded_probes
                        else {}
                    ),
                    **(
                        {
                            "context_conditions": [
                                {
                                    "condition_name": cond.condition_name,
                                    "condition_type": cond.condition_type.value,
                                    "token_limit": cond.token_limit,
                                    "overflow_multiplier": cond.overflow_multiplier,
                                    "description": cond.description,
                                }
                                for cond in cp.context_conditions
                            ]
                        }
                        if cp.context_conditions
                        else {}
                    ),
                    **(
                        {"pillar_stress_target": cp.pillar_stress_target.value}
                        if cp.pillar_stress_target
                        else {}
                    ),
                }
                for cp in self.checkpoints
            ],
            "planning_phase": {
                "overview_prompt": self.planning_phase.overview_prompt,
                "planning_deliverables": self.planning_phase.planning_deliverables,
                "planning_capture": self.planning_phase.planning_capture,
                "max_planning_time_minutes": self.planning_phase.max_planning_time_minutes,
                "required_sections": self.planning_phase.required_sections,
            },
            "repository": {
                "template_name": self.repository.template_name,
                "provided_files": self.repository.provided_files,
                "distractor_files": self.repository.distractor_files,
                "directory_structure": self.repository.directory_structure,
                "setup_commands": self.repository.setup_commands,
            },
            "memory_challenges": [
                {
                    "challenge_id": mc.challenge_id,
                    "challenge_type": mc.challenge_type.value,
                    "at_checkpoint": mc.at_checkpoint,
                    "description": mc.description,
                    "metadata": mc.metadata,
                    "affects": mc.affects,
                    "interruption_task": mc.interruption_task,
                    "duration_minutes": mc.duration_minutes,
                    "distractor_files": mc.distractor_files,
                }
                for mc in self.memory_challenges
            ],
            "complexity": {
                "length": self.complexity.length,
                "depth": self.complexity.depth,
                "composition": self.complexity.composition,
                "semantic_components": self.complexity.semantic_components,
                "component_dependencies": self.complexity.component_dependencies,
            },
            "evaluation_config": {
                "memory_checkpoint_frequency": self.evaluation_config.memory_checkpoint_frequency,
                "planning_compliance_tracking": self.evaluation_config.planning_compliance_tracking,
                "trace_capture_level": self.evaluation_config.trace_capture_level,
                "success_criteria": self.evaluation_config.success_criteria,
                "timeout_minutes": self.evaluation_config.timeout_minutes,
                "enable_memory_challenges": self.evaluation_config.enable_memory_challenges,
            },
            "metadata": {
                "created_by": self.created_by,
                "version": self.version,
                "tags": self.tags,
            },
        }

        # Add enhanced evaluation fields only if present
        if self.enhanced_evaluation:
            result["enhanced_evaluation"] = True

            if self.memory_probes:
                result["memory_probes"] = [
                    {
                        "probe_id": probe.probe_id,
                        "probe_type": probe.probe_type.value,
                        "pillar": probe.pillar.value,
                        "target_checkpoint": probe.target_checkpoint,
                        "description": probe.description,
                        "n_back_distance": probe.n_back_distance,
                        "distractor_ratio": probe.distractor_ratio,
                        "change_percentage": probe.change_percentage,
                        "interruption_duration": probe.interruption_duration,
                        "binary_scoring": probe.binary_scoring,
                        "timeout_seconds": probe.timeout_seconds,
                        "metadata": probe.metadata,
                    }
                    for probe in self.memory_probes
                ]

            if self.context_conditions:
                result["context_conditions"] = [
                    {
                        "condition_name": cond.condition_name,
                        "condition_type": cond.condition_type.value,
                        "token_limit": cond.token_limit,
                        "overflow_multiplier": cond.overflow_multiplier,
                        "description": cond.description,
                    }
                    for cond in self.context_conditions
                ]

            if self.three_dimensional_complexity:
                result["three_dimensional_complexity"] = {
                    "length_dimension": self.three_dimensional_complexity.length_dimension,
                    "depth_dimension": self.three_dimensional_complexity.depth_dimension,
                    "composition_dimension": self.three_dimensional_complexity.composition_dimension,
                    "primary_stress_pillar": self.three_dimensional_complexity.primary_stress_pillar.value,
                    "secondary_stress_pillars": [
                        pillar.value
                        for pillar in self.three_dimensional_complexity.secondary_stress_pillars
                    ],
                    "suggested_probe_density": self.three_dimensional_complexity.suggested_probe_density,
                    "complexity_tier": self.three_dimensional_complexity.complexity_tier,
                }

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskSpecification":
        """Create TaskSpecification from dictionary with backward compatibility"""
        checkpoints = []
        for cp in data["checkpoints"]:
            # Parse embedded probes if present
            embedded_probes = []
            if "embedded_probes" in cp:
                for probe_data in cp["embedded_probes"]:
                    embedded_probes.append(
                        MemoryProbe(
                            probe_id=probe_data["probe_id"],
                            probe_type=ProbeType(probe_data["probe_type"]),
                            pillar=MemoryPillar(probe_data["pillar"]),
                            target_checkpoint=probe_data["target_checkpoint"],
                            description=probe_data["description"],
                            n_back_distance=probe_data.get("n_back_distance"),
                            distractor_ratio=probe_data.get("distractor_ratio"),
                            change_percentage=probe_data.get("change_percentage"),
                            interruption_duration=probe_data.get(
                                "interruption_duration"
                            ),
                            binary_scoring=probe_data.get("binary_scoring", True),
                            timeout_seconds=probe_data.get("timeout_seconds", 300),
                            metadata=probe_data.get("metadata", {}),
                        )
                    )

            # Parse context conditions if present
            context_conditions = []
            if "context_conditions" in cp:
                for cond_data in cp["context_conditions"]:
                    context_conditions.append(
                        ContextWindowCondition(
                            condition_name=cond_data["condition_name"],
                            condition_type=ContextConditionType(
                                cond_data["condition_type"]
                            ),
                            token_limit=cond_data.get("token_limit"),
                            overflow_multiplier=cond_data.get("overflow_multiplier"),
                            description=cond_data.get("description", ""),
                        )
                    )

            # Parse pillar stress target if present
            pillar_stress_target = None
            if "pillar_stress_target" in cp:
                pillar_stress_target = MemoryPillar(cp["pillar_stress_target"])

            checkpoints.append(
                CheckpointSpecification(
                    checkpoint_id=cp["checkpoint_id"],
                    order=cp["order"],
                    title=cp["title"],
                    stub_file=cp["stub_file"],
                    stub_function=cp["stub_function"],
                    requirements=cp["requirements"],
                    test_file=cp["test_file"],
                    dependencies=cp.get("dependencies", []),
                    checkpoint_type=CheckpointType(
                        cp.get("checkpoint_type", "implementation")
                    ),
                    estimated_tokens=cp.get("estimated_tokens", 200),
                    metadata=cp.get("metadata", {}),
                    embedded_probes=embedded_probes,
                    context_conditions=context_conditions,
                    pillar_stress_target=pillar_stress_target,
                )
            )

        planning_data = data["planning_phase"]
        planning_phase = PlanningPhase(
            overview_prompt=planning_data["overview_prompt"],
            planning_deliverables=planning_data.get("planning_deliverables", {}),
            planning_capture=planning_data.get("planning_capture", {}),
            max_planning_time_minutes=planning_data.get(
                "max_planning_time_minutes", 15
            ),
            required_sections=planning_data.get("required_sections", []),
        )

        repo_data = data["repository"]
        repository = RepositoryTemplate(
            template_name=repo_data["template_name"],
            provided_files=repo_data.get("provided_files", []),
            distractor_files=repo_data.get("distractor_files", []),
            directory_structure=repo_data.get("directory_structure", {}),
            setup_commands=repo_data.get("setup_commands", []),
        )

        memory_challenges = [
            MemoryChallenge(
                challenge_id=mc["challenge_id"],
                challenge_type=MemoryChallengeType(mc["challenge_type"]),
                at_checkpoint=mc["at_checkpoint"],
                description=mc["description"],
                metadata=mc.get("metadata", {}),
                affects=mc.get("affects", []),
                interruption_task=mc.get("interruption_task"),
                duration_minutes=mc.get("duration_minutes"),
                distractor_files=mc.get("distractor_files", []),
            )
            for mc in data.get("memory_challenges", [])
        ]

        complexity_data = data.get("complexity", {})
        complexity = TaskComplexityMetrics(
            length=complexity_data.get("length", len(checkpoints)),
            depth=complexity_data.get("depth", 200),
            composition=complexity_data.get("composition", 0),
            semantic_components=complexity_data.get("semantic_components", []),
            component_dependencies=complexity_data.get("component_dependencies", {}),
        )

        eval_data = data.get("evaluation_config", {})
        evaluation_config = EvaluationConfiguration(
            memory_checkpoint_frequency=eval_data.get("memory_checkpoint_frequency", 3),
            planning_compliance_tracking=eval_data.get(
                "planning_compliance_tracking", True
            ),
            trace_capture_level=eval_data.get("trace_capture_level", "detailed"),
            success_criteria=eval_data.get(
                "success_criteria",
                {
                    "all_tests_pass": True,
                    "no_breaking_changes": True,
                    "integration_functional": True,
                    "planning_phase_completed": True,
                },
            ),
            timeout_minutes=eval_data.get("timeout_minutes", 180),
            enable_memory_challenges=eval_data.get("enable_memory_challenges", True),
        )

        metadata = data.get("metadata", {})

        # Parse enhanced evaluation fields if present
        enhanced_evaluation = data.get("enhanced_evaluation", False)

        # Parse memory probes
        memory_probes = []
        if "memory_probes" in data:
            for probe_data in data["memory_probes"]:
                memory_probes.append(
                    MemoryProbe(
                        probe_id=probe_data["probe_id"],
                        probe_type=ProbeType(probe_data["probe_type"]),
                        pillar=MemoryPillar(probe_data["pillar"]),
                        target_checkpoint=probe_data["target_checkpoint"],
                        description=probe_data["description"],
                        n_back_distance=probe_data.get("n_back_distance"),
                        distractor_ratio=probe_data.get("distractor_ratio"),
                        change_percentage=probe_data.get("change_percentage"),
                        interruption_duration=probe_data.get("interruption_duration"),
                        binary_scoring=probe_data.get("binary_scoring", True),
                        timeout_seconds=probe_data.get("timeout_seconds", 300),
                        metadata=probe_data.get("metadata", {}),
                    )
                )

        # Parse context conditions
        context_conditions = []
        if "context_conditions" in data:
            for cond_data in data["context_conditions"]:
                context_conditions.append(
                    ContextWindowCondition(
                        condition_name=cond_data["condition_name"],
                        condition_type=ContextConditionType(
                            cond_data["condition_type"]
                        ),
                        token_limit=cond_data.get("token_limit"),
                        overflow_multiplier=cond_data.get("overflow_multiplier"),
                        description=cond_data.get("description", ""),
                    )
                )

        # Parse three-dimensional complexity
        three_dimensional_complexity = None
        if "three_dimensional_complexity" in data:
            complexity_data = data["three_dimensional_complexity"]
            three_dimensional_complexity = ThreeDimensionalComplexity(
                length_dimension=complexity_data["length_dimension"],
                depth_dimension=complexity_data["depth_dimension"],
                composition_dimension=complexity_data["composition_dimension"],
                primary_stress_pillar=MemoryPillar(
                    complexity_data["primary_stress_pillar"]
                ),
                secondary_stress_pillars=[
                    MemoryPillar(pillar)
                    for pillar in complexity_data.get("secondary_stress_pillars", [])
                ],
                suggested_probe_density=complexity_data.get(
                    "suggested_probe_density", 3
                ),
                complexity_tier=complexity_data.get("complexity_tier", "medium"),
            )

        return cls(
            task_id=data["task_id"],
            title=data["title"],
            domain=data["domain"],
            description=data["description"],
            checkpoints=checkpoints,
            planning_phase=planning_phase,
            repository=repository,
            memory_challenges=memory_challenges,
            complexity=complexity,
            evaluation_config=evaluation_config,
            enhanced_evaluation=enhanced_evaluation,
            memory_probes=memory_probes,
            context_conditions=context_conditions,
            three_dimensional_complexity=three_dimensional_complexity,
            difficulty=data.get("difficulty", "medium"),
            estimated_duration_minutes=data.get("estimated_duration_minutes", 90),
            created_by=metadata.get("created_by", ""),
            version=metadata.get("version", "1.0"),
            tags=metadata.get("tags", []),
        )

    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save task specification to JSON file"""
        path = Path(file_path)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> "TaskSpecification":
        """Load task specification from JSON file"""
        path = Path(file_path)
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)


class TaskSpecificationValidator:
    """
    Validator for TaskSpecification integrity and correctness.

    Provides comprehensive validation of task specifications to ensure
    they meet WorkMemEval requirements for evaluation validity.
    """

    @staticmethod
    def validate(task_spec: TaskSpecification) -> List[str]:
        """
        Validate task specification and return list of issues.

        Returns empty list if valid, otherwise list of validation errors.
        """
        issues = []

        # Basic structure validation
        if not task_spec.task_id:
            issues.append("Task ID is required")

        if not task_spec.checkpoints:
            issues.append("Task must have at least one checkpoint")

        # Checkpoint validation
        checkpoint_ids = set()
        for cp in task_spec.checkpoints:
            if cp.checkpoint_id in checkpoint_ids:
                issues.append(f"Duplicate checkpoint ID: {cp.checkpoint_id}")
            checkpoint_ids.add(cp.checkpoint_id)

            # Dependency validation
            for dep_id in cp.dependencies:
                if dep_id not in checkpoint_ids and dep_id not in {
                    other.checkpoint_id for other in task_spec.checkpoints
                }:
                    issues.append(
                        f"Checkpoint {cp.checkpoint_id} depends on non-existent checkpoint {dep_id}"
                    )

        # Complexity validation
        if task_spec.complexity:
            if task_spec.complexity.length != len(task_spec.checkpoints):
                issues.append("Complexity length doesn't match checkpoint count")

        # Memory challenge validation
        for mc in task_spec.memory_challenges:
            if mc.at_checkpoint not in checkpoint_ids:
                issues.append(
                    f"Memory challenge {mc.challenge_id} references non-existent checkpoint {mc.at_checkpoint}"
                )

        return issues

    @staticmethod
    def is_valid(task_spec: TaskSpecification) -> bool:
        """Check if task specification is valid"""
        return len(TaskSpecificationValidator.validate(task_spec)) == 0


class TaskMigrationUtility:
    """
    Utility for migrating existing tasks to enhanced format.

    Provides automatic conversion of legacy task specifications to
    the enhanced format with memory probes and context conditions.
    """

    @staticmethod
    def detect_task_format(file_path: Union[str, Path]) -> str:
        """
        Detect task format version.

        Returns: 'legacy' or 'enhanced'
        """
        path = Path(file_path)
        with open(path, "r") as f:
            data = json.load(f)

        # Check for enhanced evaluation markers
        has_enhanced_fields = (
            "enhanced_evaluation" in data
            or "memory_probes" in data
            or "context_conditions" in data
            or "three_dimensional_complexity" in data
            or any("embedded_probes" in cp for cp in data.get("checkpoints", []))
        )

        return "enhanced" if has_enhanced_fields else "legacy"

    @staticmethod
    def migrate_to_enhanced(
        task_spec: TaskSpecification, auto_configure_probes: bool = True
    ) -> TaskSpecification:
        """
        Migrate legacy task to enhanced format.

        Args:
            task_spec: Legacy task specification
            auto_configure_probes: Whether to automatically configure probes based on complexity

        Returns:
            Enhanced task specification
        """
        if task_spec.is_enhanced_evaluation():
            return task_spec  # Already enhanced

        # Create three-dimensional complexity profile
        three_d_complexity = TaskMigrationUtility._create_complexity_profile(task_spec)

        # Auto-configure probes if requested
        memory_probes = []
        if auto_configure_probes:
            memory_probes = TaskMigrationUtility._auto_configure_probes(
                task_spec, three_d_complexity
            )

        # Create default context conditions
        context_conditions = [
            ContextWindowCondition(
                condition_name="standardized",
                condition_type=ContextConditionType.STANDARDIZED,
                token_limit=8192,
                description="Standardized 8K context window for fair comparison",
            ),
            ContextWindowCondition(
                condition_name="native",
                condition_type=ContextConditionType.NATIVE,
                description="Agent's native context window capacity",
            ),
        ]

        # Create enhanced task specification
        enhanced_task = TaskSpecification(
            task_id=task_spec.task_id,
            title=task_spec.title,
            domain=task_spec.domain,
            description=task_spec.description,
            checkpoints=task_spec.checkpoints,
            planning_phase=task_spec.planning_phase,
            repository=task_spec.repository,
            memory_challenges=task_spec.memory_challenges,
            complexity=task_spec.complexity,
            evaluation_config=task_spec.evaluation_config,
            enhanced_evaluation=True,
            memory_probes=memory_probes,
            context_conditions=context_conditions,
            three_dimensional_complexity=three_d_complexity,
            difficulty=task_spec.difficulty,
            estimated_duration_minutes=task_spec.estimated_duration_minutes,
            created_by=task_spec.created_by,
            version=task_spec.version,
            tags=task_spec.tags + ["migrated_to_enhanced"],
        )

        return enhanced_task

    @staticmethod
    def _create_complexity_profile(
        task_spec: TaskSpecification,
    ) -> ThreeDimensionalComplexity:
        """Create three-dimensional complexity profile from existing task"""
        length = len(task_spec.checkpoints)
        depth = int(task_spec.complexity.depth) if task_spec.complexity else 200
        composition = (
            task_spec.complexity.composition if task_spec.complexity else length
        )

        # Determine primary stress pillar based on task characteristics
        primary_pillar = MemoryPillar.MEMORY_FIDELITY  # Default

        if length > 8:
            primary_pillar = MemoryPillar.MEMORY_FIDELITY
        elif depth > 400:
            primary_pillar = MemoryPillar.CONTEXTUAL_RELEVANCE
        elif composition > 10:
            primary_pillar = MemoryPillar.BEHAVIORAL_INTEGRITY

        # Determine complexity tier
        difficulty_score = (length / 10.0) * (depth / 500.0) * (composition / 15.0)
        if difficulty_score < 0.3:
            tier = "low"
        elif difficulty_score < 0.6:
            tier = "medium"
        elif difficulty_score < 0.9:
            tier = "high"
        else:
            tier = "extreme"

        return ThreeDimensionalComplexity(
            length_dimension=length,
            depth_dimension=depth,
            composition_dimension=composition,
            primary_stress_pillar=primary_pillar,
            secondary_stress_pillars=[],
            suggested_probe_density=3,
            complexity_tier=tier,
        )

    @staticmethod
    def _auto_configure_probes(
        task_spec: TaskSpecification, complexity: ThreeDimensionalComplexity
    ) -> List[MemoryProbe]:
        """Auto-configure memory probes based on task complexity"""
        probes = []
        checkpoints = task_spec.checkpoints

        if not checkpoints:
            return probes

        # Get recommended probe types
        recommended_probes = complexity.get_recommended_probes()

        # Distribute probes across checkpoints
        probe_checkpoints = TaskMigrationUtility._select_probe_checkpoints(
            checkpoints, len(recommended_probes)
        )

        for i, probe_type in enumerate(recommended_probes):
            if i < len(probe_checkpoints):
                checkpoint_id = probe_checkpoints[i].checkpoint_id
                probe = TaskMigrationUtility._create_probe(
                    probe_type, checkpoint_id, i + 1
                )
                probes.append(probe)

        return probes

    @staticmethod
    def _select_probe_checkpoints(
        checkpoints: List[CheckpointSpecification], probe_count: int
    ) -> List[CheckpointSpecification]:
        """Select optimal checkpoints for probe injection"""
        if probe_count >= len(checkpoints):
            return checkpoints

        # Select evenly distributed checkpoints, avoiding the first one
        available_checkpoints = checkpoints[1:] if len(checkpoints) > 1 else checkpoints
        step = max(1, len(available_checkpoints) // probe_count)

        selected = []
        for i in range(0, len(available_checkpoints), step):
            if len(selected) < probe_count:
                selected.append(available_checkpoints[i])

        return selected

    @staticmethod
    def _create_probe(
        probe_type: ProbeType, checkpoint_id: str, probe_number: int
    ) -> MemoryProbe:
        """Create a memory probe of the specified type"""
        pillar_map = {
            ProbeType.N_BACK_INTEGRATION: MemoryPillar.MEMORY_FIDELITY,
            ProbeType.COMPRESSION_STRESS: MemoryPillar.MEMORY_FIDELITY,
            ProbeType.DISTRACTOR_INJECTION: MemoryPillar.CONTEXTUAL_RELEVANCE,
            ProbeType.CHANGE_DETECTION: MemoryPillar.CONTEXTUAL_RELEVANCE,
            ProbeType.UPDATE_ROBUSTNESS: MemoryPillar.BEHAVIORAL_INTEGRITY,
            ProbeType.CONTEXT_SWITCH: MemoryPillar.BEHAVIORAL_INTEGRITY,
        }

        descriptions = {
            ProbeType.N_BACK_INTEGRATION: "Test recall of specifications from previous checkpoints",
            ProbeType.COMPRESSION_STRESS: "Test information retention after context compression",
            ProbeType.DISTRACTOR_INJECTION: "Test filtering of relevant vs irrelevant information",
            ProbeType.CHANGE_DETECTION: "Test detection of critical specification changes",
            ProbeType.UPDATE_ROBUSTNESS: "Test propagation of requirement changes",
            ProbeType.CONTEXT_SWITCH: "Test resumption after task interruption",
        }

        probe_config = {}
        if probe_type == ProbeType.N_BACK_INTEGRATION:
            probe_config["n_back_distance"] = min(3, probe_number)
        elif probe_type == ProbeType.DISTRACTOR_INJECTION:
            probe_config["distractor_ratio"] = 0.3
        elif probe_type == ProbeType.CHANGE_DETECTION:
            probe_config["change_percentage"] = 0.01  # 1% critical changes
        elif probe_type == ProbeType.CONTEXT_SWITCH:
            probe_config["interruption_duration"] = 5  # 5 minutes

        return MemoryProbe(
            probe_id=f"auto_probe_{probe_number}_{probe_type.value}",
            probe_type=probe_type,
            pillar=pillar_map[probe_type],
            target_checkpoint=checkpoint_id,
            description=descriptions[probe_type],
            **probe_config,
        )

    @staticmethod
    def migrate_file(
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        auto_configure_probes: bool = True,
    ) -> None:
        """
        Migrate a task file to enhanced format.

        Args:
            input_path: Path to legacy task file
            output_path: Path for enhanced task file (defaults to input_path with _enhanced suffix)
            auto_configure_probes: Whether to automatically configure probes
        """
        input_path = Path(input_path)

        if output_path is None:
            output_path = (
                input_path.parent / f"{input_path.stem}_enhanced{input_path.suffix}"
            )
        else:
            output_path = Path(output_path)

        # Load and migrate task
        task_spec = TaskSpecification.load_from_file(input_path)
        enhanced_task = TaskMigrationUtility.migrate_to_enhanced(
            task_spec, auto_configure_probes
        )

        # Save enhanced task
        enhanced_task.save_to_file(output_path)

        print(f"Migrated task from {input_path} to {output_path}")
        if auto_configure_probes:
            print(f"Auto-configured {len(enhanced_task.memory_probes)} memory probes")
        print(f"Enhanced evaluation: {enhanced_task.is_enhanced_evaluation()}")


class ResearchTemplateFactory:
    """
    Factory for creating pre-configured research templates.

    Provides ready-to-use research patterns that hide implementation
    complexity behind research intent declarations.
    """

    @staticmethod
    def create_memory_fidelity_study() -> ResearchTemplate:
        """Create template for memory fidelity research"""
        return ResearchTemplate(
            template_id="memory_fidelity_study",
            name="Memory Fidelity Study",
            description="Evaluate information retention and compression capabilities",
            research_focus=MemoryPillar.MEMORY_FIDELITY,
            probe_configuration=[
                {
                    "probe_type": "n_back_integration",
                    "description": "Test recall of specifications from 2 checkpoints prior",
                    "n_back_distance": 2,
                    "binary_scoring": True,
                    "timeout_seconds": 300,
                },
                {
                    "probe_type": "compression_stress",
                    "description": "Test information retention after context compression",
                    "binary_scoring": True,
                    "timeout_seconds": 600,
                },
            ],
            context_conditions=[
                {
                    "condition_name": "standardized",
                    "condition_type": "standardized",
                    "token_limit": 8192,
                    "description": "Standardized 8K context for fair comparison",
                },
                {
                    "condition_name": "native",
                    "condition_type": "native",
                    "description": "Agent native context capacity",
                },
            ],
            complexity_targets={
                "length_bias": 1.2,  # Emphasize temporal complexity
                "depth_bias": 1.0,
                "composition_bias": 0.8,
            },
            evaluation_metrics=[
                "information_retention_rate",
                "compression_accuracy",
                "context_reread_frequency",
                "longitudinal_coherence",
            ],
            difficulty_level="moderate",
            estimated_duration_minutes=90,
            required_checkpoints=5,
            tags=["memory_fidelity", "retention", "compression"],
        )

    @staticmethod
    def create_contextual_relevance_study() -> ResearchTemplate:
        """Create template for contextual relevance research"""
        return ResearchTemplate(
            template_id="contextual_relevance_study",
            name="Contextual Relevance Study",
            description="Evaluate signal vs noise filtering and change detection",
            research_focus=MemoryPillar.CONTEXTUAL_RELEVANCE,
            probe_configuration=[
                {
                    "probe_type": "distractor_injection",
                    "description": "Test filtering of relevant vs irrelevant requirements",
                    "distractor_ratio": 0.4,
                    "binary_scoring": True,
                    "timeout_seconds": 300,
                },
                {
                    "probe_type": "change_detection",
                    "description": "Test detection of 1% critical specification changes",
                    "change_percentage": 0.01,
                    "binary_scoring": True,
                    "timeout_seconds": 300,
                },
            ],
            context_conditions=[
                {
                    "condition_name": "standardized",
                    "condition_type": "standardized",
                    "token_limit": 8192,
                    "description": "Standardized context with controlled noise",
                },
                {
                    "condition_name": "overflow",
                    "condition_type": "overflow",
                    "overflow_multiplier": 1.5,
                    "description": "Information overload condition",
                },
            ],
            complexity_targets={
                "length_bias": 0.8,
                "depth_bias": 1.3,  # Emphasize informational complexity
                "composition_bias": 1.0,
            },
            evaluation_metrics=[
                "relevance_precision",
                "relevance_recall",
                "distractor_filtering_accuracy",
                "change_detection_sensitivity",
            ],
            difficulty_level="moderate",
            estimated_duration_minutes=75,
            required_checkpoints=4,
            tags=["contextual_relevance", "filtering", "change_detection"],
        )

    @staticmethod
    def create_behavioral_integrity_study() -> ResearchTemplate:
        """Create template for behavioral integrity research"""
        return ResearchTemplate(
            template_id="behavioral_integrity_study",
            name="Behavioral Integrity Study",
            description="Evaluate state coherence and update robustness",
            research_focus=MemoryPillar.BEHAVIORAL_INTEGRITY,
            probe_configuration=[
                {
                    "probe_type": "update_robustness",
                    "description": "Test propagation of requirement changes to dependent components",
                    "binary_scoring": True,
                    "timeout_seconds": 450,
                },
                {
                    "probe_type": "context_switch",
                    "description": "Test resumption after 5-minute task interruption",
                    "interruption_duration": 5,
                    "binary_scoring": True,
                    "timeout_seconds": 300,
                },
            ],
            context_conditions=[
                {
                    "condition_name": "native",
                    "condition_type": "native",
                    "description": "Native context for realistic coordination demands",
                },
                {
                    "condition_name": "overflow",
                    "condition_type": "overflow",
                    "overflow_multiplier": 2.0,
                    "description": "Forced overflow to test memory system coordination",
                },
            ],
            complexity_targets={
                "length_bias": 1.0,
                "depth_bias": 0.9,
                "composition_bias": 1.4,  # Emphasize structural complexity
            },
            evaluation_metrics=[
                "update_propagation_accuracy",
                "state_coherence_index",
                "resumption_success_rate",
                "coordination_overhead",
            ],
            difficulty_level="complex",
            estimated_duration_minutes=120,
            required_checkpoints=6,
            tags=["behavioral_integrity", "coordination", "robustness"],
        )

    @staticmethod
    def create_balanced_study() -> ResearchTemplate:
        """Create template for balanced three-pillar research"""
        return ResearchTemplate(
            template_id="balanced_study",
            name="Balanced Three-Pillar Study",
            description="Comprehensive evaluation across all memory pillars",
            research_focus=MemoryPillar.MEMORY_FIDELITY,  # Primary focus
            probe_configuration=[
                {
                    "probe_type": "n_back_integration",
                    "description": "Memory fidelity: recall from 2 checkpoints prior",
                    "n_back_distance": 2,
                    "binary_scoring": True,
                    "timeout_seconds": 300,
                },
                {
                    "probe_type": "distractor_injection",
                    "description": "Contextual relevance: filter relevant requirements",
                    "distractor_ratio": 0.3,
                    "binary_scoring": True,
                    "timeout_seconds": 300,
                },
                {
                    "probe_type": "update_robustness",
                    "description": "Behavioral integrity: propagate requirement changes",
                    "binary_scoring": True,
                    "timeout_seconds": 400,
                },
            ],
            context_conditions=[
                {
                    "condition_name": "standardized",
                    "condition_type": "standardized",
                    "token_limit": 8192,
                    "description": "Standardized context for fair comparison",
                },
                {
                    "condition_name": "native",
                    "condition_type": "native",
                    "description": "Native context for realistic assessment",
                },
            ],
            complexity_targets={
                "length_bias": 1.0,
                "depth_bias": 1.0,
                "composition_bias": 1.0,
            },
            evaluation_metrics=[
                "information_retention_rate",
                "relevance_precision",
                "update_propagation_accuracy",
                "overall_memory_performance",
            ],
            difficulty_level="moderate",
            estimated_duration_minutes=100,
            required_checkpoints=5,
            tags=["balanced", "comprehensive", "three_pillar"],
        )

    @staticmethod
    def get_available_templates() -> Dict[str, ResearchTemplate]:
        """Get all available research templates"""
        return {
            "memory_fidelity": ResearchTemplateFactory.create_memory_fidelity_study(),
            "contextual_relevance": ResearchTemplateFactory.create_contextual_relevance_study(),
            "behavioral_integrity": ResearchTemplateFactory.create_behavioral_integrity_study(),
            "balanced": ResearchTemplateFactory.create_balanced_study(),
        }

    @staticmethod
    def get_template_by_research_focus(pillar: MemoryPillar) -> ResearchTemplate:
        """Get template optimized for specific memory pillar"""
        if pillar == MemoryPillar.MEMORY_FIDELITY:
            return ResearchTemplateFactory.create_memory_fidelity_study()
        elif pillar == MemoryPillar.CONTEXTUAL_RELEVANCE:
            return ResearchTemplateFactory.create_contextual_relevance_study()
        elif pillar == MemoryPillar.BEHAVIORAL_INTEGRITY:
            return ResearchTemplateFactory.create_behavioral_integrity_study()
        else:
            return ResearchTemplateFactory.create_balanced_study()

    @staticmethod
    def recommend_template_for_task(task_spec: "TaskSpecification") -> ResearchTemplate:
        """Recommend optimal template based on task characteristics"""
        complexity_profile = ComplexityProfile.from_task_specification(task_spec)
        return ResearchTemplateFactory.get_template_by_research_focus(
            complexity_profile.primary_stress_pillar
        )
