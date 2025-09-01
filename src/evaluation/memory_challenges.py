"""
WorkMemEval: Memory Challenge Injection System

This module implements the memory challenge injection system for WorkMemEval,
providing controlled stress testing of working memory through requirement changes,
interruptions, and information overload.
"""

import asyncio
import time
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..core.task_specification import MemoryChallenge, MemoryChallengeType, CheckpointSpecification
from ..core.action_trace import ActionTracer
from ..core.plugin_interfaces import AgentImplementation


@dataclass
class ChallengeExecutionResult:
    """Result of executing a memory challenge"""
    challenge_id: str
    success: bool
    duration_seconds: float
    agent_adaptation: Optional[str] = None  # How the agent adapted
    performance_impact: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class MemoryChallengeHandler:
    """
    Handler for executing memory challenges during task execution.
    
    This class orchestrates the injection of various memory challenges
    and tracks their impact on agent behavior and performance.
    """
    
    def __init__(self, action_tracer: ActionTracer):
        self.action_tracer = action_tracer
        self.executed_challenges: List[ChallengeExecutionResult] = []
        self.distractor_files_created: List[Path] = []
    
    async def execute_challenge(
        self,
        challenge: MemoryChallenge,
        agent: AgentImplementation,
        current_checkpoint: CheckpointSpecification,
        working_directory: Path
    ) -> ChallengeExecutionResult:
        """
        Execute a memory challenge at the specified checkpoint.
        
        Args:
            challenge: The memory challenge to execute
            agent: The agent being evaluated
            current_checkpoint: Current checkpoint being executed
            working_directory: Working directory for the task
            
        Returns:
            Result of challenge execution
        """
        start_time = time.time()
        
        # Log challenge start
        self.action_tracer.log_memory_challenge_start(
            challenge_id=challenge.challenge_id,
            challenge_type=challenge.challenge_type.value,
            description=challenge.description,
            at_checkpoint=challenge.at_checkpoint
        )
        
        print(f"🧠 Executing memory challenge: {challenge.challenge_id} ({challenge.challenge_type.value})")
        print(f"   Description: {challenge.description}")
        
        try:
            if challenge.challenge_type == MemoryChallengeType.REQUIREMENT_UPDATE:
                result = await self._execute_requirement_update(challenge, agent, current_checkpoint)
            elif challenge.challenge_type == MemoryChallengeType.CONTEXT_SWITCH:
                result = await self._execute_context_switch(challenge, agent, working_directory)
            elif challenge.challenge_type == MemoryChallengeType.INFORMATION_OVERLOAD:
                result = await self._execute_information_overload(challenge, agent, working_directory)
            elif challenge.challenge_type == MemoryChallengeType.INTEGRATION_CONSTRAINT:
                result = await self._execute_integration_constraint(challenge, agent)
            else:
                raise ValueError(f"Unknown challenge type: {challenge.challenge_type}")
            
            result.duration_seconds = time.time() - start_time
            
            # Log challenge completion
            self.action_tracer.log_memory_challenge_complete(
                challenge_id=challenge.challenge_id,
                success=result.success,
                duration_seconds=result.duration_seconds,
                agent_adaptation=result.agent_adaptation
            )
            
            self.executed_challenges.append(result)
            
            status = "✅" if result.success else "❌"
            print(f"   {status} Challenge completed in {result.duration_seconds:.2f}s")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            error_result = ChallengeExecutionResult(
                challenge_id=challenge.challenge_id,
                success=False,
                duration_seconds=duration,
                error_message=str(e)
            )
            
            # Log challenge failure
            self.action_tracer.log_memory_challenge_complete(
                challenge_id=challenge.challenge_id,
                success=False,
                error_message=str(e)
            )
            
            self.executed_challenges.append(error_result)
            print(f"   ❌ Challenge failed: {e}")
            
            return error_result
    
    async def _execute_requirement_update(
        self,
        challenge: MemoryChallenge,
        agent: AgentImplementation,
        checkpoint: CheckpointSpecification
    ) -> ChallengeExecutionResult:
        """Execute a requirement update challenge"""
        original_requirements = checkpoint.requirements
        
        # Generate updated requirements based on the challenge
        updated_requirements = self._generate_updated_requirements(
            original_requirements, 
            challenge.metadata.get('update_type', 'enhancement'),
            challenge.metadata.get('update_details', 'Add additional functionality')
        )
        
        # Log the requirement update
        self.action_tracer.log_requirement_update(
            checkpoint_id=checkpoint.checkpoint_id,
            original_requirements=original_requirements,
            updated_requirements=updated_requirements,
            update_type=challenge.metadata.get('update_type', 'enhancement')
        )
        
        # Update the checkpoint requirements (simulating mid-task change)
        checkpoint.requirements = updated_requirements
        
        # Notify the agent of the requirement change if it supports it
        if hasattr(agent, 'handle_requirement_update'):
            try:
                await agent.handle_requirement_update(checkpoint.checkpoint_id, updated_requirements)
                adaptation = "Agent acknowledged requirement update"
            except Exception as e:
                adaptation = f"Agent failed to handle update: {str(e)}"
        else:
            adaptation = "Agent does not support requirement update handling"
        
        return ChallengeExecutionResult(
            challenge_id=challenge.challenge_id,
            success=True,
            duration_seconds=0,  # Will be set by caller
            agent_adaptation=adaptation
        )
    
    async def _execute_context_switch(
        self,
        challenge: MemoryChallenge,
        agent: AgentImplementation,
        working_directory: Path
    ) -> ChallengeExecutionResult:
        """Execute a context switch challenge"""
        interruption_task = challenge.interruption_task or "Brief documentation task"
        duration_minutes = challenge.duration_minutes or 5
        
        # Log context switch start
        self.action_tracer.log_context_switch_start(
            interruption_task=interruption_task,
            duration_minutes=duration_minutes
        )
        
        # Save current agent state if supported
        saved_state = None
        if hasattr(agent, 'save_context_state'):
            try:
                saved_state = await agent.save_context_state()
            except Exception:
                pass  # Not all agents may support this
        
        # Simulate interruption task
        interruption_success = await self._simulate_interruption_task(
            agent, interruption_task, working_directory
        )
        
        # Simulate delay (in reality, this would be actual time passage)
        await asyncio.sleep(min(duration_minutes * 0.1, 2))  # Cap at 2 seconds for testing
        
        # Attempt to resume original context
        resume_success = True
        if hasattr(agent, 'restore_context_state') and saved_state:
            try:
                await agent.restore_context_state(saved_state)
                adaptation = f"Handled interruption task: {interruption_task}. Agent successfully resumed from saved state"
            except Exception as e:
                resume_success = False
                adaptation = f"Handled interruption task: {interruption_task}. Agent failed to restore state: {str(e)}"
        else:
            adaptation = f"Handled interruption task: {interruption_task}. Agent resumed without explicit state restoration"
        
        # Log context switch resumption
        self.action_tracer.log_context_switch_resume(
            resumed_successfully=resume_success,
            interruption_task=interruption_task,
            interruption_success=interruption_success
        )
        
        return ChallengeExecutionResult(
            challenge_id=challenge.challenge_id,
            success=interruption_success and resume_success,
            duration_seconds=0,  # Will be set by caller
            agent_adaptation=adaptation,
            performance_impact={
                'interruption_duration_minutes': duration_minutes,
                'interruption_success': interruption_success,
                'resume_success': resume_success
            }
        )
    
    async def _execute_information_overload(
        self,
        challenge: MemoryChallenge,
        agent: AgentImplementation,
        working_directory: Path
    ) -> ChallengeExecutionResult:
        """Execute an information overload challenge"""
        distractor_files = challenge.distractor_files or []
        
        if not distractor_files:
            # Generate default distractor files
            distractor_files = [
                'legacy_utils.py',
                'deprecated_config.json',
                'old_tests.py',
                'backup_data.csv'
            ]
        
        # Create distractor files
        created_files = []
        try:
            for file_name in distractor_files:
                file_path = working_directory / file_name
                content = self._generate_distractor_content(file_name)
                
                file_path.write_text(content)
                created_files.append(file_path)
                self.distractor_files_created.append(file_path)
            
            # Log information overload
            self.action_tracer.log_information_overload(
                distractor_files=distractor_files,
                files_created=len(created_files)
            )
            
            adaptation = f"Added {len(created_files)} distractor files to working directory"
            
            return ChallengeExecutionResult(
                challenge_id=challenge.challenge_id,
                success=True,
                duration_seconds=0,  # Will be set by caller
                agent_adaptation=adaptation,
                performance_impact={
                    'distractor_files_added': len(created_files),
                    'files_created': [str(f) for f in created_files]
                }
            )
            
        except Exception as e:
            # Clean up any partially created files
            for file_path in created_files:
                try:
                    file_path.unlink()
                except Exception:
                    pass
            
            raise e
    
    async def _execute_integration_constraint(
        self,
        challenge: MemoryChallenge,
        agent: AgentImplementation
    ) -> ChallengeExecutionResult:
        """Execute an integration constraint challenge"""
        constraint_description = challenge.metadata.get(
            'constraint_description', 
            'Components must maintain backward compatibility'
        )
        affected_checkpoints = challenge.affects or []
        
        # Log integration constraint
        self.action_tracer.log_integration_constraint(
            constraint_description=constraint_description,
            affected_checkpoints=affected_checkpoints
        )
        
        # Notify agent of constraint if supported
        if hasattr(agent, 'handle_integration_constraint'):
            try:
                await agent.handle_integration_constraint(constraint_description, affected_checkpoints)
                adaptation = "Agent acknowledged integration constraint"
            except Exception as e:
                adaptation = f"Agent failed to handle constraint: {str(e)}"
        else:
            adaptation = "Agent does not support integration constraint handling"
        
        return ChallengeExecutionResult(
            challenge_id=challenge.challenge_id,
            success=True,
            duration_seconds=0,  # Will be set by caller
            agent_adaptation=adaptation,
            performance_impact={
                'constraint_description': constraint_description,
                'affected_checkpoints': affected_checkpoints
            }
        )
    
    async def _simulate_interruption_task(
        self, 
        agent: AgentImplementation, 
        task_description: str,
        working_directory: Path
    ) -> bool:
        """Simulate an interruption task"""
        try:
            # Simple interruption: ask agent to create a brief documentation file
            if hasattr(agent, 'execute_interruption_task'):
                return await agent.execute_interruption_task(task_description)
            else:
                # Default interruption simulation
                doc_file = working_directory / 'interruption_notes.md'
                doc_file.write_text(f"# Interruption Task\n\n{task_description}\n\nCompleted at: {time.ctime()}")
                return True
        except Exception:
            return False
    
    def _generate_updated_requirements(
        self, 
        original: str, 
        update_type: str, 
        update_details: str
    ) -> str:
        """Generate updated requirements for requirement update challenge"""
        if update_type == 'enhancement':
            return f"{original}\n\nADDITIONAL REQUIREMENT: {update_details}"
        elif update_type == 'constraint':
            return f"{original}\n\nCONSTRAINT: {update_details}"
        elif update_type == 'modification':
            return f"MODIFIED REQUIREMENTS:\n{update_details}\n\nOriginal: {original}"
        else:
            return f"{original}\n\nUPDATE: {update_details}"
    
    def _generate_distractor_content(self, file_name: str) -> str:
        """Generate realistic but irrelevant content for distractor files"""
        if file_name.endswith('.py'):
            return '''"""
Legacy utility functions - DEPRECATED
Do not use these functions in new code.
"""

def old_helper_function(data):
    """This function is no longer supported"""
    pass

class LegacyProcessor:
    """Deprecated processor class"""
    def __init__(self):
        self.deprecated = True
    
    def process(self, input_data):
        return "This method is deprecated"
'''
        elif file_name.endswith('.json'):
            return '''{
    "deprecated_config": true,
    "old_settings": {
        "timeout": 30,
        "retries": 3,
        "legacy_mode": true
    },
    "note": "This configuration is no longer used"
}'''
        elif file_name.endswith('.csv'):
            return '''timestamp,old_metric,legacy_value
2023-01-01,performance,0.85
2023-01-02,reliability,0.92
2023-01-03,efficiency,0.78
'''
        else:
            return f'''# {file_name}

This is a distractor file created during memory challenge testing.
It contains irrelevant information that should not be used for the main task.

Created: {time.ctime()}
'''
    
    def cleanup_distractor_files(self):
        """Clean up distractor files created during challenges"""
        for file_path in self.distractor_files_created:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass  # Ignore cleanup errors
        self.distractor_files_created.clear()
    
    def get_challenge_summary(self) -> Dict[str, Any]:
        """Get summary of executed challenges"""
        return {
            'total_challenges': len(self.executed_challenges),
            'successful_challenges': len([c for c in self.executed_challenges if c.success]),
            'failed_challenges': len([c for c in self.executed_challenges if not c.success]),
            'challenge_types': [c.challenge_id for c in self.executed_challenges],
            'total_duration': sum(c.duration_seconds for c in self.executed_challenges),
            'distractor_files_created': len(self.distractor_files_created)
        }
