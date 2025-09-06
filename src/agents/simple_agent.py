"""
WorkMemEval: Simple Agent Implementation

A baseline agent implementation using mock components for deterministic testing
and evaluation of memory systems without external dependencies.
"""

import asyncio
import json
import re
import time
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from ..core.plugin_interfaces import AgentImplementation, MemorySystem, PluginCapabilities
from ..core.action_trace import ActionTracer, ActionType, TaskTrace, CheckpointTrace
from ..core.task_specification import TaskSpecification, CheckpointSpecification
from ..core.llm_interfaces import LLMConfig, LLMProvider
from ..llm import LLMFactory
from .secure_file_ops import SecureFileOperations, SecurityViolationError


class MockLLM:
    """
    Mock LLM for deterministic testing and development.
    
    Returns pattern-based responses without external API calls.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.response_delay = config.get('response_delay', 0.1)  # Simulate thinking time
        self.call_count = 0
        
    def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate a deterministic response based on prompt patterns"""
        self.call_count += 1
        
        # Simulate processing time
        if self.response_delay > 0:
            time.sleep(self.response_delay)
        
        prompt_lower = prompt.lower()
        
        # File operation patterns
        if "read file" in prompt_lower or "show me the contents" in prompt_lower:
            if "requirements" in prompt_lower or "spec" in prompt_lower:
                return "I need to read the file to understand the requirements. Let me do that now."
            return "I'll read the file to see its current contents."
        
        if "write file" in prompt_lower or "create file" in prompt_lower:
            return "I'll create the file with the appropriate content."
        
        if "edit file" in prompt_lower or "modify file" in prompt_lower:
            return "I'll make the necessary changes to the file."
        
        # Implementation patterns
        if "implement" in prompt_lower and "function" in prompt_lower:
            return self._generate_function_implementation(prompt)
        
        if "implement" in prompt_lower and "class" in prompt_lower:
            return self._generate_class_implementation(prompt)
        
        # Testing patterns
        if "test" in prompt_lower and ("write" in prompt_lower or "create" in prompt_lower):
            return "I'll create comprehensive tests for this functionality."
        
        # Analysis patterns
        if "analyze" in prompt_lower or "understand" in prompt_lower:
            return "Let me analyze the code and requirements to understand what needs to be done."
        
        # Planning patterns
        if "plan" in prompt_lower or "approach" in prompt_lower:
            return ("I'll break this down into steps:\n"
                   "1. Read and understand the requirements\n" 
                   "2. Analyze existing code\n"
                   "3. Implement the necessary changes\n"
                   "4. Test the implementation")
        
        # Error handling patterns
        if "error" in prompt_lower or "debug" in prompt_lower:
            return "I'll examine the error and fix the issue."
        
        # Default response
        return ("I understand the task. Let me proceed step by step to complete it effectively.")
    
    def _generate_function_implementation(self, prompt: str) -> str:
        """Generate a basic function implementation"""
        if "calculator" in prompt.lower():
            return '''def add(a, b):
    """Add two numbers"""
    return a + b

def multiply(a, b):
    """Multiply two numbers"""
    return a * b'''
        
        if "fibonacci" in prompt.lower():
            return '''def fibonacci(n):
    """Generate fibonacci sequence up to n"""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib'''
        
        return '''def example_function(param):
    """Example function implementation"""
    # TODO: Implement functionality
    return param'''
    
    def _generate_class_implementation(self, prompt: str) -> str:
        """Generate a basic class implementation"""
        return '''class ExampleClass:
    """Example class implementation"""
    
    def __init__(self, value=None):
        self.value = value
    
    def get_value(self):
        return self.value
    
    def set_value(self, value):
        self.value = value'''


class SimpleWorkMemAgent(AgentImplementation):
    """
    Simple baseline agent for WorkMemEval testing.
    
    Uses mock components for deterministic behavior and focuses on
    memory system integration and action tracing.
    """
    
    def __init__(self, memory_system: MemorySystem, config: Dict[str, Any]):
        super().__init__(memory_system, config)
        
        # Initialize LLM provider
        llm_config = config.get('llm_config', {'provider': 'mock', 'model': 'test-model'})
        self.llm = self._initialize_llm_provider(llm_config)
        
        # Agent configuration
        self.max_iterations = config.get('max_iterations', 50)
        self.memory_context_limit = config.get('memory_context_limit', 10)
        self.file_read_cache = {}  # Simple in-memory file cache
        
        # Action tracer for logging
        self.action_tracer: Optional[ActionTracer] = None
        
        # Working directory for file operations
        self.working_directory = Path(config.get('working_directory', '.'))
        
        # Secure file operations (initialized when working directory is set)
        self.secure_file_ops: Optional[SecureFileOperations] = None
        
        # Enable secure file operations if requested
        self.use_secure_file_ops = config.get('use_secure_file_ops', True)
    
    def _initialize_llm_provider(self, llm_config: Dict[str, Any]):
        """Initialize LLM provider based on configuration"""
        provider = llm_config.get('provider', 'mock')
        model = llm_config.get('model', 'test-model')
        
        config = LLMConfig(
            provider=LLMProvider(provider),
            model=model,
            temperature=llm_config.get('temperature', 0.1),
            max_tokens=llm_config.get('max_tokens', 4000),
            provider_config=llm_config
        )
        
        return LLMFactory.create_provider(config)
    
    def initialize_secure_file_ops(self, working_directory: Path) -> None:
        """Initialize secure file operations for the given working directory"""
        if self.use_secure_file_ops:
            self.secure_file_ops = SecureFileOperations(
                allowed_base_path=working_directory,
                max_file_size=1024 * 1024  # 1MB limit
            )
            print(f"Secure file operations enabled for: {working_directory}")
        else:
            print("Secure file operations disabled - using mock file operations")
    
    def get_capabilities(self) -> PluginCapabilities:
        """Return agent capabilities"""
        return PluginCapabilities(
            supports_embeddings=False,
            supports_persistence=False,
            supports_compression=False,
            supports_search=True,
            supports_introspection=True
        )
    
    def execute_task(self, task_spec: TaskSpecification, action_tracer: ActionTracer) -> bool:
        """
        Execute a complete task using memory-guided reasoning.
        
        DEPRECATED: This method is kept for compatibility but orchestration
        should now be handled by the runner calling execute_checkpoint directly.
        
        Args:
            task_spec: The task to execute
            action_tracer: Tracer for logging actions
            
        Returns:
            True if task completed successfully, False otherwise
        """
        self.action_tracer = action_tracer
        
        # Store initial task information in memory
        self._store_task_context(task_spec)
        
        # Note: Checkpoint orchestration should now be handled by the runner
        # This method is kept for compatibility but will log a warning
        print("Warning: execute_task is deprecated. Use runner orchestration instead.")
        
        return True
    
    async def execute_checkpoint(self, checkpoint: CheckpointSpecification) -> bool:
        """
        Execute a single checkpoint with memory-guided approach.
        
        Args:
            checkpoint: The checkpoint to execute
            
        Returns:
            True if checkpoint completed successfully
        """
        try:
            # Store checkpoint context in memory
            self._store_checkpoint_context(checkpoint)
            
            # Get relevant context from memory
            context = self._retrieve_relevant_context(checkpoint)
            
            # Plan the checkpoint execution
            plan = await self._plan_checkpoint_execution(checkpoint, context)
            
            # Execute the plan
            success = await self._execute_plan(checkpoint, plan)
            
            return success
            
        except Exception as e:
            self._log_action(ActionType.ERROR_ENCOUNTERED, f"Checkpoint {checkpoint.checkpoint_id} failed: {e}")
            return False
    
    def _store_task_context(self, task_spec: TaskSpecification):
        """Store task information in memory"""
        task_context = {
            'task_id': task_spec.task_id,
            'description': task_spec.description,
            'checkpoint_count': len(task_spec.checkpoints),
            'checkpoint_files': [(cp.stub_file, cp.test_file) for cp in task_spec.checkpoints]
        }
        
        self.memory_system.store_information(
            f"task_{task_spec.task_id}",
            json.dumps(task_context),
            {'type': 'task', 'timestamp': time.time()}
        )
    
    def _store_checkpoint_context(self, checkpoint: CheckpointSpecification):
        """Store checkpoint information in memory"""
        checkpoint_context = {
            'checkpoint_id': checkpoint.checkpoint_id,
            'title': checkpoint.title,
            'requirements': checkpoint.requirements,
            'stub_file': checkpoint.stub_file,
            'test_file': checkpoint.test_file,
            'dependencies': checkpoint.dependencies,
            'order': checkpoint.order
        }
        
        self.memory_system.store_information(
            f"checkpoint_{checkpoint.checkpoint_id}",
            json.dumps(checkpoint_context),
            {'type': 'checkpoint', 'timestamp': time.time()}
        )
    
    def _retrieve_relevant_context(self, checkpoint: CheckpointSpecification) -> Dict[str, Any]:
        """Retrieve relevant context from memory for checkpoint execution"""
        # Query for relevant information
        queries = [
            checkpoint.checkpoint_id,
            checkpoint.requirements,
            checkpoint.stub_file,
            checkpoint.test_file
        ]
        
        context = {'retrieved_items': []}
        
        for query in queries:
            if query.strip():
                results = self.memory_system.retrieve_information(query, {
                    'max_results': self.memory_context_limit
                })
                context['retrieved_items'].extend(results)
        
        return context
    
    async def _plan_checkpoint_execution(self, checkpoint: CheckpointSpecification, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Plan the execution steps for a checkpoint"""
        # Create a prompt for the LLM to plan execution
        prompt = f"""
Plan execution for checkpoint: {checkpoint.checkpoint_id}
Title: {checkpoint.title}
Requirements: {checkpoint.requirements}
Stub file: {checkpoint.stub_file}
Test file: {checkpoint.test_file}
Dependencies: {checkpoint.dependencies}

Context from memory:
{self._format_context_for_prompt(context)}

What steps should I take to complete this checkpoint?
"""
        
        response = await self.llm.generate_response(prompt, context)
        response_content = response.content if hasattr(response, 'content') else str(response)
        # Log planning with structured plan metadata for metrics
        if self.action_tracer:
            # Include a trimmed version of the plan in metadata
            prospective_plan = self._parse_plan_from_response(response_content, checkpoint)
            self.action_tracer.log_action(
                ActionType.PLANNING,
                success=True,
                plan=prospective_plan,
                checkpoint_id=checkpoint.checkpoint_id
            )
        
        # Convert LLM response to execution plan
        plan = self._parse_plan_from_response(response_content, checkpoint)
        return plan
    
    def _parse_plan_from_response(self, response: str, checkpoint: CheckpointSpecification) -> List[Dict[str, Any]]:
        """Parse LLM response into structured execution plan"""
        # For mock implementation, create a simple plan based on checkpoint files
        plan = []
        
        # Handle stub file and test file
        for file_path in [checkpoint.stub_file, checkpoint.test_file]:
            if file_path:  # Skip if file path is empty
                # Check if file exists (in our mock file system)
                if self._file_exists(file_path):
                    plan.append({
                        'action': 'read_file',
                        'file_path': file_path,
                        'reason': f'Read existing file to understand current state'
                    })
                else:
                    plan.append({
                        'action': 'create_file',
                        'file_path': file_path,
                        'reason': f'Create new file as required by checkpoint'
                    })
        
        # Add implementation step
        plan.append({
            'action': 'implement',
            'description': checkpoint.requirements,
            'reason': 'Implement the required functionality'
        })
        
        return plan
    
    async def _execute_plan(self, checkpoint: CheckpointSpecification, plan: List[Dict[str, Any]]) -> bool:
        """Execute the planned steps"""
        for step in plan:
            success = await self._execute_step(step)
            if not success:
                return False
        
        return True
    
    async def _execute_step(self, step: Dict[str, Any]) -> bool:
        """Execute a single step in the plan"""
        action = step.get('action')
        
        try:
            if action == 'read_file':
                return self._read_file(step['file_path'])
            elif action == 'create_file':
                return self._create_file(step['file_path'], step.get('content', ''))
            elif action == 'edit_file':
                return self._edit_file(step['file_path'], step.get('changes', ''))
            elif action == 'implement':
                return await self._implement_functionality(step['description'])
            else:
                self._log_action(ActionType.ERROR_ENCOUNTERED, f"Unknown action: {action}")
                return False
        
        except Exception as e:
            self._log_action(ActionType.ERROR_ENCOUNTERED, f"Step execution failed: {e}")
            return False
    
    def _read_file(self, file_path: str) -> bool:
        """Read a file and store its contents in memory"""
        try:
            if self.secure_file_ops:
                # Use secure file operations to read from disk
                try:
                    content = self.secure_file_ops.read_file(file_path)
                    # Update cache with real content
                    self.file_read_cache[file_path] = content
                except (FileNotFoundError, SecurityViolationError) as e:
                    self._log_action(ActionType.ERROR_ENCOUNTERED, f"Secure file read failed for {file_path}: {e}")
                    return False
            else:
                # Check cache first (mock mode)
                if file_path in self.file_read_cache:
                    content = self.file_read_cache[file_path]
                else:
                    # For mock implementation, simulate file content
                    content = self._get_mock_file_content(file_path)
                    self.file_read_cache[file_path] = content
            
            # Store file content in memory
            self.memory_system.store_information(
                f"file_content_{file_path}",
                content,
                {'type': 'file_content', 'file_path': file_path, 'timestamp': time.time()}
            )
            
            self._log_action(ActionType.FILE_READ, file_path)
            return True
            
        except Exception as e:
            self._log_action(ActionType.ERROR_ENCOUNTERED, f"Failed to read file {file_path}: {e}")
            return False
    
    def _create_file(self, file_path: str, initial_content: str = '') -> bool:
        """Create a new file with given content"""
        try:
            if self.secure_file_ops:
                # Use secure file operations to write to disk
                try:
                    # If no initial content provided, use mock content
                    if not initial_content.strip():
                        initial_content = self._get_mock_file_content(file_path)
                    
                    self.secure_file_ops.write_file(file_path, initial_content, append=False)
                    # Update cache with real content
                    self.file_read_cache[file_path] = initial_content
                except SecurityViolationError as e:
                    self._log_action(ActionType.ERROR_ENCOUNTERED, f"Secure file write failed for {file_path}: {e}")
                    return False
            else:
                # For mock implementation, store in cache
                self.file_read_cache[file_path] = initial_content
            
            # Store creation event in memory
            self.memory_system.store_information(
                f"file_created_{file_path}",
                f"Created file with {len(initial_content)} characters",
                {'type': 'file_creation', 'file_path': file_path, 'timestamp': time.time()}
            )
            
            self._log_action(ActionType.FILE_WRITE, file_path)
            return True
            
        except Exception as e:
            self._log_action(ActionType.ERROR_ENCOUNTERED, f"Failed to create file {file_path}: {e}")
            return False
    
    def _edit_file(self, file_path: str, changes: str) -> bool:
        """Edit an existing file"""
        try:
            if self.secure_file_ops:
                # Use secure file operations to read current content and write changes
                try:
                    # Read current content from disk
                    try:
                        current_content = self.secure_file_ops.read_file(file_path)
                    except FileNotFoundError:
                        # File doesn't exist yet, start with empty content
                        current_content = ''
                    
                    # Apply changes (for now, simple append)
                    new_content = current_content + '\n' + changes
                    
                    # Write back to disk
                    self.secure_file_ops.write_file(file_path, new_content, append=False)
                    
                    # Update cache
                    self.file_read_cache[file_path] = new_content
                except SecurityViolationError as e:
                    self._log_action(ActionType.ERROR_ENCOUNTERED, f"Secure file edit failed for {file_path}: {e}")
                    return False
            else:
                # Get current content from cache (mock mode)
                current_content = self.file_read_cache.get(file_path, '')
                
                # For mock implementation, append changes
                new_content = current_content + '\n' + changes
                self.file_read_cache[file_path] = new_content
            
            # Store edit event in memory
            self.memory_system.store_information(
                f"file_edited_{file_path}",
                f"Applied changes: {changes[:100]}...",
                {'type': 'file_edit', 'file_path': file_path, 'timestamp': time.time()}
            )
            
            self._log_action(ActionType.FILE_WRITE, file_path)
            return True
            
        except Exception as e:
            self._log_action(ActionType.ERROR_ENCOUNTERED, f"Failed to edit file {file_path}: {e}")
            return False
    
    async def _implement_functionality(self, description: str) -> bool:
        """Implement functionality based on description"""
        try:
            # Use LLM to generate implementation
            prompt = f"Implement the following functionality: {description}"
            response = await self.llm.generate_response(prompt)
            response_content = response.content if hasattr(response, 'content') else str(response)
            
            # Store implementation in memory
            self.memory_system.store_information(
                f"implementation_{hash(description)}",
                response_content,
                {'type': 'implementation', 'description': description, 'timestamp': time.time()}
            )
            
            # Apply the implementation to the calculator.py file if it's a calculator task
            if 'calculator' in description.lower() or 'add' in description.lower() or 'multiply' in description.lower():
                await self._apply_implementation_to_file('calculator.py', response_content, description)
            
            self._log_action(ActionType.LLM_CALL, description)
            return True
            
        except Exception as e:
            self._log_action(ActionType.ERROR_ENCOUNTERED, f"Failed to implement functionality: {e}")
            return False
    
    async def _apply_implementation_to_file(self, file_path: str, implementation: str, description: str) -> bool:
        """Apply LLM implementation to the actual file"""
        try:
            if not self.secure_file_ops:
                return True  # Skip if using mock file system
            
            # Apply implementation based on description
            
            # Read current file content
            try:
                current_content = self.secure_file_ops.read_file(file_path)
            except FileNotFoundError:
                # File doesn't exist, create it
                current_content = ''
            
            # Simple implementation replacement logic - always apply the fallback implementations
            # since MockProvider might not generate syntactically correct Python
            new_content = current_content
            
            # If it's an add function implementation
            if 'add' in description.lower():
                # Use a simple default implementation
                new_content = current_content.replace(
                    '    # TODO: Implement addition function\n    pass',
                    '    return a + b'
                )
            
            # If it's a multiply function implementation
            if 'multiply' in description.lower():
                new_content = current_content.replace(
                    '    # TODO: Implement multiplication function\n    pass',
                    '    return a * b'
                )
            
            # If it's the Calculator class implementation
            if 'calculator' in description.lower() and 'class' in description.lower():
                new_content = current_content.replace(
                    '        # TODO: Implement Calculator.add method\n        pass',
                    '        return add(a, b)'
                )
                new_content = new_content.replace(
                    '        # TODO: Implement Calculator.multiply method\n        pass',
                    '        return multiply(a, b)'
                )
            
            # Write the updated content back to the file
            if new_content != current_content:
                self.secure_file_ops.write_file(file_path, new_content, append=False)
                self.file_read_cache[file_path] = new_content
                print(f"✅ Applied implementation to {file_path}")
                return True
            else:
                print(f"⚠️ No changes made to {file_path}")
                return True
            
        except Exception as e:
            self._log_action(ActionType.ERROR_ENCOUNTERED, f"Failed to apply implementation to {file_path}: {e}")
            return False
    
    def _file_exists(self, file_path: str) -> bool:
        """Check if a file exists"""
        if self.secure_file_ops:
            # Use secure file operations to check if file exists on disk
            return self.secure_file_ops.file_exists(file_path)
        else:
            # Check cache for mock implementation
            return file_path in self.file_read_cache
    
    def _get_mock_file_content(self, file_path: str) -> str:
        """Generate mock file content based on file path"""
        if file_path.endswith('.py'):
            return f'# Python file: {file_path}\n# TODO: Implement functionality\n'
        elif file_path.endswith('.txt'):
            return f'Text file: {file_path}\nContent placeholder\n'
        elif file_path.endswith('.json'):
            return f'{{\n  "file": "{file_path}",\n  "content": "placeholder"\n}}'
        else:
            return f'File: {file_path}\nGeneric content\n'
    
    def _format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """Format retrieved context for LLM prompt"""
        items = context.get('retrieved_items', [])
        if not items:
            return "No relevant context found in memory."
        
        formatted = []
        for item in items[:5]:  # Limit context size
            formatted.append(f"- {item.get('key', 'Unknown')}: {item.get('value', '')[:200]}")
        
        return '\n'.join(formatted)
    
    def get_behavioral_trace(self) -> TaskTrace:
        """
        Get complete behavioral trace for evaluation.
        
        For this simple agent, we delegate to the ActionTracer
        which maintains the actual trace data.
        
        Returns:
            TaskTrace containing all agent behavior for working memory analysis
        """
        if self.action_tracer:
            return self.action_tracer.get_task_trace()
        else:
            # Return empty trace if no tracer available
            return TaskTrace(
                task_id="unknown",
                start_timestamp=time.time(),
                completed_successfully=False
            )
    
    def _log_action(self, action_type: ActionType, details: str):
        """Log an action if tracer is available"""
        if self.action_tracer:
            self.action_tracer.log_action(action_type, details)
