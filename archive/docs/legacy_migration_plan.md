# Legacy Migration Plan: Clean Separation Strategy

This document outlines the strategy for cleanly separating legacy and enhanced functionality in the WorkMemEval task specification system while maintaining full backward compatibility.

## Problem Statement

The current implementation mixes legacy and enhanced functionality within the same classes, creating:
- **Duplication**: Multiple complexity systems (TaskComplexityMetrics vs ThreeDimensionalComplexity)
- **Confusion**: Unclear which system to use for new development
- **Maintenance burden**: Two systems to maintain without clear boundaries
- **Migration complexity**: No clear path to eventually remove legacy code

## Solution: Loud Sectioning with Clear Boundaries

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    LEGACY SYSTEM                            │
│                 (DEPRECATED - DO NOT MODIFY)               │
├─────────────────────────────────────────────────────────────┤
│ • LegacyCheckpointSpecification                            │
│ • LegacyMemoryChallenge                                    │
│ • LegacyTaskComplexityMetrics                              │
│ • Type aliases for backward compatibility                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   ENHANCED SYSTEM                           │
│                  (NEW DEVELOPMENT)                          │
├─────────────────────────────────────────────────────────────┤
│ • MemoryProbe                                              │
│ • ContextWindowCondition                                   │
│ • EnhancedComplexityProfile                                │
│ • Research templates and configuration profiles            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  UNIFIED INTERFACE                          │
│                (BACKWARD COMPATIBLE)                        │
├─────────────────────────────────────────────────────────────┤
│ • TaskSpecification (dual-mode operation)                  │
│ • Automatic mode detection                                 │
│ • Migration utilities                                      │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Principles

### 1. Loud Sectioning
- **Clear visual separation** with prominent comment blocks
- **Explicit labeling** of legacy vs enhanced sections
- **Deprecation warnings** in legacy class docstrings
- **Usage guidance** directing developers to enhanced system

### 2. Zero Breaking Changes
- **Type aliases** maintain backward compatibility (`CheckpointSpecification = LegacyCheckpointSpecification`)
- **Existing APIs** work exactly as before
- **Legacy serialization** format fully supported
- **Gradual migration** path without forced upgrades

### 3. Clear Migration Path
- **Automatic detection** of legacy vs enhanced tasks
- **One-method migration** (`task.enable_enhanced_mode()`)
- **File-based migration** utilities
- **Safe excision** plan for future legacy removal

## Implementation Details

### Legacy System (Preserved)

```python
# =============================================================================
# LEGACY SYSTEM (PRESERVED FOR BACKWARD COMPATIBILITY)
# =============================================================================
# 
# This section contains the original WorkMemEval task specification system.
# These classes are preserved exactly as they were to ensure 100% backward
# compatibility. DO NOT MODIFY these classes - they will be deprecated in
# future versions once migration is complete.
#
# For new development, use the Enhanced System classes below.
# =============================================================================

@dataclass
class LegacyCheckpointSpecification:
    """
    LEGACY: Individual checkpoint within a WorkMemEval task.
    
    This is the original checkpoint specification. For new development,
    use EnhancedCheckpointSpecification instead.
    """
    # ... exact original implementation
```

### Enhanced System (New Development)

```python
# =============================================================================
# ENHANCED SYSTEM (NEW DEVELOPMENT)
# =============================================================================
#
# This section contains the enhanced WorkMemEval task specification system
# with memory probes, context conditions, and advanced complexity analysis.
# 
# Use these classes for all new development and research applications.
# =============================================================================

@dataclass
class MemoryProbe:
    """
    Enhanced memory probe specification for pillar-specific testing.
    """
    # ... new enhanced functionality
```

### Unified Interface (Backward Compatible)

```python
# =============================================================================
# UNIFIED INTERFACE (BACKWARD COMPATIBLE)
# =============================================================================
#
# This section provides a unified interface that maintains backward compatibility
# while enabling enhanced features. The main TaskSpecification class can operate
# in both legacy and enhanced modes.
# =============================================================================

# Type aliases for backward compatibility
CheckpointSpecification = LegacyCheckpointSpecification
MemoryChallenge = LegacyMemoryChallenge
TaskComplexityMetrics = LegacyTaskComplexityMetrics

@dataclass 
class TaskSpecification:
    """
    Unified WorkMemEval task specification with backward compatibility.
    
    This class operates in two modes:
    1. Legacy Mode: Uses original complexity system and memory challenges
    2. Enhanced Mode: Uses enhanced complexity analysis and memory probes
    
    Mode is automatically detected based on the presence of enhanced features.
    """
```

## Migration Strategy

### Phase 1: Immediate (Current)
- ✅ Create refactored implementation with clear separation
- ✅ Maintain 100% backward compatibility
- ✅ Provide migration utilities
- ✅ Update documentation with clear guidance

### Phase 2: Transition (Next 3-6 months)
- 🔄 Migrate existing tasks to enhanced format
- 🔄 Update all new development to use enhanced system
- 🔄 Add deprecation warnings to legacy classes
- 🔄 Create migration guides and examples

### Phase 3: Deprecation (6-12 months)
- ⏳ Mark legacy classes as deprecated
- ⏳ Add runtime warnings for legacy usage
- ⏳ Provide automated migration tools
- ⏳ Update all documentation to enhanced system

### Phase 4: Removal (12+ months)
- ❌ Remove legacy classes entirely
- ❌ Simplify codebase to enhanced system only
- ❌ Clean up type aliases and compatibility layers
- ❌ Final documentation cleanup

## Usage Guidance

### For Existing Code (Legacy Mode)
```python
# Existing code continues to work unchanged
task = TaskSpecification.load_from_file("existing_task.json")
# Uses legacy complexity system automatically
complexity = task.complexity  # Returns LegacyTaskComplexityMetrics
```

### For New Development (Enhanced Mode)
```python
# New development should use enhanced mode
task = TaskSpecification.load_from_file("existing_task.json")
enhanced_task = task.enable_enhanced_mode()
# Uses enhanced complexity system
complexity = enhanced_task.enhanced_complexity  # Returns EnhancedComplexityProfile
```

### For Migration
```python
# Migrate existing tasks
from src.core.task_specification_refactored import LegacyMigrationUtility

# File-based migration
LegacyMigrationUtility.migrate_file("old_task.json", "new_task.json")

# In-memory migration
legacy_task = TaskSpecification.load_from_file("old_task.json")
enhanced_task = legacy_task.enable_enhanced_mode()
```

## Benefits of This Approach

### 1. Clear Boundaries
- **No confusion** about which system to use
- **Explicit deprecation** path for legacy code
- **Clean separation** enables safe removal later

### 2. Zero Risk Migration
- **Existing code** continues to work unchanged
- **Gradual migration** at user's pace
- **Rollback capability** if issues arise

### 3. Maintainability
- **Single source of truth** for each system
- **Clear ownership** of legacy vs enhanced code
- **Simplified testing** with separate test suites

### 4. Future-Proof
- **Clean excision** path for legacy removal
- **No technical debt** accumulation
- **Simplified architecture** post-migration

## File Structure

```
src/core/
├── task_specification.py              # Current mixed implementation (to be replaced)
├── task_specification_refactored.py   # New clean implementation
└── task_specification_legacy.py       # Pure legacy implementation (future)

tests/
├── test_task_specification_legacy.py  # Legacy system tests
├── test_task_specification_enhanced.py # Enhanced system tests
└── test_task_specification_migration.py # Migration tests

docs/
├── legacy_migration_plan.md           # This document
├── enhanced_system_guide.md           # Enhanced system documentation
└── migration_examples.md              # Migration examples and tutorials
```

## Next Steps

1. **Replace current implementation** with refactored version
2. **Update all imports** to use new module
3. **Run comprehensive tests** to ensure backward compatibility
4. **Create migration examples** for common use cases
5. **Begin Phase 2** transition planning

This approach provides a clean, maintainable solution that eliminates confusion while preserving backward compatibility and enabling safe future removal of legacy code.