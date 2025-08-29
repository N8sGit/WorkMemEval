# WorkMemEval: Hybrid Task Structure Design

## Overview

WorkMemEval employs a **hybrid task structure** that combines the measurement precision of controlled checkpoints with the realistic freedom of open-ended software development. This approach provides **skeletal reference points** for objective evaluation while allowing agents to implement solutions using their preferred architecture and design patterns.

## Core Design Philosophy

**Freedom Zones = Behavioral Data Generation**
The purpose of allowing agents architectural freedom between checkpoints is **not** to judge their implementation choices, but to create realistic, complex development processes that generate rich **Action Traces**. Without this freedom:
- Tasks would be too simplistic (mere fill-in-the-blank exercises)
- No complex memory state would emerge to manage or forget
- Working memory evaluation would be meaningless

**Checkpoints = Objective Measurement Points**
Checkpoints serve as measurement anchors where our evaluation harness focuses on exactly two things:
1. **Did the tests pass?** (Task Success gating metric)
2. **What memory-related behaviors did we observe in the Action Trace while the agent worked toward passing those tests?**

The evaluation system is completely agnostic to whether the code that passed the tests is elegant, clumsy, well-architected, or messy. Code quality is irrelevant to working memory assessment.

## The Action Trace: Core Data Source

**What Freedom Zones Generate:**
```python
# Rich behavioral trace from realistic development process
action_trace = [
    {'timestamp': t1, 'action': 'read_file', 'file': 'user_model.py', 'context': '...'},
    {'timestamp': t2, 'action': 'implement_function', 'target': 'authenticate_user', '...'},
    {'timestamp': t3, 'action': 'read_file', 'file': 'user_model.py', 'context': '...'}, # Re-read!
    {'timestamp': t4, 'action': 'run_tests', 'test_file': 'test_auth.py', 'result': 'fail'},
    {'timestamp': t5, 'action': 'modify_function', 'target': 'authenticate_user', '...'},
    # ... hundreds more actions across complex development process
]
```

**What Checkpoints Measure:**
```python
# Analysis of action trace for working memory behaviors
def analyze_checkpoint_completion(checkpoint_id, action_trace):
    return {
        'context_reread_rate': count_unnecessary_file_reaccesses(trace),
        'state_coherence': check_system_consistency(trace),
        'dependency_tracking': verify_cross_checkpoint_integration(trace),
        'error_patterns': analyze_unforced_errors(trace)
    }
```

## Task Structure Framework

### Checkpoint Categories

**1. Implementation Checkpoints (60%)**
```python
def authenticate_user(username: str, password: str) -> AuthResult:
    """
    CHECKPOINT: Core authentication logic
    REQUIREMENTS: Handle password validation, rate limiting, return appropriate states
    TEST_GATED: Must pass security and functionality tests
    """
    pass
```

**2. Integration Checkpoints (25%)**
```python
def connect_auth_to_api_gateway(auth_service, gateway_config) -> GatewayResult:
    """
    CHECKPOINT: System integration point
    REQUIREMENTS: Connect previously implemented auth system with API gateway
    WORKING_MEMORY_CHALLENGE: Must reference and integrate prior work
    """
    pass
```

**3. Extension Checkpoints (15%)**
```python
def add_two_factor_authentication(existing_auth_system) -> AuthSystem:
    """
    CHECKPOINT: Feature extension
    REQUIREMENTS: Extend existing authentication to support 2FA
    MEMORY_UPDATE_CHALLENGE: Modify prior implementation without breaking existing functionality
    """
    pass
```

### Freedom Zones

**Between Every Checkpoint, Agents Can:**
- Create supporting classes, functions, and modules
- Choose their own architectural patterns (MVC, Repository, Service Layer, etc.)
- Organize files and directories as they see fit
- Implement validation, logging, error handling, and utilities
- Refactor existing code to accommodate new requirements
- Choose database schemas, ORM approaches, and data structures

## Critical Design Principle: Process Complexity Enables Memory Evaluation

### Why Freedom Zones Are Essential

**Realistic Complexity Generation**: Without architectural freedom between checkpoints, tasks would reduce to simple fill-in-the-blank exercises. The working memory challenge emerges from:
- Managing dependencies across multiple files and components
- Maintaining state awareness through complex development processes  
- Handling information overload as system complexity grows
- Integrating new requirements with existing implementations

**Rich Action Trace Generation**: Freedom zones create the realistic development processes that generate the behavioral data we need:
```python
# Simple task (no freedom): Limited trace
trace = [read_spec, implement_function, run_test]  # No memory challenge

# Complex task (with freedom): Rich behavioral data
trace = [read_spec, explore_codebase, create_helper_functions, refactor_existing_code, 
         implement_checkpoint, handle_errors, integrate_with_previous_work, ...]
```

**Working Memory Stress Testing**: The freedom to make architectural choices creates realistic memory burdens:
- Agents must remember their own design decisions across checkpoints
- Complex file structures create spatial navigation challenges
- Multiple valid approaches test memory system robustness under different strategies

### What This Means for Evaluation

**Implementation Agnostic**: WorkMemEval is completely neutral about how agents solve problems. A messy, unstructured solution that demonstrates excellent working memory (tracks dependencies, maintains state, integrates components) scores higher than a beautiful, clean solution with poor memory behaviors.

**Process-Focused**: We evaluate the **journey** (action trace analysis), not the **destination** (code quality). The checkpoint tests merely gate whether the measurement is valid.

### Implementation Guidelines

**Layer 1 Metrics Must Be:**
- Countable (number of errors, percentage of tests passed)
- Verifiable (external ground truth comparison)
- Architecture-agnostic (work regardless of implementation approach)
- Reproducible (same measurement on same trace)

**Layer 2 Analysis Should:**
- Describe, don't score behavioral patterns
- Characterize architectural choices without judgment
- Provide context for understanding Layer 1 results
- Generate insights for working memory research

**Example Evaluation Output:**
```
CHECKPOINT 5 COMPLETION ANALYSIS:
Tests Passed: ✓ (Task Success gate satisfied)

Working Memory Metrics:
- Context Reread Rate: 12% (agent unnecessarily re-accessed 3 of 25 files)
- State Coherence Index: 87% (maintained system consistency across integrations)  
- Dependency Tracking: 94% (successfully referenced 15 of 16 prior checkpoint implementations)
- Error Correction Overhead: 3 unforced errors (low backtracking, good working memory)

Action Trace Insights:
Agent demonstrated strong cross-checkpoint awareness, consistently building on 
prior implementations without information loss. Minimal context thrashing during 
complex integration tasks. Memory system appears robust under moderate complexity.
```

### Dual-Layer Analysis Framework

**Layer 1: Quantitative Evaluation (Official Benchmark Scores)**
```python
def measure_checkpoint_completion(checkpoint_id, agent_state, test_results):
    """
    OBJECTIVE METRICS - Primary benchmark scores
    Maps directly to Memory Fidelity, Contextual Relevance, Behavioral Integrity
    """
    return CheckpointMetrics(
        # Memory Fidelity
        information_retention=context_reread_rate(),
        task_completion_integrity_loss=tcil_score(),
        
        # Contextual Relevance  
        relevance_score=assess_context_appropriateness(),
        
        # Behavioral Integrity
        error_correction_overhead=count_unforced_errors(),
        state_coherence_index=programmatic_consistency_checks(),
        update_robustness=requirement_change_success_rate(),
        resumption_success_rate=context_switch_recovery_rate()
    )
```

**Layer 2: Working Memory Behavioral Analysis (Descriptive Only)**
```python
def analyze_working_memory_behaviors(agent_trace, context_access_log):
    """
    MEMORY-FOCUSED ANALYSIS - No scoring, only memory behavior characterization
    Provides insights into HOW agents manage working memory, not code quality
    """
    return WorkingMemoryAnalysis(
        context_access_patterns=describe_file_access_sequences(),
        information_prioritization=analyze_what_agent_focuses_on(),
        memory_overflow_handling=describe_response_to_information_overload(),
        dependency_tracking_style=characterize_cross_checkpoint_references(),
        context_switching_strategy=analyze_interruption_recovery_patterns()
    )
    # NOTE: Focus purely on memory behaviors, ignore implementation quality
```

### Layer 1: Quantitative Working Memory Metrics (Official Scores)

**Information Retention (Memory Fidelity)**
- Context re-read rate: Frequency of unnecessary re-accessing previously read files
- TCIL Score: Quality preservation through compression events
- **Scoring**: Objective percentage/ratio measurements

**Contextual Relevance** 
- Relevance score: Multi-method assessment of context appropriateness for current checkpoint
- **Scoring**: Quantifiable through test-driven requirements and dependency analysis

**Behavioral Integrity**
- Error correction overhead: Count of unforced errors and backtracking patterns
- State coherence index: Percentage of programmatic consistency checks passed
- Update robustness: Binary success rate for mid-task requirement changes
- Resumption success rate: Binary success rate for context switch recovery
- **Scoring**: All metrics are countable, verifiable, and objective

### Layer 2: Working Memory Behavioral Analysis (Descriptive Only)

**Context Access Pattern Analysis**
- Sequence and timing of file accesses relative to checkpoint requirements
- Identification of unnecessary re-reading (memory failure indicators)
- **Output**: Description of how agent navigates information space

**Information Prioritization Characterization**  
- What information agent focuses on at each checkpoint
- How agent handles competing or contradictory information
- **Output**: Behavioral profile of attention and filtering strategies

**Memory Overflow Response Analysis**
- How agent behaves when context becomes large or complex
- Strategies for managing information beyond immediate working memory capacity
- **Output**: Descriptive patterns of memory management under stress

**Cross-Checkpoint Reference Tracking**
- How agent maintains awareness of dependencies between checkpoints
- Patterns of referring back to previous implementations
- **Output**: Characterization of long-term state tracking behaviors

## Task Design Template

### Core Structure
```yaml
task_definition:
  domain: "web_app" | "data_processing" | "api_service" | "ml_pipeline"
  estimated_duration: 45-180  # minutes
  checkpoint_count: 8-20      # length parameter
  avg_checkpoint_complexity: 150-400  # tokens (depth parameter)

checkpoints:
  - id: "checkpoint_1"
    type: "implementation"
    stub_function: "create_user_model"
    requirements: "User data model with validation"
    test_file: "test_user_model.py"
    dependencies: []
    freedom_scope: "database choice, validation approach, field organization"
    
  - id: "checkpoint_5"  
    type: "integration"
    stub_function: "connect_user_auth"
    requirements: "Integrate user model (checkpoint_1) with auth system (checkpoint_3)"
    test_file: "test_user_auth_integration.py"
    dependencies: ["checkpoint_1", "checkpoint_3"]
    working_memory_challenge: "cross_checkpoint_state_tracking"

working_memory_challenges:
  - type: "requirement_update"
    at_checkpoint: 8
    description: "User model now needs team membership support"
    
  - type: "context_switch"
    at_checkpoint: 12
    description: "Implement unrelated logging system, then return to main task"
    
  - type: "integration_constraint"
    at_checkpoint: 15
    description: "New security requirement affects multiple previous checkpoints"
```

### Checkpoint Design Principles

**Natural Development Boundaries**
- Each checkpoint represents a realistic development milestone
- API boundaries feel like natural separation points
- Requirements align with typical software engineering practices

**Progressive Complexity**
- Early checkpoints establish foundation with minimal dependencies
- Middle checkpoints require integration of multiple prior components
- Late checkpoints involve system-wide modifications and extensions

**Working Memory Load Scaling**
- Initial checkpoints: 2-3 concepts to track
- Mid-task checkpoints: 5-8 interconnected components
- Final checkpoints: 10+ system elements requiring coordination

## Example Task: E-commerce API Development

### Task Overview
**Domain**: API Service  
**Duration**: 120 minutes  
**Checkpoints**: 12  
**Complexity**: Medium-Hard  

### Checkpoint Progression

**Foundation Phase (Checkpoints 1-3)**
```python
# Checkpoint 1: Data Foundation
def create_user_model(user_data: dict) -> User:
    """Implement user data model with validation"""
    pass

# Checkpoint 2: Authentication Base  
def authenticate_user(username: str, password: str) -> AuthResult:
    """Core authentication logic"""
    pass

# Checkpoint 3: Product Catalog
def create_product(product_data: dict, seller_id: str) -> Product:
    """Product creation and catalog management"""
    pass
```

**Integration Phase (Checkpoints 4-8)**
```python
# Checkpoint 4: User-Product Relationship
def assign_product_to_seller(product_id: str, seller_id: str) -> AssignmentResult:
    """Connect products with authenticated users"""
    # WORKING_MEMORY: Must integrate checkpoints 1, 2, 3
    pass

# Checkpoint 6: Shopping Cart
def add_to_cart(user_id: str, product_id: str, quantity: int) -> CartResult:
    """Shopping cart functionality"""
    # WORKING_MEMORY: Track user auth state, product availability
    pass
```

**Extension Phase (Checkpoints 9-12)**
```python
# Checkpoint 10: Payment Processing
def process_payment(cart_id: str, payment_info: PaymentInfo) -> PaymentResult:
    """Handle payment for cart contents"""
    # WORKING_MEMORY: Integrate cart, user, product, and auth systems
    pass

# Checkpoint 12: Order History
def get_user_order_history(user_id: str, filters: OrderFilters) -> List[Order]:
    """Retrieve user's historical orders"""
    # MEMORY_UPDATE_CHALLENGE: System now needs order persistence across sessions
    pass
```

### Working Memory Challenges

**Progressive State Complexity**
- Checkpoint 1: Track user data structure
- Checkpoint 4: Remember user model + auth system + product catalog
- Checkpoint 10: Coordinate 6+ interconnected systems
- Checkpoint 12: Maintain session state + historical data consistency

**Mid-Task Requirement Changes**
- At Checkpoint 7: "Products now support inventory tracking"
- At Checkpoint 11: "Authentication now requires email verification"

**Context Switching**
- At Checkpoint 8: Implement logging system (unrelated to main task)
- Resume at Checkpoint 9: Return to e-commerce development

## Benefits and Validation

### For Scientific Rigor
- **Objective Benchmarking**: Layer 1 provides quantifiable, comparable scores free from subjective bias
- **Reproducible Results**: Checkpoint-based measurement eliminates evaluator interpretation variance
- **Research Validity**: Clear separation between quantitative evaluation and qualitative analysis

### For Development Realism
- **Architectural Freedom**: Agents make realistic software design decisions without scoring penalty
- **Natural Workflow**: Checkpoints mirror actual development milestones  
- **Creative Problem Solving**: Multiple valid implementation approaches, all evaluated fairly

### For Research Insights
- **Dual-Purpose Analysis**: Objective scores for comparison + rich behavioral data for understanding
- **Memory System Testing**: Clear evaluation framework for different working memory architectures
- **Failure Mode Diagnosis**: Layer 1 identifies *what* failed, Layer 2 explains *why*

## Implementation Guidelines

### Task Creation Process
1. **Domain Selection**: Choose realistic software development scenario
2. **Checkpoint Identification**: Map natural development milestones to required stubs
3. **Dependency Mapping**: Establish working memory requirements between checkpoints
4. **Test Design**: Create comprehensive test suites for each checkpoint
5. **Challenge Injection**: Add memory obstacles (updates, interruptions, complexity)
6. **Validation**: Ensure realistic development flow and measurement objectives

### Quality Criteria
- **Natural Progression**: Each checkpoint feels like logical next step
- **Realistic Requirements**: Specifications match real software development needs
- **Measurable Complexity**: Clear quantitative scaling of working memory demands
- **Architectural Freedom**: Sufficient flexibility for multiple valid approaches
- **Integration Dependencies**: Clear working memory challenges requiring prior checkpoint knowledge

This hybrid approach transforms WorkMemEval from artificial constraint satisfaction into realistic software development evaluation while maintaining the measurement precision essential for working memory research.