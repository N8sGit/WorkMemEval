# WorkMemEval Documentation

## Overview

WorkMemEval is a minimal, test-oriented evaluation harness for working-memory research in AI agents. This documentation covers the complete system architecture, from basic usage to advanced research capabilities.

## Documentation Structure

### Core Architecture
- **[Tiered Complexity Architecture](tiered_complexity_architecture.md)** - Three-tier system design and rationale
- **[Enhanced Evaluation System](enhanced_evaluation_system.md)** - Advanced memory evaluation capabilities
- **[Memory Probe Framework](memory_probe_framework.md)** - Systematic memory assessment through controlled challenges

### Task and Complexity Analysis
- **[Task Complexity Measurement](task_complexity_measurement.md)** - Three-dimensional complexity analysis framework

## Quick Start Guide

### Basic Usage (Tier 1)
```python
from src.evaluation.runner import BasicWorkMemEvalRunner

# Simple evaluation - identical to original system
runner = BasicWorkMemEvalRunner()
result = await runner.run_evaluation(task_path, agent, memory_system)
```

### Enhanced Evaluation (Tier 2)
```python
# Enhanced evaluation with memory probes and context management
runner = BasicWorkMemEvalRunner(
    enable_enhanced_evaluation=True,
    context_condition="standardized"
)
result = await runner.run_evaluation(task_path, agent, memory_system)

# Access enhanced metrics
pillar_scores = result.enhanced_metrics["three_pillar_scores"]
context_analysis = result.enhanced_metrics["context_window_analysis"]
```

## Key Features

### Three-Pillar Memory Evaluation
- **Memory Fidelity**: Information retention and compression effectiveness
- **Contextual Relevance**: Signal vs. noise filtering and attention management  
- **Behavioral Integrity**: State coherence and robustness under stress

### Context Window Management
- **Standardized Condition**: Fixed 8K context for fair comparison
- **Native Condition**: Agent's natural context capacity
- **Overflow Condition**: Forced overflow to stress memory systems

### Memory Probe System
- **6 Probe Types** across 3 memory pillars
- **Intelligent Scheduling** based on memory pressure analysis
- **Natural Integration** within task execution flow
- **Objective Scoring** through measurable criteria

### Progressive Complexity
- **Tier 1**: Zero complexity increase for existing users
- **Tier 2**: Research-grade capabilities with minimal configuration
- **Tier 3**: Complete framework control (future)

## Architecture Principles

### Backward Compatibility
- 100% compatibility with existing tasks, agents, and memory systems
- Zero performance impact when enhanced features disabled
- Identical API surface for basic usage

### Progressive Disclosure
- Advanced features revealed only when needed
- Intelligent defaults minimize configuration burden
- Clear upgrade path from basic to advanced usage

### Research Enablement
- Sophisticated memory evaluation capabilities
- Objective, measurable assessment criteria
- Comprehensive metrics and analysis tools

## System Components

### Core Evaluation Engine
```
BasicWorkMemEvalRunner
├── TaskSpecificationLoader
├── PytestRunner / DockerTestRunner
├── FileSystemWatcher
└── ActionTracer
```

### Enhanced Evaluation Components
```
Enhanced Pipeline (Tier 2)
├── ContextWindowManager
│   ├── Context Usage Monitoring
│   ├── Compression Event Management
│   └── Efficiency Analysis
├── ProbeScheduler
│   ├── Intelligent Probe Scheduling
│   ├── Interference Detection
│   └── Response Collection
└── Enhanced Metrics Collection
    ├── Three-Pillar Scoring
    ├── Context Analytics
    └── Behavioral Analysis
```

## Usage Patterns

### Educational and Basic Research
```python
# Teaching working memory concepts
runner = BasicWorkMemEvalRunner()
result = await runner.run_evaluation("tasks/simple_calculator.json", 
                                   student_agent, basic_memory)
```

### Comparative Memory System Research
```python
# Comparing memory systems under controlled conditions
runner = BasicWorkMemEvalRunner(enable_enhanced_evaluation=True)

for memory_system in [contextual_memory, episodic_memory, hybrid_memory]:
    result = await runner.run_evaluation("tasks/complex_api.json",
                                       research_agent, memory_system,
                                       context_condition="standardized")
    # Analyze three-pillar scores for comparison
```

### Memory System Stress Testing
```python
# Testing robustness under overflow conditions
runner = BasicWorkMemEvalRunner(
    enable_enhanced_evaluation=True,
    context_condition="overflow"
)
result = await runner.run_evaluation("tasks/integration_challenge.json",
                                   test_agent, memory_system_under_test)
```

## Research Applications

### Memory System Development
- Evaluate memory system effectiveness across three pillars
- Identify strengths and weaknesses in memory architectures
- Compare compression and retention strategies

### Agent Architecture Research
- Assess working memory capabilities of different agent designs
- Study context management strategies
- Evaluate robustness under memory pressure

### Cognitive Architecture Studies
- Model human-like working memory limitations
- Study attention and filtering mechanisms
- Research context switching and interruption recovery

## Performance Characteristics

### Tier 1 (Basic Usage)
- **Overhead**: Zero additional overhead
- **Memory**: Identical to original system
- **Execution Time**: No measurable difference

### Tier 2 (Enhanced Evaluation)
- **Overhead**: Minimal (~5-10% execution time increase)
- **Memory**: ~2-3MB additional per evaluation
- **Execution Time**: Probe injection adds controlled delays

## Future Roadmap

### Tier 3 Development (Advanced Usage)
- Custom probe development framework
- Advanced injection strategies
- Multi-condition evaluation orchestration
- Research template system

### Research Platform Integration
- Memory system comparison benchmarks
- Advanced analytics and visualization
- Integration with external research tools
- Publication-ready result export

## Getting Started

1. **Basic Usage**: Start with existing WorkMemEval functionality
2. **Enhanced Evaluation**: Add `enable_enhanced_evaluation=True` flag
3. **Research Applications**: Explore three-pillar metrics and context conditions
4. **Advanced Features**: Await Tier 3 development for complete customization

## Contributing

The WorkMemEval framework is designed for extensibility and research collaboration. Key extension points include:

- Custom memory probe development
- Enhanced metrics and analysis algorithms
- Context management strategies
- Research template creation

For detailed implementation guidance, see the individual documentation files for each system component.

## Support and Community

WorkMemEval is built for the research community with emphasis on:
- Clear, comprehensive documentation
- Reproducible evaluation protocols
- Open architecture for extension and customization
- Research-grade reliability and validity

The tiered architecture ensures that researchers can engage with the framework at their appropriate level while providing clear paths for capability growth as research needs evolve.