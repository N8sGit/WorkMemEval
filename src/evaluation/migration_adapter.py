"""
Backward Compatibility Adapter

Provides seamless migration from legacy evaluation format to compact format
while maintaining compatibility with existing analysis tools.
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
from datetime import datetime

from .compact_recording import CompactEvaluation, CompactRecorder
from .optimized_metrics import OptimizedMetricsCalculator


class LegacyAdapter:
    """Adapter for backward compatibility with legacy evaluation format"""
    
    def __init__(self, legacy_base_path: str = "evaluation_runs"):
        self.legacy_base_path = Path(legacy_base_path)
        self.compact_recorder = CompactRecorder()
        self.metrics_calculator = OptimizedMetricsCalculator()
        self.logger = logging.getLogger(__name__)
    
    def migrate_legacy_to_compact(self, legacy_file: str, output_path: Optional[str] = None) -> str:
        """Migrate legacy evaluation file to compact format"""
        
        # Load legacy format
        with open(legacy_file, 'r') as f:
            legacy_data = json.load(f)
        
        # Convert to compact format
        compact = self.compact_recorder.compact_evaluation(legacy_data)
        
        # Determine output path
        if output_path is None:
            legacy_path = Path(legacy_file)
            output_path = str(legacy_path.parent / f"{legacy_path.stem}_compact.json")
        
        # Save compact format
        self.compact_recorder.save_compact(compact, output_path)
        
        self.logger.info(f"Migrated {legacy_file} → {output_path}")
        return output_path
    
    def batch_migrate_directory(self, directory: str, dry_run: bool = False) -> Dict[str, Any]:
        """Batch migrate legacy files in directory"""
        
        legacy_files = list(Path(directory).glob("**/*.json"))
        migrated_files = []
        skipped_files = []
        
        for legacy_file in legacy_files:
            try:
                # Skip already compact files
                if "_compact" in str(legacy_file):
                    skipped_files.append(str(legacy_file))
                    continue
                
                if not dry_run:
                    compact_path = self.migrate_legacy_to_compact(str(legacy_file))
                    migrated_files.append(compact_path)
                else:
                    migrated_files.append(str(legacy_file))
                    
            except Exception as e:
                self.logger.error(f"Failed to migrate {legacy_file}: {e}")
                skipped_files.append(str(legacy_file))
        
        return {
            'migrated': migrated_files,
            'skipped': skipped_files,
            'total_processed': len(legacy_files),
            'migration_success_rate': len(migrated_files) / len(legacy_files)
        }
    
    def legacy_format_reader(self, compact_file: str) -> Dict[str, Any]:
        """Read compact file and return legacy-compatible format"""
        
        # Load compact evaluation
        compact = self.compact_recorder.load_compact(compact_file)
        
        # Convert to legacy format
        legacy_format = self._compact_to_legacy(compact)
        
        return legacy_format
    
    def _compact_to_legacy(self, compact: CompactEvaluation) -> Dict[str, Any]:
        """Convert compact evaluation to legacy format"""
        
        # Build legacy-compatible structure
        legacy = {
            'task_id': compact.task_id,
            'agent_name': compact.agent,
            'memory_system_name': compact.memory_system,
            'task_completed_successfully': compact.success,
            'execution_time_seconds': compact.duration,
            'timestamp': datetime.now().timestamp(),
            'task_trace': self._build_legacy_task_trace(compact),
            'checkpoint_results': self._build_legacy_checkpoint_results(compact),
            'working_memory_metrics': self._build_legacy_metrics(compact),
            'summary_hash': compact.summary_hash
        }
        
        return legacy
    
    def _build_legacy_task_trace(self, compact: CompactEvaluation) -> Dict[str, Any]:
        """Build legacy task trace from compact data"""
        
        # Create minimal task trace structure
        task_trace = {
            'task_id': compact.task_id,
            'start_timestamp': datetime.now().timestamp(),
            'end_timestamp': datetime.now().timestamp() + compact.duration,
            'completed_successfully': compact.success,
            'total_duration_ms': compact.duration * 1000,
            'checkpoint_traces': [],
            'summary_statistics': {
                'total_actions': sum(cp.actions for cp in compact.checkpoints),
                'unique_files_accessed': len(set(
                    f for cp in compact.checkpoints 
                    for f in cp.files_accessed
                )),
                'overall_error_rate': sum(
                    len(cp.errors) for cp in compact.checkpoints
                ) / sum(cp.actions for cp in compact.checkpoints) if compact.checkpoints else 0.0
            }
        }
        
        # Build checkpoint traces
        for checkpoint in compact.checkpoints:
            checkpoint_trace = {
                'checkpoint_id': checkpoint.id,
                'start_timestamp': datetime.now().timestamp(),
                'end_timestamp': datetime.now().timestamp() + checkpoint.duration_ms/1000,
                'tests_passed': checkpoint.success,
                'completion_duration_ms': checkpoint.duration_ms,
                'actions': self._build_legacy_actions(checkpoint),
                'summary': {
                    'total_actions': checkpoint.actions,
                    'error_rate': len(checkpoint.errors) / checkpoint.actions if checkpoint.actions > 0 else 0.0,
                    'file_access_pattern': {
                        f: [datetime.now().timestamp()] for f in checkpoint.files_accessed
                    }
                }
            }
            task_trace['checkpoint_traces'].append(checkpoint_trace)
        
        return task_trace
    
    def _build_legacy_checkpoint_results(self, compact: CompactEvaluation) -> List[Dict[str, Any]]:
        """Build legacy checkpoint results"""
        
        results = []
        for checkpoint in compact.checkpoints:
            result = {
                'checkpoint_id': checkpoint.id,
                'completed_successfully': checkpoint.success,
                'execution_time_seconds': checkpoint.duration_ms / 1000,
                'tests_passed': checkpoint.success,
                'actions_taken': checkpoint.actions,
                'files_accessed': checkpoint.files_accessed,
                'errors_encountered': checkpoint.errors,
                'memory_usage_peak_mb': None,  # Not available in compact
                'llm_calls_made': None,  # Not available in compact
                'context_switches': None  # Not available in compact
            }
            results.append(result)
        
        return results
    
    def _build_legacy_metrics(self, compact: CompactEvaluation) -> Dict[str, Any]:
        """Build legacy working memory metrics"""
        
        return {
            'memory_fidelity': compact.metrics.get('memory_fidelity', 0.0),
            'contextual_relevance': compact.metrics.get('contextual_relevance', 0.0),
            'behavioral_integrity': compact.metrics.get('behavioral_integrity', 0.0),
            'context_reread_rate': self._calculate_reread_rate(compact),
            'error_rate': self._calculate_error_rate(compact),
            'file_reread_statistics': self._build_file_reread_stats(compact)
        }
    
    def _calculate_reread_rate(self, compact: CompactEvaluation) -> float:
        """Calculate reread rate for legacy format"""
        total_files = sum(len(cp.files_accessed) for cp in compact.checkpoints)
        total_rereads = sum(len(cp.files_reread) for cp in compact.checkpoints)
        
        return total_rereads / total_files if total_files > 0 else 0.0
    
    def _calculate_error_rate(self, compact: CompactEvaluation) -> float:
        """Calculate error rate for legacy format"""
        total_actions = sum(cp.actions for cp in compact.checkpoints)
        total_errors = sum(len(cp.errors) for cp in compact.checkpoints)
        
        return total_errors / total_actions if total_actions > 0 else 0.0
    
    def _build_file_reread_stats(self, compact: CompactEvaluation) -> Dict[str, Any]:
        """Build file reread statistics for legacy format"""
        
        all_accesses = []
        for checkpoint in compact.checkpoints:
            all_accesses.extend(checkpoint.files_accessed)
        
        unique_files = len(set(all_accesses))
        total_accesses = len(all_accesses)
        
        return {
            'total_file_accesses': total_accesses,
            'unique_files_accessed': unique_files,
            'unnecessary_rereads': total_accesses - unique_files,
            'reread_rate': (total_accesses - unique_files) / total_accesses if total_accesses > 0 else 0.0
        }
    
    def _build_legacy_actions(self, checkpoint) -> List[Dict[str, Any]]:
        """Build legacy action format"""
        
        # Create minimal action representations
        actions = []
        
        # Add checkpoint start
        actions.append({
            'timestamp': datetime.now().timestamp(),
            'action_type': 'checkpoint_start',
            'success': True,
            'checkpoint_id': checkpoint.id
        })
        
        # Add file operations
        for file_path in checkpoint.files_accessed:
            actions.append({
                'timestamp': datetime.now().timestamp(),
                'action_type': 'file_read',
                'success': True,
                'file_path': file_path
            })
        
        # Add errors
        for error in checkpoint.errors:
            actions.append({
                'timestamp': datetime.now().timestamp(),
                'action_type': 'error',
                'success': False,
                'metadata': {'error': error}
            })
        
        # Add checkpoint complete
        actions.append({
            'timestamp': datetime.now().timestamp(),
            'action_type': 'checkpoint_complete',
            'success': checkpoint.success,
            'checkpoint_id': checkpoint.id
        })
        
        return actions
    
    def validate_compatibility(self, legacy_file: str, compact_file: str) -> Dict[str, Any]:
        """Validate compatibility between legacy and compact formats"""
        
        # Load both formats
        with open(legacy_file, 'r') as f:
            legacy_data = json.load(f)
        
        compact_data = self.legacy_format_reader(compact_file)
        
        # Compare key metrics
        legacy_metrics = legacy_data.get('working_memory_metrics', {})
        compact_metrics = compact_data.get('working_memory_metrics', {})
        
        validation = {
            'metrics_match': {},
            'structure_valid': True,
            'errors': []
        }
        
        # Compare individual metrics
        for metric in ['memory_fidelity', 'contextual_relevance', 'behavioral_integrity']:
            legacy_val = legacy_metrics.get(metric, 0.0)
            compact_val = compact_metrics.get(metric, 0.0)
            
            # Allow small differences due to rounding/format
            matches = abs(legacy_val - compact_val) < 0.01
            validation['metrics_match'][metric] = {
                'legacy': legacy_val,
                'compact': compact_val,
                'matches': matches
            }
        
        # Check structure
        required_keys = ['task_id', 'agent_name', 'working_memory_metrics']
        for key in required_keys:
            if key not in compact_data:
                validation['structure_valid'] = False
                validation['errors'].append(f"Missing key: {key}")
        
        validation['overall_valid'] = all(
            m['matches'] for m in validation['metrics_match'].values()
        ) and validation['structure_valid']
        
        return validation
    
    def create_compatibility_report(self, directory: str) -> str:
        """Create compatibility report for directory"""
        
        report_path = Path(directory) / "compatibility_report.json"
        
        legacy_files = list(Path(directory).glob("**/*.json"))
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_files': len(legacy_files),
            'migration_status': {},
            'recommendations': []
        }
        
        for legacy_file in legacy_files:
            try:
                compact_file = self.migrate_legacy_to_compact(str(legacy_file))
                validation = self.validate_compatibility(str(legacy_file), compact_file)
                
                report['migration_status'][str(legacy_file)] = {
                    'migrated': True,
                    'validation': validation,
                    'compact_file': compact_file
                }
                
            except Exception as e:
                report['migration_status'][str(legacy_file)] = {
                    'migrated': False,
                    'error': str(e)
                }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return str(report_path)
