"""
YAML Task Loader with Comprehensive Validation

This module provides the TaskLoader class for loading and validating YAML task
configurations with detailed error reporting and schema validation.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import ValidationError

from .yaml_task_models import YAMLTaskSpecification, TaskValidationError


class TaskLoader:
    """
    Loads and validates YAML task configurations with comprehensive error handling.
    
    Provides detailed validation messages and supports both strict and permissive
    loading modes for different use cases.
    """
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize TaskLoader.
        
        Args:
            strict_mode: If True, reject tasks with any validation warnings.
                        If False, allow tasks with warnings but log them.
        """
        self.strict_mode = strict_mode
        self._validation_warnings: List[str] = []
    
    def load_task(self, yaml_path: Union[str, Path]) -> YAMLTaskSpecification:
        """
        Load and validate a YAML task configuration.
        
        Args:
            yaml_path: Path to the YAML task file
            
        Returns:
            Validated YAMLTaskSpecification instance
            
        Raises:
            TaskValidationError: If validation fails
            FileNotFoundError: If YAML file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        yaml_path = Path(yaml_path)
        
        if not yaml_path.exists():
            raise FileNotFoundError(f"Task file not found: {yaml_path}")
        
        if not yaml_path.suffix.lower() in ['.yaml', '.yml']:
            raise TaskValidationError(f"File must have .yaml or .yml extension: {yaml_path}")
        
        try:
            # Load YAML content
            with open(yaml_path, 'r', encoding='utf-8') as f:
                raw_data = yaml.safe_load(f)
            
            if raw_data is None:
                raise TaskValidationError(f"Empty YAML file: {yaml_path}")
            
            if not isinstance(raw_data, dict):
                raise TaskValidationError(f"YAML file must contain a dictionary, got {type(raw_data).__name__}")
            
            # Validate with Pydantic model
            task_spec = self._validate_task_data(raw_data, yaml_path)
            
            # Perform additional semantic validation
            self._perform_semantic_validation(task_spec, yaml_path)
            
            # Handle validation warnings
            if self._validation_warnings:
                if self.strict_mode:
                    raise TaskValidationError(
                        f"Task validation failed with warnings (strict mode enabled)",
                        {"warnings": self._validation_warnings}
                    )
                else:
                    # Log warnings but continue
                    print(f"Warning: Task {task_spec.task_id} has validation warnings:")
                    for warning in self._validation_warnings:
                        print(f"  - {warning}")
            
            return task_spec
            
        except yaml.YAMLError as e:
            raise TaskValidationError(f"YAML parsing error in {yaml_path}: {str(e)}")
        except ValidationError as e:
            # Convert Pydantic validation error to our custom error
            field_errors = {}
            for error in e.errors():
                field_path = '.'.join(str(loc) for loc in error['loc'])
                if field_path not in field_errors:
                    field_errors[field_path] = []
                field_errors[field_path].append(error['msg'])
            
            raise TaskValidationError(
                f"Task validation failed for {yaml_path}",
                field_errors
            )
    
    def _validate_task_data(self, raw_data: Dict[str, Any], yaml_path: Path) -> YAMLTaskSpecification:
        """
        Validate raw YAML data against Pydantic model.
        
        Args:
            raw_data: Raw YAML data as dictionary
            yaml_path: Path to YAML file (for error reporting)
            
        Returns:
            Validated YAMLTaskSpecification
            
        Raises:
            ValidationError: If Pydantic validation fails
        """
        # Pre-validation checks
        self._check_required_top_level_fields(raw_data, yaml_path)
        
        # Validate with Pydantic
        return YAMLTaskSpecification(**raw_data)
    
    def _check_required_top_level_fields(self, data: Dict[str, Any], yaml_path: Path) -> None:
        """Check for required top-level fields with helpful error messages."""
        required_fields = [
            'task_id', 'title', 'domain', 'difficulty', 
            'description', 'memory_dimensions', 'success_criteria'
        ]
        
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            raise TaskValidationError(
                f"Missing required fields in {yaml_path}: {', '.join(missing_fields)}\n"
                f"Required fields: {', '.join(required_fields)}"
            )
    
    def _perform_semantic_validation(self, task_spec: YAMLTaskSpecification, yaml_path: Path) -> None:
        """
        Perform additional semantic validation beyond Pydantic schema validation.
        
        Args:
            task_spec: Validated task specification
            yaml_path: Path to YAML file (for error reporting)
        """
        self._validation_warnings.clear()
        
        # Validate memory dimensions are realistic for domain
        self._validate_memory_dimensions_for_domain(task_spec)
        
        # Validate success criteria are measurable
        self._validate_success_criteria_measurability(task_spec)
        
        # Validate memory probe configuration
        self._validate_memory_probe_configuration(task_spec)
        
        # Validate task complexity coherence
        self._validate_task_complexity_coherence(task_spec)
        
        # Validate evaluation configuration
        self._validate_evaluation_configuration(task_spec)
    
    def _validate_memory_dimensions_for_domain(self, task_spec: YAMLTaskSpecification) -> None:
        """Validate memory dimensions are appropriate for the task domain."""
        dims = task_spec.memory_dimensions
        domain = task_spec.domain
        
        # Domain-specific validation rules
        domain_expectations = {
            'distributed_systems': {
                'min_info_density': 400,
                'min_temporal_span': 30,
                'min_dependency_depth': 3
            },
            'data_processing': {
                'min_info_density': 300,
                'min_temporal_span': 25,
                'min_dependency_depth': 2
            },
            'web_services': {
                'min_info_density': 250,
                'min_temporal_span': 20,
                'min_dependency_depth': 2
            },
            'security': {
                'min_info_density': 500,
                'min_temporal_span': 35,
                'min_dependency_depth': 3
            },
            'infrastructure': {
                'min_info_density': 350,
                'min_temporal_span': 30,
                'min_dependency_depth': 3
            }
        }
        
        if domain in domain_expectations:
            expectations = domain_expectations[domain]
            
            if dims.information_density < expectations['min_info_density']:
                self._validation_warnings.append(
                    f"Information density ({dims.information_density}) may be too low for {domain} domain "
                    f"(recommended minimum: {expectations['min_info_density']})"
                )
            
            if dims.temporal_span < expectations['min_temporal_span']:
                self._validation_warnings.append(
                    f"Temporal span ({dims.temporal_span}min) may be too short for {domain} domain "
                    f"(recommended minimum: {expectations['min_temporal_span']}min)"
                )
            
            if dims.dependency_depth < expectations['min_dependency_depth']:
                self._validation_warnings.append(
                    f"Dependency depth ({dims.dependency_depth}) may be too shallow for {domain} domain "
                    f"(recommended minimum: {expectations['min_dependency_depth']})"
                )
    
    def _validate_success_criteria_measurability(self, task_spec: YAMLTaskSpecification) -> None:
        """Validate that success criteria are objectively measurable."""
        measurable_indicators = [
            'pass', 'fail', 'correctly', 'successfully', 'must', 'should', 'will',
            'error', 'exception', 'timeout', 'performance', 'response time',
            'accuracy', 'precision', 'recall', 'coverage', 'compliance'
        ]
        
        subjective_words = [
            'good', 'bad', 'nice', 'clean', 'elegant', 'beautiful', 'ugly',
            'reasonable', 'appropriate', 'suitable', 'adequate'
        ]
        
        for i, criterion in enumerate(task_spec.success_criteria):
            criterion_lower = criterion.lower()
            
            # Check for measurable indicators
            has_measurable = any(indicator in criterion_lower for indicator in measurable_indicators)
            has_subjective = any(word in criterion_lower for word in subjective_words)
            
            if not has_measurable:
                self._validation_warnings.append(
                    f"Success criterion {i+1} may not be objectively measurable: '{criterion}'"
                )
            
            if has_subjective:
                self._validation_warnings.append(
                    f"Success criterion {i+1} contains subjective language: '{criterion}'"
                )
    
    def _validate_memory_probe_configuration(self, task_spec: YAMLTaskSpecification) -> None:
        """Validate memory probe configuration is sensible."""
        if not task_spec.memory_probes:
            return
        
        probes = task_spec.memory_probes
        max_duration = task_spec.evaluation_config.max_duration_minutes
        
        # Check probe distribution
        trigger_times = sorted([probe.trigger_at_minute for probe in probes])
        
        # Warn if probes are too early (before agent has context)
        early_probes = [t for t in trigger_times if t < 10]
        if early_probes:
            self._validation_warnings.append(
                f"Memory probes triggered very early ({early_probes}) may not be effective "
                f"before agent builds sufficient context"
            )
        
        # Warn if probes are too clustered
        for i in range(1, len(trigger_times)):
            if trigger_times[i] - trigger_times[i-1] < 5:
                self._validation_warnings.append(
                    f"Memory probes at {trigger_times[i-1]}min and {trigger_times[i]}min "
                    f"are too close together (minimum 5min spacing recommended)"
                )
        
        # Check probe types are diverse
        probe_types = [probe.type for probe in probes]
        if len(set(probe_types)) == 1 and len(probe_types) > 1:
            self._validation_warnings.append(
                f"All memory probes use the same type ({probe_types[0]}) - "
                f"consider diversifying probe types for comprehensive evaluation"
            )
    
    def _validate_task_complexity_coherence(self, task_spec: YAMLTaskSpecification) -> None:
        """Validate that task complexity dimensions are coherent."""
        dims = task_spec.memory_dimensions
        difficulty = task_spec.difficulty
        
        # Expected complexity ranges by difficulty
        complexity_ranges = {
            'beginner': {
                'info_density': (100, 400),
                'temporal_span': (10, 30),
                'context_switches': (0, 2),
                'dependency_depth': (1, 2)
            },
            'intermediate': {
                'info_density': (300, 800),
                'temporal_span': (20, 60),
                'context_switches': (1, 4),
                'dependency_depth': (2, 4)
            },
            'advanced': {
                'info_density': (600, 1200),
                'temporal_span': (45, 120),
                'context_switches': (3, 6),
                'dependency_depth': (3, 6)
            },
            'expert': {
                'info_density': (1000, 2000),
                'temporal_span': (90, 180),
                'context_switches': (4, 10),
                'dependency_depth': (4, 8)
            }
        }
        
        if difficulty in complexity_ranges:
            ranges = complexity_ranges[difficulty]
            
            # Check each dimension
            if not (ranges['info_density'][0] <= dims.information_density <= ranges['info_density'][1]):
                self._validation_warnings.append(
                    f"Information density ({dims.information_density}) may not match {difficulty} difficulty "
                    f"(expected range: {ranges['info_density'][0]}-{ranges['info_density'][1]})"
                )
            
            if not (ranges['temporal_span'][0] <= dims.temporal_span <= ranges['temporal_span'][1]):
                self._validation_warnings.append(
                    f"Temporal span ({dims.temporal_span}min) may not match {difficulty} difficulty "
                    f"(expected range: {ranges['temporal_span'][0]}-{ranges['temporal_span'][1]}min)"
                )
    
    def _validate_evaluation_configuration(self, task_spec: YAMLTaskSpecification) -> None:
        """Validate evaluation configuration is sensible."""
        eval_config = task_spec.evaluation_config
        dims = task_spec.memory_dimensions
        
        # Check duration vs temporal span
        if eval_config.max_duration_minutes < dims.temporal_span * 1.2:
            self._validation_warnings.append(
                f"Max duration ({eval_config.max_duration_minutes}min) should be at least 20% longer "
                f"than temporal span ({dims.temporal_span}min) to allow for completion"
            )
        
        # Check context window limit is reasonable
        if eval_config.context_window_limit:
            if eval_config.context_window_limit < dims.information_density * 2:
                self._validation_warnings.append(
                    f"Context window limit ({eval_config.context_window_limit} tokens) may be too small "
                    f"for information density ({dims.information_density} tokens)"
                )
    
    def validate_task_library(self, library_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Validate an entire task library directory.
        
        Args:
            library_path: Path to directory containing YAML task files
            
        Returns:
            Dictionary with validation results for each task
        """
        library_path = Path(library_path)
        
        if not library_path.exists():
            raise FileNotFoundError(f"Task library directory not found: {library_path}")
        
        results = {
            'valid_tasks': [],
            'invalid_tasks': [],
            'warnings': [],
            'summary': {}
        }
        
        # Find all YAML files
        yaml_files = list(library_path.rglob('*.yaml')) + list(library_path.rglob('*.yml'))
        
        for yaml_file in yaml_files:
            try:
                task_spec = self.load_task(yaml_file)
                results['valid_tasks'].append({
                    'file': str(yaml_file.relative_to(library_path)),
                    'task_id': task_spec.task_id,
                    'title': task_spec.title,
                    'domain': task_spec.domain,
                    'difficulty': task_spec.difficulty
                })
                
                if self._validation_warnings:
                    results['warnings'].append({
                        'file': str(yaml_file.relative_to(library_path)),
                        'task_id': task_spec.task_id,
                        'warnings': self._validation_warnings.copy()
                    })
                
            except (TaskValidationError, FileNotFoundError, yaml.YAMLError) as e:
                results['invalid_tasks'].append({
                    'file': str(yaml_file.relative_to(library_path)),
                    'error': str(e)
                })
        
        # Generate summary
        results['summary'] = {
            'total_files': len(yaml_files),
            'valid_tasks': len(results['valid_tasks']),
            'invalid_tasks': len(results['invalid_tasks']),
            'tasks_with_warnings': len(results['warnings']),
            'domains': list(set(task['domain'] for task in results['valid_tasks'])),
            'difficulties': list(set(task['difficulty'] for task in results['valid_tasks']))
        }
        
        return results
    
    def get_validation_warnings(self) -> List[str]:
        """Get validation warnings from the last load operation."""
        return self._validation_warnings.copy()
    
    def clear_warnings(self) -> None:
        """Clear accumulated validation warnings."""
        self._validation_warnings.clear()


def load_yaml_task(yaml_path: Union[str, Path], strict_mode: bool = True) -> YAMLTaskSpecification:
    """
    Convenience function to load a single YAML task.
    
    Args:
        yaml_path: Path to YAML task file
        strict_mode: Whether to use strict validation mode
        
    Returns:
        Validated YAMLTaskSpecification
        
    Raises:
        TaskValidationError: If validation fails
    """
    loader = TaskLoader(strict_mode=strict_mode)
    return loader.load_task(yaml_path)


def validate_yaml_task_library(library_path: Union[str, Path], strict_mode: bool = True) -> Dict[str, Any]:
    """
    Convenience function to validate an entire task library.
    
    Args:
        library_path: Path to task library directory
        strict_mode: Whether to use strict validation mode
        
    Returns:
        Dictionary with validation results
    """
    loader = TaskLoader(strict_mode=strict_mode)
    return loader.validate_task_library(library_path)