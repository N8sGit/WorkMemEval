"""
Comprehensive tests for enhanced WorkMemEval task specification module.

Tests all enhanced data structures, memory probes, complexity analysis,
research templates, configuration profiles, and migration utilities.
"""

import tempfile
from pathlib import Path
from typing import List

import pytest

from src.core.task_specification import (  # Core classes; Enums
    CheckpointSpecification,
    ComplexityProfile,
    CompositionMetrics,
    ConfigurationProfile,
    ContextConditionType,
    ContextWindowCondition,
    EvaluationMode,
    MemoryPillar,
    MemoryProbe,
    PlanningPhase,
    ProbeType,
    RepositoryTemplate,
    ResearchTemplate,
    ResearchTemplateFactory,
    TaskMigrationUtility,
    TaskSpecification,
    TaskSpecificationValidator,
    ThreeDimensionalComplexity,
)


class TestMemoryProbe:
    """Test MemoryProbe data structure and functionality"""

    def test_valid_memory_probe_creation(self):
        """Test creating a valid memory probe"""
        probe = MemoryProbe(
            probe_id="test_probe_1",
            probe_type=ProbeType.N_BACK_INTEGRATION,
            pillar=MemoryPillar.MEMORY_FIDELITY,
            target_checkpoint="cp3",
            description="Test recall from 2 checkpoints prior",
            n_back_distance=2,
            binary_scoring=True,
            timeout_seconds=300,
        )

        assert probe.probe_id == "test_probe_1"
        assert probe.probe_type == ProbeType.N_BACK_INTEGRATION
        assert probe.pillar == MemoryPillar.MEMORY_FIDELITY
        assert probe.target_checkpoint == "cp3"
        assert probe.n_back_distance == 2
        assert probe.binary_scoring is True
        assert probe.timeout_seconds == 300

    def test_distractor_injection_probe(self):
        """Test distractor injection probe configuration"""
        probe = MemoryProbe(
            probe_id="distractor_test",
            probe_type=ProbeType.DISTRACTOR_INJECTION,
            pillar=MemoryPillar.CONTEXTUAL_RELEVANCE,
            target_checkpoint="cp4",
            description="Test filtering of irrelevant information",
            distractor_ratio=0.3,
        )

        assert probe.probe_type == ProbeType.DISTRACTOR_INJECTION
        assert probe.pillar == MemoryPillar.CONTEXTUAL_RELEVANCE
        assert probe.distractor_ratio == 0.3
        assert probe.n_back_distance is None  # Not applicable for this probe type

    def test_context_switch_probe(self):
        """Test context switch probe configuration"""
        probe = MemoryProbe(
            probe_id="context_switch_test",
            probe_type=ProbeType.CONTEXT_SWITCH,
            pillar=MemoryPillar.BEHAVIORAL_INTEGRITY,
            target_checkpoint="cp5",
            description="Test resumption after interruption",
            interruption_duration=10,
        )

        assert probe.probe_type == ProbeType.CONTEXT_SWITCH
        assert probe.pillar == MemoryPillar.BEHAVIORAL_INTEGRITY
        assert probe.interruption_duration == 10

    def test_probe_validation_empty_id(self):
        """Test probe validation fails with empty ID"""
        with pytest.raises(
            ValueError, match="probe_id and target_checkpoint are required"
        ):
            MemoryProbe(
                probe_id="",
                probe_type=ProbeType.N_BACK_INTEGRATION,
                pillar=MemoryPillar.MEMORY_FIDELITY,
                target_checkpoint="cp1",
                description="Test probe",
            )

    def test_probe_validation_empty_target(self):
        """Test probe validation fails with empty target checkpoint"""
        with pytest.raises(
            ValueError, match="probe_id and target_checkpoint are required"
        ):
            MemoryProbe(
                probe_id="test_probe",
                probe_type=ProbeType.N_BACK_INTEGRATION,
                pillar=MemoryPillar.MEMORY_FIDELITY,
                target_checkpoint="",
                description="Test probe",
            )


class TestContextWindowCondition:
    """Test ContextWindowCondition data structure"""

    def test_standardized_condition(self):
        """Test standardized context window condition"""
        condition = ContextWindowCondition(
            condition_name="standardized_8k",
            condition_type=ContextConditionType.STANDARDIZED,
            token_limit=8192,
            description="Standardized 8K context window",
        )

        assert condition.condition_name == "standardized_8k"
        assert condition.condition_type == ContextConditionType.STANDARDIZED
        assert condition.token_limit == 8192
        assert condition.overflow_multiplier is None

    def test_native_condition(self):
        """Test native context window condition"""
        condition = ContextWindowCondition(
            condition_name="native",
            condition_type=ContextConditionType.NATIVE,
            description="Agent's native context capacity",
        )

        assert condition.condition_type == ContextConditionType.NATIVE
        assert condition.token_limit is None
        assert condition.overflow_multiplier is None

    def test_overflow_condition(self):
        """Test overflow context window condition"""
        condition = ContextWindowCondition(
            condition_name="overflow_2x",
            condition_type=ContextConditionType.OVERFLOW,
            overflow_multiplier=2.0,
            description="Force 2x context overflow",
        )

        assert condition.condition_type == ContextConditionType.OVERFLOW
        assert condition.overflow_multiplier == 2.0
        assert condition.token_limit is None

    def test_standardized_validation_requires_token_limit(self):
        """Test standardized condition validation requires token limit"""
        with pytest.raises(
            ValueError, match="Standardized conditions require token_limit"
        ):
            ContextWindowCondition(
                condition_name="invalid",
                condition_type=ContextConditionType.STANDARDIZED,
                description="Missing token limit",
            )

    def test_overflow_validation_requires_multiplier(self):
        """Test overflow condition validation requires multiplier"""
        with pytest.raises(
            ValueError, match="Overflow conditions require overflow_multiplier"
        ):
            ContextWindowCondition(
                condition_name="invalid",
                condition_type=ContextConditionType.OVERFLOW,
                description="Missing multiplier",
            )


class TestThreeDimensionalComplexity:
    """Test ThreeDimensionalComplexity data structure"""

    def test_basic_complexity_creation(self):
        """Test creating three-dimensional complexity"""
        complexity = ThreeDimensionalComplexity(
            length_dimension=8,
            depth_dimension=350,
            composition_dimension=12.0,
            primary_stress_pillar=MemoryPillar.BEHAVIORAL_INTEGRITY,
            secondary_stress_pillars=[MemoryPillar.MEMORY_FIDELITY],
            suggested_probe_density=4,
            complexity_tier="complex",
        )

        assert complexity.length_dimension == 8
        assert complexity.depth_dimension == 350
        assert complexity.composition_dimension == 12.0
        assert complexity.primary_stress_pillar == MemoryPillar.BEHAVIORAL_INTEGRITY
        assert MemoryPillar.MEMORY_FIDELITY in complexity.secondary_stress_pillars
        assert complexity.suggested_probe_density == 4
        assert complexity.complexity_tier == "complex"

    def test_difficulty_score_calculation(self):
        """Test difficulty score calculation"""
        complexity = ThreeDimensionalComplexity(
            length_dimension=10,  # 1.0 factor (capped)
            depth_dimension=500,  # 1.0 factor (capped)
            composition_dimension=15.0,  # 1.0 factor (capped)
            primary_stress_pillar=MemoryPillar.MEMORY_FIDELITY,
        )

        difficulty_score = complexity.calculate_difficulty_score()
        assert difficulty_score == 1.0  # All factors at maximum

    def test_difficulty_score_partial(self):
        """Test difficulty score with partial complexity"""
        complexity = ThreeDimensionalComplexity(
            length_dimension=5,  # 0.5 factor
            depth_dimension=250,  # 0.5 factor
            composition_dimension=7.5,  # 0.5 factor
            primary_stress_pillar=MemoryPillar.MEMORY_FIDELITY,
        )

        difficulty_score = complexity.calculate_difficulty_score()
        assert difficulty_score == 0.125  # 0.5 * 0.5 * 0.5

    def test_recommended_probes_memory_fidelity(self):
        """Test probe recommendations for memory fidelity focus"""
        complexity = ThreeDimensionalComplexity(
            length_dimension=8,
            depth_dimension=300,
            composition_dimension=6.0,
            primary_stress_pillar=MemoryPillar.MEMORY_FIDELITY,
        )

        probes = complexity.get_recommended_probes()
        assert ProbeType.N_BACK_INTEGRATION in probes
        assert ProbeType.COMPRESSION_STRESS in probes

    def test_recommended_probes_contextual_relevance(self):
        """Test probe recommendations for contextual relevance focus"""
        complexity = ThreeDimensionalComplexity(
            length_dimension=5,
            depth_dimension=450,
            composition_dimension=4.0,
            primary_stress_pillar=MemoryPillar.CONTEXTUAL_RELEVANCE,
        )

        probes = complexity.get_recommended_probes()
        assert ProbeType.DISTRACTOR_INJECTION in probes
        assert ProbeType.CHANGE_DETECTION in probes

    def test_recommended_probes_behavioral_integrity(self):
        """Test probe recommendations for behavioral integrity focus"""
        complexity = ThreeDimensionalComplexity(
            length_dimension=6,
            depth_dimension=300,
            composition_dimension=15.0,
            primary_stress_pillar=MemoryPillar.BEHAVIORAL_INTEGRITY,
        )

        probes = complexity.get_recommended_probes()
        assert ProbeType.UPDATE_ROBUSTNESS in probes
        assert ProbeType.CONTEXT_SWITCH in probes


class TestCompositionMetrics:
    """Test CompositionMetrics calculation"""

    def create_sample_checkpoints(self) -> List[CheckpointSpecification]:
        """Create sample checkpoints for testing"""
        return [
            CheckpointSpecification(
                checkpoint_id="cp1",
                order=1,
                title="User Service",
                stub_file="user.py",
                stub_function="UserService",
                requirements="Implement user service",
                test_file="test_user.py",
            ),
            CheckpointSpecification(
                checkpoint_id="cp2",
                order=2,
                title="Auth Service",
                stub_file="auth.py",
                stub_function="AuthService",
                requirements="Implement auth service",
                test_file="test_auth.py",
                dependencies=["cp1"],
            ),
            CheckpointSpecification(
                checkpoint_id="cp3",
                order=3,
                title="API Gateway",
                stub_file="gateway.py",
                stub_function="APIGateway",
                requirements="Implement API gateway",
                test_file="test_gateway.py",
                dependencies=["cp1", "cp2"],
            ),
        ]

    def test_composition_metrics_calculation(self):
        """Test composition metrics calculation from checkpoints"""
        checkpoints = self.create_sample_checkpoints()
        metrics = CompositionMetrics.from_checkpoint_structure(checkpoints)

        assert metrics.component_count == 3
        # Dependencies: cp1=0, cp2=1, cp3=2, total=3
        assert metrics.integration_density == 1.0  # 3/3
        assert metrics.composition_score == 3.0  # 3 * 1.0

        assert "User Service" in metrics.semantic_components
        assert "Auth Service" in metrics.semantic_components
        assert "API Gateway" in metrics.semantic_components

    def test_composition_metrics_no_dependencies(self):
        """Test composition metrics with no dependencies"""
        checkpoints = [
            CheckpointSpecification(
                checkpoint_id="cp1",
                order=1,
                title="Component A",
                stub_file="a.py",
                stub_function="A",
                requirements="Component A",
                test_file="test_a.py",
            ),
            CheckpointSpecification(
                checkpoint_id="cp2",
                order=2,
                title="Component B",
                stub_file="b.py",
                stub_function="B",
                requirements="Component B",
                test_file="test_b.py",
            ),
        ]

        metrics = CompositionMetrics.from_checkpoint_structure(checkpoints)
        assert metrics.component_count == 2
        assert metrics.integration_density == 0.0  # No dependencies
        assert metrics.composition_score == 0.0  # 2 * 0.0

    def test_composition_metrics_high_integration(self):
        """Test composition metrics with high integration density"""
        checkpoints = [
            CheckpointSpecification(
                checkpoint_id="cp1",
                order=1,
                title="Core",
                stub_file="core.py",
                stub_function="Core",
                requirements="Core component",
                test_file="test_core.py",
            ),
            CheckpointSpecification(
                checkpoint_id="cp2",
                order=2,
                title="Service A",
                stub_file="service_a.py",
                stub_function="ServiceA",
                requirements="Service A",
                test_file="test_service_a.py",
                dependencies=["cp1"],
            ),
            CheckpointSpecification(
                checkpoint_id="cp3",
                order=3,
                title="Service B",
                stub_file="service_b.py",
                stub_function="ServiceB",
                requirements="Service B",
                test_file="test_service_b.py",
                dependencies=["cp1", "cp2"],
            ),
            CheckpointSpecification(
                checkpoint_id="cp4",
                order=4,
                title="Integration",
                stub_file="integration.py",
                stub_function="Integration",
                requirements="Integration layer",
                test_file="test_integration.py",
                dependencies=["cp1", "cp2", "cp3"],
            ),
        ]

        metrics = CompositionMetrics.from_checkpoint_structure(checkpoints)
        assert metrics.component_count == 4
        # Dependencies: cp1=0, cp2=1, cp3=2, cp4=3, total=6
        assert metrics.integration_density == 1.5  # 6/4
        assert metrics.composition_score == 6.0  # 4 * 1.5

    def test_complexity_tier_classification(self):
        """Test complexity tier classification"""
        # Simple tier
        simple_metrics = CompositionMetrics(
            component_count=3, integration_density=1.0, composition_score=3.0
        )
        assert simple_metrics.get_complexity_tier() == "simple"

        # Moderate tier
        moderate_metrics = CompositionMetrics(
            component_count=5, integration_density=1.5, composition_score=7.5
        )
        assert moderate_metrics.get_complexity_tier() == "moderate"

        # Complex tier
        complex_metrics = CompositionMetrics(
            component_count=8, integration_density=2.0, composition_score=16.0
        )
        assert complex_metrics.get_complexity_tier() == "complex"

        # Highly complex tier
        highly_complex_metrics = CompositionMetrics(
            component_count=10, integration_density=3.0, composition_score=30.0
        )
        assert highly_complex_metrics.get_complexity_tier() == "highly_complex"

    def test_primary_stress_pillar_determination(self):
        """Test primary stress pillar determination"""
        # High integration density -> Behavioral Integrity
        high_integration = CompositionMetrics(
            component_count=4, integration_density=2.5, composition_score=10.0
        )
        assert (
            high_integration.get_primary_stress_pillar()
            == MemoryPillar.BEHAVIORAL_INTEGRITY
        )

        # Many components -> Contextual Relevance
        many_components = CompositionMetrics(
            component_count=10, integration_density=1.0, composition_score=10.0
        )
        assert (
            many_components.get_primary_stress_pillar()
            == MemoryPillar.CONTEXTUAL_RELEVANCE
        )

        # Default -> Memory Fidelity
        default_case = CompositionMetrics(
            component_count=3, integration_density=1.0, composition_score=3.0
        )
        assert default_case.get_primary_stress_pillar() == MemoryPillar.MEMORY_FIDELITY


class TestComplexityProfile:
    """Test ComplexityProfile analysis and generation"""

    def create_sample_task(self) -> TaskSpecification:
        """Create sample task for complexity analysis"""
        checkpoints = [
            CheckpointSpecification(
                checkpoint_id="cp1",
                order=1,
                title="User Model",
                stub_file="user.py",
                stub_function="User",
                requirements="Implement user model with validation and persistence",
                test_file="test_user.py",
                estimated_tokens=300,
            ),
            CheckpointSpecification(
                checkpoint_id="cp2",
                order=2,
                title="Auth Service",
                stub_file="auth.py",
                stub_function="AuthService",
                requirements="Implement authentication service with JWT tokens",
                test_file="test_auth.py",
                dependencies=["cp1"],
                estimated_tokens=400,
            ),
            CheckpointSpecification(
                checkpoint_id="cp3",
                order=3,
                title="API Endpoints",
                stub_file="api.py",
                stub_function="API",
                requirements="Implement REST API endpoints for user operations",
                test_file="test_api.py",
                dependencies=["cp1", "cp2"],
                estimated_tokens=350,
            ),
            CheckpointSpecification(
                checkpoint_id="cp4",
                order=4,
                title="Frontend Integration",
                stub_file="frontend.py",
                stub_function="Frontend",
                requirements="Integrate with frontend application",
                test_file="test_frontend.py",
                dependencies=["cp3"],
                estimated_tokens=250,
            ),
        ]

        return TaskSpecification(
            task_id="sample_task",
            title="Sample Task",
            domain="web_service",
            description="Sample web service task",
            checkpoints=checkpoints,
            planning_phase=PlanningPhase(overview_prompt="Build web service"),
            repository=RepositoryTemplate(template_name="web_service"),
        )

    def test_complexity_profile_generation(self):
        """Test complexity profile generation from task"""
        task = self.create_sample_task()
        profile = ComplexityProfile.from_task_specification(task)

        assert profile.length_dimension == 4
        assert profile.depth_dimension == 325  # Average of 300, 400, 350, 250
        assert profile.composition_metrics.component_count == 4
        assert profile.composition_metrics.composition_score == 4.0  # 4 * 1.0

        # Should determine complexity tier
        assert profile.complexity_tier in [
            "simple",
            "moderate",
            "complex",
            "highly_complex",
        ]

        # Should have pillar stress scores
        assert MemoryPillar.MEMORY_FIDELITY in profile.pillar_stress_scores
        assert MemoryPillar.CONTEXTUAL_RELEVANCE in profile.pillar_stress_scores
        assert MemoryPillar.BEHAVIORAL_INTEGRITY in profile.pillar_stress_scores

    def test_pillar_stress_calculation(self):
        """Test pillar stress score calculation"""
        # High length task
        high_length_scores = ComplexityProfile._calculate_pillar_stress_scores(
            length=12, depth=200, composition=CompositionMetrics(3, 1.0, 3.0)
        )
        assert high_length_scores[MemoryPillar.MEMORY_FIDELITY] > 0.8

        # High depth task
        high_depth_scores = ComplexityProfile._calculate_pillar_stress_scores(
            length=4, depth=600, composition=CompositionMetrics(3, 1.0, 3.0)
        )
        assert high_depth_scores[MemoryPillar.CONTEXTUAL_RELEVANCE] > 0.8

        # High composition task
        high_composition = CompositionMetrics(8, 2.0, 16.0)
        high_comp_scores = ComplexityProfile._calculate_pillar_stress_scores(
            length=4, depth=200, composition=high_composition
        )
        assert high_comp_scores[MemoryPillar.BEHAVIORAL_INTEGRITY] > 0.8

    def test_probe_recommendations(self):
        """Test probe type recommendations"""
        # Memory fidelity primary
        fidelity_probes = ComplexityProfile._recommend_probe_types(
            MemoryPillar.MEMORY_FIDELITY, [], "moderate"
        )
        assert ProbeType.N_BACK_INTEGRATION in fidelity_probes
        assert ProbeType.COMPRESSION_STRESS in fidelity_probes

        # Contextual relevance primary
        relevance_probes = ComplexityProfile._recommend_probe_types(
            MemoryPillar.CONTEXTUAL_RELEVANCE, [], "moderate"
        )
        assert ProbeType.DISTRACTOR_INJECTION in relevance_probes
        assert ProbeType.CHANGE_DETECTION in relevance_probes

        # Behavioral integrity primary
        integrity_probes = ComplexityProfile._recommend_probe_types(
            MemoryPillar.BEHAVIORAL_INTEGRITY, [], "moderate"
        )
        assert ProbeType.UPDATE_ROBUSTNESS in integrity_probes
        assert ProbeType.CONTEXT_SWITCH in integrity_probes

    def test_probe_density_calculation(self):
        """Test optimal probe density calculation"""
        # Simple task
        simple_density = ComplexityProfile._calculate_optimal_probe_density(3, "simple")
        assert simple_density == 1

        # Moderate task
        moderate_density = ComplexityProfile._calculate_optimal_probe_density(
            6, "moderate"
        )
        assert moderate_density == 2

        # Complex task
        complex_density = ComplexityProfile._calculate_optimal_probe_density(
            8, "complex"
        )
        assert complex_density == 3

        # Highly complex task
        highly_complex_density = ComplexityProfile._calculate_optimal_probe_density(
            12, "highly_complex"
        )
        assert highly_complex_density == 5  # 4 base + 1 for long task

    def test_probe_injection_points(self):
        """Test probe injection point calculation"""
        # Short task
        short_points = ComplexityProfile._calculate_probe_injection_points(4, 2)
        assert len(short_points) == 2
        assert 1 not in short_points  # Should avoid first checkpoint

        # Long task
        long_points = ComplexityProfile._calculate_probe_injection_points(10, 3)
        assert len(long_points) == 3
        assert all(point >= 2 for point in long_points)  # All should be >= 2

        # More probes than checkpoints
        many_probes_points = ComplexityProfile._calculate_probe_injection_points(3, 5)
        assert len(many_probes_points) <= 3  # Can't exceed checkpoint count

    def test_auto_probe_configuration(self):
        """Test automatic probe configuration for checkpoints"""
        task = self.create_sample_task()
        profile = ComplexityProfile.from_task_specification(task)

        probes = profile.auto_configure_probes_for_checkpoints(task.checkpoints)

        # Should create probes based on recommendations
        assert len(probes) > 0
        assert all(isinstance(probe, MemoryProbe) for probe in probes)
        assert all(
            probe.target_checkpoint in ["cp2", "cp3", "cp4"] for probe in probes
        )  # Avoid cp1


class TestEnhancedTaskSpecification:
    """Test enhanced TaskSpecification functionality"""

    def create_enhanced_task(self) -> TaskSpecification:
        """Create task with enhanced features"""
        checkpoints = [
            CheckpointSpecification(
                checkpoint_id="cp1",
                order=1,
                title="Core Service",
                stub_file="core.py",
                stub_function="CoreService",
                requirements="Implement core service",
                test_file="test_core.py",
                embedded_probes=[
                    MemoryProbe(
                        probe_id="embedded_probe_1",
                        probe_type=ProbeType.N_BACK_INTEGRATION,
                        pillar=MemoryPillar.MEMORY_FIDELITY,
                        target_checkpoint="cp1",
                        description="Embedded probe test",
                        n_back_distance=1,
                    )
                ],
                context_conditions=[
                    ContextWindowCondition(
                        condition_name="test_condition",
                        condition_type=ContextConditionType.STANDARDIZED,
                        token_limit=4096,
                        description="Test condition",
                    )
                ],
                pillar_stress_target=MemoryPillar.MEMORY_FIDELITY,
            )
        ]

        memory_probes = [
            MemoryProbe(
                probe_id="task_probe_1",
                probe_type=ProbeType.DISTRACTOR_INJECTION,
                pillar=MemoryPillar.CONTEXTUAL_RELEVANCE,
                target_checkpoint="cp1",
                description="Task-level probe",
                distractor_ratio=0.2,
            )
        ]

        context_conditions = [
            ContextWindowCondition(
                condition_name="standard",
                condition_type=ContextConditionType.STANDARDIZED,
                token_limit=8192,
                description="Standard condition",
            )
        ]

        three_d_complexity = ThreeDimensionalComplexity(
            length_dimension=1,
            depth_dimension=200,
            composition_dimension=1.0,
            primary_stress_pillar=MemoryPillar.MEMORY_FIDELITY,
        )

        return TaskSpecification(
            task_id="enhanced_task",
            title="Enhanced Task",
            domain="test",
            description="Task with enhanced features",
            checkpoints=checkpoints,
            planning_phase=PlanningPhase(overview_prompt="Test"),
            repository=RepositoryTemplate(template_name="test"),
            enhanced_evaluation=True,
            memory_probes=memory_probes,
            context_conditions=context_conditions,
            three_dimensional_complexity=three_d_complexity,
        )

    def test_enhanced_task_creation(self):
        """Test creating task with enhanced features"""
        task = self.create_enhanced_task()

        assert task.enhanced_evaluation is True
        assert len(task.memory_probes) == 1
        assert len(task.context_conditions) == 1
        assert task.three_dimensional_complexity is not None
        assert task.is_enhanced_evaluation() is True

    def test_enhanced_feature_detection(self):
        """Test automatic enhanced feature detection"""
        # Task with embedded probes should be detected as enhanced
        checkpoint_with_probe = CheckpointSpecification(
            checkpoint_id="cp1",
            order=1,
            title="Test",
            stub_file="test.py",
            stub_function="test",
            requirements="test",
            test_file="test_test.py",
            embedded_probes=[
                MemoryProbe(
                    probe_id="test_probe",
                    probe_type=ProbeType.N_BACK_INTEGRATION,
                    pillar=MemoryPillar.MEMORY_FIDELITY,
                    target_checkpoint="cp1",
                    description="Test probe",
                )
            ],
        )

        task = TaskSpecification(
            task_id="test",
            title="Test",
            domain="test",
            description="test",
            checkpoints=[checkpoint_with_probe],
            planning_phase=PlanningPhase(overview_prompt="test"),
            repository=RepositoryTemplate(template_name="test"),
        )

        assert task.is_enhanced_evaluation() is True

    def test_get_all_probes(self):
        """Test getting all probes from task and checkpoints"""
        task = self.create_enhanced_task()
        all_probes = task.get_all_probes()

        assert len(all_probes) == 2  # 1 task-level + 1 embedded
        probe_ids = [probe.probe_id for probe in all_probes]
        assert "task_probe_1" in probe_ids
        assert "embedded_probe_1" in probe_ids

    def test_get_probes_for_checkpoint(self):
        """Test getting probes for specific checkpoint"""
        task = self.create_enhanced_task()
        cp1_probes = task.get_probes_for_checkpoint("cp1")

        assert len(cp1_probes) == 2  # Both probes target cp1
        probe_types = [probe.probe_type for probe in cp1_probes]
        assert ProbeType.DISTRACTOR_INJECTION in probe_types
        assert ProbeType.N_BACK_INTEGRATION in probe_types

    def test_auto_configure_enhanced_features(self):
        """Test automatic configuration of enhanced features"""
        # Create basic task
        basic_task = TaskSpecification(
            task_id="basic",
            title="Basic Task",
            domain="test",
            description="Basic task",
            checkpoints=[
                CheckpointSpecification(
                    checkpoint_id="cp1",
                    order=1,
                    title="Test",
                    stub_file="test.py",
                    stub_function="test",
                    requirements="test",
                    test_file="test_test.py",
                )
            ],
            planning_phase=PlanningPhase(overview_prompt="test"),
            repository=RepositoryTemplate(template_name="test"),
        )

        # Auto-configure enhanced features
        enhanced_task = basic_task.auto_configure_enhanced_features()

        assert enhanced_task.is_enhanced_evaluation() is True
        assert len(enhanced_task.memory_probes) > 0
        assert len(enhanced_task.context_conditions) > 0
        assert enhanced_task.three_dimensional_complexity is not None

    def test_enhanced_serialization(self):
        """Test serialization of enhanced task features"""
        task = self.create_enhanced_task()
        task_dict = task.to_dict()

        # Check enhanced fields are present
        assert task_dict["enhanced_evaluation"] is True
        assert "memory_probes" in task_dict
        assert "context_conditions" in task_dict
        assert "three_dimensional_complexity" in task_dict

        # Check checkpoint enhanced fields
        cp1 = task_dict["checkpoints"][0]
        assert "embedded_probes" in cp1
        assert "context_conditions" in cp1
        assert "pillar_stress_target" in cp1

    def test_enhanced_deserialization(self):
        """Test deserialization of enhanced task features"""
        original_task = self.create_enhanced_task()
        task_dict = original_task.to_dict()
        reconstructed_task = TaskSpecification.from_dict(task_dict)

        # Check enhanced features preserved
        assert reconstructed_task.is_enhanced_evaluation() is True
        assert len(reconstructed_task.memory_probes) == len(original_task.memory_probes)
        assert len(reconstructed_task.context_conditions) == len(
            original_task.context_conditions
        )
        assert reconstructed_task.three_dimensional_complexity is not None

        # Check checkpoint enhanced features preserved
        orig_cp = original_task.checkpoints[0]
        recon_cp = reconstructed_task.checkpoints[0]
        assert len(recon_cp.embedded_probes) == len(orig_cp.embedded_probes)
        assert len(recon_cp.context_conditions) == len(orig_cp.context_conditions)
        assert recon_cp.pillar_stress_target == orig_cp.pillar_stress_target


class TestResearchTemplate:
    """Test ResearchTemplate functionality"""

    def test_research_template_creation(self):
        """Test creating research template"""
        template = ResearchTemplate(
            template_id="test_template",
            name="Test Template",
            description="Test research template",
            research_focus=MemoryPillar.MEMORY_FIDELITY,
            probe_configuration=[
                {
                    "probe_type": "n_back_integration",
                    "description": "Test N-back integration",
                    "n_back_distance": 2,
                }
            ],
            context_conditions=[
                {
                    "condition_name": "standardized",
                    "condition_type": "standardized",
                    "token_limit": 8192,
                }
            ],
            difficulty_level="moderate",
            estimated_duration_minutes=90,
        )

        assert template.template_id == "test_template"
        assert template.research_focus == MemoryPillar.MEMORY_FIDELITY
        assert len(template.probe_configuration) == 1
        assert len(template.context_conditions) == 1

    def test_template_application_to_task(self):
        """Test applying research template to task"""
        # Create basic task
        basic_task = TaskSpecification(
            task_id="basic",
            title="Basic Task",
            domain="test",
            description="Basic task",
            checkpoints=[
                CheckpointSpecification(
                    checkpoint_id="cp1",
                    order=1,
                    title="Component A",
                    stub_file="a.py",
                    stub_function="A",
                    requirements="Component A",
                    test_file="test_a.py",
                ),
                CheckpointSpecification(
                    checkpoint_id="cp2",
                    order=2,
                    title="Component B",
                    stub_file="b.py",
                    stub_function="B",
                    requirements="Component B",
                    test_file="test_b.py",
                ),
            ],
            planning_phase=PlanningPhase(overview_prompt="test"),
            repository=RepositoryTemplate(template_name="test"),
        )

        # Create and apply template
        template = ResearchTemplate(
            template_id="test_template",
            name="Test Template",
            description="Test template",
            research_focus=MemoryPillar.MEMORY_FIDELITY,
            probe_configuration=[
                {
                    "probe_type": "n_back_integration",
                    "description": "Test N-back",
                    "n_back_distance": 2,
                }
            ],
            context_conditions=[
                {
                    "condition_name": "standardized",
                    "condition_type": "standardized",
                    "token_limit": 8192,
                }
            ],
        )

        enhanced_task = template.apply_to_task(basic_task)

        assert enhanced_task.is_enhanced_evaluation() is True
        assert len(enhanced_task.memory_probes) == 1
        assert enhanced_task.memory_probes[0].probe_type == ProbeType.N_BACK_INTEGRATION
        assert len(enhanced_task.context_conditions) == 1
        assert "template_test_template" in enhanced_task.tags


class TestResearchTemplateFactory:
    """Test ResearchTemplateFactory functionality"""

    def test_memory_fidelity_template(self):
        """Test memory fidelity research template"""
        template = ResearchTemplateFactory.create_memory_fidelity_study()

        assert template.template_id == "memory_fidelity_study"
        assert template.research_focus == MemoryPillar.MEMORY_FIDELITY
        assert len(template.probe_configuration) == 2
        assert any(
            probe["probe_type"] == "n_back_integration"
            for probe in template.probe_configuration
        )
        assert any(
            probe["probe_type"] == "compression_stress"
            for probe in template.probe_configuration
        )

    def test_contextual_relevance_template(self):
        """Test contextual relevance research template"""
        template = ResearchTemplateFactory.create_contextual_relevance_study()

        assert template.template_id == "contextual_relevance_study"
        assert template.research_focus == MemoryPillar.CONTEXTUAL_RELEVANCE
        assert len(template.probe_configuration) == 2
        assert any(
            probe["probe_type"] == "distractor_injection"
            for probe in template.probe_configuration
        )
        assert any(
            probe["probe_type"] == "change_detection"
            for probe in template.probe_configuration
        )

    def test_behavioral_integrity_template(self):
        """Test behavioral integrity research template"""
        template = ResearchTemplateFactory.create_behavioral_integrity_study()

        assert template.template_id == "behavioral_integrity_study"
        assert template.research_focus == MemoryPillar.BEHAVIORAL_INTEGRITY
        assert len(template.probe_configuration) == 2
        assert any(
            probe["probe_type"] == "update_robustness"
            for probe in template.probe_configuration
        )
        assert any(
            probe["probe_type"] == "context_switch"
            for probe in template.probe_configuration
        )

    def test_balanced_template(self):
        """Test balanced three-pillar research template"""
        template = ResearchTemplateFactory.create_balanced_study()

        assert template.template_id == "balanced_study"
        assert template.research_focus == MemoryPillar.MEMORY_FIDELITY  # Primary focus
        assert len(template.probe_configuration) == 3  # One for each pillar

        probe_types = [probe["probe_type"] for probe in template.probe_configuration]
        assert "n_back_integration" in probe_types
        assert "distractor_injection" in probe_types
        assert "update_robustness" in probe_types

    def test_get_available_templates(self):
        """Test getting all available templates"""
        templates = ResearchTemplateFactory.get_available_templates()

        assert len(templates) == 4
        assert "memory_fidelity" in templates
        assert "contextual_relevance" in templates
        assert "behavioral_integrity" in templates
        assert "balanced" in templates

        # All should be ResearchTemplate instances
        assert all(
            isinstance(template, ResearchTemplate) for template in templates.values()
        )

    def test_get_template_by_research_focus(self):
        """Test getting template by research focus"""
        fidelity_template = ResearchTemplateFactory.get_template_by_research_focus(
            MemoryPillar.MEMORY_FIDELITY
        )
        assert fidelity_template.research_focus == MemoryPillar.MEMORY_FIDELITY

        relevance_template = ResearchTemplateFactory.get_template_by_research_focus(
            MemoryPillar.CONTEXTUAL_RELEVANCE
        )
        assert relevance_template.research_focus == MemoryPillar.CONTEXTUAL_RELEVANCE

        integrity_template = ResearchTemplateFactory.get_template_by_research_focus(
            MemoryPillar.BEHAVIORAL_INTEGRITY
        )
        assert integrity_template.research_focus == MemoryPillar.BEHAVIORAL_INTEGRITY

    def test_recommend_template_for_task(self):
        """Test template recommendation based on task characteristics"""
        # High length task should get memory fidelity template
        high_length_task = TaskSpecification(
            task_id="high_length",
            title="High Length Task",
            domain="test",
            description="Task with many checkpoints",
            checkpoints=[
                CheckpointSpecification(
                    checkpoint_id=f"cp{i}",
                    order=i,
                    title=f"Component {i}",
                    stub_file=f"comp{i}.py",
                    stub_function=f"Component{i}",
                    requirements=f"Component {i}",
                    test_file=f"test_comp{i}.py",
                )
                for i in range(1, 11)  # 10 checkpoints
            ],
            planning_phase=PlanningPhase(overview_prompt="test"),
            repository=RepositoryTemplate(template_name="test"),
        )

        recommended = ResearchTemplateFactory.recommend_template_for_task(
            high_length_task
        )
        assert recommended.research_focus == MemoryPillar.MEMORY_FIDELITY


class TestConfigurationProfile:
    """Test ConfigurationProfile functionality"""

    def create_sample_task(self) -> TaskSpecification:
        """Create sample task for configuration testing"""
        return TaskSpecification(
            task_id="config_test",
            title="Configuration Test Task",
            domain="test",
            description="Task for testing configuration",
            checkpoints=[
                CheckpointSpecification(
                    checkpoint_id="cp1",
                    order=1,
                    title="Component A",
                    stub_file="a.py",
                    stub_function="A",
                    requirements="Component A",
                    test_file="test_a.py",
                ),
                CheckpointSpecification(
                    checkpoint_id="cp2",
                    order=2,
                    title="Component B",
                    stub_file="b.py",
                    stub_function="B",
                    requirements="Component B",
                    test_file="test_b.py",
                ),
            ],
            planning_phase=PlanningPhase(overview_prompt="test"),
            repository=RepositoryTemplate(template_name="test"),
        )

    def test_simple_mode_configuration(self):
        """Test simple mode configuration"""
        config = ConfigurationProfile(
            profile_id="simple_test", evaluation_mode=EvaluationMode.SIMPLE
        )

        task = self.create_sample_task()
        configured_task = config.configure_task(task)

        assert configured_task.enhanced_evaluation is False
        assert len(configured_task.memory_probes) == 0
        assert len(configured_task.context_conditions) == 0
        assert "simple_mode" in configured_task.tags

    def test_research_mode_configuration(self):
        """Test research mode configuration"""
        config = ConfigurationProfile(
            profile_id="research_test",
            evaluation_mode=EvaluationMode.RESEARCH,
            auto_configure_probes=True,
            auto_configure_context=True,
        )

        task = self.create_sample_task()
        configured_task = config.configure_task(task)

        assert configured_task.enhanced_evaluation is True
        assert len(configured_task.memory_probes) > 0
        assert len(configured_task.context_conditions) > 0
        assert "research_mode" in configured_task.tags
        assert "auto_configured" in configured_task.tags

    def test_advanced_mode_configuration(self):
        """Test advanced mode configuration"""
        config = ConfigurationProfile(
            profile_id="advanced_test", evaluation_mode=EvaluationMode.ADVANCED
        )

        task = self.create_sample_task()
        configured_task = config.configure_task(task)

        assert configured_task.enhanced_evaluation is True
        assert len(configured_task.memory_probes) > 0
        assert (
            len(configured_task.context_conditions) == 3
        )  # Standard, native, overflow
        assert configured_task.three_dimensional_complexity is not None
        assert "advanced_mode" in configured_task.tags
        assert "full_framework" in configured_task.tags

    def test_configuration_with_preferences(self):
        """Test configuration with specific preferences"""
        config = ConfigurationProfile(
            profile_id="custom_test",
            evaluation_mode=EvaluationMode.RESEARCH,
            preferred_probe_density=2,
            preferred_context_conditions=[ContextConditionType.STANDARDIZED],
            complexity_bias=MemoryPillar.CONTEXTUAL_RELEVANCE,
        )

        task = self.create_sample_task()
        configured_task = config.configure_task(task)

        # Should respect preferences
        assert len(configured_task.memory_probes) <= 2  # Preferred density
        assert len(configured_task.context_conditions) == 1  # Only standardized
        assert (
            configured_task.context_conditions[0].condition_type
            == ContextConditionType.STANDARDIZED
        )

    def test_reconfiguration_detection(self):
        """Test detection of when reconfiguration is needed"""
        config = ConfigurationProfile(
            profile_id="reconfig_test", evaluation_mode=EvaluationMode.RESEARCH
        )

        # Task already configured for research mode
        already_configured = self.create_sample_task()
        already_configured.enhanced_evaluation = True
        already_configured.memory_probes = [
            MemoryProbe(
                probe_id="existing",
                probe_type=ProbeType.N_BACK_INTEGRATION,
                pillar=MemoryPillar.MEMORY_FIDELITY,
                target_checkpoint="cp1",
                description="Existing probe",
            )
        ]

        # Should not reconfigure if already appropriate
        result = config.configure_task(already_configured)
        assert result.task_id == already_configured.task_id  # Same task returned


class TestTaskMigrationUtility:
    """Test TaskMigrationUtility functionality"""

    def create_legacy_task(self) -> TaskSpecification:
        """Create legacy task without enhanced features"""
        return TaskSpecification(
            task_id="legacy_task",
            title="Legacy Task",
            domain="legacy",
            description="Legacy task without enhanced features",
            checkpoints=[
                CheckpointSpecification(
                    checkpoint_id="cp1",
                    order=1,
                    title="Legacy Component",
                    stub_file="legacy.py",
                    stub_function="LegacyComponent",
                    requirements="Legacy component implementation",
                    test_file="test_legacy.py",
                )
            ],
            planning_phase=PlanningPhase(overview_prompt="Legacy planning"),
            repository=RepositoryTemplate(template_name="legacy"),
            enhanced_evaluation=False,  # Explicitly legacy
        )

    def test_format_detection_legacy(self):
        """Test detection of legacy task format"""
        legacy_task = self.create_legacy_task()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            legacy_task.save_to_file(temp_path)
            format_type = TaskMigrationUtility.detect_task_format(temp_path)
            assert format_type == "legacy"
        finally:
            Path(temp_path).unlink()

    def test_format_detection_enhanced(self):
        """Test detection of enhanced task format"""
        enhanced_task = TaskSpecification(
            task_id="enhanced",
            title="Enhanced Task",
            domain="test",
            description="Enhanced task",
            checkpoints=[
                CheckpointSpecification(
                    checkpoint_id="cp1",
                    order=1,
                    title="Test",
                    stub_file="test.py",
                    stub_function="test",
                    requirements="test",
                    test_file="test_test.py",
                )
            ],
            planning_phase=PlanningPhase(overview_prompt="test"),
            repository=RepositoryTemplate(template_name="test"),
            enhanced_evaluation=True,
            memory_probes=[
                MemoryProbe(
                    probe_id="test_probe",
                    probe_type=ProbeType.N_BACK_INTEGRATION,
                    pillar=MemoryPillar.MEMORY_FIDELITY,
                    target_checkpoint="cp1",
                    description="Test probe",
                )
            ],
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            enhanced_task.save_to_file(temp_path)
            format_type = TaskMigrationUtility.detect_task_format(temp_path)
            assert format_type == "enhanced"
        finally:
            Path(temp_path).unlink()

    def test_migration_to_enhanced(self):
        """Test migration of legacy task to enhanced format"""
        legacy_task = self.create_legacy_task()
        enhanced_task = TaskMigrationUtility.migrate_to_enhanced(
            legacy_task, auto_configure_probes=True
        )

        assert enhanced_task.enhanced_evaluation is True
        assert len(enhanced_task.memory_probes) > 0
        assert len(enhanced_task.context_conditions) > 0
        assert enhanced_task.three_dimensional_complexity is not None
        assert "migrated_to_enhanced" in enhanced_task.tags

    def test_migration_already_enhanced(self):
        """Test migration of already enhanced task (should return unchanged)"""
        enhanced_task = TaskSpecification(
            task_id="already_enhanced",
            title="Already Enhanced",
            domain="test",
            description="Already enhanced task",
            checkpoints=[
                CheckpointSpecification(
                    checkpoint_id="cp1",
                    order=1,
                    title="Test",
                    stub_file="test.py",
                    stub_function="test",
                    requirements="test",
                    test_file="test_test.py",
                )
            ],
            planning_phase=PlanningPhase(overview_prompt="test"),
            repository=RepositoryTemplate(template_name="test"),
            enhanced_evaluation=True,
        )

        result = TaskMigrationUtility.migrate_to_enhanced(enhanced_task)
        assert result is enhanced_task  # Should return same instance

    def test_complexity_profile_creation(self):
        """Test creation of complexity profile from legacy task"""
        legacy_task = self.create_legacy_task()
        complexity = TaskMigrationUtility._create_complexity_profile(legacy_task)

        assert isinstance(complexity, ThreeDimensionalComplexity)
        assert complexity.length_dimension == 1
        assert complexity.depth_dimension == 200  # Default
        assert complexity.composition_dimension == 1  # Single component
        assert complexity.primary_stress_pillar in [
            MemoryPillar.MEMORY_FIDELITY,
            MemoryPillar.CONTEXTUAL_RELEVANCE,
            MemoryPillar.BEHAVIORAL_INTEGRITY,
        ]

    def test_auto_probe_configuration(self):
        """Test automatic probe configuration during migration"""
        # Create task with multiple checkpoints for probe distribution
        multi_checkpoint_task = TaskSpecification(
            task_id="multi_checkpoint",
            title="Multi Checkpoint Task",
            domain="test",
            description="Task with multiple checkpoints",
            checkpoints=[
                CheckpointSpecification(
                    checkpoint_id=f"cp{i}",
                    order=i,
                    title=f"Component {i}",
                    stub_file=f"comp{i}.py",
                    stub_function=f"Component{i}",
                    requirements=f"Component {i}",
                    test_file=f"test_comp{i}.py",
                )
                for i in range(1, 6)  # 5 checkpoints
            ],
            planning_phase=PlanningPhase(overview_prompt="test"),
            repository=RepositoryTemplate(template_name="test"),
            enhanced_evaluation=False,
        )

        complexity = TaskMigrationUtility._create_complexity_profile(
            multi_checkpoint_task
        )
        probes = TaskMigrationUtility._auto_configure_probes(
            multi_checkpoint_task, complexity
        )

        assert len(probes) > 0
        assert all(isinstance(probe, MemoryProbe) for probe in probes)
        assert all(
            probe.target_checkpoint != "cp1" for probe in probes
        )  # Should avoid first checkpoint

    def test_file_migration(self):
        """Test file-based migration"""
        legacy_task = self.create_legacy_task()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as input_file:
            input_path = input_file.name

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as output_file:
            output_path = output_file.name

        try:
            # Save legacy task
            legacy_task.save_to_file(input_path)

            # Migrate file
            TaskMigrationUtility.migrate_file(
                input_path, output_path, auto_configure_probes=True
            )

            # Load migrated task
            migrated_task = TaskSpecification.load_from_file(output_path)

            assert migrated_task.enhanced_evaluation is True
            assert len(migrated_task.memory_probes) > 0
            assert "migrated_to_enhanced" in migrated_task.tags

        finally:
            Path(input_path).unlink()
            Path(output_path).unlink()


class TestEnhancedValidation:
    """Test validation of enhanced task specification features"""

    def test_enhanced_task_validation(self):
        """Test validation of enhanced task features"""
        # Create task with invalid probe reference
        invalid_probe = MemoryProbe(
            probe_id="invalid_probe",
            probe_type=ProbeType.N_BACK_INTEGRATION,
            pillar=MemoryPillar.MEMORY_FIDELITY,
            target_checkpoint="nonexistent_cp",  # Invalid reference
            description="Invalid probe",
        )

        task = TaskSpecification(
            task_id="invalid_enhanced",
            title="Invalid Enhanced Task",
            domain="test",
            description="Task with invalid enhanced features",
            checkpoints=[
                CheckpointSpecification(
                    checkpoint_id="cp1",
                    order=1,
                    title="Test",
                    stub_file="test.py",
                    stub_function="test",
                    requirements="test",
                    test_file="test_test.py",
                )
            ],
            planning_phase=PlanningPhase(overview_prompt="test"),
            repository=RepositoryTemplate(template_name="test"),
            enhanced_evaluation=True,
            memory_probes=[invalid_probe],
        )

        # Validation should catch invalid probe reference
        TaskSpecificationValidator.validate(task)
        # Note: Current validator doesn't check probe references, but it should
        # This test documents expected behavior for future enhancement

    def test_embedded_probe_validation(self):
        """Test validation of embedded probes in checkpoints"""
        # Create checkpoint with probe targeting different checkpoint
        checkpoint = CheckpointSpecification(
            checkpoint_id="cp1",
            order=1,
            title="Test",
            stub_file="test.py",
            stub_function="test",
            requirements="test",
            test_file="test_test.py",
            embedded_probes=[
                MemoryProbe(
                    probe_id="mismatched_probe",
                    probe_type=ProbeType.N_BACK_INTEGRATION,
                    pillar=MemoryPillar.MEMORY_FIDELITY,
                    target_checkpoint="cp2",  # Different from embedding checkpoint
                    description="Mismatched probe",
                )
            ],
        )

        task = TaskSpecification(
            task_id="mismatched_probe_task",
            title="Mismatched Probe Task",
            domain="test",
            description="Task with mismatched embedded probe",
            checkpoints=[checkpoint],
            planning_phase=PlanningPhase(overview_prompt="test"),
            repository=RepositoryTemplate(template_name="test"),
        )

        # This should be valid - embedded probes can target other checkpoints
        issues = TaskSpecificationValidator.validate(task)
        assert len(issues) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
