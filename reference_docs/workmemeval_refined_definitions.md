# WorkMemEval: Refined Operational Definitions & Task Complexity

## Refined Operational Definitions

### Current Definitions (Your Framework)

**Context**: Ambient content available to the model's stateless "viewport" of its environment at runtime. *Specious, ephemeral and contingent.*

**Working Memory**: A logical system for determining, retaining, compressing, and presenting immediately task relevant context to the agent at any given time. *Guided, continuous, and conditioned.*

### Refinement Analysis

#### **Strengths of Current Definitions**:
- **Clear Functional Distinction**: Context is passive viewport, working memory is active system
- **Temporal Characterization**: Context is ephemeral, working memory is continuous
- **Control Dimension**: Context is contingent, working memory is guided
- **Elegant Contrasts**: Specious vs. guided, ephemeral vs. continuous, contingent vs. conditioned

#### **Potential Refinements**:

**Enhanced Context Definition**:
> **Context**: The complete set of information accessible within an agent's processing window at a given moment, including all files, conversation history, and environmental state. Context is *stateless* (no memory between processing steps), *passive* (no selection mechanism), and *bounded* (limited by technical constraints rather than relevance).

**Enhanced Working Memory Definition**:
> **Working Memory**: An active cognitive system that selectively maintains, manipulates, and retrieves task-relevant information across processing steps. Working memory is *stateful* (preserves information over time), *selective* (filters based on relevance), and *adaptive* (adjusts to task demands rather than technical limits).

### **Operational Measurement Implications**:

| Dimension | Context | Working Memory |
|-----------|---------|----------------|
| **Information Selection** | All available data | Relevance-filtered subset |
| **Temporal Persistence** | Single processing step | Across task progression |
| **Capacity Limits** | Technical (token limits) | Cognitive (relevance limits) |
| **Update Mechanism** | Replace entirely | Selective update/integrate |
| **Organization** | Sequential/unstructured | Hierarchical/task-organized |

### **Measurement Operationalization**:

**Context System Indicators**:
- Information access follows availability, not relevance
- No persistence across processing boundaries
- Capacity failures at technical limits (token overflow)
- Uniform treatment of relevant and irrelevant information

**Working Memory System Indicators**:  
- Information access follows task relevance patterns
- Strategic information retention across steps
- Capacity management through intelligent compression
- Differential treatment based on task importance

---

## Task Complexity Space: Three-Dimensional Framework

### **Issue with Current Two-Dimensional Model**:

**Length × Depth** captures temporal and informational complexity but misses **structural complexity**:
- How many distinct semantic components must be coordinated?
- What is the interconnection pattern between components?
- How do we distinguish between "deep but simple" vs. "deep and compositionally complex" tasks?

### **Proposed Three-Dimensional Model**:

#### **Dimension 1: Task Length** (Temporal Complexity)
*Number of sequential checkpoints requiring memory persistence*

**What it tests**: Information retention over time, longitudinal coherence
**Working memory stress**: Can agent maintain state across extended sequences?
**Measurement**: Count of checkpoints in task progression

**Examples**:
- Short (2-4 checkpoints): Basic function → Integration
- Medium (5-8 checkpoints): Multi-component system development  
- Long (9+ checkpoints): Complex application with multiple subsystems

#### **Dimension 2: Task Depth** (Informational Complexity)
*Average information density per checkpoint specification*

**What it tests**: Information filtering and focus under noise
**Working memory stress**: Can agent extract relevant signals from complex specifications?
**Measurement**: Average tokens per checkpoint requirement, distractor file count

**Examples**:
- Shallow (100-200 tokens): Simple, clear requirements
- Medium (200-400 tokens): Detailed specifications with context
- Deep (400+ tokens): Complex requirements with multiple constraints and examples

#### **Dimension 3: Task Composition** (Structural Complexity)
*Number of distinct semantic components and their interconnection density*

**What it tests**: Multi-component coordination and integration management
**Working memory stress**: Can agent track relationships between multiple interacting parts?

### **Task Composition Measurement Framework**:

#### **Semantic Component Definition**:
A **semantic component** is a distinct functional unit that:
1. Has clear functional boundaries (authentication, data storage, API endpoint)
2. Can be implemented independently but requires integration
3. Has explicit dependencies on other components
4. Contributes unique functionality to overall system

#### **Composition Metrics**:

**Component Count (C)**: Number of distinct semantic components
```python
# Example: User Management API
components = [
    "User Data Model",           # Data structure
    "Password Authentication",    # Security component  
    "User Repository",           # Data access
    "Authentication Service",    # Business logic
    "REST API Endpoints",        # Interface layer
    "Session Management",        # State management
    "Admin Features"             # Authorization component
]
# Component Count = 7
```

**Integration Density (I)**: Average number of dependencies per component
```python
# Dependency mapping
dependencies = {
    "User Data Model": [],                                    # 0 deps
    "Password Authentication": ["User Data Model"],           # 1 dep
    "User Repository": ["User Data Model"],                   # 1 dep  
    "Authentication Service": ["User Data Model", "Password Authentication", "User Repository"], # 3 deps
    "REST API Endpoints": ["Authentication Service"],         # 1 dep
    "Session Management": ["Authentication Service"],         # 1 dep
    "Admin Features": ["REST API Endpoints", "Session Management"] # 2 deps
}
# Integration Density = (0+1+1+3+1+1+2)/7 = 1.29
```

**Composition Score**: C × I (total coordination burden)
```python
# Composition Score = 7 × 1.29 = 9.03
```

### **Three-Dimensional Complexity Examples**:

#### **Simple Task**: Calculator API
- **Length**: 3 checkpoints
- **Depth**: 150 tokens average  
- **Composition**: 3 components, 0.67 integration density
- **Profile**: Low temporal, low informational, low structural complexity

#### **Medium Task**: User Management API  
- **Length**: 7 checkpoints
- **Depth**: 280 tokens average
- **Composition**: 7 components, 1.29 integration density  
- **Profile**: Medium temporal, medium informational, medium structural complexity

#### **Complex Task**: Microservice Integration
- **Length**: 15 checkpoints
- **Depth**: 450 tokens average
- **Composition**: 12 components, 2.1 integration density
- **Profile**: High temporal, high informational, high structural complexity

### **Working Memory Pillar Mapping**:

**Length → Memory Fidelity**: Longitudinal information retention
**Depth → Contextual Relevance**: Information filtering and signal extraction  
**Composition → Behavioral Integrity**: Multi-component coordination and integration

### **Relevance Determination in Task Space**

#### **Component-Based Relevance Model**:

**For any given checkpoint, relevant information includes**:
1. **Direct Dependencies**: Components explicitly required by current checkpoint
2. **Transitive Dependencies**: Components required by direct dependencies  
3. **Integration Context**: Shared interfaces and contracts between components
4. **System Constraints**: Global requirements that affect component implementation

#### **Algorithmic Relevance Calculation**:
```python
def calculate_relevant_files(checkpoint, task_spec):
    relevant = set()
    
    # Direct checkpoint requirements
    relevant.add(checkpoint.stub_file)
    relevant.add(checkpoint.test_file)
    
    # Component dependencies
    for dep_id in checkpoint.dependencies:
        dep_checkpoint = find_checkpoint(dep_id)
        relevant.add(dep_checkpoint.stub_file)
        
        # Transitive dependencies  
        for transitive_dep in dep_checkpoint.dependencies:
            trans_checkpoint = find_checkpoint(transitive_dep)
            relevant.add(trans_checkpoint.stub_file)
    
    # Integration interfaces
    for component in get_related_components(checkpoint.component_id):
        relevant.add(component.interface_file)
    
    # System-level requirements
    relevant.update(["requirements.txt", "README.md", "config/"])
    
    return relevant

def calculate_relevance_score(accessed_files, relevant_files, distractor_files):
    """Enhanced relevance calculation using composition structure"""
    
    relevant_accessed = len(accessed_files & relevant_files)
    irrelevant_accessed = len(accessed_files & distractor_files)
    total_accessed = len(accessed_files)
    
    if total_accessed == 0:
        return 1.0
    
    # Precision: How much of what you accessed was relevant?
    precision = relevant_accessed / total_accessed
    
    # Recall: How much of what you needed did you access?
    recall = relevant_accessed / len(relevant_files)
    
    # F1 with penalty for distractor access
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    distractor_penalty = irrelevant_accessed / total_accessed
    
    return f1 * (1 - distractor_penalty)
```

### **Task Design Implications**:

#### **Complexity Scaling Strategy**:
```python
# Systematic difficulty progression
tasks = [
    # Beginner: Low all dimensions
    {"length": 3, "depth": 150, "composition": 2.0},
    
    # Intermediate: Scale one dimension
    {"length": 7, "depth": 150, "composition": 2.0},  # Temporal stress
    {"length": 3, "depth": 400, "composition": 2.0},  # Informational stress  
    {"length": 3, "depth": 150, "composition": 8.0},  # Structural stress
    
    # Advanced: Scale multiple dimensions
    {"length": 7, "depth": 400, "composition": 5.0},  # Combined stress
    
    # Expert: High all dimensions  
    {"length": 12, "depth": 500, "composition": 12.0}  # Maximum stress
]
```

#### **Diagnostic Power Enhancement**:
Three dimensions enable more precise failure mode identification:
- **High Length failures**: Memory fidelity problems (can't retain over time)
- **High Depth failures**: Contextual relevance problems (can't filter information)
- **High Composition failures**: Behavioral integrity problems (can't coordinate components)

This three-dimensional framework provides much more precise control over working memory stress patterns and enables systematic investigation of how different aspects of complexity affect agent performance.

---

## Validation Framework for Enhanced Definitions

### **Context vs. Working Memory Distinction Validation**:

1. **Controlled Experiment**: Same agent, same task, with and without explicit memory system
2. **Expected Result**: Working memory system should show better relevance scores, lower reread rates
3. **Measurement**: Compare behavioral patterns using operational definitions

### **Three-Dimensional Complexity Validation**:

1. **Dimension Independence**: Tasks high in one dimension, low in others should show specific failure patterns
2. **Additive Effects**: Tasks high in multiple dimensions should show multiplicative difficulty increases  
3. **Pillar Mapping**: Each dimension should primarily stress its predicted working memory pillar

This enhanced framework provides the theoretical precision needed for rigorous academic publication and practical implementation.