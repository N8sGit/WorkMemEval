# WorkMemEval: Task Schema & End-to-End Example

## JSON Task Schema

```json
{
  "task_id": "user_management_api",
  "metadata": {
    "title": "User Management API Development",
    "domain": "api_service", 
    "difficulty": "medium",
    "estimated_duration_minutes": 90,
    "length": 8,
    "depth": 280,
    "description": "Build a user management API with authentication, profile management, and basic admin features"
  },
  
  "repository": {
    "template_repo": "user_management_starter",
    "provided_files": [
      "src/models/__init__.py",
      "src/auth/__init__.py", 
      "src/api/__init__.py",
      "tests/test_checkpoints.py",
      "requirements.txt",
      "README.md"
    ],
    "distractor_files": [
      "legacy/old_user_system.py",
      "docs/outdated_spec.md",
      "config/development.yml"
    ]
  },
  
  "planning_phase": {
    "overview_prompt": "You will be building a complete User Management API with authentication, profile management, and admin features. This system will involve multiple components that need to work together: user data models, password security, data access layers, REST API endpoints, session management, and admin functionality.\n\nBefore starting implementation, please:\n1. Read through the repository structure and understand the codebase organization\n2. Review the test files to understand the expected functionality\n3. Create a detailed implementation plan that outlines:\n   - Your approach to the overall system architecture\n   - How you'll handle dependencies between components\n   - Your strategy for integrating the different pieces\n   - Any potential challenges you anticipate\n\nYour plan will help guide the implementation process. You'll be implementing this system progressively through multiple checkpoints, and maintaining awareness of your overall plan while working on individual components will be important for success.",
    
    "planning_deliverables": {
      "architecture_plan": "High-level system architecture and component relationships",
      "implementation_strategy": "Step-by-step approach to building the system", 
      "integration_approach": "How components will work together",
      "risk_assessment": "Potential challenges and mitigation strategies"
    },
    
    "planning_capture": {
      "plan_document": "IMPLEMENTATION_PLAN.md",
      "max_planning_time": 15,
      "required_sections": ["Architecture Overview", "Implementation Strategy", "Component Dependencies", "Integration Plan"]
    }
  },
  
  "checkpoints": [
    {
      "checkpoint_id": "cp1_user_model",
      "order": 1,
      "title": "User Data Model",
      "stub_file": "src/models/user.py",
      "stub_function": "User",
      "requirements": "Implement User class with fields: id, username, email, password_hash, created_at, is_active. Include basic validation for email format and username uniqueness checking.",
      "test_file": "tests/test_cp1_user_model.py",
      "dependencies": [],
      "estimated_tokens": 250
    },
    
    {
      "checkpoint_id": "cp2_password_auth", 
      "order": 2,
      "title": "Password Authentication",
      "stub_file": "src/auth/password.py",
      "stub_function": "hash_password, verify_password",
      "requirements": "Implement secure password hashing using bcrypt and password verification. Functions should handle salt generation and verification timing attack protection.",
      "test_file": "tests/test_cp2_password_auth.py", 
      "dependencies": ["cp1_user_model"],
      "estimated_tokens": 180
    },
    
    {
      "checkpoint_id": "cp3_user_repository",
      "order": 3, 
      "title": "User Data Access",
      "stub_file": "src/models/repository.py",
      "stub_function": "UserRepository", 
      "requirements": "Implement UserRepository class with methods: create_user(), find_by_username(), find_by_email(), update_user(), delete_user(). Should integrate with User model from checkpoint 1.",
      "test_file": "tests/test_cp3_user_repository.py",
      "dependencies": ["cp1_user_model"],
      "estimated_tokens": 320
    },
    
    {
      "checkpoint_id": "cp4_auth_service",
      "order": 4,
      "title": "Authentication Service Integration", 
      "stub_file": "src/auth/service.py",
      "stub_function": "AuthService",
      "requirements": "Implement AuthService that combines UserRepository and password functions to provide: register_user(), authenticate_user(), change_password(). Must integrate components from checkpoints 1, 2, and 3.",
      "test_file": "tests/test_cp4_auth_service.py",
      "dependencies": ["cp1_user_model", "cp2_password_auth", "cp3_user_repository"],
      "estimated_tokens": 280
    },
    
    {
      "checkpoint_id": "cp5_api_endpoints",
      "order": 5,
      "title": "REST API Endpoints",
      "stub_file": "src/api/user_routes.py", 
      "stub_function": "UserRoutes",
      "requirements": "Implement Flask routes for: POST /users (register), POST /auth (login), GET /users/me (profile), PUT /users/me (update profile). Should use AuthService from checkpoint 4.",
      "test_file": "tests/test_cp5_api_endpoints.py",
      "dependencies": ["cp4_auth_service"],
      "estimated_tokens": 340
    },
    
    {
      "checkpoint_id": "cp6_session_management",
      "order": 6,
      "title": "Session & Token Management",
      "stub_file": "src/auth/sessions.py",
      "stub_function": "SessionManager", 
      "requirements": "Implement session management with JWT tokens. Provide: generate_token(), validate_token(), refresh_token(), logout(). Must integrate with existing auth system.",
      "test_file": "tests/test_cp6_session_management.py",
      "dependencies": ["cp4_auth_service"],
      "estimated_tokens": 300
    },
    
    {
      "checkpoint_id": "cp7_admin_features",
      "order": 7,
      "title": "Admin User Management",
      "stub_file": "src/api/admin_routes.py",
      "stub_function": "AdminRoutes",
      "requirements": "Implement admin endpoints: GET /admin/users (list all), PUT /admin/users/{id}/activate, DELETE /admin/users/{id}. Must enforce admin permissions and integrate with all previous systems.",
      "test_file": "tests/test_cp7_admin_features.py", 
      "dependencies": ["cp5_api_endpoints", "cp6_session_management"],
      "estimated_tokens": 260
    },
    
    {
      "checkpoint_id": "cp8_integration_tests",
      "order": 8,
      "title": "End-to-End Integration",
      "stub_file": "tests/integration_tests.py",
      "stub_function": "test_complete_user_workflow",
      "requirements": "Implement integration tests that verify complete user workflows: registration → login → profile update → admin actions. Must test all components working together.",
      "test_file": "tests/test_cp8_integration.py",
      "dependencies": ["cp7_admin_features"],
      "estimated_tokens": 380
    }
  ],
  
  "working_memory_challenges": [
    {
      "type": "requirement_update",
      "at_checkpoint": "cp5_api_endpoints", 
      "description": "REQUIREMENT CHANGE: User model now requires email verification before account activation. Update previous implementations accordingly.",
      "affects": ["cp1_user_model", "cp4_auth_service"]
    },
    
    {
      "type": "context_switch",
      "at_checkpoint": "cp6_session_management",
      "interruption": {
        "task": "Implement a simple logging utility in src/utils/logger.py",
        "duration": "10 minutes",
        "description": "Brief interruption to add logging infrastructure before continuing with session management"
      }
    },
    
    {
      "type": "information_overload",
      "at_checkpoint": "cp7_admin_features",
      "distractor_injection": [
        "docs/security_considerations.md (20 pages)",
        "examples/legacy_admin_system.py (500 lines)", 
        "config/permissions_matrix.yml (complex RBAC rules)"
      ]
    }
  ],
  
  "evaluation_config": {
    "memory_checkpoints": ["cp4_auth_service", "cp6_session_management", "cp8_integration_tests"],
    "planning_compliance_tracking": {
      "track_plan_adherence": true,
      "measure_plan_updates": true,
      "assess_architectural_consistency": true
    },
    "trace_capture": {
      "file_access_logging": true,
      "function_call_tracking": true, 
      "context_size_monitoring": true,
      "error_pattern_detection": true,
      "plan_reference_tracking": true
    },
    "success_criteria": {
      "all_tests_pass": true,
      "no_breaking_changes": true,
      "integration_functional": true,
      "planning_phase_completed": true
    }
  }
}
```

## Repository Structure

```
user_management_starter/
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py                    # CP1 stub
│   │   └── repository.py              # CP3 stub
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── password.py                # CP2 stub
│   │   ├── service.py                 # CP4 stub
│   │   └── sessions.py                # CP6 stub
│   ├── api/
│   │   ├── __init__.py
│   │   ├── user_routes.py             # CP5 stub
│   │   └── admin_routes.py            # CP7 stub
│   └── utils/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── test_cp1_user_model.py
│   ├── test_cp2_password_auth.py
│   ├── test_cp3_user_repository.py
│   ├── test_cp4_auth_service.py
│   ├── test_cp5_api_endpoints.py
│   ├── test_cp6_session_management.py
│   ├── test_cp7_admin_features.py
│   ├── test_cp8_integration.py
│   └── integration_tests.py           # CP8 stub
├── legacy/
│   └── old_user_system.py             # Distractor file
├── docs/
│   ├── api_spec.md
│   └── outdated_spec.md               # Distractor file
├── config/
│   ├── development.yml                # Distractor file
│   └── test_config.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Example Stub Files

### src/models/user.py (Checkpoint 1)
```python
"""
User data model implementation
CHECKPOINT 1: Implement User class with validation
"""
from datetime import datetime
from typing import Optional

class User:
    """
    User data model
    
    REQUIREMENTS:
    - Fields: id, username, email, password_hash, created_at, is_active
    - Email format validation
    - Username uniqueness checking interface
    """
    
    def __init__(self, username: str, email: str, password_hash: str, user_id: Optional[int] = None):
        # TODO: Implement User initialization
        pass
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        # TODO: Implement email validation
        pass
    
    def to_dict(self) -> dict:
        """Convert user to dictionary representation"""
        # TODO: Implement serialization
        pass
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Create user from dictionary"""
        # TODO: Implement deserialization
        pass
```

### src/auth/service.py (Checkpoint 4) 
```python
"""
Authentication service that integrates user management and password handling
CHECKPOINT 4: Combine previous components into cohesive auth system
"""
from typing import Optional, Tuple
from ..models.user import User
from ..models.repository import UserRepository
from .password import hash_password, verify_password

class AuthService:
    """
    Integrated authentication service
    
    REQUIREMENTS:
    - Integrate User model (CP1), password functions (CP2), UserRepository (CP3)
    - Provide: register_user(), authenticate_user(), change_password()
    - Handle validation and error cases
    """
    
    def __init__(self, user_repository: UserRepository):
        # TODO: Initialize auth service with repository
        pass
    
    def register_user(self, username: str, email: str, password: str) -> Tuple[bool, str]:
        """
        Register new user
        Returns: (success, message/user_id)
        """
        # TODO: Implement user registration
        # Must use User model validation and password hashing
        pass
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[User]]:
        """
        Authenticate user credentials
        Returns: (success, user_object_or_none)
        """
        # TODO: Implement authentication
        # Must use repository lookup and password verification
        pass
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Change user password with verification
        Returns: (success, message)
        """
        # TODO: Implement password change
        # Must verify old password and update with new hash
        pass
```

## Test Files

### tests/test_cp4_auth_service.py
```python
"""
Test suite for AuthService integration (Checkpoint 4)
Tests integration of User model, password functions, and repository
"""
import pytest
from src.auth.service import AuthService
from src.models.repository import UserRepository
from src.models.user import User

class TestAuthService:
    
    def setup_method(self):
        """Setup test fixtures"""
        self.user_repo = UserRepository()
        self.auth_service = AuthService(self.user_repo)
    
    def test_register_user_success(self):
        """Test successful user registration"""
        success, result = self.auth_service.register_user(
            "testuser", "test@example.com", "securepassword123"
        )
        
        assert success is True
        assert isinstance(result, str)  # Should return user ID
        
        # Verify user was actually created
        user = self.user_repo.find_by_username("testuser")
        assert user is not None
        assert user.email == "test@example.com"
        assert user.is_active is True
    
    def test_register_user_duplicate_username(self):
        """Test registration with duplicate username"""
        # First registration
        self.auth_service.register_user("duplicate", "first@example.com", "password1")
        
        # Second registration with same username
        success, message = self.auth_service.register_user(
            "duplicate", "second@example.com", "password2"
        )
        
        assert success is False
        assert "username" in message.lower()
        assert "exists" in message.lower()
    
    def test_authenticate_user_success(self):
        """Test successful authentication"""
        # Register user first
        self.auth_service.register_user("authuser", "auth@example.com", "mypassword")
        
        # Authenticate
        success, user = self.auth_service.authenticate_user("authuser", "mypassword") 
        
        assert success is True
        assert isinstance(user, User)
        assert user.username == "authuser"
        assert user.email == "auth@example.com"
    
    def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password"""
        self.auth_service.register_user("authuser", "auth@example.com", "correctpassword")
        
        success, user = self.auth_service.authenticate_user("authuser", "wrongpassword")
        
        assert success is False
        assert user is None
    
    def test_authenticate_nonexistent_user(self):
        """Test authentication of nonexistent user"""
        success, user = self.auth_service.authenticate_user("nonexistent", "password")
        
        assert success is False
        assert user is None
    
    def test_change_password_success(self):
        """Test successful password change"""
        # Register and get user ID
        success, user_id = self.auth_service.register_user(
            "changeuser", "change@example.com", "oldpassword"
        )
        
        # Change password
        success, message = self.auth_service.change_password(
            int(user_id), "oldpassword", "newpassword123"
        )
        
        assert success is True
        
        # Verify old password no longer works
        auth_success, _ = self.auth_service.authenticate_user("changeuser", "oldpassword")
        assert auth_success is False
        
        # Verify new password works
        auth_success, user = self.auth_service.authenticate_user("changeuser", "newpassword123")
        assert auth_success is True
        assert user is not None
    
    def test_change_password_wrong_old_password(self):
        """Test password change with incorrect old password"""
        success, user_id = self.auth_service.register_user(
            "changeuser", "change@example.com", "oldpassword"
        )
        
        success, message = self.auth_service.change_password(
            int(user_id), "wrongoldpassword", "newpassword123"
        )
        
        assert success is False
        assert "incorrect" in message.lower() or "wrong" in message.lower()
```

## Evaluation Harness Logic

### WorkMemEval Task Runner
```python
"""
WorkMemEval Task Execution and Evaluation Harness
"""
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class ActionTraceEntry:
    timestamp: float
    action_type: str
    file_path: Optional[str]
    function_name: Optional[str]
    context_size: int
    success: bool
    metadata: Dict[str, Any]

@dataclass
class PlanningResult:
    planning_completed: bool
    plan_document_path: str
    planning_duration: float
    plan_quality_indicators: Dict[str, bool]
    baseline_plan_content: str

@dataclass
class CheckpointResult:
    checkpoint_id: str
    tests_passed: bool
    completion_time: float
    working_memory_metrics: Dict[str, float]
    planning_compliance_metrics: Dict[str, float]
    action_trace: List[ActionTraceEntry]

class WorkMemEvalRunner:
    
    def __init__(self, task_definition_path: str, agent_interface):
        """Initialize task runner with task definition and agent interface"""
        with open(task_definition_path, 'r') as f:
            self.task_def = json.load(f)
        
        self.agent = agent_interface
        self.action_trace = []
        self.current_checkpoint = 0
        self.start_time = time.time()
        
    def run_task(self) -> Dict[str, Any]:
        """Execute complete task and return evaluation results"""
        print(f"Starting task: {self.task_def['metadata']['title']}")
        
        # Setup repository
        self._setup_repository()
        
        # Execute planning phase
        planning_result = self._execute_planning_phase()
        
        if not planning_result.planning_completed:
            return {
                'task_id': self.task_def['task_id'],
                'completion_status': 'failed_planning',
                'planning_result': planning_result,
                'checkpoint_results': [],
                'final_metrics': {},
                'total_duration': time.time() - self.start_time
            }
        
        # Store baseline plan for compliance tracking
        self.baseline_plan = planning_result.baseline_plan_content
        
        # Execute checkpoints progressively
        checkpoint_results = []
        for checkpoint in self.task_def['checkpoints']:
            result = self._execute_checkpoint(checkpoint)
            checkpoint_results.append(result)
            
            if not result.tests_passed:
                print(f"Task failed at checkpoint {checkpoint['checkpoint_id']}")
                break
                
            # Check for working memory challenges
            self._handle_memory_challenges(checkpoint)
        
        # Calculate final metrics
        final_metrics = self._calculate_final_metrics(checkpoint_results, planning_result)
        
        return {
            'task_id': self.task_def['task_id'],
            'completion_status': 'completed' if len(checkpoint_results) == len(self.task_def['checkpoints']) else 'failed',
            'planning_result': planning_result,
            'checkpoint_results': checkpoint_results,
            'final_metrics': final_metrics,
            'total_duration': time.time() - self.start_time
        }
    
    def _execute_checkpoint(self, checkpoint: Dict[str, Any]) -> CheckpointResult:
        """Execute a single checkpoint and measure working memory"""
        print(f"Presenting checkpoint: {checkpoint['title']}")
        
        checkpoint_start = time.time()
        
        # Present checkpoint requirements to agent
        self._present_checkpoint(checkpoint)
        
        # Capture action trace during implementation
        trace_start_idx = len(self.action_trace)
        
        # Let agent work on checkpoint
        self._agent_implement_checkpoint(checkpoint)
        
        # Run tests to check completion
        tests_passed = self._run_checkpoint_tests(checkpoint['test_file'])
        
        # Extract action trace for this checkpoint
        checkpoint_trace = self.action_trace[trace_start_idx:]
        
        # Calculate working memory metrics
        wm_metrics = self._calculate_working_memory_metrics(checkpoint_trace, checkpoint)
        
        # Calculate planning compliance metrics
        planning_metrics = self._calculate_planning_compliance_metrics(checkpoint_trace, checkpoint)
        
        return CheckpointResult(
            checkpoint_id=checkpoint['checkpoint_id'],
            tests_passed=tests_passed,
            completion_time=time.time() - checkpoint_start,
            working_memory_metrics=wm_metrics,
            planning_compliance_metrics=planning_metrics,
            action_trace=checkpoint_trace
        )
    
    def _execute_planning_phase(self) -> PlanningResult:
        """Execute the planning phase and capture baseline plan"""
        print("Starting planning phase...")
        
        planning_start = time.time()
        planning_config = self.task_def['planning_phase']
        
        # Present overview prompt to agent
        self._present_planning_prompt(planning_config['overview_prompt'])
        
        # Log planning phase start
        self._log_action('start_planning_phase')
        
        # Agent creates implementation plan
        plan_completed = self._agent_create_plan(planning_config)
        
        # Capture the plan document
        plan_document_path = planning_config['planning_capture']['plan_document']
        baseline_plan_content = self._read_plan_document(plan_document_path) if plan_completed else ""
        
        # Assess plan quality
        plan_quality = self._assess_plan_quality(baseline_plan_content, planning_config) if plan_completed else {}
        
        planning_duration = time.time() - planning_start
        
        # Log planning completion
        self._log_action('complete_planning_phase', plan_document_path, success=plan_completed,
                        metadata={'planning_duration': planning_duration})
        
        return PlanningResult(
            planning_completed=plan_completed,
            plan_document_path=plan_document_path,
            planning_duration=planning_duration,
            plan_quality_indicators=plan_quality,
            baseline_plan_content=baseline_plan_content
        )
    
    def _calculate_planning_compliance_metrics(self, trace: List[ActionTraceEntry], checkpoint: Dict) -> Dict[str, float]:
        """Calculate how well agent follows their initial plan during checkpoint execution"""
        
        # Plan Reference Rate: How often does agent reference their plan?
        plan_references = [entry for entry in trace if self._is_plan_reference(entry)]
        total_actions = len(trace)
        plan_reference_rate = len(plan_references) / total_actions if total_actions > 0 else 0
        
        # Architectural Consistency: Does implementation match planned architecture?
        architectural_consistency = self._assess_architectural_consistency(trace, checkpoint)
        
        # Plan Deviation: How much does execution deviate from planned approach?
        plan_deviation_score = self._calculate_plan_deviation(trace, checkpoint)
        
        # Strategy Adherence: Does agent follow their stated implementation strategy?
        strategy_adherence = self._assess_strategy_adherence(trace, checkpoint)
        
        return {
            'plan_reference_rate': plan_reference_rate,
            'architectural_consistency': architectural_consistency,
            'plan_deviation_score': plan_deviation_score,
            'strategy_adherence': strategy_adherence
        }
    
    def _is_plan_reference(self, action: ActionTraceEntry) -> bool:
        """Check if action involves referencing the implementation plan"""
        plan_document = self.task_def['planning_phase']['planning_capture']['plan_document']
        
        # Direct plan file access
        if action.file_path == plan_document:
            return True
            
        # Plan-related keywords in action metadata
        if action.metadata and any(keyword in str(action.metadata).lower() 
                                 for keyword in ['plan', 'architecture', 'strategy', 'approach']):
            return True
            
        return False
    
    def _assess_architectural_consistency(self, trace: List[ActionTraceEntry], checkpoint: Dict) -> float:
        """Assess whether implementation follows planned architecture"""
        # This would analyze the implementation choices against the baseline plan
        # For now, simplified heuristic based on file organization and component structure
        
        # Extract file creation patterns from trace
        file_creates = [entry for entry in trace if entry.action_type == 'create_file']
        
        # Check if file organization matches planned structure (simplified)
        # In real implementation, this would parse the baseline plan and compare structures
        consistency_score = 0.85  # Placeholder - would be computed from actual plan analysis
        
        return consistency_score
    
    def _calculate_plan_deviation(self, trace: List[ActionTraceEntry], checkpoint: Dict) -> float:
        """Calculate how much the execution deviates from the original plan"""
        # This would compare the actual implementation sequence against planned sequence
        # For now, simplified metric based on unexpected file accesses and approach changes
        
        unexpected_actions = 0
        total_actions = len(trace)
        
        # Heuristic: excessive file exploration might indicate deviation from plan
        exploration_actions = [entry for entry in trace if self._is_exploration_action(entry)]
        unexpected_actions += len(exploration_actions)
        
        deviation_score = unexpected_actions / total_actions if total_actions > 0 else 0
        return min(1.0, deviation_score)  # Cap at 1.0
    
    def _assess_strategy_adherence(self, trace: List[ActionTraceEntry], checkpoint: Dict) -> float:
        """Assess whether agent follows their stated implementation strategy"""
        # This would analyze whether the implementation approach matches the planned strategy
        # Simplified implementation - in practice would parse strategy from baseline plan
        
        # Look for systematic approach vs ad-hoc implementation
        systematic_indicators = [
            'read_requirements', 'analyze_dependencies', 'write_tests_first', 
            'incremental_implementation', 'integration_testing'
        ]
        
        systematic_actions = sum(1 for entry in trace 
                               if any(indicator in entry.action_type.lower() 
                                     for indicator in systematic_indicators))
        
        adherence_score = min(1.0, systematic_actions / 5)  # Normalize to 0-1
        return adherence_score
    
    def _is_exploration_action(self, action: ActionTraceEntry) -> bool:
        """Check if action represents unplanned exploration"""
        exploration_patterns = ['list_directory', 'browse_files', 'search_codebase']
        return any(pattern in action.action_type.lower() for pattern in exploration_patterns)
    
    def _calculate_working_memory_metrics(self, trace: List[ActionTraceEntry], checkpoint: Dict) -> Dict[str, float]:
        """Calculate working memory metrics from action trace"""
        
        # Information Retention: Context re-read rate
        file_accesses = [entry for entry in trace if entry.action_type == 'read_file']
        unique_files = set(entry.file_path for entry in file_accesses)
        total_accesses = len(file_accesses)
        unnecessary_rereads = total_accesses - len(unique_files) if len(unique_files) > 0 else 0
        context_reread_rate = unnecessary_rereads / total_accesses if total_accesses > 0 else 0
        
        # Contextual Relevance: F1-score of file access precision/recall
        required_files = self._get_required_files_for_checkpoint(checkpoint)
        accessed_files = unique_files
        distractor_files = self._get_distractor_files()
        
        # Files that should be accessed (relevant)
        relevant_accessed = len(accessed_files.intersection(required_files))
        # Files that shouldn't be accessed (distractors)
        irrelevant_accessed = len(accessed_files.intersection(distractor_files))
        
        # Precision: What fraction of accessed files were relevant?
        precision = relevant_accessed / len(accessed_files) if accessed_files else 1.0
        
        # Recall: What fraction of required files were accessed?
        recall = relevant_accessed / len(required_files) if required_files else 1.0
        
        # F1-score combines both
        relevance_f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        # Behavioral Integrity: Comprehensive error correction overhead
        # Count all unforced errors during implementation
        failed_commands = [entry for entry in trace if not entry.success]
        
        # Detect backtracking patterns (implementing, then undoing/reverting)
        write_actions = [entry for entry in trace if entry.action_type in ['write_file', 'modify_file']]
        backtrack_count = self._detect_backtracking_patterns(write_actions)
        
        # Test-specific failures
        test_runs = [entry for entry in trace if entry.action_type == 'run_tests']
        failed_test_runs = [entry for entry in test_runs if not entry.success]
        
        # Total error overhead: all types of unforced errors
        total_actions = len(trace)
        total_errors = len(failed_commands) + backtrack_count + len(failed_test_runs)
        error_correction_overhead = total_errors / total_actions if total_actions > 0 else 0
        
        # State Coherence: Check system consistency 
        state_coherence_index = self._check_state_coherence(trace)
        
        return {
            'context_reread_rate': context_reread_rate,
            'relevance_f1_score': relevance_f1_score,
            'relevance_precision': precision,
            'relevance_recall': recall,
            'error_correction_overhead': error_correction_overhead,
            'state_coherence_index': state_coherence_index
        }
    
    def _get_required_files_for_checkpoint(self, checkpoint: Dict) -> set:
        """Determine which files are actually needed for a checkpoint"""
        required = set()
        
        # Always need the stub file itself
        required.add(checkpoint['stub_file'])
        
        # Need files from dependency checkpoints
        for dep_id in checkpoint['dependencies']:
            dep_checkpoint = next(cp for cp in self.task_def['checkpoints'] if cp['checkpoint_id'] == dep_id)
            required.add(dep_checkpoint['stub_file'])
        
        # Add test file for reference
        required.add(checkpoint['test_file'])
        
        # Repository-specific logic could add common files like __init__.py, requirements.txt
        required.update(['requirements.txt', 'README.md'])
        
        return required
    
    def _get_distractor_files(self) -> set:
        """Get set of distractor files that should generally be avoided"""
        return set(self.task_def['repository'].get('distractor_files', []))
    
    def _detect_backtracking_patterns(self, write_actions: List[ActionTraceEntry]) -> int:
        """Detect patterns where agent writes then reverts/rewrites same file repeatedly"""
        file_write_counts = {}
        
        for action in write_actions:
            file_path = action.file_path
            if file_path not in file_write_counts:
                file_write_counts[file_path] = 0
            file_write_counts[file_path] += 1
        
        # Backtracking heuristic: files written more than 3 times suggest confusion/backtracking
        backtrack_count = sum(max(0, count - 3) for count in file_write_counts.values())
        
        return backtrack_count
    
    def _agent_implement_checkpoint(self, checkpoint: Dict[str, Any]):
        """Interface with agent to implement checkpoint"""
        # This would interface with the actual agent (Aider, etc.)
        # For now, simulate the interaction
        
        stub_file = checkpoint['stub_file']
        requirements = checkpoint['requirements']
        
        # Log that agent is working on checkpoint
        self._log_action('start_checkpoint', stub_file, checkpoint['stub_function'])
        
        # Simulate agent reading files, implementing, testing
        # In real implementation, this would:
        # 1. Call agent with checkpoint requirements
        # 2. Monitor agent actions (file reads, writes, test runs)
        # 3. Log all actions to action_trace
        # 4. Continue until tests pass or timeout
        
        pass
    
    def _log_action(self, action_type: str, file_path: str = None, function_name: str = None, 
                   success: bool = True, metadata: Dict = None):
        """Log agent action to trace"""
        entry = ActionTraceEntry(
            timestamp=time.time(),
            action_type=action_type,
            file_path=file_path,
            function_name=function_name,
            context_size=self._get_current_context_size(),
            success=success,
            metadata=metadata or {}
        )
        self.action_trace.append(entry)
    
    def _run_checkpoint_tests(self, test_file: str) -> bool:
        """Run tests for checkpoint and return pass/fail"""
        try:
            result = subprocess.run(['pytest', test_file, '-v'], 
                                  capture_output=True, text=True, cwd=self.repo_path)
            
            self._log_action('run_tests', test_file, success=(result.returncode == 0),
                           metadata={'output': result.stdout, 'errors': result.stderr})
            
            return result.returncode == 0
        except Exception as e:
            self._log_action('run_tests', test_file, success=False,
                           metadata={'error': str(e)})
            return False
    
    def _handle_memory_challenges(self, checkpoint: Dict[str, Any]):
        """Inject working memory challenges if specified"""
        challenges = self.task_def.get('working_memory_challenges', [])
        
        for challenge in challenges:
            if challenge.get('at_checkpoint') == checkpoint['checkpoint_id']:
                
                if challenge['type'] == 'requirement_update':
                    self._inject_requirement_change(challenge)
                    
                elif challenge['type'] == 'context_switch':
                    self._inject_context_switch(challenge)
                    
                elif challenge['type'] == 'information_overload':
                    self._inject_information_overload(challenge)
    
    def _calculate_final_metrics(self, checkpoint_results: List[CheckpointResult], planning_result: PlanningResult) -> Dict[str, float]:
        """Calculate final aggregated working memory and planning compliance metrics"""
        if not checkpoint_results:
            return {'planning_completed': planning_result.planning_completed}
        
        # Aggregate working memory metrics across checkpoints
        wm_metrics = ['context_reread_rate', 'relevance_f1_score', 'error_correction_overhead', 'state_coherence_index']
        final_metrics = {}
        
        for metric in wm_metrics:
            values = [cp.working_memory_metrics.get(metric, 0) for cp in checkpoint_results]
            final_metrics[f'avg_{metric}'] = sum(values) / len(values)
        
        # Aggregate planning compliance metrics
        planning_metrics = ['plan_reference_rate', 'architectural_consistency', 'plan_deviation_score', 'strategy_adherence']
        
        for metric in planning_metrics:
            values = [cp.planning_compliance_metrics.get(metric, 0) for cp in checkpoint_results]
            final_metrics[f'avg_{metric}'] = sum(values) / len(values)
        
        # Planning quality indicators
        final_metrics['planning_completed'] = planning_result.planning_completed
        final_metrics['planning_duration'] = planning_result.planning_duration
        
        if planning_result.plan_quality_indicators:
            for indicator, value in planning_result.plan_quality_indicators.items():
                final_metrics[f'plan_quality_{indicator}'] = float(value)
        
        # Additional granular relevance metrics
        precision_values = [cp.working_memory_metrics.get('relevance_precision', 0) for cp in checkpoint_results]
        recall_values = [cp.working_memory_metrics.get('relevance_recall', 0) for cp in checkpoint_results]
        final_metrics['avg_relevance_precision'] = sum(precision_values) / len(precision_values)
        final_metrics['avg_relevance_recall'] = sum(recall_values) / len(recall_values)
        
        # Task completion rate
        successful_checkpoints = sum(1 for cp in checkpoint_results if cp.tests_passed)
        final_metrics['task_completion_rate'] = successful_checkpoints / len(self.task_def['checkpoints'])
        
        # Working memory degradation over time
        reread_rates = [cp.working_memory_metrics.get('context_reread_rate', 0) for cp in checkpoint_results]
        final_metrics['memory_degradation'] = reread_rates[-1] - reread_rates[0] if len(reread_rates) > 1 else 0
        
        # Planning compliance degradation over time
        strategy_adherence_values = [cp.planning_compliance_metrics.get('strategy_adherence', 0) for cp in checkpoint_results]
        final_metrics['planning_compliance_degradation'] = (strategy_adherence_values[0] - strategy_adherence_values[-1]) if len(strategy_adherence_values) > 1 else 0
        
        # Cross-checkpoint complexity scaling (emergent measurement)
        dependency_loads = [len(cp_def['dependencies']) for cp_def in self.task_def['checkpoints']]
        final_metrics['max_dependency_load'] = max(dependency_loads)
        final_metrics['avg_dependency_load'] = sum(dependency_loads) / len(dependency_loads)
        
        return final_metrics

# Usage example
if __name__ == "__main__":
    # Initialize with task definition and agent interface
    runner = WorkMemEvalRunner('user_management_api.json', agent_interface)
    
    # Run task and get results
    results = runner.run_task()
    
    # Display results
    print(f"Task Completion: {results['completion_status']}")
    print(f"Final Working Memory Metrics: {results['final_metrics']}")
```

This comprehensive example establishes the complete pattern for WorkMemEval tasks:

1. **JSON Schema**: Structured task definition with checkpoints, dependencies, and challenges
2. **Repository Structure**: Realistic starter codebase with stubs and distractors
3. **Progressive Complexity**: Each checkpoint builds on previous ones with increasing working memory load
4. **Objective Testing**: Each checkpoint has concrete tests that must pass
5. **Action Trace Capture**: Complete logging of agent behaviors for memory analysis
6. **Working Memory Challenges**: Requirement updates, context switches, and information overload
7. **Evaluation Harness**: Automated execution and metric calculation

This pattern can be replicated across different domains (web apps, data processing, ML pipelines) while maintaining consistent evaluation methodology.