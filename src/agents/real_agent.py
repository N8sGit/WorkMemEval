"""
Real Agent Implementation using OpenRouter LLM

Replaces the mock agent with a real LLM-powered agent for WorkMemEval.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import os
from dotenv import load_dotenv

from ..core.plugin_interfaces import AgentImplementation
from ..core.action_trace import ActionTracer, ActionType, TaskTrace, CheckpointTrace
from ..core.task_specification import TaskSpecification, CheckpointSpecification
from .secure_file_ops import SecureFileOperations, SecurityViolationError
from .openrouter_llm import OpenRouterLLM


class RealAgent(AgentImplementation):
    """
    Real agent implementation using OpenRouter LLM for agentic coding tasks.
    """
    
    def __init__(self, memory_system, config: Dict[str, Any]):
        super().__init__(memory_system, config)
        
        # Load environment variables
        load_dotenv()
        
        # Initialize real LLM
        llm_config = {
            'model': config.get('model', 'moonshotai/kimi-k2'),
            'max_tokens': config.get('max_tokens', 4000),
            'temperature': config.get('temperature', 0.1),
            'timeout': config.get('timeout', 60)
        }
        
        self.llm = OpenRouterLLM(llm_config)
        self.file_ops = SecureFileOperations(allowed_base_path=os.getcwd())
        self.action_tracer = ActionTracer(task_id=f"real_agent_{int(time.time())}")
        self.current_task = None
        
    def get_capabilities(self):
        """Return agent capabilities"""
        from ..memory.memory_system import PluginCapabilities
        return PluginCapabilities(
            supports_planning=True,
            supports_debugging=True,
            supports_git_operations=True,
            supports_async=True
        )
    
    async def execute_checkpoint(self, checkpoint: CheckpointSpecification) -> bool:
        """
        Execute a checkpoint using the real LLM with improved measurement
        
        Args:
            checkpoint: The checkpoint specification to execute
            
        Returns:
            bool: True if checkpoint completed successfully
        """
        try:
            self.action_tracer.log_action(
                ActionType.CHECKPOINT_START,
                checkpoint_id=checkpoint.checkpoint_id,
                description=checkpoint.checkpoint_id
            )

            # Build context from current files
            context = self._build_checkpoint_context(checkpoint)
            
            # Generate structured plan
            plan_prompt = self._build_planning_prompt(checkpoint, context)
            plan_response = self.llm.generate_response(plan_prompt, context)
            
            # Extract structured plan for measurement
            plan_steps = self._extract_structured_plan(plan_response)
            
            # Log structured plan with proper metadata
            self.action_tracer.log_action(
                ActionType.PLANNING,
                plan=plan_steps,
                checkpoint_id=checkpoint.checkpoint_id,
                metadata={"structured_plan": plan_steps}
            )

            # Execute implementation with plan adherence tracking
            implementation_prompt = self._build_implementation_prompt(checkpoint, context, plan_steps)
            implementation_response = self.llm.generate_response(implementation_prompt, context)
            
            # Parse and execute with action tracking
            executed_actions = await self._execute_with_tracking(implementation_response, checkpoint, plan_steps)
            
            # Log executed actions against plan
            self.action_tracer.log_action(
                ActionType.CHECKPOINT_COMPLETE,
                checkpoint_id=checkpoint.checkpoint_id,
                executed_actions=executed_actions,
                plan_adherence=self._calculate_plan_adherence(plan_steps, executed_actions)
            )
            
            return True
            
        except Exception as e:
            self.action_tracer.log_action(
                ActionType.COMMAND_EXECUTE,
                error=str(e),
                checkpoint_id=checkpoint.checkpoint_id
            )
            return False
    
    def get_behavioral_trace(self) -> TaskTrace:
        """Get complete behavioral trace for evaluation"""
        return self.action_tracer.get_task_trace()
    
    def _build_context(self, checkpoint: CheckpointSpecification) -> Dict[str, Any]:
        """Build context for LLM from current state"""
        context = {
            'checkpoint_id': checkpoint.checkpoint_id,
            'requirements': checkpoint.requirements,
            'files': {},
            'test_file': checkpoint.test_file
        }
        
        # Read current files if they exist
        workspace_path = Path.cwd()
        
        # Read stub file if provided
        if checkpoint.stub_file:
            stub_path = workspace_path / checkpoint.stub_file
            if stub_path.exists():
                try:
                    content = self.file_ops.read_file(str(stub_path))
                    context['files'][checkpoint.stub_file] = content
                except SecurityViolationError:
                    pass
        
        # Read test file
        if checkpoint.test_file:
            test_path = workspace_path / checkpoint.test_file
            if test_path.exists():
                try:
                    content = self.file_ops.read_file(str(test_path))
                    context['files'][checkpoint.test_file] = content
                except SecurityViolationError:
                    pass
        
        # Add memory system context
        memory_context = self.memory_system.retrieve_relevant_information(
            f"checkpoint_{checkpoint.checkpoint_id}"
        )
        if memory_context:
            context['memory_context'] = memory_context
            
        return context
    
    def _create_planning_prompt(self, checkpoint: CheckpointSpecification, context: Dict[str, Any]) -> str:
        """Create planning prompt for LLM"""
        return f"""
You need to plan the implementation for checkpoint: {checkpoint.checkpoint_id}

Requirements: {checkpoint.requirements}

Current files available: {list(context.get('files', {}).keys())}

Please provide a detailed plan including:
1. Analysis of the requirements
2. Step-by-step implementation approach
3. Files to modify or create
4. Testing strategy

Keep your response focused and actionable.
"""
    
    def _create_implementation_prompt(self, checkpoint: CheckpointSpecification, context: Dict[str, Any], plan: str) -> str:
        """Create implementation prompt for LLM"""
        return f"""
Now implement the solution for checkpoint: {checkpoint.checkpoint_id}

Requirements: {checkpoint.requirements}

Planning output: {plan}

Current context: {json.dumps(context, indent=2)}

Please provide the complete implementation including:
1. Code changes/additions
2. File paths for any new files
3. Complete code for each file
4. Any necessary explanations

Format your response clearly with file paths and code blocks.
"""
    
    async def _execute_llm_suggestions(self, response: str, checkpoint: CheckpointSpecification) -> bool:
        """Execute the suggestions from LLM response"""
        try:
            # Parse the response for code blocks and file operations
            # This is a simplified parser - in practice you might want more sophisticated parsing
            
            lines = response.split('\n')
            current_file = None
            code_block = []
            in_code_block = False
            
            for line in lines:
                if line.startswith('```') and not in_code_block:
                    in_code_block = True
                    code_block = []
                elif line.startswith('```') and in_code_block:
                    in_code_block = False
                    if current_file and code_block:
                        content = '\n'.join(code_block)
                        try:
                            self.file_ops.write_file(current_file, content)
                            self.action_tracer.log_action(
                                ActionType.FILE_WRITE,
                                file_path=current_file,
                                content_length=len(content)
                            )
                        except SecurityViolationError:
                            continue
                elif in_code_block:
                    code_block.append(line)
                elif line.strip().startswith('File:') or line.strip().startswith('file:'):
                    # Extract filename from lines like "File: calculator.py"
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        current_file = parts[1].strip()
            
            # Run tests if test file exists
            if checkpoint.test_file:
                test_path = Path(checkpoint.test_file)
                if test_path.exists():
                    import subprocess
                    try:
                        result = subprocess.run(['python', '-m', 'pytest', str(test_path), '-v'], 
                                              capture_output=True, text=True, timeout=30)
                        
                        self.action_tracer.log_action(
                            ActionType.TEST_RUN,
                            test_file=str(test_path),
                            success=result.returncode == 0,
                            output=result.stdout
                        )
                        
                        return result.returncode == 0
                    except subprocess.TimeoutExpired:
                        return False
            
            return True
            
        except Exception as e:
            self.action_tracer.log_action(
                ActionType.COMMAND_EXECUTE,
                error=str(e),
                checkpoint_id=checkpoint.checkpoint_id
            )
            return False
    
    def _store_task_context(self, task_spec):
        """Store task context for evaluation runner compatibility"""
        self.current_task = task_spec
        self.action_tracer.log_action(
            ActionType.CHECKPOINT_START,
            task_id=task_spec.task_id,
            task_description=task_spec.description
        )

    def _extract_structured_plan(self, response: str) -> List[Dict[str, Any]]:
        """Extract structured plan from LLM response"""
        plan_steps = []
        
        # Parse markdown code blocks for plan
        import re
        plan_pattern = r'(?:plan|steps|actions):?\s*\n?((?:\s*[-*•]\s*.+\n?)+)'
        matches = re.findall(plan_pattern, response, re.IGNORECASE | re.MULTILINE)
        
        if matches:
            for match in matches:
                lines = [line.strip() for line in match.split('\n') if line.strip()]
                for line in lines:
                    if line.startswith(('- ', '* ', '• ')):
                        step_text = line[2:].strip()
                        plan_steps.append({
                            'type': 'file_operation',
                            'description': step_text,
                            'token': step_text.lower().replace(' ', '_')
                        })
        
        # Fallback: extract numbered steps
        if not plan_steps:
            numbered_pattern = r'(?:\d+\.\s*)(.+)'
            numbered_matches = re.findall(numbered_pattern, response, re.MULTILINE)
            for step in numbered_matches:
                plan_steps.append({
                    'type': 'file_operation',
                    'description': step.strip(),
                    'token': step.strip().lower().replace(' ', '_')
                })
        
        # Final fallback: create plan from response structure
        if not plan_steps:
            plan_steps.append({
                'type': 'implementation',
                'description': response,
                'token': 'implement_changes'
            })
            
        return plan_steps

    def _calculate_plan_adherence(self, plan_steps: List[Dict], executed_actions: List[Dict]) -> float:
        """Calculate how well executed actions match the plan"""
        if not plan_steps:
            return 1.0
            
        plan_tokens = [step.get('token', '') for step in plan_steps]
        executed_tokens = []
        
        for action in executed_actions:
            action_type = action.get('type', '')
            description = action.get('description', '')
            token = f"{action_type}_{description.lower().replace(' ', '_')}"
            executed_tokens.append(token)
        
        # Calculate overlap
        plan_set = set(plan_tokens)
        executed_set = set(executed_tokens)
        
        if not plan_set:
            return 1.0
            
        overlap = len(plan_set.intersection(executed_set))
        return overlap / len(plan_set)

    def _execute_with_tracking(self, response: str, checkpoint: CheckpointSpecification, plan_steps: List[Dict]) -> List[Dict]:
        """Execute implementation with action tracking"""
        executed_actions = []
        
        # Parse code blocks from response
        import re
        code_blocks = re.findall(r'```(?:python)?\s*([^`]+)\s*```', response, re.IGNORECASE)
        
        for block in code_blocks:
            lines = block.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith(('def ', 'class ', 'import ', 'from ')):
                    executed_actions.append({
                        'type': 'file_write',
                        'description': line[:50] + '...' if len(line) > 50 else line,
                        'content': line
                    })
        
        return executed_actions

    def _build_improved_context(self, checkpoint: CheckpointSpecification) -> Dict[str, Any]:
        """Build context with proper file universe for relevance scoring"""
        context = self._build_checkpoint_context(checkpoint)
        
        # Add file universe definition
        relevant_files = []
        if hasattr(checkpoint, 'requirements'):
            # Extract relevant files from requirements
            req_text = str(checkpoint.requirements)
            file_pattern = r'\b(\w+\.py)\b'
            import re
            relevant_files = re.findall(file_pattern, req_text)
        
        context['relevant_files'] = relevant_files
        context['file_universe'] = {
            'relevant': relevant_files,
            'total_files': len([f for f in Path('.').glob('*.py') if f.is_file()])
        }
        
        return context

    def get_agent_stats(self) -> Dict[str, Any]:
        """Get agent performance statistics"""
        llm_stats = self.llm.get_stats()
        trace = self.action_tracer.get_task_trace()
        return {
            **llm_stats,
            'total_actions': len(trace.actions) if trace else 0,
            'checkpoints_completed': len([a for a in (trace.actions if trace else []) 
                                        if a.action_type == ActionType.CHECKPOINT_COMPLETE]),
            'measurement_system': 'improved_v2'
        }
