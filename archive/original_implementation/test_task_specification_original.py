"""
Unit tests for WorkMemEval task specification module.

Tests all core data structures, validation logic, and serialization/deserialization
following TDD principles with comprehensive coverage.
"""

import tempfile
from pathlib import Path

import pytest

from src.core.task_specification import (
    CheckpointSpecification,
    CheckpointType,
    EvaluationConfiguration,
    MemoryChallenge,
    MemoryChallengeType,
    PlanningPhase,
    RepositoryTemplate,
    TaskComplexityMetrics,
    TaskSpecification,
    TaskSpecificationValidator,
)


class TestCheckpointSpecification:
    """Test CheckpointSpecification data structure"""

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


class TestMemoryChallenge:
    """Test MemoryChallenge data structure"""

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


class TestTaskComplexityMetrics:
    """Test TaskComplexityMetrics calculation"""

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
            component_dependencies={
                "A": [],
                "B": [],
                "C": [],
            },  # Empty dependencies for each component
        )

        # Should calculate component count when no dependencies exist
        assert complexity.composition == 3


class TestTaskSpecification:
    """Test TaskSpecification core functionality"""

    def create_sample_task(self) -> TaskSpecification:
        """Create a sample task specification for testing"""
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
            task_id="test_task",
            title="Test Task",
            domain="test",
            description="Test task description",
            checkpoints=checkpoints,
            planning_phase=planning_phase,
            repository=repository,
        )

    def test_valid_task_creation(self):
        """Test creating a valid task specification"""
        task = self.create_sample_task()

        assert task.task_id == "test_task"
        assert task.title == "Test Task"
        assert len(task.checkpoints) == 2
        assert task.complexity.length == 2
        assert task.complexity.depth == 200.0  # Default token count

    def test_auto_complexity_calculation(self):
        """Test automatic complexity calculation from checkpoints"""
        task = self.create_sample_task()

        # Should auto-calculate complexity
        assert task.complexity is not None
        assert task.complexity.length == 2
        assert len(task.complexity.semantic_components) == 2
        assert "User Model" in task.complexity.semantic_components
        assert "Auth Service" in task.complexity.semantic_components

    def test_get_checkpoint_by_id(self):
        """Test checkpoint retrieval by ID"""
        task = self.create_sample_task()

        cp1 = task.get_checkpoint_by_id("cp1")
        assert cp1 is not None
        assert cp1.title == "User Model"

        cp_none = task.get_checkpoint_by_id("nonexistent")
        assert cp_none is None

    def test_get_required_files_for_checkpoint(self):
        """Test required files calculation for checkpoint"""
        task = self.create_sample_task()

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

    def test_task_validation_missing_required_fields(self):
        """Test task validation fails with missing required fields"""
        with pytest.raises(ValueError, match="task_id and title are required"):
            TaskSpecification(
                task_id="",
                title="Test",
                domain="test",
                description="test",
                checkpoints=[],
                planning_phase=PlanningPhase(overview_prompt="test"),
                repository=RepositoryTemplate(template_name="test"),
            )

    def test_task_validation_no_checkpoints(self):
        """Test task validation fails with no checkpoints"""
        with pytest.raises(ValueError, match="Task must have at least one checkpoint"):
            TaskSpecification(
                task_id="test",
                title="Test",
                domain="test",
                description="test",
                checkpoints=[],
                planning_phase=PlanningPhase(overview_prompt="test"),
                repository=RepositoryTemplate(template_name="test"),
            )

    def test_dependency_validation_nonexistent_checkpoint(self):
        """Test dependency validation fails with non-existent checkpoint"""
        checkpoint = CheckpointSpecification(
            checkpoint_id="cp1",
            order=1,
            title="Test",
            stub_file="test.py",
            stub_function="test",
            requirements="test",
            test_file="test_test.py",
            dependencies=["nonexistent"],  # Invalid dependency
        )

        with pytest.raises(ValueError, match="depends on non-existent checkpoint"):
            TaskSpecification(
                task_id="test",
                title="Test",
                domain="test",
                description="test",
                checkpoints=[checkpoint],
                planning_phase=PlanningPhase(overview_prompt="test"),
                repository=RepositoryTemplate(template_name="test"),
            )


class TestTaskSpecificationSerialization:
    """Test task specification serialization and deserialization"""

    def create_full_sample_task(self) -> TaskSpecification:
        """Create a comprehensive sample task for serialization testing"""
        checkpoints = [
            CheckpointSpecification(
                checkpoint_id="cp1",
                order=1,
                title="User Model",
                stub_file="src/models/user.py",
                stub_function="User",
                requirements="Implement User class with validation",
                test_file="tests/test_user.py",
                estimated_tokens=250,
                metadata={"complexity": "medium"},
            ),
            CheckpointSpecification(
                checkpoint_id="cp2",
                order=2,
                title="Auth Service",
                stub_file="src/auth/service.py",
                stub_function="AuthService",
                requirements="Implement authentication service",
                test_file="tests/test_auth.py",
                dependencies=["cp1"],
                checkpoint_type=CheckpointType.INTEGRATION,
                estimated_tokens=300,
            ),
        ]

        planning_phase = PlanningPhase(
            overview_prompt="Build a user management system with authentication",
            planning_deliverables={
                "architecture": "System architecture overview",
                "components": "Component breakdown",
            },
            planning_capture={"plan_document": "PLAN.md", "max_time": 20},
            required_sections=["Architecture", "Components", "Integration"],
        )

        repository = RepositoryTemplate(
            template_name="user_management_starter",
            provided_files=["README.md", "requirements.txt", "src/__init__.py"],
            distractor_files=["legacy/old_system.py", "docs/outdated.md"],
            directory_structure={
                "src": ["models", "auth", "api"],
                "tests": ["unit", "integration"],
            },
            setup_commands=["pip install -r requirements.txt"],
        )

        memory_challenges = [
            MemoryChallenge(
                challenge_id="req_update_1",
                challenge_type=MemoryChallengeType.REQUIREMENT_UPDATE,
                at_checkpoint="cp2",
                description="User model now requires email verification",
                affects=["cp1"],
                metadata={"priority": "high"},
            ),
            MemoryChallenge(
                challenge_id="context_switch_1",
                challenge_type=MemoryChallengeType.CONTEXT_SWITCH,
                at_checkpoint="cp2",
                description="Add logging utility",
                interruption_task="Create logging utility in src/utils/logger.py",
                duration_minutes=15,
            ),
        ]

        complexity = TaskComplexityMetrics(
            length=2,
            depth=275.0,
            composition=0,  # Will be calculated
            semantic_components=["User Model", "Auth Service"],
            component_dependencies={"User Model": [], "Auth Service": ["User Model"]},
        )

        evaluation_config = EvaluationConfiguration(
            memory_checkpoint_frequency=2,
            planning_compliance_tracking=True,
            trace_capture_level="comprehensive",
            timeout_minutes=120,
            enable_memory_challenges=True,
        )

        return TaskSpecification(
            task_id="user_management_api",
            title="User Management API",
            domain="api_service",
            description="Build a complete user management API with authentication",
            checkpoints=checkpoints,
            planning_phase=planning_phase,
            repository=repository,
            memory_challenges=memory_challenges,
            complexity=complexity,
            evaluation_config=evaluation_config,
            difficulty="intermediate",
            estimated_duration_minutes=120,
            created_by="test_author",
            version="1.0",
            tags=["api", "authentication", "user-management"],
        )

    def test_to_dict_conversion(self):
        """Test conversion of task specification to dictionary"""
        task = self.create_full_sample_task()
        task_dict = task.to_dict()

        # Check basic fields
        assert task_dict["task_id"] == "user_management_api"
        assert task_dict["title"] == "User Management API"
        assert task_dict["domain"] == "api_service"
        assert task_dict["difficulty"] == "intermediate"

        # Check checkpoints
        assert len(task_dict["checkpoints"]) == 2
        cp1 = task_dict["checkpoints"][0]
        assert cp1["checkpoint_id"] == "cp1"
        assert cp1["title"] == "User Model"
        assert cp1["checkpoint_type"] == "implementation"

        # Check planning phase
        planning = task_dict["planning_phase"]
        assert "Build a user management system" in planning["overview_prompt"]
        assert "architecture" in planning["planning_deliverables"]

        # Check memory challenges
        assert len(task_dict["memory_challenges"]) == 2
        challenge1 = task_dict["memory_challenges"][0]
        assert challenge1["challenge_type"] == "requirement_update"

        # Check complexity
        complexity = task_dict["complexity"]
        assert complexity["length"] == 2
        assert complexity["depth"] == 275.0

    def test_from_dict_conversion(self):
        """Test creation of task specification from dictionary"""
        original_task = self.create_full_sample_task()
        task_dict = original_task.to_dict()
        reconstructed_task = TaskSpecification.from_dict(task_dict)

        # Check basic equality
        assert reconstructed_task.task_id == original_task.task_id
        assert reconstructed_task.title == original_task.title
        assert reconstructed_task.domain == original_task.domain

        # Check checkpoints
        assert len(reconstructed_task.checkpoints) == len(original_task.checkpoints)
        for orig_cp, recon_cp in zip(
            original_task.checkpoints, reconstructed_task.checkpoints
        ):
            assert orig_cp.checkpoint_id == recon_cp.checkpoint_id
            assert orig_cp.title == recon_cp.title
            assert orig_cp.checkpoint_type == recon_cp.checkpoint_type
            assert orig_cp.dependencies == recon_cp.dependencies

        # Check memory challenges
        assert len(reconstructed_task.memory_challenges) == len(
            original_task.memory_challenges
        )

        # Check complexity
        assert reconstructed_task.complexity.length == original_task.complexity.length
        assert reconstructed_task.complexity.depth == original_task.complexity.depth

    def test_roundtrip_serialization(self):
        """Test full roundtrip serialization: task -> dict -> task"""
        original_task = self.create_full_sample_task()

        # Convert to dict and back
        task_dict = original_task.to_dict()
        reconstructed_task = TaskSpecification.from_dict(task_dict)

        # Should be functionally identical
        assert original_task.task_id == reconstructed_task.task_id
        assert original_task.title == reconstructed_task.title
        assert len(original_task.checkpoints) == len(reconstructed_task.checkpoints)
        assert len(original_task.memory_challenges) == len(
            reconstructed_task.memory_challenges
        )

        # Test required files calculation works the same
        cp1_files_orig = original_task.get_required_files_for_checkpoint("cp1")
        cp1_files_recon = reconstructed_task.get_required_files_for_checkpoint("cp1")
        assert cp1_files_orig == cp1_files_recon

    def test_file_save_and_load(self):
        """Test saving to and loading from JSON file"""
        original_task = self.create_full_sample_task()

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

            # Test complex field preservation
            assert loaded_task.evaluation_config.trace_capture_level == "comprehensive"
            assert (
                loaded_task.memory_challenges[0].challenge_type
                == MemoryChallengeType.REQUIREMENT_UPDATE
            )

        finally:
            Path(temp_path).unlink()


class TestTaskSpecificationValidator:
    """Test TaskSpecificationValidator functionality"""

    def test_valid_task_passes_validation(self):
        """Test that a valid task passes validation"""
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

    def test_invalid_memory_challenge_checkpoint_fails_validation(self):
        """Test that memory challenge referencing non-existent checkpoint fails"""
        checkpoint = CheckpointSpecification(
            checkpoint_id="cp1",
            order=1,
            title="Test",
            stub_file="test.py",
            stub_function="test",
            requirements="test",
            test_file="test_test.py",
        )

        invalid_challenge = MemoryChallenge(
            challenge_id="challenge1",
            challenge_type=MemoryChallengeType.REQUIREMENT_UPDATE,
            at_checkpoint="nonexistent_cp",  # Invalid reference
            description="test challenge",
        )

        task = TaskSpecification(
            task_id="invalid_task",
            title="Invalid Task",
            domain="test",
            description="test",
            checkpoints=[checkpoint],
            planning_phase=PlanningPhase(overview_prompt="test"),
            repository=RepositoryTemplate(template_name="test"),
            memory_challenges=[invalid_challenge],
        )

        issues = TaskSpecificationValidator.validate(task)
        assert len(issues) > 0
        assert any("references non-existent checkpoint" in issue for issue in issues)

    def test_complexity_length_mismatch_fails_validation(self):
        """Test that complexity length mismatch fails validation"""
        checkpoint = CheckpointSpecification(
            checkpoint_id="cp1",
            order=1,
            title="Test",
            stub_file="test.py",
            stub_function="test",
            requirements="test",
            test_file="test_test.py",
        )

        # Create task with explicit complexity that doesn't match checkpoint count
        task = TaskSpecification(
            task_id="invalid_task",
            title="Invalid Task",
            domain="test",
            description="test",
            checkpoints=[checkpoint],  # 1 checkpoint
            planning_phase=PlanningPhase(overview_prompt="test"),
            repository=RepositoryTemplate(template_name="test"),
        )

        # Manually set invalid complexity
        task.complexity.length = 3  # Doesn't match 1 checkpoint

        issues = TaskSpecificationValidator.validate(task)
        assert len(issues) > 0
        assert any(
            "Complexity length doesn't match checkpoint count" in issue
            for issue in issues
        )


if __name__ == "__main__":
    pytest.main([__file__])
