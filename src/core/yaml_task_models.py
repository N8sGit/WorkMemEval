"""
YAML Task Configuration Models for Memory Evaluation Harness

This module provides Pydantic models for validating YAML task configurations
with comprehensive error messages and schema validation.
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class TaskDomain(str, Enum):
    """Supported task domains for memory evaluation"""
    DISTRIBUTED_SYSTEMS = "distributed_systems"
    DATA_PROCESSING = "data_processing"
    WEB_SERVICES = "web_services"
    SECURITY = "security"
    INFRASTRUCTURE = "infrastructure"


class TaskDifficulty(str, Enum):
    """Task difficulty levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class MemoryProbeType(str, Enum):
    """Types of memory probes for testing working memory"""
    N_BACK_RECALL = "n_back_recall"
    CONTEXT_SWITCH = "context_switch"
    SPECIFICATION_DRIFT = "specification_drift"
    DISTRACTOR_INJECTION = "distractor_injection"
    COMPRESSION_STRESS = "compression_stress"


class MemoryDimensions(BaseModel):
    """Quantified memory demand dimensions for task complexity"""
    
    information_density: int = Field(
        ...,
        ge=100,
        le=2000,
        description="Critical information tokens that must be retained"
    )
    
    temporal_span: int = Field(
        ...,
        ge=10,
        le=180,
        description="Minutes of sustained attention required"
    )
    
    context_switches: int = Field(
        ...,
        ge=0,
        le=10,
        description="Number of major context shifts during task"
    )
    
    dependency_depth: int = Field(
        ...,
        ge=1,
        le=8,
        description="Levels of interdependent concepts"
    )

    @field_validator('information_density')
    @classmethod
    def validate_information_density(cls, v):
        if v < 100:
            raise ValueError("Information density too low - tasks need at least 100 critical tokens")
        if v > 2000:
            raise ValueError("Information density too high - exceeds reasonable working memory limits")
        return v

    @field_validator('temporal_span')
    @classmethod
    def validate_temporal_span(cls, v):
        if v < 10:
            raise ValueError("Temporal span too short - tasks need at least 10 minutes for meaningful evaluation")
        if v > 180:
            raise ValueError("Temporal span too long - exceeds reasonable evaluation session length")
        return v


class MemoryProbe(BaseModel):
    """Memory probe specification for testing specific memory aspects"""
    
    type: MemoryProbeType = Field(..., description="Type of memory probe")
    trigger_at_minute: int = Field(..., ge=1, description="When to trigger the probe (minutes into task)")
    description: str = Field(..., min_length=10, description="Human-readable description of the probe")
    
    # Probe-specific configuration
    target_information: Optional[str] = Field(None, description="Specific information to test (for n_back_recall)")
    interruption_task: Optional[str] = Field(None, description="Interruption task description (for context_switch)")
    duration_minutes: Optional[int] = Field(None, ge=1, le=30, description="Duration of interruption (for context_switch)")
    requirement_change: Optional[str] = Field(None, description="New requirement to add (for specification_drift)")
    distractor_ratio: Optional[float] = Field(None, ge=0.1, le=0.8, description="Ratio of distractor to relevant info")

    @model_validator(mode='after')
    def validate_probe_config(self):
        probe_type = self.type
        
        if probe_type == MemoryProbeType.N_BACK_RECALL:
            if not self.target_information:
                raise ValueError("n_back_recall probes must specify target_information")
                
        elif probe_type == MemoryProbeType.CONTEXT_SWITCH:
            if not self.interruption_task:
                raise ValueError("context_switch probes must specify interruption_task")
            if not self.duration_minutes:
                raise ValueError("context_switch probes must specify duration_minutes")
                
        elif probe_type == MemoryProbeType.SPECIFICATION_DRIFT:
            if not self.requirement_change:
                raise ValueError("specification_drift probes must specify requirement_change")
                
        elif probe_type == MemoryProbeType.DISTRACTOR_INJECTION:
            if not self.distractor_ratio:
                raise ValueError("distractor_injection probes must specify distractor_ratio")
        
        return self


class YAMLCheckpoint(BaseModel):
    """Checkpoint specification for task execution"""
    
    id: str = Field(..., description="Unique checkpoint identifier")
    title: str = Field(..., description="Human-readable title")
    order: int = Field(..., ge=1, description="Execution order")
    stub_file: str = Field(..., description="File to implement")
    stub_function: str = Field("main", description="Function/class to implement")
    requirements: str = Field(..., description="Implementation requirements")
    test_file: str = Field(..., description="Test file to verify implementation")
    dependencies: List[str] = Field(default_factory=list, description="IDs of dependent checkpoints")
    estimated_tokens: int = Field(200, description="Estimated token complexity")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class YAMLPlanningPhase(BaseModel):
    """Planning phase configuration"""
    
    overview_prompt: str = Field(..., description="Prompt to show agent during planning")
    planning_deliverables: Dict[str, str] = Field(default_factory=dict, description="Expected deliverables")
    max_planning_time_minutes: int = Field(15, description="Time limit for planning")
    required_sections: List[str] = Field(default_factory=list, description="Required sections in plan")


class YAMLRepository(BaseModel):
    """Repository template configuration"""
    
    template_name: str = Field(..., description="Name of the template to use")
    provided_files: List[str] = Field(default_factory=list, description="Files provided to agent")
    distractor_files: List[str] = Field(default_factory=list, description="Irrelevant files for relevance testing")
    setup_commands: List[str] = Field(default_factory=list, description="Commands to run during setup")


class EvaluationConfig(BaseModel):
    """Configuration for task evaluation behavior"""
    
    max_duration_minutes: int = Field(60, ge=30, le=300, description="Maximum task duration")
    context_window_limit: Optional[int] = Field(None, ge=1024, description="Optional context window constraint")
    allow_external_memory: bool = Field(True, description="Whether agent can use external memory systems")
    track_context_usage: bool = Field(True, description="Whether to monitor context window usage patterns")
    
    @field_validator('context_window_limit')
    @classmethod
    def validate_context_limit(cls, v):
        if v is not None and v < 1024:
            raise ValueError("Context window limit must be at least 1024 tokens if specified")
        return v


class YAMLTaskSpecification(BaseModel):
    """Complete YAML task specification with validation"""
    
    task_id: str = Field(..., pattern=r'^[a-z0-9_]+$', description="Unique task identifier (lowercase, underscores only)")
    title: str = Field(..., min_length=5, max_length=100, description="Human-readable task title")
    domain: TaskDomain = Field(..., description="Task domain category")
    difficulty: TaskDifficulty = Field(..., description="Task difficulty level")
    
    description: str = Field(..., min_length=50, description="Detailed task description with requirements")
    
    # Execution details
    checkpoints: List[YAMLCheckpoint] = Field(..., description="Execution checkpoints")
    working_history: List[Dict[str, Any]] = Field(default_factory=list, description="Pre-existing context/history to inject (inline)")
    history_file: Optional[str] = Field(None, description="Path to a JSON or YAML file containing pre-existing context")
    planning_phase: Optional[YAMLPlanningPhase] = Field(None, description="Planning phase configuration")
    repository: Optional[YAMLRepository] = Field(None, description="Repository template configuration")
    
    memory_dimensions: MemoryDimensions = Field(..., description="Quantified memory demand dimensions")
    
    success_criteria: List[str] = Field(
        ..., 
        min_length=3, 
        max_length=10,
        description="List of measurable success criteria"
    )
    
    memory_probes: List[MemoryProbe] = Field(
        default_factory=list,
        max_length=6,
        description="Memory probes for testing working memory aspects"
    )
    
    evaluation_config: EvaluationConfig = Field(
        default_factory=EvaluationConfig,
        description="Evaluation configuration settings"
    )
    
    # Optional metadata
    tags: List[str] = Field(default_factory=list, description="Task tags for categorization")
    created_by: str = Field("", description="Task creator")
    version: str = Field("1.0", description="Task version")

    @field_validator('task_id')
    @classmethod
    def validate_task_id(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Task ID must contain only letters, numbers, underscores, and hyphens")
        if len(v) < 3:
            raise ValueError("Task ID must be at least 3 characters long")
        return v

    @field_validator('success_criteria')
    @classmethod
    def validate_success_criteria(cls, v):
        for criterion in v:
            if len(criterion.strip()) < 10:
                raise ValueError(f"Success criterion too short: '{criterion}' - must be at least 10 characters")
            if not any(word in criterion.lower() for word in ['must', 'should', 'will', 'correctly', 'successfully']):
                raise ValueError(f"Success criterion should be measurable: '{criterion}' - consider using words like 'must', 'should', 'correctly'")
        return v

    @model_validator(mode='after')
    def validate_memory_probes_and_coherence(self):
        """Validate memory probes and overall task coherence"""
        
        # Validate memory probes
        if self.memory_probes:
            max_duration = self.evaluation_config.max_duration_minutes
            
            for probe in self.memory_probes:
                if probe.trigger_at_minute >= max_duration:
                    raise ValueError(f"Probe trigger time ({probe.trigger_at_minute}min) must be less than task duration ({max_duration}min)")
            
            # Check for reasonable probe distribution
            trigger_times = [probe.trigger_at_minute for probe in self.memory_probes]
            if len(set(trigger_times)) != len(trigger_times):
                raise ValueError("Memory probes cannot have identical trigger times")
        
        # Check memory dimensions are consistent with evaluation config
        if self.memory_dimensions.temporal_span > self.evaluation_config.max_duration_minutes:
            raise ValueError(
                f"Memory temporal span ({self.memory_dimensions.temporal_span}min) "
                f"exceeds task duration ({self.evaluation_config.max_duration_minutes}min)"
            )
        
        # Validate probe count is reasonable for task complexity
        if len(self.memory_probes) > self.memory_dimensions.context_switches + 3:
            raise ValueError(
                f"Too many memory probes ({len(self.memory_probes)}) for task complexity "
                f"(max recommended: {self.memory_dimensions.context_switches + 3})"
            )
        
        return self

    def to_task_specification(self, base_path: Optional[Path] = None) -> 'TaskSpecification':
        """Convert YAML specification to executable TaskSpecification.
        
        Args:
            base_path: Optional directory to resolve relative paths (e.g. history_file)
        """
        from .task_specification import (
            TaskSpecification, CheckpointSpecification, 
            PlanningPhase, RepositoryTemplate,
            MemoryProbe as ExecProbe, ProbeType, MemoryPillar,
            EvaluationConfiguration as ExecEvalConfig,
            ContextWindowCondition, ContextConditionType
        )
        
        # Convert checkpoints
        exec_checkpoints = []
        for cp in self.checkpoints:
            exec_checkpoints.append(CheckpointSpecification(
                checkpoint_id=cp.id,
                order=cp.order,
                title=cp.title,
                stub_file=cp.stub_file,
                stub_function=cp.stub_function,
                requirements=cp.requirements,
                test_file=cp.test_file,
                dependencies=cp.dependencies,
                estimated_tokens=cp.estimated_tokens,
                metadata=cp.metadata
            ))

        # Convert planning phase
        if self.planning_phase:
            exec_planning = PlanningPhase(
                overview_prompt=self.planning_phase.overview_prompt,
                planning_deliverables=self.planning_phase.planning_deliverables,
                max_planning_time_minutes=self.planning_phase.max_planning_time_minutes,
                required_sections=self.planning_phase.required_sections
            )
        else:
            exec_planning = PlanningPhase(overview_prompt="Default planning prompt")

        # Convert repository
        if self.repository:
            exec_repo = RepositoryTemplate(
                template_name=self.repository.template_name,
                provided_files=self.repository.provided_files,
                distractor_files=self.repository.distractor_files,
                setup_commands=self.repository.setup_commands
            )
        else:
            exec_repo = RepositoryTemplate(template_name="default")

        # Convert probes
        exec_probes = []
        for p in self.memory_probes:
            # Safe string conversion of probe type
            p_type_str = str(p.type).lower()
            
            # Default to N_BACK_INTEGRATION
            target_probe_type = ProbeType.N_BACK_INTEGRATION
            
            if "n_back" in p_type_str:
                target_probe_type = ProbeType.N_BACK_INTEGRATION
            elif "context_switch" in p_type_str:
                target_probe_type = ProbeType.CONTEXT_SWITCH
            elif "specification_drift" in p_type_str:
                target_probe_type = ProbeType.UPDATE_ROBUSTNESS
            elif "distractor" in p_type_str:
                target_probe_type = ProbeType.DISTRACTOR_INJECTION
            elif "compression" in p_type_str:
                target_probe_type = ProbeType.COMPRESSION_STRESS
            
            # Map pillars
            target_pillar = MemoryPillar.MEMORY_FIDELITY
            if target_probe_type in (ProbeType.DISTRACTOR_INJECTION, ProbeType.CHANGE_DETECTION):
                target_pillar = MemoryPillar.CONTEXTUAL_RELEVANCE
            elif target_probe_type in (ProbeType.UPDATE_ROBUSTNESS, ProbeType.CONTEXT_SWITCH):
                target_pillar = MemoryPillar.BEHAVIORAL_INTEGRITY
            
            # Find closest checkpoint
            avg_cp_duration = self.evaluation_config.max_duration_minutes / len(self.checkpoints)
            target_cp_idx = min(
                int(p.trigger_at_minute / avg_cp_duration),
                len(self.checkpoints) - 1
            )
            target_cp = self.checkpoints[target_cp_idx].id
            
            exec_probes.append(ExecProbe(
                probe_id=f"yaml_probe_{p_type_str}_{p.trigger_at_minute}",
                probe_type=target_probe_type,
                pillar=target_pillar,
                target_checkpoint=target_cp,
                description=p.description,
                distractor_ratio=p.distractor_ratio,
                interruption_duration=p.duration_minutes
            ))

        # Create TaskSpecification
        # Note: self.domain and self.difficulty are likely strings due to use_enum_values=True
        # We ensure they are strings for TaskSpecification
        domain_str = str(self.domain)
        difficulty_str = str(self.difficulty)
        
        # Convert history (merge inline and file-based)
        combined_history = list(self.working_history)
        if self.history_file:
            history_path = Path(self.history_file)
            
            # If not absolute, try resolving relative to base_path
            if not history_path.is_absolute() and base_path:
                history_path = base_path / history_path
            
            if history_path.exists():
                try:
                    with open(history_path, 'r') as f:
                        if history_path.suffix.lower() == '.json':
                            import json
                            file_history = json.load(f)
                        else:
                            file_history = yaml.safe_load(f)
                        
                        if isinstance(file_history, list):
                            combined_history.extend(file_history)
                        else:
                            print(f"Warning: history_file {self.history_file} did not contain a list")
                except Exception as e:
                    print(f"Warning: failed to load history_file {self.history_file}: {e}")
            else:
                print(f"Warning: history_file not found at {history_path}")

        task_spec = TaskSpecification(
            task_id=self.task_id,
            title=self.title,
            domain=domain_str,
            description=self.description,
            checkpoints=exec_checkpoints,
            working_history=combined_history,
            planning_phase=exec_planning,
            repository=exec_repo,
            memory_probes=exec_probes,
            difficulty=difficulty_str,
            estimated_duration_minutes=self.evaluation_config.max_duration_minutes,
            created_by=self.created_by,
            version=self.version,
            tags=self.tags
        )
        
        if self.evaluation_config.context_window_limit:
            task_spec.context_conditions = [
                ContextWindowCondition(
                    condition_name="standardized_yaml",
                    condition_type=ContextConditionType.STANDARDIZED,
                    token_limit=self.evaluation_config.context_window_limit,
                    description=f"YAML-configured limit: {self.evaluation_config.context_window_limit}"
                )
            ]
            
        return task_spec

    model_config = {
        "use_enum_values": True,
        "validate_assignment": True,
        "extra": "forbid",  # Reject unknown fields
        "json_schema_extra": {
            "example": {
                "task_id": "distributed_cache_001",
                "title": "Distributed Cache Implementation",
                "domain": "distributed_systems",
                "difficulty": "intermediate",
                "description": "Implement a distributed caching system that handles node failures gracefully...",
                "memory_dimensions": {
                    "information_density": 850,
                    "temporal_span": 45,
                    "context_switches": 3,
                    "dependency_depth": 4
                },
                "success_criteria": [
                    "Cache operations (GET/PUT/DELETE) work correctly under normal conditions",
                    "System handles node failures without data loss",
                    "Performance degrades gracefully under increasing load"
                ],
                "memory_probes": [
                    {
                        "type": "n_back_recall",
                        "trigger_at_minute": 25,
                        "target_information": "initial_architecture_decisions",
                        "description": "Recall the key architectural decisions made in the first 10 minutes"
                    }
                ],
                "evaluation_config": {
                    "max_duration_minutes": 60,
                    "context_window_limit": 8192,
                    "allow_external_memory": True,
                    "track_context_usage": True
                }
            }
        }
    }


class TaskValidationError(Exception):
    """Custom exception for task validation errors with detailed messages"""
    
    def __init__(self, message: str, field_errors: Optional[Dict[str, List[str]]] = None):
        self.message = message
        self.field_errors = field_errors or {}
        super().__init__(self.message)
    
    def __str__(self):
        if not self.field_errors:
            return self.message
        
        error_details = []
        for field, errors in self.field_errors.items():
            error_details.append(f"  {field}: {'; '.join(errors)}")
        
        return f"{self.message}\nField errors:\n" + "\n".join(error_details)