"""
Integration tests for enhanced evaluation system.

Tests the complete enhanced evaluation pipeline including:
- Feature flag system
- Context window management
- Probe injection framework
- Enhanced metrics collection
"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.evaluation.runner import BasicWorkMemEvalRunner
from src.evaluation.context_window_manager import ContextWindowManager, ContextState
from src.evaluation.probe_scheduler import ProbeScheduler
from src.core.task_specification import (
    TaskSpecification, CheckpointSpecification, MemoryProbe,
    ProbeType, MemoryPillar, PlanningPhase, RepositoryTemplate
)
from src.core.plugin_interfaces import AgentImplementation, MemorySystem


class MockAgent(AgentImplementation):
    """Mock agent for testing"""
    
    def __init__(self):
        self.action_tracer = None
        self.context_window_size = 8192
        
    async def execute_checkpoint(self, checkpoint):
        pass
        
    def get_behavioral_trace(self):
        mock_trace = Mock()
        mock_trace.checkpoints = {}
        return mock_trace
        
    def _store_task_context(self, task_spec):
        pass
        
    def initialize_secure_file_ops(self, working_directory):
        pass
        
    def get_capabilities(self):
        return {"enhanced_evaluation": True}


class MockMemorySystem(MemorySystem):
    """Mock memory system for testing"""
    
    def compress_context(self):
        return {"success": True, "compression_ratio": 0.5}


def test_enhanced_evaluation_feature_flags():
    """Test that enhanced evaluation can be enabled/disabled via feature flags"""
    
    # Test disabled (default)
    basic_runner = BasicWorkMemEvalRunner()
    assert not basic_runner.enhanced_evaluation_enabled
    assert basic_runner.context_window_manager is None
    assert basic_runner.probe_scheduler is None
    
    # Test enabled
    enhanced_runner = BasicWorkMemEvalRunner(enable_enhanced_evaluation=True)
    assert enhanced_runner.enhanced_evaluation_enabled
    assert enhanced_runner.context_window_manager is not None
    assert enhanced_runner.probe_scheduler is not None


def test_context_window_manager_initialization():
    """Test context window manager configuration"""
    
    manager = ContextWindowManager()
    
    # Test standardized condition
    manager.configure_condition("standardized")
    assert manager.current_condition.condition_name == "standardized"
    assert manager.current_condition.token_limit == 8192
    
    # Test with mock agent
    mock_agent = MockAgent()
    manager.configure_condition("native", mock_agent)
    assert manager.current_condition.condition_name == "native"
    assert manager.current_condition.token_limit == 8192  # Mock agent's capacity


def test_probe_scheduler_functionality():
    """Test probe scheduling and injection"""
    
    scheduler = ProbeScheduler()
    
    # Create test probe
    test_probe = MemoryProbe(
        probe_id="test_probe",
        probe_type=ProbeType.N_BACK_INTEGRATION,
        pillar=MemoryPillar.MEMORY_FIDELITY,
        target_checkpoint="cp1",
        description="Test probe"
    )
    
    # Test scheduling
    scheduled = scheduler.schedule_probes([test_probe])
    assert "cp1" in scheduled
    assert len(scheduled["cp1"]) == 1
    assert scheduled["cp1"][0].probe_id == "test_probe"


def test_enhanced_task_specification():
    """Test enhanced task specification features"""
    
    # Create task with enhanced features
    task = TaskSpecification(
        task_id="test_task",
        title="Test Task",
        domain="test",
        description="Test description",
        checkpoints=[
            CheckpointSpecification(
                checkpoint_id="cp1",
                order=1,
                title="Test Checkpoint",
                stub_file="test.py",
                stub_function="test_func",
                requirements="Test requirements",
                test_file="test_test.py"
            )
        ],
        planning_phase=PlanningPhase(overview_prompt="Test planning"),
        repository=RepositoryTemplate(template_name="test_template"),
        memory_probes=[
            MemoryProbe(
                probe_id="test_probe",
                probe_type=ProbeType.N_BACK_INTEGRATION,
                pillar=MemoryPillar.MEMORY_FIDELITY,
                target_checkpoint="cp1",
                description="Test probe"
            )
        ]
    )
    
    # Test enhanced mode detection
    assert task.is_enhanced_mode()
    
    # Test enhanced mode enablement
    enhanced_task = task.enable_enhanced_mode()
    assert enhanced_task.enhanced_complexity is not None
    assert len(enhanced_task.context_conditions) > 0


def test_context_usage_monitoring():
    """Test context window usage monitoring"""
    
    manager = ContextWindowManager()
    manager.configure_condition("standardized")
    
    mock_agent = MockAgent()
    
    # Test monitoring
    metrics = manager.monitor_context_usage(mock_agent)
    assert metrics.token_limit == 8192
    assert metrics.state in [state for state in ContextState]
    assert 0 <= metrics.efficiency_score <= 1.0


def test_probe_interference_detection():
    """Test probe interference detection and resolution"""
    
    scheduler = ProbeScheduler()
    
    # Create conflicting probes (same checkpoint, same pillar)
    probe1 = MemoryProbe(
        probe_id="probe1",
        probe_type=ProbeType.N_BACK_INTEGRATION,
        pillar=MemoryPillar.MEMORY_FIDELITY,
        target_checkpoint="cp1",
        description="Test probe 1"
    )
    
    probe2 = MemoryProbe(
        probe_id="probe2",
        probe_type=ProbeType.COMPRESSION_STRESS,
        pillar=MemoryPillar.MEMORY_FIDELITY,
        target_checkpoint="cp1",
        description="Test probe 2"
    )
    
    # Test interference calculation
    interference = scheduler._calculate_probe_interference(probe1, probe2)
    assert 0 <= interference <= 1.0
    
    # Same checkpoint and pillar should have some interference
    assert interference > 0.5


def test_backward_compatibility():
    """Test that enhanced features don't break existing functionality"""
    
    # Create basic task without enhanced features
    basic_task = TaskSpecification(
        task_id="basic_task",
        title="Basic Task",
        domain="test",
        description="Basic test task",
        checkpoints=[
            CheckpointSpecification(
                checkpoint_id="cp1",
                order=1,
                title="Basic Checkpoint",
                stub_file="basic.py",
                stub_function="basic_func",
                requirements="Basic requirements",
                test_file="test_basic.py"
            )
        ],
        planning_phase=PlanningPhase(overview_prompt="Basic planning"),
        repository=RepositoryTemplate(template_name="basic_template")
    )
    
    # Should not be in enhanced mode
    assert not basic_task.is_enhanced_mode()
    
    # Should be able to enable enhanced mode
    enhanced_task = basic_task.enable_enhanced_mode()
    assert enhanced_task.is_enhanced_mode()
    assert enhanced_task.enhanced_complexity is not None


if __name__ == "__main__":
    # Run tests
    test_enhanced_evaluation_feature_flags()
    test_context_window_manager_initialization()
    test_probe_scheduler_functionality()
    test_enhanced_task_specification()
    test_context_usage_monitoring()
    test_probe_interference_detection()
    test_backward_compatibility()
    
    print("✅ All enhanced evaluation integration tests passed!")