"""
WorkMemEval: Task Specification Core Data Structures (Refactored)

This module provides a clean separation between legacy and enhanced functionality
while maintaining full backward compatibility.

ARCHITECTURE:
- Legacy classes: Preserved exactly as-is for backward compatibility
- Enhanced classes: New functionality with clear naming and separation
- Migration utilities: Bridge between legacy and enhanced systems
- Progressive disclosure: Optional enhanced features that don't interfere with legacy usage
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# =============================================================================
# LEGACY SYSTEM (PRESERVED FOR BACKWARD COMPATIBILITY)
# =============================================================================
#
# This section contains the original WorkMemEval task specification system.
# These classes are preserved exactly as they were to ensure 100% backward
# compatibility. DO NOT MODIFY these classes - they will be deprecated in
# future versions once migration is complete.
#
# For new development, use the Enhanced System classes below.
# =============================================================================


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


@dataclass
class LegacyCheckpointSpecification:
    """
    LEGACY: Individual checkpoint within a WorkMemEval task.

    This is the original checkpoint specification. For new development,
    use EnhancedCheckpointSpecification instead.
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

    def __post_init__(self):
        """Validate checkpoint specification"""
        if not self.checkpoint_id:
            raise ValueError("checkpoint_id cannot be empty")
        if not self.stub_file or not self.test_file:
            raise ValueError("stub_file and test_file are required")
        if self.order < 1:
            raise ValueError("order must be >= 1")


@dataclass
class LegacyMemoryChallenge:
    """
    LEGACY: Working memory challenge injection point.

    This is the original memory challenge system. For new development,
    use the enhanced memory probe system instead.
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
class LegacyTaskComplexityMetrics:
    """
    LEGACY: Three-dimensional task complexity measurement.

    This is the original complexity system. For new development,
    use EnhancedComplexityProfile instead.
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


# =============================================================================
# ENHANCED SYSTEM (NEW DEVELOPMENT)
# =============================================================================
#
# This section contains the enhanced WorkMemEval task specification system
# with memory probes, context conditions, and advanced complexity analysis.
#
# Use these classes for all new development and research applications.
# =============================================================================


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

    SIMPLE = "simple"  # Tier 1: Basic evaluation (legacy functionality)
    RESEARCH = "research"  # Tier 2: Enhanced evaluation with smart defaults
    ADVANCED = "advanced"  # Tier 3: Full framework control


@dataclass
class MemoryProbe:
    """
    Enhanced memory probe specification for pillar-specific testing.

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
class EnhancedComplexityProfile:
    """
    Enhanced three-dimensional complexity analysis.

    Provides comprehensive complexity analysis with pillar mapping
    and automatic probe configuration capabilities.
    """

    # Core three-dimensional metrics
    length_dimension: int  # Temporal complexity
    depth_dimension: int  # Informational complexity
    composition_dimension: float  # Structural complexity

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
    def from_legacy_task(
        cls, task_spec: "TaskSpecification"
    ) -> "EnhancedComplexityProfile":
        """Create enhanced complexity profile from legacy task specification"""
        checkpoints = task_spec.checkpoints

        # Calculate dimensions
        length_dim = len(checkpoints)
        depth_dim = (
            int(sum(cp.estimated_tokens for cp in checkpoints) / len(checkpoints))
            if checkpoints
            else 200
        )

        # Calculate composition from dependencies
        total_deps = sum(len(cp.dependencies) for cp in checkpoints)
        composition_dim = (
            (len(checkpoints) * total_deps / len(checkpoints)) if checkpoints else 0
        )

        # Calculate overall difficulty
        length_factor = min(length_dim / 10.0, 1.0)
        depth_factor = min(depth_dim / 500.0, 1.0)
        composition_factor = min(composition_dim / 15.0, 1.0)
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
        pillar_scores = {
            MemoryPillar.MEMORY_FIDELITY: min(length_dim / 10.0, 1.0),
            MemoryPillar.CONTEXTUAL_RELEVANCE: min(depth_dim / 500.0, 1.0),
            MemoryPillar.BEHAVIORAL_INTEGRITY: min(composition_dim / 15.0, 1.0),
        }

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
            composition_dimension=composition_dim,
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


# =============================================================================
# UNIFIED INTERFACE (BACKWARD COMPATIBLE)
# =============================================================================
#
# This section provides a unified interface that maintains backward compatibility
# while enabling enhanced features. The main TaskSpecification class can operate
# in both legacy and enhanced modes.
# =============================================================================

# Type aliases for backward compatibility
CheckpointSpecification = LegacyCheckpointSpecification
MemoryChallenge = LegacyMemoryChallenge
TaskComplexityMetrics = LegacyTaskComplexityMetrics


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
    Unified WorkMemEval task specification with backward compatibility.

    This class operates in two modes:
    1. Legacy Mode: Uses original complexity system and memory challenges
    2. Enhanced Mode: Uses enhanced complexity analysis and memory probes

    Mode is automatically detected based on the presence of enhanced features.
    """

    task_id: str
    title: str
    domain: str  # e.g., "api_service", "data_processing"
    description: str

    # Core task structure (backward compatible)
    checkpoints: List[CheckpointSpecification]
    planning_phase: PlanningPhase
    repository: RepositoryTemplate

    # Legacy system (preserved for backward compatibility)
    memory_challenges: List[MemoryChallenge] = field(default_factory=list)
    complexity: Optional[TaskComplexityMetrics] = None
    evaluation_config: EvaluationConfiguration = field(
        default_factory=EvaluationConfiguration
    )

    # Enhanced system (optional, enables enhanced mode)
    memory_probes: List[MemoryProbe] = field(default_factory=list)
    context_conditions: List[ContextWindowCondition] = field(default_factory=list)
    enhanced_complexity: Optional[EnhancedComplexityProfile] = None

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

        # Auto-calculate legacy complexity if not provided (for backward compatibility)
        if self.complexity is None:
            self.complexity = self._calculate_legacy_complexity()

        # Validate checkpoint order and dependencies
        self._validate_checkpoint_dependencies()

    def is_enhanced_mode(self) -> bool:
        """Check if task uses enhanced evaluation features"""
        return bool(
            self.memory_probes or self.context_conditions or self.enhanced_complexity
        )

    def get_complexity_profile(
        self,
    ) -> Union[TaskComplexityMetrics, EnhancedComplexityProfile]:
        """Get complexity profile (legacy or enhanced based on mode)"""
        if self.is_enhanced_mode() and self.enhanced_complexity:
            return self.enhanced_complexity
        return self.complexity

    def enable_enhanced_mode(self) -> "TaskSpecification":
        """Convert task to enhanced mode with auto-configuration"""
        if self.is_enhanced_mode() and self.enhanced_complexity is not None:
            return self  # Already fully enhanced

        # Generate enhanced complexity profile
        self.enhanced_complexity = EnhancedComplexityProfile.from_legacy_task(self)

        # Auto-configure memory probes based on complexity
        self.memory_probes = self._auto_configure_probes()

        # Add default context conditions
        self.context_conditions = [
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

        # Add enhanced mode tag
        if "enhanced_mode" not in self.tags:
            self.tags.append("enhanced_mode")

        return self

    def _calculate_legacy_complexity(self) -> TaskComplexityMetrics:
        """Auto-calculate legacy complexity from checkpoint structure"""
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

    def _validate_checkpoint_dependencies(self):
        """Validate that all checkpoint dependencies exist and form valid DAG"""
        checkpoint_ids = {cp.checkpoint_id for cp in self.checkpoints}

        for cp in self.checkpoints:
            for dep_id in cp.dependencies:
                if dep_id not in checkpoint_ids:
                    raise ValueError(
                        f"Checkpoint {cp.checkpoint_id} depends on non-existent checkpoint {dep_id}"
                    )

    def _auto_configure_probes(self) -> List[MemoryProbe]:
        """Auto-configure memory probes based on enhanced complexity analysis"""
        if not self.enhanced_complexity:
            return []

        probes = []
        probe_types = self.enhanced_complexity.recommended_probe_types
        injection_points = self.enhanced_complexity.probe_injection_points

        # Create probes at recommended injection points
        for i, probe_type in enumerate(probe_types):
            if i < len(injection_points):
                checkpoint_order = injection_points[i]
                target_checkpoint = next(
                    (
                        cp.checkpoint_id
                        for cp in self.checkpoints
                        if cp.order == checkpoint_order
                    ),
                    self.checkpoints[-1].checkpoint_id,  # Fallback to last checkpoint
                )

                probe = self._create_probe(probe_type, target_checkpoint, i + 1)
                probes.append(probe)

        return probes

    def _create_probe(
        self, probe_type: ProbeType, checkpoint_id: str, probe_number: int
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
            probe_id=f"auto_probe_{probe_number}_{probe_type.value}",
            probe_type=probe_type,
            pillar=pillar_map[probe_type],
            target_checkpoint=checkpoint_id,
            description=descriptions[probe_type],
            **probe_config,
        )

    def get_checkpoint_by_id(
        self, checkpoint_id: str
    ) -> Optional[CheckpointSpecification]:
        """Get checkpoint by ID"""
        return next(
            (cp for cp in self.checkpoints if cp.checkpoint_id == checkpoint_id), None
        )

    def get_required_files_for_checkpoint(self, checkpoint_id: str) -> set:
        """Calculate which files are required for a given checkpoint"""
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
        """Convert to dictionary for JSON serialization"""
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
            }
            if self.complexity
            else None,
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

        # Add enhanced features only if in enhanced mode
        if self.is_enhanced_mode():
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

            if self.enhanced_complexity:
                result["enhanced_complexity"] = {
                    "length_dimension": self.enhanced_complexity.length_dimension,
                    "depth_dimension": self.enhanced_complexity.depth_dimension,
                    "composition_dimension": self.enhanced_complexity.composition_dimension,
                    "overall_difficulty_score": self.enhanced_complexity.overall_difficulty_score,
                    "complexity_tier": self.enhanced_complexity.complexity_tier,
                    "primary_stress_pillar": self.enhanced_complexity.primary_stress_pillar.value,
                    "secondary_stress_pillars": [
                        pillar.value
                        for pillar in self.enhanced_complexity.secondary_stress_pillars
                    ],
                    "pillar_stress_scores": {
                        pillar.value: score
                        for pillar, score in self.enhanced_complexity.pillar_stress_scores.items()
                    },
                    "recommended_probe_types": [
                        probe_type.value
                        for probe_type in self.enhanced_complexity.recommended_probe_types
                    ],
                    "optimal_probe_density": self.enhanced_complexity.optimal_probe_density,
                    "probe_injection_points": self.enhanced_complexity.probe_injection_points,
                }

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskSpecification":
        """Create TaskSpecification from dictionary with backward compatibility"""
        # Parse checkpoints
        checkpoints = [
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
            )
            for cp in data["checkpoints"]
        ]

        # Parse planning phase
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

        # Parse repository
        repo_data = data["repository"]
        repository = RepositoryTemplate(
            template_name=repo_data["template_name"],
            provided_files=repo_data.get("provided_files", []),
            distractor_files=repo_data.get("distractor_files", []),
            directory_structure=repo_data.get("directory_structure", {}),
            setup_commands=repo_data.get("setup_commands", []),
        )

        # Parse legacy memory challenges
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

        # Parse legacy complexity
        complexity = None
        if "complexity" in data and data["complexity"]:
            complexity_data = data["complexity"]
            complexity = TaskComplexityMetrics(
                length=complexity_data.get("length", len(checkpoints)),
                depth=complexity_data.get("depth", 200),
                composition=complexity_data.get("composition", 0),
                semantic_components=complexity_data.get("semantic_components", []),
                component_dependencies=complexity_data.get(
                    "component_dependencies", {}
                ),
            )

        # Parse evaluation config
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

        # Parse enhanced features (if present)
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

        enhanced_complexity = None
        if "enhanced_complexity" in data:
            ec_data = data["enhanced_complexity"]
            enhanced_complexity = EnhancedComplexityProfile(
                length_dimension=ec_data["length_dimension"],
                depth_dimension=ec_data["depth_dimension"],
                composition_dimension=ec_data["composition_dimension"],
                overall_difficulty_score=ec_data["overall_difficulty_score"],
                complexity_tier=ec_data["complexity_tier"],
                primary_stress_pillar=MemoryPillar(ec_data["primary_stress_pillar"]),
                secondary_stress_pillars=[
                    MemoryPillar(pillar)
                    for pillar in ec_data.get("secondary_stress_pillars", [])
                ],
                pillar_stress_scores={
                    MemoryPillar(pillar): score
                    for pillar, score in ec_data.get("pillar_stress_scores", {}).items()
                },
                recommended_probe_types=[
                    ProbeType(probe_type)
                    for probe_type in ec_data.get("recommended_probe_types", [])
                ],
                optimal_probe_density=ec_data.get("optimal_probe_density", 3),
                probe_injection_points=ec_data.get("probe_injection_points", []),
            )

        # Parse metadata
        metadata = data.get("metadata", {})

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
            memory_probes=memory_probes,
            context_conditions=context_conditions,
            enhanced_complexity=enhanced_complexity,
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


# =============================================================================
# VALIDATION AND UTILITIES
# =============================================================================


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

        # Legacy complexity validation
        if task_spec.complexity:
            if task_spec.complexity.length != len(task_spec.checkpoints):
                issues.append("Complexity length doesn't match checkpoint count")

        # Legacy memory challenge validation
        for mc in task_spec.memory_challenges:
            if mc.at_checkpoint not in checkpoint_ids:
                issues.append(
                    f"Memory challenge {mc.challenge_id} references non-existent checkpoint {mc.at_checkpoint}"
                )

        # Enhanced mode validation
        if task_spec.is_enhanced_mode():
            # Memory probe validation
            for probe in task_spec.memory_probes:
                if probe.target_checkpoint not in checkpoint_ids:
                    issues.append(
                        f"Memory probe {probe.probe_id} targets non-existent checkpoint {probe.target_checkpoint}"
                    )

        return issues

    @staticmethod
    def is_valid(task_spec: TaskSpecification) -> bool:
        """Check if task specification is valid"""
        return len(TaskSpecificationValidator.validate(task_spec)) == 0


class LegacyMigrationUtility:
    """
    Utility for migrating legacy tasks to enhanced mode.

    Provides automatic conversion of legacy task specifications to
    enhanced mode with memory probes and context conditions.
    """

    @staticmethod
    def migrate_to_enhanced(task_spec: TaskSpecification) -> TaskSpecification:
        """
        Migrate legacy task to enhanced mode.

        Args:
            task_spec: Task specification (legacy or enhanced)

        Returns:
            Enhanced task specification
        """
        if task_spec.is_enhanced_mode():
            return task_spec  # Already enhanced

        return task_spec.enable_enhanced_mode()

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
            "memory_probes" in data
            or "context_conditions" in data
            or "enhanced_complexity" in data
        )

        return "enhanced" if has_enhanced_fields else "legacy"

    @staticmethod
    def migrate_file(
        input_path: Union[str, Path], output_path: Optional[Union[str, Path]] = None
    ) -> None:
        """
        Migrate a task file to enhanced format.

        Args:
            input_path: Path to task file
            output_path: Path for enhanced task file (defaults to input_path with _enhanced suffix)
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
        enhanced_task = LegacyMigrationUtility.migrate_to_enhanced(task_spec)

        # Save enhanced task
        enhanced_task.save_to_file(output_path)

        print(f"Migrated task from {input_path} to {output_path}")
        print(f"Enhanced mode: {enhanced_task.is_enhanced_mode()}")
        if enhanced_task.is_enhanced_mode():
            print(f"Memory probes: {len(enhanced_task.memory_probes)}")
            print(f"Context conditions: {len(enhanced_task.context_conditions)}")
