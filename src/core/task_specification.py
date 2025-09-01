"""
WorkMemEval: Task Specification Core Data Structures

This module defines the foundational data structures for WorkMemEval task specifications,
following the hybrid task structure design that combines controlled checkpoints with
architectural freedom zones.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from enum import Enum
import json
from pathlib import Path


class CheckpointType(Enum):
    """Types of checkpoints in WorkMemEval tasks"""
    IMPLEMENTATION = "implementation"    # Core functionality development
    INTEGRATION = "integration"         # Component combination and coordination  
    EXTENSION = "extension"             # Feature addition to existing system


class MemoryChallengeType(Enum):
    """Types of working memory challenges"""
    REQUIREMENT_UPDATE = "requirement_update"      # Mid-task specification changes
    CONTEXT_SWITCH = "context_switch"              # Task interruption and resumption
    INFORMATION_OVERLOAD = "information_overload"   # Distractor files and complexity
    INTEGRATION_CONSTRAINT = "integration_constraint" # Cross-checkpoint dependencies


@dataclass
class CheckpointSpecification:
    """
    Individual checkpoint within a WorkMemEval task.
    
    Represents a controlled measurement point with specific requirements,
    test criteria, and dependency relationships.
    """
    checkpoint_id: str
    order: int
    title: str
    stub_file: str                    # File where implementation is required
    stub_function: str                # Function/class to implement
    requirements: str                 # Natural language requirements
    test_file: str                   # Pytest file that must pass
    dependencies: List[str] = field(default_factory=list)  # Other checkpoint IDs
    checkpoint_type: CheckpointType = CheckpointType.IMPLEMENTATION
    estimated_tokens: int = 200      # Estimated complexity (depth dimension)
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
class MemoryChallenge:
    """
    Working memory challenge injection point.
    
    Represents controlled stress testing of working memory through
    requirement changes, interruptions, or information overload.
    """
    challenge_id: str
    challenge_type: MemoryChallengeType
    at_checkpoint: str               # Checkpoint ID where challenge occurs
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Type-specific fields
    affects: List[str] = field(default_factory=list)           # For requirement updates
    interruption_task: Optional[str] = None                    # For context switches
    duration_minutes: Optional[int] = None                     # For context switches
    distractor_files: List[str] = field(default_factory=list) # For information overload


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
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get attribute by key name (for backward compatibility with dict access)"""
        return getattr(self, key, default)


@dataclass
class TaskComplexityMetrics:
    """
    Three-dimensional task complexity measurement.
    
    Implements the Length × Depth × Composition complexity space
    for systematic difficulty scaling.
    """
    length: int                      # Number of sequential checkpoints
    depth: float                     # Average tokens per checkpoint specification  
    composition: float               # Component count × integration density
    
    # Component analysis
    semantic_components: List[str] = field(default_factory=list)
    component_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    
    def calculate_composition_score(self) -> float:
        """Calculate composition complexity score (C × I)"""
        if not self.semantic_components:
            return 0
        
        if not self.component_dependencies:
            return len(self.semantic_components)
        
        total_dependencies = sum(len(deps) for deps in self.component_dependencies.values())
        
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
class EvaluationConfiguration:
    """
    Configuration for evaluation behavior and metric calculation.
    """
    memory_checkpoint_frequency: int = 3  # Memory snapshots every N checkpoints
    planning_compliance_tracking: bool = True
    trace_capture_level: str = "detailed"  # basic, detailed, comprehensive
    success_criteria: Dict[str, bool] = field(default_factory=lambda: {
        "all_tests_pass": True,
        "no_breaking_changes": True,
        "integration_functional": True,
        "planning_phase_completed": True
    })
    timeout_minutes: int = 180
    enable_memory_challenges: bool = True


@dataclass 
class TaskSpecification:
    """
    Complete WorkMemEval task specification.
    
    Represents a full task including metadata, checkpoints, memory challenges,
    complexity metrics, and evaluation configuration. This is the primary
    unit of evaluation in WorkMemEval.
    """
    task_id: str
    title: str
    domain: str                      # e.g., "api_service", "data_processing"
    description: str
    
    # Core task structure
    checkpoints: List[CheckpointSpecification]
    planning_phase: PlanningPhase
    repository: RepositoryTemplate
    
    # Working memory challenges
    memory_challenges: List[MemoryChallenge] = field(default_factory=list)
    
    # Complexity and evaluation
    complexity: TaskComplexityMetrics = field(default=None)
    evaluation_config: EvaluationConfiguration = field(default_factory=EvaluationConfiguration)
    
    # Metadata
    difficulty: str = "medium"       # beginner, intermediate, advanced, expert
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
        
        # Auto-calculate complexity metrics if not provided
        if self.complexity is None:
            self.complexity = self._calculate_complexity()
        
        # Validate checkpoint order and dependencies
        self._validate_checkpoint_dependencies()
    
    def _calculate_complexity(self) -> TaskComplexityMetrics:
        """Auto-calculate task complexity from checkpoint structure"""
        length = len(self.checkpoints)
        depth = sum(cp.estimated_tokens for cp in self.checkpoints) / length if self.checkpoints else 0
        
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
            component_dependencies=dependencies
        )
    
    def _validate_checkpoint_dependencies(self):
        """Validate that all checkpoint dependencies exist and form valid DAG"""
        checkpoint_ids = {cp.checkpoint_id for cp in self.checkpoints}
        
        for cp in self.checkpoints:
            for dep_id in cp.dependencies:
                if dep_id not in checkpoint_ids:
                    raise ValueError(f"Checkpoint {cp.checkpoint_id} depends on non-existent checkpoint {dep_id}")
        
        # TODO: Add cycle detection for dependency graph
    
    def get_checkpoint_by_id(self, checkpoint_id: str) -> Optional[CheckpointSpecification]:
        """Get checkpoint by ID"""
        return next((cp for cp in self.checkpoints if cp.checkpoint_id == checkpoint_id), None)
    
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
        required.update(['requirements.txt', 'README.md'])
        
        return required
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'task_id': self.task_id,
            'title': self.title,
            'domain': self.domain,
            'description': self.description,
            'difficulty': self.difficulty,
            'estimated_duration_minutes': self.estimated_duration_minutes,
            'checkpoints': [
                {
                    'checkpoint_id': cp.checkpoint_id,
                    'order': cp.order,
                    'title': cp.title,
                    'stub_file': cp.stub_file,
                    'stub_function': cp.stub_function,
                    'requirements': cp.requirements,
                    'test_file': cp.test_file,
                    'dependencies': cp.dependencies,
                    'checkpoint_type': cp.checkpoint_type.value,
                    'estimated_tokens': cp.estimated_tokens,
                    'metadata': cp.metadata
                }
                for cp in self.checkpoints
            ],
            'planning_phase': {
                'overview_prompt': self.planning_phase.overview_prompt,
                'planning_deliverables': self.planning_phase.planning_deliverables,
                'planning_capture': self.planning_phase.planning_capture,
                'max_planning_time_minutes': self.planning_phase.max_planning_time_minutes,
                'required_sections': self.planning_phase.required_sections
            },
            'repository': {
                'template_name': self.repository.template_name,
                'provided_files': self.repository.provided_files,
                'distractor_files': self.repository.distractor_files,
                'directory_structure': self.repository.directory_structure,
                'setup_commands': self.repository.setup_commands
            },
            'memory_challenges': [
                {
                    'challenge_id': mc.challenge_id,
                    'challenge_type': mc.challenge_type.value,
                    'at_checkpoint': mc.at_checkpoint,
                    'description': mc.description,
                    'metadata': mc.metadata,
                    'affects': mc.affects,
                    'interruption_task': mc.interruption_task,
                    'duration_minutes': mc.duration_minutes,
                    'distractor_files': mc.distractor_files
                }
                for mc in self.memory_challenges
            ],
            'complexity': {
                'length': self.complexity.length,
                'depth': self.complexity.depth,
                'composition': self.complexity.composition,
                'semantic_components': self.complexity.semantic_components,
                'component_dependencies': self.complexity.component_dependencies
            },
            'evaluation_config': {
                'memory_checkpoint_frequency': self.evaluation_config.memory_checkpoint_frequency,
                'planning_compliance_tracking': self.evaluation_config.planning_compliance_tracking,
                'trace_capture_level': self.evaluation_config.trace_capture_level,
                'success_criteria': self.evaluation_config.success_criteria,
                'timeout_minutes': self.evaluation_config.timeout_minutes,
                'enable_memory_challenges': self.evaluation_config.enable_memory_challenges
            },
            'metadata': {
                'created_by': self.created_by,
                'version': self.version,
                'tags': self.tags
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskSpecification':
        """Create TaskSpecification from dictionary"""
        checkpoints = [
            CheckpointSpecification(
                checkpoint_id=cp['checkpoint_id'],
                order=cp['order'],
                title=cp['title'],
                stub_file=cp['stub_file'],
                stub_function=cp['stub_function'],
                requirements=cp['requirements'],
                test_file=cp['test_file'],
                dependencies=cp.get('dependencies', []),
                checkpoint_type=CheckpointType(cp.get('checkpoint_type', 'implementation')),
                estimated_tokens=cp.get('estimated_tokens', 200),
                metadata=cp.get('metadata', {})
            )
            for cp in data['checkpoints']
        ]
        
        planning_data = data['planning_phase']
        planning_phase = PlanningPhase(
            overview_prompt=planning_data['overview_prompt'],
            planning_deliverables=planning_data.get('planning_deliverables', {}),
            planning_capture=planning_data.get('planning_capture', {}),
            max_planning_time_minutes=planning_data.get('max_planning_time_minutes', 15),
            required_sections=planning_data.get('required_sections', [])
        )
        
        repo_data = data['repository']
        repository = RepositoryTemplate(
            template_name=repo_data['template_name'],
            provided_files=repo_data.get('provided_files', []),
            distractor_files=repo_data.get('distractor_files', []),
            directory_structure=repo_data.get('directory_structure', {}),
            setup_commands=repo_data.get('setup_commands', [])
        )
        
        memory_challenges = [
            MemoryChallenge(
                challenge_id=mc['challenge_id'],
                challenge_type=MemoryChallengeType(mc['challenge_type']),
                at_checkpoint=mc['at_checkpoint'],
                description=mc['description'],
                metadata=mc.get('metadata', {}),
                affects=mc.get('affects', []),
                interruption_task=mc.get('interruption_task'),
                duration_minutes=mc.get('duration_minutes'),
                distractor_files=mc.get('distractor_files', [])
            )
            for mc in data.get('memory_challenges', [])
        ]
        
        complexity_data = data.get('complexity', {})
        complexity = TaskComplexityMetrics(
            length=complexity_data.get('length', len(checkpoints)),
            depth=complexity_data.get('depth', 200),
            composition=complexity_data.get('composition', 0),
            semantic_components=complexity_data.get('semantic_components', []),
            component_dependencies=complexity_data.get('component_dependencies', {})
        )
        
        eval_data = data.get('evaluation_config', {})
        evaluation_config = EvaluationConfiguration(
            memory_checkpoint_frequency=eval_data.get('memory_checkpoint_frequency', 3),
            planning_compliance_tracking=eval_data.get('planning_compliance_tracking', True),
            trace_capture_level=eval_data.get('trace_capture_level', 'detailed'),
            success_criteria=eval_data.get('success_criteria', {
                "all_tests_pass": True,
                "no_breaking_changes": True,
                "integration_functional": True,
                "planning_phase_completed": True
            }),
            timeout_minutes=eval_data.get('timeout_minutes', 180),
            enable_memory_challenges=eval_data.get('enable_memory_challenges', True)
        )
        
        metadata = data.get('metadata', {})
        
        return cls(
            task_id=data['task_id'],
            title=data['title'],
            domain=data['domain'],
            description=data['description'],
            checkpoints=checkpoints,
            planning_phase=planning_phase,
            repository=repository,
            memory_challenges=memory_challenges,
            complexity=complexity,
            evaluation_config=evaluation_config,
            difficulty=data.get('difficulty', 'medium'),
            estimated_duration_minutes=data.get('estimated_duration_minutes', 90),
            created_by=metadata.get('created_by', ''),
            version=metadata.get('version', '1.0'),
            tags=metadata.get('tags', [])
        )
    
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save task specification to JSON file"""
        path = Path(file_path)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> 'TaskSpecification':
        """Load task specification from JSON file"""
        path = Path(file_path)
        with open(path, 'r') as f:
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
                if dep_id not in checkpoint_ids and dep_id not in {other.checkpoint_id for other in task_spec.checkpoints}:
                    issues.append(f"Checkpoint {cp.checkpoint_id} depends on non-existent checkpoint {dep_id}")
        
        # Complexity validation
        if task_spec.complexity:
            if task_spec.complexity.length != len(task_spec.checkpoints):
                issues.append("Complexity length doesn't match checkpoint count")
        
        # Memory challenge validation
        for mc in task_spec.memory_challenges:
            if mc.at_checkpoint not in checkpoint_ids:
                issues.append(f"Memory challenge {mc.challenge_id} references non-existent checkpoint {mc.at_checkpoint}")
        
        return issues
    
    @staticmethod
    def is_valid(task_spec: TaskSpecification) -> bool:
        """Check if task specification is valid"""
        return len(TaskSpecificationValidator.validate(task_spec)) == 0
