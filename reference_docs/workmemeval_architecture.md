# WorkMemEval: Universal Agent Evaluation Architecture

## Strategic Design Principle: Custom Agent with Plugin Architecture

WorkMemEval achieves comprehensive working memory evaluation through a **custom agent implementation** with pluggable memory systems. The architecture prioritizes clean instrumentation and universal memory system compatibility over external agent integration.

## Core Architecture: Custom Agent + Pluggable Memory Systems

### 1. Custom Agent Implementation
```python
# workmemeval/agents/instrumented_agent.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class InstrumentedAgent(ABC):
    """
    Universal interface defining the behavioral hooks WorkMemEval requires
    All agent adapters must implement this interface for evaluation compatibility
    """
    
    @abstractmethod
    async def initialize_evaluation(self, task_spec: TaskSpecification) -> None:
        """Initialize agent for WorkMemEval task execution"""
        pass
    
    @abstractmethod
    async def present_planning_prompt(self, prompt: str) -> PlanningResponse:
        """Present planning phase prompt and capture planning behavior"""
        pass
    
    @abstractmethod
    async def present_checkpoint(self, checkpoint: CheckpointSpec) -> CheckpointResponse:
        """Present checkpoint requirements and begin implementation"""
        pass
    
    @abstractmethod
    def get_action_trace(self) -> List[ActionTraceEntry]:
        """Get comprehensive behavioral trace for current execution"""
        pass
    
    @abstractmethod
    def get_context_snapshot(self) -> ContextSnapshot:
        """Get current agent context state for memory analysis"""
        pass
    
    @abstractmethod
    async def handle_memory_challenge(self, challenge: MemoryChallenge) -> ChallengeResponse:
        """Handle working memory challenges (interruptions, requirement changes)"""
        pass

# Standard event types that all adapters must emit
@dataclass
class StandardActionTraceEntry:
    """Universal action trace format"""
    timestamp: float
    agent_id: str
    action_type: str  # Standardized: 'file_read', 'file_write', 'llm_call', 'context_update'
    file_path: Optional[str]
    success: bool
    context_size_before: int
    context_size_after: int
    metadata: Dict[str, Any]  # Agent-specific details

@dataclass
class StandardContextSnapshot:
    """Universal context state format"""
    timestamp: float
    files_in_context: List[str]
    context_token_count: int
    memory_state: Dict[str, Any]  # Agent-specific memory representation
    working_directory: str
```

### 2. Aider Instrumentation Adapter
```python
# workmemeval/agents/aider_adapter.py
class AiderInstrumentedAdapter(InstrumentedAgent):
    """
    Deep integration adapter for Aider agent
    Translates Aider's internal behaviors to WorkMemEval's standard interface
    """
    
    def __init__(self, aider_args):
        self.aider_coder = self._create_instrumented_aider_coder(aider_args)
        self.action_tracer = AiderActionTracer()
        self.checkpoint_manager = CheckpointManager()
        
    def _create_instrumented_aider_coder(self, args):
        """Create Aider coder with WorkMemEval hooks"""
        
        # Minimal modification to Aider core - just add hooks
        class InstrumentedEditBlockCoder(EditBlockCoder):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.workmemeval_adapter = kwargs.get('workmemeval_adapter')
            
            def send_message(self, message, history=None):
                # Pre-message hook
                if self.workmemeval_adapter:
                    pre_context = self.workmemeval_adapter._capture_aider_context()
                    self.workmemeval_adapter.action_tracer.log_message_start(message, pre_context)
                
                # Original Aider logic
                response = super().send_message(message, history)
                
                # Post-message hook
                if self.workmemeval_adapter:
                    post_context = self.workmemeval_adapter._capture_aider_context()
                    self.workmemeval_adapter.action_tracer.log_message_complete(response, post_context)
                
                return response
            
            def apply_edits(self, edits):
                # File edit tracking
                if self.workmemeval_adapter:
                    for edit in edits:
                        self.workmemeval_adapter.action_tracer.log_file_edit_start(edit)
                
                result = super().apply_edits(edits)
                
                if self.workmemeval_adapter:
                    for edit in edits:
                        self.workmemeval_adapter.action_tracer.log_file_edit_complete(edit, result)
                
                return result
        
        return InstrumentedEditBlockCoder(
            *self._parse_aider_args(args),
            workmemeval_adapter=self
        )
    
    async def present_checkpoint(self, checkpoint: CheckpointSpec) -> CheckpointResponse:
        """Present checkpoint using Aider's native messaging"""
        
        prompt = self._build_checkpoint_prompt(checkpoint)
        
        # Use Aider's messaging system
        response = await self.aider_coder.send_message(prompt)
        
        # Start monitoring for completion
        self.checkpoint_manager.start_monitoring(checkpoint)
        
        return CheckpointResponse(
            checkpoint_id=checkpoint.id,
            agent_response=response,
            monitoring_started=True
        )
    
    def get_action_trace(self) -> List[ActionTraceEntry]:
        """Convert Aider-specific trace to standard format"""
        aider_trace = self.action_tracer.get_raw_trace()
        
        standard_trace = []
        for entry in aider_trace:
            standard_entry = StandardActionTraceEntry(
                timestamp=entry.timestamp,
                agent_id="aider",
                action_type=self._standardize_action_type(entry.action_type),
                file_path=entry.file_path,
                success=entry.success,
                context_size_before=entry.pre_context_size,
                context_size_after=entry.post_context_size,
                metadata={
                    'aider_specific': entry.aider_metadata,
                    'llm_model': entry.model_info,
                    'edit_type': entry.edit_type
                }
            )
            standard_trace.append(standard_entry)
        
        return standard_trace
    
    def _capture_aider_context(self) -> AiderContextSnapshot:
        """Capture Aider's internal context state"""
        return AiderContextSnapshot(
            abs_fnames=list(self.aider_coder.abs_fnames),
            cur_messages=self.aider_coder.cur_messages.copy(),
            context_tokens=self.aider_coder.main_model.token_count(
                self.aider_coder.format_messages()
            ),
            fence_cache=self.aider_coder.fence.copy(),
            git_repo_state=self.aider_coder.repo.get_head_commit()
        )
    
    def _standardize_action_type(self, aider_action_type: str) -> str:
        """Map Aider-specific actions to standard types"""
        mapping = {
            'aider_file_read': 'file_read',
            'aider_file_write': 'file_write', 
            'aider_llm_call': 'llm_call',
            'aider_context_update': 'context_update',
            'aider_edit_planning': 'planning',
            'aider_fence_selection': 'context_management'
        }
        return mapping.get(aider_action_type, aider_action_type)
```

### 3. Future Agent Adapters (Examples)
```python
# workmemeval/agents/devin_adapter.py
class DevinInstrumentedAdapter(InstrumentedAgent):
    """Adapter for Devin agent architecture"""
    
    def __init__(self, devin_config):
        self.devin_agent = DevinAgent(devin_config)
        self.action_tracer = DevinActionTracer()
    
    async def present_checkpoint(self, checkpoint: CheckpointSpec) -> CheckpointResponse:
        # Devin-specific checkpoint presentation logic
        pass
    
    def get_action_trace(self) -> List[ActionTraceEntry]:
        # Convert Devin's internal trace to standard format
        pass

# workmemeval/agents/cursor_adapter.py  
class CursorInstrumentedAdapter(InstrumentedAgent):
    """Adapter for Cursor agent architecture"""
    pass

# workmemeval/agents/custom_adapter.py
class CustomAgentAdapter(InstrumentedAgent):
    """Template for custom agent implementations"""
    pass
```

### 4. Universal Evaluation Harness
```python
# workmemeval/evaluation/universal_runner.py
class UniversalWorkMemEvalRunner:
    """
    Agent-agnostic evaluation harness
    Works with any agent implementing InstrumentedAgent interface
    """
    
    def __init__(self, task_spec: TaskSpecification, agent: InstrumentedAgent):
        self.task_spec = task_spec
        self.agent = agent
        self.evaluator = WorkMemEvalEvaluator(task_spec)
        
    async def run_evaluation(self) -> EvaluationResult:
        """Execute WorkMemEval evaluation against any compatible agent"""
        
        # Initialize agent for evaluation
        await self.agent.initialize_evaluation(self.task_spec)
        
        # Planning phase
        planning_result = await self._execute_planning_phase()
        
        # Checkpoint progression  
        checkpoint_results = []
        for checkpoint in self.task_spec.checkpoints:
            result = await self._execute_checkpoint(checkpoint)
            checkpoint_results.append(result)
            
            if not result.task_success:
                break
        
        # Calculate final metrics using standard trace format
        final_metrics = self.evaluator.calculate_final_metrics(
            planning_result=planning_result,
            checkpoint_results=checkpoint_results,
            action_trace=self.agent.get_action_trace()
        )
        
        return EvaluationResult(
            agent_id=self.agent.agent_id,
            task_id=self.task_spec.task_id,
            planning_result=planning_result,
            checkpoint_results=checkpoint_results,
            final_metrics=final_metrics
        )
    
    async def _execute_checkpoint(self, checkpoint: CheckpointSpec) -> CheckpointResult:
        """Execute checkpoint evaluation - agent agnostic"""
        
        # Present checkpoint to agent
        response = await self.agent.present_checkpoint(checkpoint)
        
        # Monitor for completion using standard test runner
        completion_result = await self._wait_for_checkpoint_completion(checkpoint)
        
        # Evaluate using standard trace format
        trace = self.agent.get_action_trace()
        checkpoint_trace = [entry for entry in trace if entry.checkpoint_id == checkpoint.id]
        
        evaluation = self.evaluator.evaluate_checkpoint(
            checkpoint=checkpoint,
            action_trace=checkpoint_trace,
            test_result=completion_result
        )
        
        return evaluation
```

### 5. Agent Factory Pattern
```python
# workmemeval/agents/factory.py
class AgentFactory:
    """Factory for creating instrumented agents"""
    
    SUPPORTED_AGENTS = {
        'aider': AiderInstrumentedAdapter,
        'devin': DevinInstrumentedAdapter,
        'cursor': CursorInstrumentedAdapter,
        'custom': CustomAgentAdapter
    }
    
    @classmethod
    def create_agent(cls, agent_type: str, config: Dict[str, Any]) -> InstrumentedAgent:
        """Create instrumented agent instance"""
        
        if agent_type not in cls.SUPPORTED_AGENTS:
            raise ValueError(f"Unsupported agent type: {agent_type}")
        
        adapter_class = cls.SUPPORTED_AGENTS[agent_type]
        return adapter_class(config)

# Usage
def run_workmemeval_benchmark():
    task_spec = TaskSpecificationLoader.load("user_management_api.json")
    
    # Evaluate Aider
    aider_agent = AgentFactory.create_agent('aider', {'model': 'gpt-4'})
    aider_result = await UniversalWorkMemEvalRunner(task_spec, aider_agent).run_evaluation()
    
    # Evaluate Devin (when adapter is available)
    devin_agent = AgentFactory.create_agent('devin', {'api_key': 'xxx'})
    devin_result = await UniversalWorkMemEvalRunner(task_spec, devin_agent).run_evaluation()
    
    # Compare results
    comparison = WorkMemEvalComparator.compare([aider_result, devin_result])
```

## Strategic Benefits of Adapter Architecture

### 1. **Agent Neutrality Achieved**
- **Universal Interface**: All agents evaluated against same standard interface
- **Fair Comparison**: No agent-specific biases in core evaluation logic
- **Level Playing Field**: New agents only need adapter implementation

### 2. **Maintenance Isolation**  
- **Decoupled Evolution**: Core WorkMemEval evolves independently of any specific agent
- **Focused Updates**: Agent changes only affect specific adapters
- **Sustainable Development**: Maintenance burden distributed across adapter maintainers

### 3. **Research Platform Scalability**
- **Easy Agent Addition**: New agents require only adapter implementation
- **Comparative Studies**: Direct comparison across different agent architectures
- **Community Contributions**: Researchers can contribute adapters for their agents

### 4. **Deep Insight Preservation**
- **Rich Aider Integration**: First adapter maintains all deep integration benefits
- **Agent-Specific Intelligence**: Each adapter can capture architecture-specific insights
- **Optimal Fidelity**: No compromise on behavioral detail for any agent

## Implementation Strategy Refinement

### Phase 1: Universal Foundation (Weeks 1-2)
1. Define `InstrumentedAgent` interface and standard trace formats
2. Build `UniversalWorkMemEvalRunner` against generic interface
3. Create evaluation engine using standard formats
4. Build test infrastructure for interface compliance

### Phase 2: Aider Reference Implementation (Weeks 3-6)  
1. Implement `AiderInstrumentedAdapter` with deep integration hooks
2. Add minimal modifications to Aider core (hook points only)
3. Implement Aider-specific trace translation to standard format
4. Validate full evaluation pipeline with Aider

### Phase 3: Platform Validation (Weeks 7-8)
1. Create template for new agent adapters
2. Build documentation and adapter development guide
3. Implement comparative analysis tools
4. Validate benchmark across multiple task types

### Phase 4: Ecosystem Expansion (Ongoing)
1. Community contribution framework for new adapters
2. Adapter certification process
3. Cross-agent comparative studies
4. Continuous platform enhancement

This refined architecture transforms WorkMemEval from an "Aider benchmark" into a **universal working memory evaluation platform** while preserving all the deep integration benefits you identified for Aider specifically.

## Integration Strategy

### 1. Aider Fork with Evaluation Mode
```python
# aider/main.py - Add WorkMemEval mode
def main():
    parser = argparse.ArgumentParser()
    # ... existing Aider args ...
    parser.add_argument('--workmemeval', action='store_true', 
                       help='Enable WorkMemEval benchmark mode')
    parser.add_argument('--task-spec', type=str,
                       help='Path to WorkMemEval task specification')
    
    args = parser.parse_args()
    
    if args.workmemeval:
        # Initialize WorkMemEval mode
        evaluator = WorkMemEvalMode(args.task_spec)
        coder = evaluator.create_evaluation_coder(args)
    else:
        # Standard Aider mode
        coder = Coder.create(args)
    
    # ... rest of main()
```

### 2. Enhanced Coder Class with Evaluation Hooks
```python
# aider/coders/base_coder.py - Add evaluation instrumentation
class Coder:
    def __init__(self, *args, **kwargs):
        # ... existing initialization ...
        
        # WorkMemEval instrumentation (optional)
        self.evaluation_mode = kwargs.get('evaluation_mode', False)
        if self.evaluation_mode:
            self.action_tracer = ActionTracer()
            self.checkpoint_manager = CheckpointManager(kwargs['task_spec'])
            self.memory_monitor = MemoryMonitor()
    
    def send_message(self, message, history=None):
        """Enhanced with evaluation hooks"""
        
        if self.evaluation_mode:
            # Pre-message state capture
            pre_state = self._capture_evaluation_state()
            self.action_tracer.log_message_start(message, pre_state)
        
        # Execute original Aider logic
        response = super().send_message(message, history)
        
        if self.evaluation_mode:
            # Post-message state capture
            post_state = self._capture_evaluation_state()
            self.action_tracer.log_message_complete(response, post_state)
            
            # Check for checkpoint completion
            self.checkpoint_manager.check_completion_status()
        
        return response
    
    def apply_edits(self, edits):
        """Enhanced with file operation tracking"""
        
        if self.evaluation_mode:
            # Track file modifications for working memory analysis
            for edit in edits:
                self.action_tracer.log_file_edit(
                    file_path=edit.path,
                    edit_type=edit.operation,
                    content_before=self._get_file_content(edit.path),
                    edit_content=edit.content
                )
        
        # Execute original edit logic
        result = super().apply_edits(edits)
        
        if self.evaluation_mode:
            # Post-edit state tracking
            for edit in edits:
                self.action_tracer.log_file_edit_complete(
                    file_path=edit.path,
                    content_after=self._get_file_content(edit.path),
                    success=edit.path in result.successful_edits
                )
        
        return result
```

### 3. Native File System Monitoring
```python
# aider/io.py - Enhanced with evaluation hooks
class InputOutput:
    def __init__(self, *args, **kwargs):
        # ... existing initialization ...
        self.evaluation_tracer = kwargs.get('evaluation_tracer')
    
    def read_text(self, filename):
        """Enhanced read_text with access tracking"""
        
        if self.evaluation_tracer:
            self.evaluation_tracer.log_file_access(
                file_path=filename,
                access_type='read',
                timestamp=time.time(),
                context_size=len(self.coder.cur_messages) if hasattr(self, 'coder') else 0
            )
        
        # Execute original read logic
        content = super().read_text(filename)
        
        if self.evaluation_tracer:
            self.evaluation_tracer.log_file_access_complete(
                file_path=filename,
                content_size=len(content),
                success=True
            )
        
        return content
    
    def write_text(self, filename, content):
        """Enhanced write_text with modification tracking"""
        
        # Pre-write state
        existing_content = None
        if self.evaluation_tracer and os.path.exists(filename):
            existing_content = self.read_text(filename)
            
        if self.evaluation_tracer:
            self.evaluation_tracer.log_file_write(
                file_path=filename,
                content_size=len(content),
                is_new_file=not os.path.exists(filename),
                previous_content=existing_content
            )
        
        # Execute original write logic
        result = super().write_text(filename, content)
        
        return result
```

### 4. Deep Context Management Hooks
```python
# aider/coders/editblock_coder.py - Enhanced context tracking
class EditBlockCoder(Coder):
    def update_cur_messages(self, edited):
        """Enhanced with context change tracking"""
        
        if self.evaluation_mode:
            # Capture context before update
            pre_context = ContextSnapshot(
                files=list(self.abs_fnames),
                message_count=len(self.cur_messages),
                context_tokens=self.main_model.token_count(self.format_messages()),
                memory_state=self.memory_monitor.get_current_state()
            )
        
        # Execute original context update
        super().update_cur_messages(edited)
        
        if self.evaluation_mode:
            # Capture context after update
            post_context = ContextSnapshot(
                files=list(self.abs_fnames),
                message_count=len(self.cur_messages),
                context_tokens=self.main_model.token_count(self.format_messages()),
                memory_state=self.memory_monitor.get_current_state()
            )
            
            # Log context transition for working memory analysis
            self.action_tracer.log_context_transition(
                pre_context=pre_context,
                post_context=post_context,
                trigger='message_update',
                files_added=post_context.files - pre_context.files,
                files_removed=pre_context.files - post_context.files
            )
    
    def choose_fence(self, fname):
        """Track fence selection decisions"""
        if self.evaluation_mode:
            self.action_tracer.log_fence_selection(fname, self.fence)
        return super().choose_fence(fname)
```

### 5. Native Test Integration
```python
# aider/test_runner.py - New module for WorkMemEval
class WorkMemEvalTestRunner:
    """
    Native test runner integrated into Aider for checkpoint completion detection
    """
    
    def __init__(self, coder, task_spec):
        self.coder = coder
        self.task_spec = task_spec
        self.active_checkpoint = None
        self.test_watcher = FileSystemWatcher()
        
    def start_checkpoint_monitoring(self, checkpoint: CheckpointSpec):
        """Start monitoring for checkpoint completion"""
        self.active_checkpoint = checkpoint
        
        # Watch test file for changes
        self.test_watcher.watch(
            checkpoint.test_file,
            callback=self._on_test_file_changed
        )
        
        # Start periodic test execution
        asyncio.create_task(self._periodic_test_execution())
    
    async def _periodic_test_execution(self):
        """Periodically run tests to detect completion"""
        while self.active_checkpoint:
            
            # Execute tests using subprocess
            result = await self._run_pytest(self.active_checkpoint.test_file)
            
            # Log test execution
            self.coder.action_tracer.log_test_execution(
                checkpoint_id=self.active_checkpoint.id,
                test_file=self.active_checkpoint.test_file,
                success=result.returncode == 0,
                output=result.stdout,
                errors=result.stderr
            )
            
            # Check for completion
            if result.returncode == 0:
                await self._signal_checkpoint_completion(result)
                break
                
            await asyncio.sleep(10)  # Configurable interval
    
    async def _signal_checkpoint_completion(self, test_result):
        """Signal completion and trigger next checkpoint"""
        
        # Log completion
        self.coder.action_tracer.log_checkpoint_completion(
            checkpoint_id=self.active_checkpoint.id,
            completion_time=time.time(),
            test_result=test_result
        )
        
        # Trigger evaluation calculation
        evaluation = self.coder.evaluator.evaluate_checkpoint(
            checkpoint=self.active_checkpoint,
            action_trace=self.coder.action_tracer.get_checkpoint_trace(self.active_checkpoint.id)
        )
        
        # Progress to next checkpoint
        next_checkpoint = self.coder.checkpoint_manager.get_next_checkpoint()
        if next_checkpoint:
            await self.coder.present_checkpoint(next_checkpoint)
            self.start_checkpoint_monitoring(next_checkpoint)
        else:
            await self.coder.complete_task_evaluation()
```

## Key Integration Benefits

### 1. Native Behavioral Capture
```python
# Deep access to Aider's internal state
class ActionTracer:
    def capture_llm_call(self, messages, response, model_info):
        """Capture every LLM interaction with full context"""
        
    def capture_file_selection(self, available_files, selected_files, selection_reason):
        """Track Aider's file selection decisions"""
        
    def capture_edit_planning(self, planned_edits, edit_reasoning):
        """Track Aider's edit planning process"""
        
    def capture_context_compression(self, pre_compression, post_compression, compression_trigger):
        """Track when and how Aider compresses context"""
```

### 2. Seamless User Experience
```bash
# Standard Aider usage
aider --model gpt-4 src/

# WorkMemEval mode (same interface, different evaluation)
aider --workmemeval --task-spec user_management_api.json --model gpt-4 src/
```

### 3. Minimal Core Changes
```python
# Changes to core Aider are minimal and conditional
if self.evaluation_mode:
    # WorkMemEval instrumentation
    self.log_action(action_type, details)
    
# Original Aider logic proceeds unchanged
return self.original_method()
```

## Implementation Strategy

### Phase 1: Fork and Basic Hooks
1. Fork Aider repository
2. Add `--workmemeval` mode flag
3. Add basic action logging hooks to core methods
4. Implement simple checkpoint progression

### Phase 2: Deep Integration
1. Add comprehensive behavioral capture
2. Implement native test monitoring
3. Add three-pillar evaluation engine
4. Build task specification loading

### Phase 3: Memory System Integration
1. Add pluggable memory system interface
2. Implement different memory backends
3. Add memory operation tracking
4. Build comparative evaluation framework

### Phase 4: Research Platform
1. Add experimental memory systems
2. Build analysis and visualization tools
3. Add batch evaluation capabilities
4. Create benchmark dataset

## Risk Mitigation

### Stability Preservation
- **Feature Flags**: All WorkMemEval code behind `evaluation_mode` checks
- **Minimal Core Changes**: Hooks are additive, not modificational
- **Separate Modules**: Most evaluation logic in separate files
- **Testing**: Comprehensive tests ensure standard Aider functionality preserved

### Maintenance Strategy
- **Upstream Tracking**: Regular merges from main Aider repository
- **Isolated Changes**: WorkMemEval changes clearly separated and documented
- **Contribution Back**: Generic hooks could be contributed to upstream Aider

## Direct Integration Advantages

### 1. **Unparalleled Behavioral Visibility**
```python
# We can capture internal Aider decisions that external wrappers can't see:
- LLM prompt construction and response processing
- File selection and context management logic  
- Edit planning and execution reasoning
- Context compression triggers and strategies
- Memory management decisions
```

### 2. **Zero Performance Overhead**
- No external process communication
- No API abstraction layers
- No data serialization/deserialization
- Direct access to Aider's data structures

### 3. **Perfect Synchronization** 
- Evaluation hooks execute in same process as agent
- No race conditions between agent actions and monitoring
- Atomic capture of state transitions
- Real-time metric calculation

### 4. **Native Context Management**
Building into Aider gives us direct access to its sophisticated context management:
```python
# aider/coders/base_coder.py
def format_messages(self):
    """We can instrument Aider's context formatting directly"""
    
    if self.evaluation_mode:
        # Capture context composition decisions
        self.memory_monitor.log_context_composition(
            files_included=self.abs_fnames,
            message_history_length=len(self.cur_messages),
            context_tokens=self.main_model.token_count(formatted),
            composition_strategy=self.get_context_strategy()
        )
    
    formatted = super().format_messages()
    return formatted
```

## WorkMemEval-Specific Components

### 1. Task Specification Loader
```python
# aider/workmemeval/task_loader.py
class TaskSpecificationLoader:
    """Load and validate WorkMemEval task specifications"""
    
    @staticmethod
    def load(task_spec_path: str) -> TaskSpecification:
        with open(task_spec_path, 'r') as f:
            spec_data = json.load(f)
        
        # Validate specification format
        TaskSpecificationValidator.validate(spec_data)
        
        return TaskSpecification.from_dict(spec_data)
```

### 2. Checkpoint Manager
```python
# aider/workmemeval/checkpoint_manager.py
class CheckpointManager:
    """Manages checkpoint progression and presentation"""
    
    def __init__(self, task_spec: TaskSpecification, coder):
        self.task_spec = task_spec
        self.coder = coder
        self.current_checkpoint_index = 0
        self.checkpoint_start_times = {}
        
    async def start_planning_phase(self):
        """Present planning phase to agent"""
        planning_prompt = self.task_spec.planning_phase.overview_prompt
        
        # Use Aider's native messaging system
        await self.coder.send_message(planning_prompt)
        
        # Monitor for plan document creation
        plan_document = self.task_spec.planning_phase.planning_capture.plan_document
        await self._wait_for_plan_completion(plan_document)
    
    async def present_next_checkpoint(self):
        """Present next checkpoint requirements to agent"""
        if self.current_checkpoint_index >= len(self.task_spec.checkpoints):
            return False  # No more checkpoints
        
        checkpoint = self.task_spec.checkpoints[self.current_checkpoint_index]
        
        # Build checkpoint presentation
        prompt = self._build_checkpoint_prompt(checkpoint)
        
        # Record checkpoint start
        self.checkpoint_start_times[checkpoint.id] = time.time()
        
        # Present to agent via Aider's messaging
        await self.coder.send_message(prompt)
        
        # Start test monitoring
        self.coder.test_runner.start_checkpoint_monitoring(checkpoint)
        
        return True
    
    def _build_checkpoint_prompt(self, checkpoint: CheckpointSpec) -> str:
        """Build checkpoint presentation prompt"""
        return f"""
## Checkpoint {checkpoint.order}: {checkpoint.title}

**Implementation Target**: `{checkpoint.stub_file}` - `{checkpoint.stub_function}`

**Requirements**:
{checkpoint.requirements}

**Dependencies**: {', '.join(checkpoint.dependencies) if checkpoint.dependencies else 'None'}

**Test File**: `{checkpoint.test_file}`

Please implement the required functionality. The checkpoint will be considered complete when all tests in `{checkpoint.test_file}` pass.
"""
```

### 3. Native Action Tracer
```python
# aider/workmemeval/action_tracer.py
class ActionTracer:
    """Comprehensive behavioral trace capture integrated into Aider"""
    
    def __init__(self):
        self.trace_entries = []
        self.current_checkpoint = None
        self.context_snapshots = []
        
    def log_file_access(self, file_path: str, access_type: str, **kwargs):
        """Log file system access with full context"""
        entry = ActionTraceEntry(
            timestamp=time.time(),
            action_type=f'file_{access_type}',
            file_path=file_path,
            checkpoint_id=self.current_checkpoint.id if self.current_checkpoint else None,
            context_size=kwargs.get('context_size', 0),
            metadata=kwargs
        )
        self.trace_entries.append(entry)
    
    def log_llm_interaction(self, messages, response, model_info):
        """Log LLM calls with full prompt/response context"""
        entry = ActionTraceEntry(
            timestamp=time.time(),
            action_type='llm_call',
            metadata={
                'model': model_info.name,
                'prompt_tokens': model_info.prompt_tokens,
                'completion_tokens': model_info.completion_tokens,
                'response_content': response,
                'message_count': len(messages)
            }
        )
        self.trace_entries.append(entry)
    
    def log_context_transition(self, pre_context, post_context, trigger):
        """Log context management decisions"""
        entry = ActionTraceEntry(
            timestamp=time.time(),
            action_type='context_transition',
            metadata={
                'trigger': trigger,
                'files_added': list(post_context.files - pre_context.files),
                'files_removed': list(pre_context.files - post_context.files),
                'token_change': post_context.context_tokens - pre_context.context_tokens
            }
        )
        self.trace_entries.append(entry)
    
    def get_checkpoint_trace(self, checkpoint_id: str) -> List[ActionTraceEntry]:
        """Get all trace entries for specific checkpoint"""
        return [entry for entry in self.trace_entries 
                if entry.checkpoint_id == checkpoint_id]
```

### 4. Integrated Evaluator
```python
# aider/workmemeval/evaluator.py  
class WorkMemEvalEvaluator:
    """Three-pillar evaluation engine integrated with Aider"""
    
    def __init__(self, task_spec: TaskSpecification):
        self.task_spec = task_spec
        self.checkpoint_evaluations = []
        
    def evaluate_checkpoint_completion(self, checkpoint: CheckpointSpec, 
                                     action_trace: List[ActionTraceEntry],
                                     test_result) -> CheckpointEvaluation:
        """Evaluate checkpoint using three-pillar framework"""
        
        # Gating metric: Task Success
        if not test_result.all_passed:
            return CheckpointEvaluation(
                checkpoint_id=checkpoint.id,
                task_success=False,
                working_memory_metrics=None
            )
        
        # Calculate working memory metrics
        metrics = self._calculate_working_memory_metrics(action_trace, checkpoint)
        
        evaluation = CheckpointEvaluation(
            checkpoint_id=checkpoint.id,
            task_success=True,
            working_memory_metrics=metrics,
            action_trace_summary=self._summarize_trace(action_trace)
        )
        
        self.checkpoint_evaluations.append(evaluation)
        return evaluation
    
    def _calculate_working_memory_metrics(self, trace: List[ActionTraceEntry], 
                                        checkpoint: CheckpointSpec) -> Dict[str, float]:
        """Calculate comprehensive working memory metrics"""
        
        # Pillar 1: Memory Fidelity
        context_reread_rate = self._calculate_context_reread_rate(trace)
        compression_quality = self._calculate_compression_quality(trace)
        
        # Pillar 2: Contextual Relevance
        relevance_f1_score = self._calculate_relevance_f1_score(trace, checkpoint)
        
        # Pillar 3: Behavioral Integrity  
        error_correction_overhead = self._calculate_error_correction_overhead(trace)
        state_coherence_index = self._calculate_state_coherence_index(trace)
        
        return {
            'memory_fidelity': {
                'context_reread_rate': context_reread_rate,
                'compression_quality': compression_quality,
                'overall_fidelity': np.mean([1-context_reread_rate, compression_quality])
            },
            'contextual_relevance': {
                'relevance_f1_score': relevance_f1_score,
                'overall_relevance': relevance_f1_score
            },
            'behavioral_integrity': {
                'error_correction_overhead': error_correction_overhead,
                'state_coherence_index': state_coherence_index,
                'overall_integrity': np.mean([1-error_correction_overhead, state_coherence_index])
            }
        }
```

## Implementation Roadmap

### Week 1-2: Core Infrastructure
```bash
git clone https://github.com/paul-gauthier/aider.git
cd aider
git checkout -b workmemeval-integration

# Add basic evaluation mode
# Implement task specification loader  
# Add minimal action tracing hooks
```

### Week 3-4: Deep Integration
```bash
# Add comprehensive behavioral capture
# Implement checkpoint management
# Build test monitoring system
# Add three-pillar evaluator
```

### Week 5-6: Memory System Interface
```bash
# Add pluggable memory system support
# Implement baseline memory systems
# Add memory operation tracking
# Build comparative evaluation
```

### Week 7-8: Research Platform
```bash
# Add batch evaluation capabilities
# Build analysis and visualization tools
# Create example task specifications
# Write comprehensive documentation
```

This integrated architecture gives us **unprecedented insight** into agent working memory while maintaining Aider's proven capabilities. The result is a research platform that can advance our understanding of agentic working memory through rigorous, objective measurement.