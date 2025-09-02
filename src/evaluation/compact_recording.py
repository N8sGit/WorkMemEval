"""
Compact Evaluation Recording System

Provides efficient recording of evaluation results with minimal storage overhead
while preserving all essential data for working memory analysis.
"""

import json
import zlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib


@dataclass
class CompactAction:
    """Minimal action representation"""
    type: str
    success: bool
    file_path: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CompactCheckpoint:
    """Essential checkpoint data"""
    id: str
    success: bool
    duration_ms: float
    actions: int
    files_accessed: List[str]
    files_reread: List[str]  # Files accessed in previous checkpoints
    errors: List[str]
    memory_score: Dict[str, float]  # Per-checkpoint metrics


@dataclass
class CompactEvaluation:
    """Minimal evaluation result"""
    task_id: str
    agent: str
    memory_system: str
    success: bool
    duration: float
    checkpoints: List[CompactCheckpoint]
    metrics: Dict[str, float]  # Three-pillar scores
    summary_hash: str  # Integrity check
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompactEvaluation':
        """Restore from dictionary"""
        return cls(**data)


class CompactRecorder:
    """Efficient evaluation recording system"""
    
    def __init__(self, compression_level: int = 6):
        self.compression_level = compression_level
        self.file_cache = {}  # Deduplicate file paths
        self.error_cache = {}  # Deduplicate error messages
    
    def compact_evaluation(self, full_result: Dict[str, Any]) -> CompactEvaluation:
        """Convert full evaluation to compact format"""
        
        # Extract essential data only
        task_trace = full_result.get('task_trace', {})
        checkpoint_results = full_result.get('checkpoint_results', [])
        
        # Build compact checkpoints
        compact_checkpoints = []
        previous_files = set()
        
        for i, (cp_trace, cp_result) in enumerate(zip(
            task_trace.get('checkpoint_traces', []),
            checkpoint_results
        )):
            cp_id = cp_trace.get('checkpoint_id', f'cp{i+1}')
            
            # Extract file access patterns
            files_accessed = list(set(cp_result.get('files_accessed', [])))
            files_reread = [f for f in files_accessed if f in previous_files]
            
            # Deduplicate errors
            errors = self._deduplicate_errors(cp_result.get('errors_encountered', []))
            
            # Calculate per-checkpoint memory score
            memory_score = self._calculate_checkpoint_memory_score(cp_trace)
            
            compact_checkpoint = CompactCheckpoint(
                id=cp_id,
                success=cp_result.get('completed_successfully', False),
                duration_ms=cp_result.get('execution_time_seconds', 0) * 1000,
                actions=len(cp_trace.get('actions', [])),
                files_accessed=files_accessed,
                files_reread=files_reread,
                errors=errors,
                memory_score=memory_score
            )
            
            compact_checkpoints.append(compact_checkpoint)
            previous_files.update(files_accessed)
        
        # Create compact evaluation
        compact = CompactEvaluation(
            task_id=full_result.get('task_id', 'unknown'),
            agent=full_result.get('agent_name', 'unknown'),
            memory_system=full_result.get('memory_system_name', 'unknown'),
            success=full_result.get('task_completed_successfully', False),
            duration=full_result.get('execution_time_seconds', 0),
            checkpoints=compact_checkpoints,
            metrics=self._extract_metrics(full_result),
            summary_hash=self._generate_summary_hash(full_result)
        )
        
        return compact
    
    def _deduplicate_errors(self, errors: List[str]) -> List[str]:
        """Deduplicate and categorize error messages"""
        if not errors:
            return []
        
        # Hash-based deduplication
        seen = set()
        deduped = []
        
        for error in errors:
            # Normalize error message (remove timestamps, paths)
            normalized = self._normalize_error(error)
            error_hash = hashlib.md5(normalized.encode()).hexdigest()[:8]
            
            if error_hash not in seen:
                seen.add(error_hash)
                deduped.append(normalized)
        
        return deduped
    
    def _normalize_error(self, error: str) -> str:
        """Normalize error message for deduplication"""
        # Remove timestamps, file paths, line numbers
        normalized = re.sub(r'/[^\s]+', '<PATH>', error)
        normalized = re.sub(r'\d+:\d+', '<LINE>', normalized)
        normalized = re.sub(r'\d{4}-\d{2}-\d{2}.*', '', normalized)
        return normalized.strip()
    
    def _calculate_checkpoint_memory_score(self, checkpoint_trace: Dict[str, Any]) -> Dict[str, float]:
        """Calculate per-checkpoint memory metrics"""
        actions = checkpoint_trace.get('actions', [])
        
        # Count file access patterns
        file_reads = [a for a in actions if a.get('action_type') == 'file_read']
        unique_files = len(set(a.get('file_path') for a in file_reads if a.get('file_path')))
        total_reads = len(file_reads)
        
        return {
            'reread_rate': (total_reads - unique_files) / total_reads if total_reads > 0 else 0,
            'error_rate': len([a for a in actions if not a.get('success', True)]) / len(actions) if actions else 0
        }
    
    def _extract_metrics(self, full_result: Dict[str, Any]) -> Dict[str, float]:
        """Extract three-pillar metrics"""
        working_memory = full_result.get('working_memory_metrics', {})
        
        return {
            'memory_fidelity': working_memory.get('memory_fidelity', 0.0),
            'contextual_relevance': working_memory.get('contextual_relevance', 0.0),
            'behavioral_integrity': working_memory.get('behavioral_integrity', 0.0)
        }
    
    def _generate_summary_hash(self, full_result: Dict[str, Any]) -> str:
        """Generate integrity hash for verification"""
        # Create hash from essential data
        essential_data = {
            'task_id': full_result.get('task_id'),
            'agent': full_result.get('agent_name'),
            'success': full_result.get('task_completed_successfully'),
            'checkpoints': len(full_result.get('checkpoint_results', [])),
            'total_actions': full_result.get('task_trace', {}).get('summary_statistics', {}).get('total_actions', 0)
        }
        
        return hashlib.md5(json.dumps(essential_data, sort_keys=True).encode()).hexdigest()
    
    def save_compact(self, compact: CompactEvaluation, filepath: str) -> None:
        """Save compact evaluation with optional compression"""
        data = compact.to_dict()
        
        # Optional compression
        json_str = json.dumps(data, separators=(',', ':'))
        
        if self.compression_level > 0:
            compressed = zlib.compress(json_str.encode(), self.compression_level)
            with open(filepath + '.gz', 'wb') as f:
                f.write(compressed)
        else:
            with open(filepath, 'w') as f:
                f.write(json_str)
    
    def load_compact(self, filepath: str) -> CompactEvaluation:
        """Load compact evaluation"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            # Try compressed format
            with open(filepath, 'rb') as f:
                compressed = f.read()
                json_str = zlib.decompress(compressed).decode()
                data = json.loads(json_str)
        
        return CompactEvaluation.from_dict(data)


class RecordingConfig:
    """Configuration for recording modes"""
    
    MODES = {
        'full': {'compact': False, 'compress': False},
        'compact': {'compact': True, 'compress': False},
        'summary': {'compact': True, 'compress': True, 'summary_only': True},
        'debug': {'compact': False, 'compress': False, 'include_debug': True}
    }
    
    @classmethod
    def get_recorder(cls, mode: str = 'compact') -> CompactRecorder:
        """Get appropriate recorder for mode"""
        config = cls.MODES.get(mode, cls.MODES['compact'])
        return CompactRecorder(
            compression_level=6 if config.get('compress') else 0
        )
