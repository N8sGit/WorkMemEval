# Task Complexity Measurement in WorkMemEval

This document explains how WorkMemEval measures and analyzes task complexity using the three-dimensional complexity framework, enabling systematic evaluation of AI agent working memory capabilities.

## Overview

WorkMemEval uses a **three-dimensional complexity space** to characterize tasks:

- **Length Dimension**: Temporal complexity (sequential demands)
- **Depth Dimension**: Informational complexity (cognitive load per step)
- **Composition Dimension**: Structural complexity (coordination demands)

Each dimension primarily stresses a different aspect of working memory:

| Dimension | Primary Stress | Memory Pillar |
|-----------|----------------|---------------|
| Length | Temporal demands | Memory Fidelity |
| Depth | Information filtering | Contextual Relevance |
| Composition | Coordination demands | Behavioral Integrity |

## Length Dimension: Temporal Complexity

### Definition
The number of sequential checkpoints an agent must complete, representing temporal working memory demands.

### Calculation
```python
length_dimension = len(task.checkpoints)
```

### Memory Stress
- **Low (1-3 checkpoints)**: Minimal temporal demands
- **Medium (4-7 checkpoints)**: Moderate sequence tracking
- **High (8-12 checkpoints)**: Significant temporal coordination
- **Extreme (13+ checkpoints)**: Maximum sequential complexity

### Example Analysis
```python
# Simple task: 3 checkpoints
task_simple = ["Parse input", "Process data", "Generate output"]
length_score = 3  # Low temporal complexity

# Complex task: 10 checkpoints  
task_complex = [
    "Initialize system", "Load configuration", "Connect database",
    "Authenticate user", "Validate permissions", "Query data",
    "Transform results", "Apply business rules", "Format output", "Send response"
]
length_score = 10  # High temporal complexity
```

### Memory Fidelity Implications
Long sequences stress **Memory Fidelity** by requiring agents to:
- Retain specifications from early checkpoints
- Maintain context across extended sequences
- Recall dependencies between distant checkpoints

## Depth Dimension: Informational Complexity

### Definition
The average informational density per checkpoint, measured in tokens of specification text.

### Calculation
```python
total_tokens = sum(checkpoint.estimated_tokens for checkpoint in task.checkpoints)
depth_dimension = total_tokens / len(task.checkpoints)
```

### Token Estimation
Tokens are estimated from checkpoint requirements text:
```python
# Example checkpoint with depth analysis
checkpoint = CheckpointSpecification(
    title="Implement OAuth2 Authentication",
    requirements="""
    Implement OAuth2 authentication flow with the following requirements:
    - Support authorization code grant type
    - Implement PKCE for security enhancement  
    - Handle token refresh automatically
    - Validate JWT tokens with proper signature verification
    - Support multiple identity providers (Google, GitHub, Microsoft)
    - Implement proper error handling for expired tokens
    - Store tokens securely using encryption
    - Provide logout functionality that revokes tokens
    """,
    estimated_tokens=450  # Dense informational content
)
```

### Complexity Tiers
- **Low (50-150 tokens)**: Simple, focused requirements
- **Medium (150-300 tokens)**: Moderate specification detail
- **High (300-500 tokens)**: Complex, multi-faceted requirements
- **Extreme (500+ tokens)**: Dense, comprehensive specifications

### Contextual Relevance Implications
High depth stresses **Contextual Relevance** by requiring agents to:
- Filter relevant from irrelevant information
- Identify critical vs optional requirements
- Maintain focus amid information density

## Composition Dimension: Structural Complexity

### Definition
The structural coordination complexity, calculated as **Component Count × Integration Density**.

### Detailed Calculation

#### Step 1: Component Extraction
```python
def extract_components(checkpoints):
    components = []
    for checkpoint in checkpoints:
        # Extract semantic component from title
        component_name = checkpoint.title
        components.append(component_name)
    return components

# Example
checkpoints = [
    "User Authentication Service",
    "Database Schema Design", 
    "REST API Implementation",
    "Frontend Integration",
    "Payment Gateway Integration"
]
component_count = 5
```

#### Step 2: Dependency Analysis
```python
def analyze_dependencies(checkpoints):
    dependencies = {}
    for checkpoint in checkpoints:
        dependencies[checkpoint.title] = checkpoint.dependencies
    return dependencies

# Example dependency structure
dependencies = {
    "User Authentication Service": [],
    "Database Schema Design": [],
    "REST API Implementation": ["Database Schema Design"],
    "Frontend Integration": ["REST API Implementation", "User Authentication Service"],
    "Payment Gateway Integration": ["User Authentication Service", "REST API Implementation"]
}
```

#### Step 3: Integration Density Calculation
```python
def calculate_integration_density(dependencies):
    total_dependencies = sum(len(deps) for deps in dependencies.values())
    component_count = len(dependencies)
    return total_dependencies / component_count if component_count > 0 else 0

# Example calculation
total_deps = 0 + 0 + 1 + 2 + 2 = 5
integration_density = 5 / 5 = 1.0
```

#### Step 4: Final Composition Score
```python
composition_score = component_count × integration_density
composition_score = 5 × 1.0 = 5.0
```

### Structural Complexity Examples

#### Linear Pipeline (Low Complexity)
```python
# Score: 4 × 0.75 = 3.0
checkpoints = [
    "Read Input File",        # deps: []
    "Parse Data",            # deps: ["Read Input File"]
    "Transform Data",        # deps: ["Parse Data"]  
    "Write Output File"      # deps: ["Transform Data"]
]
```

#### Service Architecture (Medium Complexity)
```python
# Score: 6 × 1.33 = 8.0
checkpoints = [
    "User Service",          # deps: []
    "Auth Service",          # deps: []
    "Database Service",      # deps: []
    "API Gateway",           # deps: ["User Service", "Auth Service"]
    "Web Frontend",          # deps: ["API Gateway"]
    "Admin Dashboard"        # deps: ["API Gateway", "Database Service"]
]
```

#### Microservices Mesh (High Complexity)
```python
# Score: 8 × 2.25 = 18.0
checkpoints = [
    "User Service",          # deps: []
    "Auth Service",          # deps: ["User Service"]
    "Order Service",         # deps: ["User Service", "Auth Service"]
    "Payment Service",       # deps: ["User Service", "Order Service"]
    "Inventory Service",     # deps: ["Order Service"]
    "Notification Service",  # deps: ["User Service", "Order Service", "Payment Service"]
    "Analytics Service",     # deps: ["User Service", "Order Service", "Payment Service"]
    "API Gateway"            # deps: ["Auth Service", "Order Service", "Payment Service"]
]
```

### Behavioral Integrity Implications
High composition complexity stresses **Behavioral Integrity** by requiring agents to:
- Coordinate changes across multiple components
- Maintain consistency between interdependent parts
- Handle cascading updates and side effects

## Complexity Profile Generation

### Automatic Analysis
```python
complexity_profile = ComplexityProfile.from_task_specification(task)

print(f"Length: {complexity_profile.length_dimension}")
print(f"Depth: {complexity_profile.depth_dimension}")  
print(f"Composition: {complexity_profile.composition_metrics.composition_score}")
print(f"Primary stress pillar: {complexity_profile.primary_stress_pillar}")
```

### Pillar Stress Calculation
```python
def calculate_pillar_stress_scores(length, depth, composition):
    # Normalize to 0-1 scale
    fidelity_score = min(length / 10.0, 1.0)        # Length stress
    relevance_score = min(depth / 500.0, 1.0)       # Depth stress  
    integrity_score = min(composition / 15.0, 1.0)  # Composition stress
    
    return {
        MemoryPillar.MEMORY_FIDELITY: fidelity_score,
        MemoryPillar.CONTEXTUAL_RELEVANCE: relevance_score,
        MemoryPillar.BEHAVIORAL_INTEGRITY: integrity_score
    }
```

### Difficulty Scoring
```python
def calculate_overall_difficulty(length, depth, composition):
    length_factor = min(length / 10.0, 1.0)
    depth_factor = min(depth / 500.0, 1.0)
    composition_factor = min(composition / 15.0, 1.0)
    
    # Multiplicative difficulty (all dimensions matter)
    difficulty_score = length_factor * depth_factor * composition_factor
    
    if difficulty_score < 0.3:
        return "simple"
    elif difficulty_score < 0.6:
        return "moderate"
    elif difficulty_score < 0.9:
        return "complex"
    else:
        return "highly_complex"
```

## Memory Probe Configuration

### Automatic Probe Selection
Based on complexity analysis, the system automatically recommends appropriate memory probes:

```python
def recommend_probes(complexity_profile):
    primary_pillar = complexity_profile.primary_stress_pillar
    
    if primary_pillar == MemoryPillar.MEMORY_FIDELITY:
        return [ProbeType.N_BACK_INTEGRATION, ProbeType.COMPRESSION_STRESS]
    elif primary_pillar == MemoryPillar.CONTEXTUAL_RELEVANCE:
        return [ProbeType.DISTRACTOR_INJECTION, ProbeType.CHANGE_DETECTION]
    elif primary_pillar == MemoryPillar.BEHAVIORAL_INTEGRITY:
        return [ProbeType.UPDATE_ROBUSTNESS, ProbeType.CONTEXT_SWITCH]
```

### Probe Injection Points
```python
def calculate_probe_injection_points(length, probe_count):
    # Avoid first checkpoint, distribute evenly
    available_points = list(range(2, length + 1))
    step = max(1, len(available_points) // probe_count)
    
    injection_points = []
    for i in range(0, len(available_points), step):
        if len(injection_points) < probe_count:
            injection_points.append(available_points[i])
    
    return injection_points
```

## Practical Examples

### Example 1: Simple Web Scraper
```python
# Task: Build a web scraper
checkpoints = [
    "Setup HTTP client",           # 150 tokens, deps: []
    "Parse HTML content",          # 200 tokens, deps: ["Setup HTTP client"]
    "Extract target data"          # 180 tokens, deps: ["Parse HTML content"]
]

# Complexity Analysis:
# Length: 3 (low temporal complexity)
# Depth: 177 average tokens (low-medium informational complexity)
# Composition: 3 × 0.67 = 2.0 (low structural complexity)
# Primary Pillar: MEMORY_FIDELITY (default for simple tasks)
# Difficulty: simple
```

### Example 2: E-commerce Platform
```python
# Task: Build e-commerce platform
checkpoints = [
    "User authentication system",     # 400 tokens, deps: []
    "Product catalog service",        # 350 tokens, deps: []
    "Shopping cart functionality",    # 300 tokens, deps: ["User authentication system"]
    "Payment processing",             # 450 tokens, deps: ["User authentication system", "Shopping cart functionality"]
    "Order management",               # 380 tokens, deps: ["Product catalog service", "Payment processing"]
    "Admin dashboard",                # 320 tokens, deps: ["User authentication system", "Product catalog service", "Order management"]
    "Email notifications",            # 250 tokens, deps: ["Order management"]
    "API documentation"               # 200 tokens, deps: ["Payment processing", "Order management"]
]

# Complexity Analysis:
# Length: 8 (high temporal complexity)
# Depth: 331 average tokens (medium-high informational complexity)
# Composition: 8 × 1.5 = 12.0 (high structural complexity)
# Primary Pillar: BEHAVIORAL_INTEGRITY (high coordination demands)
# Difficulty: complex
```

## Research Applications

### Comparative Studies
Researchers can use complexity measurements to:
- Compare agent performance across equivalent complexity levels
- Study how different complexity dimensions affect memory performance
- Design controlled experiments with specific complexity targets

### Longitudinal Analysis
Track how agents handle increasing complexity:
```python
complexity_progression = [
    ("simple", 0.2),      # Difficulty score
    ("moderate", 0.5),
    ("complex", 0.8),
    ("highly_complex", 1.0)
]
```

### Memory System Evaluation
Different memory systems may excel at different complexity dimensions:
- **Vector databases**: May handle high depth (information filtering)
- **Graph databases**: May handle high composition (relationship tracking)
- **Hierarchical memory**: May handle high length (temporal sequences)

## Implementation Notes

### Token Estimation Accuracy
For more accurate depth measurement, consider:
- Using actual tokenizer counts instead of estimates
- Accounting for code examples in requirements
- Including test specification complexity

### Dynamic Complexity
Some tasks have complexity that emerges during execution:
- Requirements that change mid-task
- Dependencies discovered during implementation
- Integration challenges not apparent in specifications

### Cultural and Domain Factors
Complexity perception may vary by:
- Programming language familiarity
- Domain expertise
- Architectural patterns knowledge

This measurement framework provides a systematic foundation for understanding and comparing the working memory demands of different software development tasks, enabling rigorous research into AI agent cognitive capabilities.