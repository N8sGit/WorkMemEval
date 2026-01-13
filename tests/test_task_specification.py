"""
Comprehensive tests for WorkMemEval task specification module.

Tests both legacy and enhanced functionality with complete coverage
of the cleanly separated implementation.
"""

import tempfile
from pathlib import Path

import pytest

from src.core.task_specification import (  # Unified interface (backward compatible); Enhanced system classes; Enums
    CheckpointSpecification,
    CheckpointType,
    ContextConditionType,
    ContextWindowCondition,
    EnhancedComplexityProfile,
    LegacyMigrationUtility,
    MemoryChallenge,
    MemoryChallengeType,
    MemoryPillar,
    MemoryProbe,
    PlanningPhase,
    ProbeType,
    RepositoryTemplate,
    TaskComplexityMetrics,
    TaskSpecification,
    TaskSpecificationValidator,
)

# =============================================================================
# LEGACY SYSTEM TESTS (BACKWARD COMPATIBILITY)
# =============================================================================


class TestLegacyCheckpointSpecification:
    """Test legacy CheckpointSpecification functionality"""

    def test_valid_checkpoint_creation(self):
        """Test creating a valid checkpoint specification"""
        checkpoint = CheckpointSpecification(
            checkpoint_id="cp1",
            order=1,
            title="User Model",
            stub_file="src/models/user.py",
            stub_function="User",
            requirements="Implement User class with validation",
            test_file="tests/test_user_model.py",
        )

        assert checkpoint.checkpoint_id == "cp1"
        assert checkpoint.order == 1
        assert checkpoint.title == "User Model"
        assert checkpoint.checkpoint_type == CheckpointType.IMPLEMENTATION
        assert checkpoint.estimated_tokens == 200
        assert checkpoint.dependencies == []
        assert checkpoint.metadata == {}

    def test_checkpoint_with_dependencies(self):
        """Test checkpoint with dependencies"""
        checkpoint = CheckpointSpecification(
            checkpoint_id="cp2",
            order=2,
            title="Auth Service",
            stub_file="src/auth/service.py",
            stub_function="AuthService",
            requirements="Implement authentication service",
            test_file="tests/test_auth_service.py",
            dependencies=["cp1"],
            checkpoint_type=CheckpointType.INTEGRATION,
            estimated_tokens=350,
        )

        assert checkpoint.dependencies == ["cp1"]
        assert checkpoint.checkpoint_type == CheckpointType.INTEGRATION
        assert checkpoint.estimated_tokens == 350

    def test_checkpoint_validation_empty_id(self):
        """Test checkpoint validation fails with empty ID"""
        with pytest.raises(ValueError, match="checkpoint_id cannot be empty"):
            CheckpointSpecification(
                checkpoint_id="",
                order=1,
                title="Test",
                stub_file="test.py",
                stub_function="test",
                requirements="test",
                test_file="test_test.py",
            )

    def test_checkpoint_validation_missing_files(self):
        """Test checkpoint validation fails with missing files"""
        with pytest.raises(ValueError, match="stub_file and test_file are required"):
            CheckpointSpecification(
                checkpoint_id="test",
                order=1,
                title="Test",
                stub_file="",
                stub_function="test",
                requirements="test",
                test_file="test_test.py",
            )

    def test_checkpoint_validation_invalid_order(self):
        """Test checkpoint validation fails with invalid order"""
        with pytest.raises(ValueError, match="order must be >= 1"):
            CheckpointSpecification(
                checkpoint_id="test",
                order=0,
                title="Test",
                stub_file="test.py",
                stub_function="test",
                requirements="test",
                test_file="test_test.py",
            )


class TestLegacyMemoryChallenge:
    """Test legacy MemoryChallenge functionality"""

    def test_requirement_update_challenge(self):
        """Test requirement update memory challenge"""
        challenge = MemoryChallenge(
            challenge_id="req_update_1",
            challenge_type=MemoryChallengeType.REQUIREMENT_UPDATE,
            at_checkpoint="cp3",
            description="User model now requires email verification",
            affects=["cp1", "cp2"],
        )

        assert challenge.challenge_type == MemoryChallengeType.REQUIREMENT_UPDATE
        assert challenge.affects == ["cp1", "cp2"]
        assert challenge.interruption_task is None

    def test_context_switch_challenge(self):
        """Test context switch memory challenge"""
        challenge = MemoryChallenge(
            challenge_id="context_switch_1",
            challenge_type=MemoryChallengeType.CONTEXT_SWITCH,
            at_checkpoint="cp4",
            description="Implement logging utility",
            interruption_task="Create src/utils/logger.py",
            duration_minutes=10,
        )

        assert challenge.challenge_type == MemoryChallengeType.CONTEXT_SWITCH
        assert challenge.interruption_task == "Create src/utils/logger.py"
        assert challenge.duration_minutes == 10

    def test_information_overload_challenge(self):
        """Test information overload memory challenge"""
        challenge = MemoryChallenge(
            challenge_id="overload_1",
            challenge_type=MemoryChallengeType.INFORMATION_OVERLOAD,
            at_checkpoint="cp5",
            description="Add complex documentation files",
            distractor_files=["docs/security.md", "legacy/old_system.py"],
        )

        assert challenge.challenge_type == MemoryChallengeType.INFORMATION_OVERLOAD
        assert challenge.distractor_files == [
            "docs/security.md",
            "legacy/old_system.py",
        ]


class TestLegacyTaskComplexityMetrics:
    """Test legacy TaskComplexityMetrics calculation"""

    def test_basic_complexity_calculation(self):
        """Test basic complexity metrics calculation"""
        complexity = TaskComplexityMetrics(
            length=5,
            depth=250.0,
            composition=0,  # Will be calculated
            semantic_components=["User", "Auth", "API"],
            component_dependencies={
                "User": [],
                "Auth": ["User"],
                "API": ["User", "Auth"],
            },
        )

        assert complexity.length == 5
        assert complexity.depth == 250.0
        # Composition = 3 components × (0+1+2)/3 = 3 × 1.0 = 3.0
        assert complexity.composition == 3.0

    def test_complex_dependency_calculation(self):
        """Test complex component dependency calculation"""
        complexity = TaskComplexityMetrics(
            length=7,
            depth=300.0,
            composition=0,
            semantic_components=["A", "B", "C", "D"],
            component_dependencies={
                "A": [],
                "B": ["A"],
                "C": ["A", "B"],
                "D": ["A", "B", "C"],
            },
        )

        # Total dependencies: 0+1+2+3 = 6
        # Integration density: 6/4 = 1.5
        # Composition score: 4 × 1.5 = 6.0
        assert complexity.composition == 6.0

    def test_no_dependencies_calculation(self):
        """Test composition calculation with no dependencies"""
        complexity = TaskComplexityMetrics(
            length=3,
            depth=200.0,
            composition=0,
            semantic_components=["A", "B", "C"],
            component_dependencies={"A": [], "B": [], "C": []},
        )

        # Should calculate component count when no dependencies exist
        assert complexity.composition == 3


class TestLegacyTaskSpecification:
    """Test legacy TaskSpecification functionality"""

    def create_legacy_task(self) -> TaskSpecification:
        """Create a legacy task specification for testing"""
        checkpoints = [
            CheckpointSpecification(
                checkpoint_id="cp1",
                order=1,
                title="User Model",
                stub_file="src/models/user.py",
                stub_function="User",
                requirements="Implement User class",
                test_file="tests/test_user.py",
            ),
            CheckpointSpecification(
                checkpoint_id="cp2",
                order=2,
                title="Auth Service",
                stub_file="src/auth/service.py",
                stub_function="AuthService",
                requirements="Implement auth service",
                test_file="tests/test_auth.py",
                dependencies=["cp1"],
            ),
        ]

        planning_phase = PlanningPhase(
            overview_prompt="Create a user management system",
            required_sections=["Architecture", "Components"],
        )

        repository = RepositoryTemplate(
            template_name="user_management_starter",
            provided_files=["README.md", "requirements.txt"],
            distractor_files=["legacy/old_system.py"],
        )

        return TaskSpecification(
            task_id="legacy_test_task",
            title="Legacy Test Task",
            domain="test",
            description="Test task description",
            checkpoints=checkpoints,
            planning_phase=planning_phase,
            repository=repository,
        )

    def test_legacy_task_creation(self):
        """Test creating a legacy task specification"""
        task = self.create_legacy_task()

        assert task.task_id == "legacy_test_task"
        assert task.title == "Legacy Test Task"
        assert len(task.checkpoints) == 2
        assert task.complexity.length == 2
        assert task.complexity.depth == 200.0  # Default token count
        assert not task.is_enhanced_mode()  # Should be in legacy mode

    def test_auto_complexity_calculation(self):
        """Test automatic complexity calculation from checkpoints"""
        task = self.create_legacy_task()

        # Should auto-calculate complexity
        assert task.complexity is not None
        assert task.complexity.length == 2
        assert len(task.complexity.semantic_components) == 2
        assert "User Model" in task.complexity.semantic_components
        assert "Auth Service" in task.complexity.semantic_components

    def test_get_checkpoint_by_id(self):
        """Test checkpoint retrieval by ID"""
        task = self.create_legacy_task()

        cp1 = task.get_checkpoint_by_id("cp1")
        assert cp1 is not None
        assert cp1.title == "User Model"

        cp_none = task.get_checkpoint_by_id("nonexistent")
        assert cp_none is None

    def test_get_required_files_for_checkpoint(self):
        """Test required files calculation for checkpoint"""
        task = self.create_legacy_task()

        # cp1 has no dependencies
        cp1_files = task.get_required_files_for_checkpoint("cp1")
        expected_cp1 = {
            "src/models/user.py",
            "tests/test_user.py",
            "requirements.txt",
            "README.md",
        }
        assert cp1_files == expected_cp1

        # cp2 depends on cp1
        cp2_files = task.get_required_files_for_checkpoint("cp2")
        expected_cp2 = {
            "src/auth/service.py",
            "tests/test_auth.py",
            "src/models/user.py",  # From dependency
            "requirements.txt",
            "README.md",
        }
        assert cp2_files == expected_cp2

    def test_legacy_serialization(self):
        """Test legacy task serialization"""
        task = self.create_legacy_task()
        task_dict = task.to_dict()

        # Should have legacy fields
        assert "task_id" in task_dict
        assert "checkpoints" in task_dict
        assert "memory_challenges" in task_dict
        assert "complexity" in task_dict

        # Should not have enhanced fields
        assert "memory_probes" not in task_dict
        assert "context_conditions" not in task_dict
        assert "enhanced_complexity" not in task_dict

    def test_legacy_deserialization(self):
        """Test legacy task deserialization"""
        original_task = self.create_legacy_task()
        task_dict = original_task.to_dict()
        reconstructed_task = TaskSpecification.from_dict(task_dict)

        # Check basic equality
        assert reconstructed_task.task_id == original_task.task_id
        assert reconstructed_task.title == original_task.title
        assert reconstructed_task.domain == original_task.domain
        assert not reconstructed_task.is_enhanced_mode()

        # Check checkpoints
        assert len(reconstructed_task.checkpoints) == len(original_task.checkpoints)
        for orig_cp, recon_cp in zip(
            original_task.checkpoints, reconstructed_task.checkpoints
        ):
            assert orig_cp.checkpoint_id == recon_cp.checkpoint_id
            assert orig_cp.title == recon_cp.title
            assert orig_cp.checkpoint_type == recon_cp.checkpoint_type
            assert orig_cp.dependencies == recon_cp.dependencies

    def test_legacy_file_operations(self):
        """Test legacy file save/load operations"""
        original_task = self.create_legacy_task()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            # Save to file
            original_task.save_to_file(temp_path)

            # Load from file
            loaded_task = TaskSpecification.load_from_file(temp_path)

            # Should be identical
            assert loaded_task.task_id == original_task.task_id
            assert loaded_task.title == original_task.title
            assert len(loaded_task.checkpoints) == len(original_task.checkpoints)
            assert not loaded_task.is_enhanced_mode()

        finally:
            Path(temp_path).unlink()


class TestLegacyValidation:
    """Test legacy validation functionality"""

    def test_valid_task_passes_validation(self):
        """Test that a valid legacy task passes validation"""
        checkpoint = CheckpointSpecification(
            checkpoint_id="cp1",
            order=1,
            title="Test",
            stub_file="test.py",
            stub_function="test",
            requirements="test",
            test_file="test_test.py",
        )

        task = TaskSpecification(
            task_id="valid_task",
            title="Valid Task",
            domain="test",
            description="test",
            checkpoints=[checkpoint],
            planning_phase=PlanningPhase(overview_prompt="test"),
            repository=RepositoryTemplate(template_name="test"),
        )

        issues = TaskSpecificationValidator.validate(task)
        assert len(issues) == 0
        assert TaskSpecificationValidator.is_valid(task) is True

    def test_duplicate_checkpoint_ids_fail_validation(self):
        """Test that duplicate checkpoint IDs fail validation"""
        checkpoint1 = CheckpointSpecification(
            checkpoint_id="cp1",
            order=1,
            title="Test1",
            stub_file="test1.py",
            stub_function="test1",
            requirements="test1",
            test_file="test_test1.py",
        )

        checkpoint2 = CheckpointSpecification(
            checkpoint_id="cp1",  # Duplicate ID
            order=2,
            title="Test2",
            stub_file="test2.py",
            stub_function="test2",
            requirements="test2",
            test_file="test_test2.py",
        )

        task = TaskSpecification(
            task_id="invalid_task",
            title="Invalid Task",
            domain="test",
            description="test",
            checkpoints=[checkpoint1, checkpoint2],
            planning_phase=PlanningPhase(overview_prompt="test"),
            repository=RepositoryTemplate(template_name="test"),
        )

        issues = TaskSpecificationValidator.validate(task)
        assert len(issues) > 0
        assert any("Duplicate checkpoint ID" in issue for issue in issues)
        assert TaskSpecificationValidator.is_valid(task) is False


# =============================================================================
# ENHANCED SYSTEM TESTS
# =============================================================================


class TestMemoryProbe:
    """Test MemoryProbe functionality"""

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


class TestContextWindowCondition:
    """Test ContextWindowCondition functionality"""

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


class TestEnhancedComplexityProfile:
    """Test EnhancedComplexityProfile functionality"""

    def create_sample_task(self) -> TaskSpecification:
        """Create sample task for complexity analysis"""
        checkpoints = [
            CheckpointSpecification(
                checkpoint_id="cp1",
                order=1,
                title="User Model",
                stub_file="user.py",
                stub_function="User",
                requirements="Implement user model",
                test_file="test_user.py",
                estimated_tokens=300,
            ),
            CheckpointSpecification(
                checkpoint_id="cp2",
                order=2,
                title="Auth Service",
                stub_file="auth.py",
                stub_function="AuthService",
                requirements="Implement authentication service",
                test_file="test_auth.py",
                dependencies=["cp1"],
                estimated_tokens=400,
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

    def test_enhanced_complexity_from_legacy_task(self):
        """Test creating enhanced complexity profile from legacy task"""
        task = self.create_sample_task()
        profile = EnhancedComplexityProfile.from_legacy_task(task)

        assert profile.length_dimension == 2
        assert profile.depth_dimension == 350  # Average of 300, 400
        assert (
            profile.composition_dimension == 1.0
        )  # 2 components * 0.5 integration density

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

    def test_probe_recommendations(self):
        """Test probe type recommendations"""
        # Memory fidelity primary
        fidelity_probes = EnhancedComplexityProfile._recommend_probe_types(
            MemoryPillar.MEMORY_FIDELITY, [], "moderate"
        )
        assert ProbeType.N_BACK_INTEGRATION in fidelity_probes
        assert ProbeType.COMPRESSION_STRESS in fidelity_probes


class TestEnhancedTaskSpecification:
    """Test enhanced TaskSpecification functionality"""

    def test_enhanced_mode_activation(self):
        """Test enabling enhanced mode on legacy task"""
        # Create legacy task
        checkpoints = [
            CheckpointSpecification(
                checkpoint_id="cp1",
                order=1,
                title="Component A",
                stub_file="a.py",
                stub_function="A",
                requirements="Component A",
                test_file="test_a.py",
            )
        ]

        legacy_task = TaskSpecification(
            task_id="test",
            title="Test Task",
            domain="test",
            description="Test task",
            checkpoints=checkpoints,
            planning_phase=PlanningPhase(overview_prompt="test"),
            repository=RepositoryTemplate(template_name="test"),
        )

        # Should start in legacy mode
        assert not legacy_task.is_enhanced_mode()

        # Enable enhanced mode
        enhanced_task = legacy_task.enable_enhanced_mode()

        # Should now be in enhanced mode
        assert enhanced_task.is_enhanced_mode()
        assert len(enhanced_task.memory_probes) > 0
        assert len(enhanced_task.context_conditions) > 0
        assert enhanced_task.enhanced_complexity is not None
        assert "enhanced_mode" in enhanced_task.tags

    def test_enhanced_serialization(self):
        """Test serialization of enhanced mode tasks"""
        # Create and enhance task
        checkpoints = [
            CheckpointSpecification(
                checkpoint_id="cp1",
                order=1,
                title="Component A",
                stub_file="a.py",
                stub_function="A",
                requirements="Component A",
                test_file="test_a.py",
            )
        ]

        task = TaskSpecification(
            task_id="test",
            title="Test Task",
            domain="test",
            description="Test task",
            checkpoints=checkpoints,
            planning_phase=PlanningPhase(overview_prompt="test"),
            repository=RepositoryTemplate(template_name="test"),
        )

        enhanced_task = task.enable_enhanced_mode()
        task_dict = enhanced_task.to_dict()

        # Should have enhanced fields
        assert "memory_probes" in task_dict
        assert "context_conditions" in task_dict
        assert "enhanced_complexity" in task_dict

        # Should still have legacy fields for compatibility
        assert "complexity" in task_dict
        assert "memory_challenges" in task_dict

    def test_enhanced_deserialization(self):
        """Test deserialization of enhanced mode tasks"""
        # Create enhanced task
        checkpoints = [
            CheckpointSpecification(
                checkpoint_id="cp1",
                order=1,
                title="Component A",
                stub_file="a.py",
                stub_function="A",
                requirements="Component A",
                test_file="test_a.py",
            )
        ]

        task = TaskSpecification(
            task_id="test",
            title="Test Task",
            domain="test",
            description="Test task",
            checkpoints=checkpoints,
            planning_phase=PlanningPhase(overview_prompt="test"),
            repository=RepositoryTemplate(template_name="test"),
        )

        enhanced_task = task.enable_enhanced_mode()
        task_dict = enhanced_task.to_dict()
        reconstructed_task = TaskSpecification.from_dict(task_dict)

        # Should be in enhanced mode
        assert reconstructed_task.is_enhanced_mode()
        assert len(reconstructed_task.memory_probes) > 0
        assert len(reconstructed_task.context_conditions) > 0
        assert reconstructed_task.enhanced_complexity is not None


# =============================================================================
# MIGRATION AND UTILITIES TESTS
# =============================================================================


class TestMigrationUtilities:
    """Test migration utilities"""

    def test_format_detection(self):
        """Test detection of legacy vs enhanced format"""
        # Create legacy task
        legacy_task = TaskSpecification(
            task_id="legacy",
            title="Legacy Task",
            domain="test",
            description="Legacy task",
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

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            # Save legacy task
            legacy_task.save_to_file(temp_path)
            format_type = LegacyMigrationUtility.detect_task_format(temp_path)
            assert format_type == "legacy"

            # Enable enhanced mode and save
            enhanced_task = legacy_task.enable_enhanced_mode()
            enhanced_task.save_to_file(temp_path)
            format_type = LegacyMigrationUtility.detect_task_format(temp_path)
            assert format_type == "enhanced"

        finally:
            Path(temp_path).unlink()

    def test_migration_utility(self):
        """Test migration utility"""
        # Create legacy task
        legacy_task = TaskSpecification(
            task_id="legacy",
            title="Legacy Task",
            domain="test",
            description="Legacy task",
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

        # Migrate to enhanced
        enhanced_task = LegacyMigrationUtility.migrate_to_enhanced(legacy_task)

        assert enhanced_task.is_enhanced_mode()
        assert len(enhanced_task.memory_probes) > 0
        assert len(enhanced_task.context_conditions) > 0

    def test_file_migration(self):
        """Test file-based migration"""
        # Create legacy task
        legacy_task = TaskSpecification(
            task_id="legacy",
            title="Legacy Task",
            domain="test",
            description="Legacy task",
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
            LegacyMigrationUtility.migrate_file(input_path, output_path)

            # Load migrated task
            migrated_task = TaskSpecification.load_from_file(output_path)

            assert migrated_task.is_enhanced_mode()
            assert len(migrated_task.memory_probes) > 0

        finally:
            Path(input_path).unlink()
            Path(output_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
