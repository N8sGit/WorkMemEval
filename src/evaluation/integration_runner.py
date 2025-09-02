"""
Integration Runner for Compact Recording

Integrates the compact recording system with the main evaluation pipeline
to ensure results are properly written to evaluation_runs.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from .compact_recording import CompactRecorder
from .recording_pipeline import EvaluationRecorder
from .optimized_metrics import OptimizedMetricsCalculator


class CompactEvaluationRunner:
    """Runner that integrates compact recording with evaluation pipeline"""
    
    def __init__(self, base_path: str = "evaluation_runs"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        self.recorder = EvaluationRecorder(base_path=str(self.base_path))
        self.compact_recorder = CompactRecorder()
        self.metrics_calculator = OptimizedMetricsCalculator()
    
    def run_evaluation(self, task_id: str, agent_name: str, 
                      task_result: Dict[str, Any], 
                      recording_mode: str = "compact") -> str:
        """Run evaluation and save results to evaluation_runs"""
        
        # Ensure directory structure exists
        task_dir = self.base_path / task_id
        task_dir.mkdir(exist_ok=True)
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        filename = f"{timestamp}.json"
        filepath = task_dir / filename
        
        # Record based on mode
        if recording_mode == "compact":
            compact_eval = self.compact_recorder.compact_evaluation(task_result)
            self.compact_recorder.save_compact(compact_eval, str(filepath))
        elif recording_mode == "legacy":
            with open(filepath, 'w') as f:
                json.dump(task_result, f, indent=2)
        elif recording_mode == "both":
            # Save both formats
            compact_eval = self.compact_recorder.compact_evaluation(task_result)
            
            # Compact format
            compact_path = task_dir / f"{timestamp}_compact.json"
            self.compact_recorder.save_compact(compact_eval, str(compact_path))
            
            # Legacy format
            with open(filepath, 'w') as f:
                json.dump(task_result, f, indent=2)
        
        return str(filepath)
    
    def create_sample_evaluation(self, task_id: str = "sample_task") -> Dict[str, Any]:
        """Create a sample evaluation for testing"""
        
        return {
            'task_id': task_id,
            'agent_name': 'test_agent',
            'memory_system_name': 'test_memory',
            'task_completed_successfully': True,
            'execution_time_seconds': 45.2,
            'timestamp': datetime.now().timestamp(),
            'task_trace': {
                'total_duration_ms': 45200,
                'summary_statistics': {
                    'total_actions': 15,
                    'unique_files_accessed': 3,
                    'overall_error_rate': 0.1
                }
            },
            'checkpoint_results': [
                {
                    'checkpoint_id': 'cp1',
                    'completed_successfully': True,
                    'execution_time_seconds': 20.1,
                    'actions_taken': 8,
                    'files_accessed': ['src/main.py', 'src/utils.py'],
                    'errors_encountered': []
                },
                {
                    'checkpoint_id': 'cp2',
                    'completed_successfully': True,
                    'execution_time_seconds': 25.1,
                    'actions_taken': 7,
                    'files_accessed': ['src/utils.py', 'src/config.py'],
                    'errors_encountered': ['ImportError: No module named config']
                }
            ],
            'working_memory_metrics': {
                'memory_fidelity': 0.85,
                'contextual_relevance': 0.92,
                'behavioral_integrity': 0.78
            }
        }
    
    def test_integration(self) -> Dict[str, str]:
        """Test the integration with actual file creation"""
        
        # Create sample evaluation
        sample_eval = self.create_sample_evaluation("integration_test")
        
        # Test different recording modes
        results = {}
        
        # Compact mode
        compact_path = self.run_evaluation(
            "test_task", "test_agent", sample_eval, "compact"
        )
        results['compact'] = compact_path
        
        # Legacy mode
        legacy_path = self.run_evaluation(
            "test_task", "test_agent", sample_eval, "legacy"
        )
        results['legacy'] = legacy_path
        
        # Both modes
        both_path = self.run_evaluation(
            "test_task", "test_agent", sample_eval, "both"
        )
        results['both'] = both_path
        
        return results
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics for evaluation_runs directory"""
        
        if not self.base_path.exists():
            return {'empty': True}
        
        total_files = 0
        total_size = 0
        file_types = {}
        
        for file_path in self.base_path.rglob("*.json"):
            total_files += 1
            file_size = file_path.stat().st_size
            total_size += file_size
            
            file_type = "legacy"
            if "_compact" in str(file_path):
                file_type = "compact"
            
            file_types[file_type] = file_types.get(file_type, 0) + 1
        
        return {
            'total_files': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'file_types': file_types,
            'directory': str(self.base_path)
        }
    
    def cleanup_test_files(self):
        """Clean up test files"""
        
        test_dirs = ["test_task", "integration_test", "sample_task"]
        
        for test_dir in test_dirs:
            dir_path = self.base_path / test_dir
            if dir_path.exists():
                for file_path in dir_path.rglob("*.json"):
                    file_path.unlink()
                dir_path.rmdir()


# CLI interface for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test compact recording integration")
    parser.add_argument("--mode", choices=["compact", "legacy", "both"], 
                       default="compact", help="Recording mode")
    parser.add_argument("--test", action="store_true", 
                       help="Run integration test")
    
    args = parser.parse_args()
    
    runner = CompactEvaluationRunner()
    
    if args.test:
        print("Running integration test...")
        results = runner.test_integration()
        
        for mode, path in results.items():
            print(f"✓ {mode}: {path}")
            if Path(path).exists():
                size = Path(path).stat().st_size
                print(f"  Size: {size} bytes")
        
        stats = runner.get_storage_stats()
        print(f"\nStorage stats: {stats}")
    else:
        # Create single test evaluation
        sample_eval = runner.create_sample_evaluation()
        result_path = runner.run_evaluation("demo", "demo_agent", sample_eval, args.mode)
        print(f"✓ Created: {result_path}")
        
        if Path(result_path).exists():
            size = Path(result_path).stat().st_size
            print(f"  Size: {size} bytes")
