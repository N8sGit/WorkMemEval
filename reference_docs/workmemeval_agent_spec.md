# WorkMemEval Coding Agent Implementation Spec

## 1. Architecture Overview

### Single-Agent Architecture with Memory Separation
Following the research guidance that "single-agent architectures consistently outperform complex multi-agent coordination in production environments," we implement a unified agent with separated memory systems.

```python
class WorkMemEvalAgent:
    def __init__(self):
        self.working_memory = WorkingMemory()  # Session-specific, task-focused
        self.persistent_memory = PersistentMemory()  # Long-term patterns & solutions
        self.planner = TaskPlanner()
        self.executor = CodeExecutor()
        self.observer = StateObserver()
```

### Core Components
- **Memory Manager**: Dual-tier memory (working + persistent)
- **Task Planner**: Plan-and-Execute pattern for cost reduction
- **Code Executor**: Unified diff editing with Docker containerization
- **State Observer**: Comprehensive logging for benchmark evaluation
- **Tool Interface**: Minimal tool set (bash, file editing, testing)

## 2. Memory Architecture (Critical Component)

### Working Memory (RAM-equivalent)
```python
class WorkingMemory:
    def __init__(self):
        self.current_task = None
        self.active_files = {}  # filename -> file_state
        self.dependency_graph = {}  # file -> dependencies
        self.test_results = []
        self.error_history = []
        self.progress_checkpoints = []
        self.context_window = []  # L1 cache - recent files
        
    def update_state(self, step_id, state_change):
        """Track state changes for WorkMemEval metrics"""
        self.progress_checkpoints.append({
            'step': step_id,
            'timestamp': time.time(),
            'change': state_change,
            'snapshot': self.create_snapshot()
        })
```

### Persistent Memory (Long-term Knowledge)
```python
class PersistentMemory:
    def __init__(self):
        self.solution_patterns = {}  # problem_type -> solution_template
        self.file_summaries = {}  # L2 cache - file interfaces
        self.codebase_index = None  # L3 storage - vector database
        self.learned_dependencies = {}
        self.successful_strategies = []
        
    def store_solution_pattern(self, problem_type, solution, success_score):
        """Episodic memory for solution reuse"""
        if problem_type not in self.solution_patterns:
            self.solution_patterns[problem_type] = []
        
        self.solution_patterns[problem_type].append({
            'solution': solution,
            'success_score': success_score,
            'timestamp': time.time()
        })
```

## 3. Task Planning & Execution

### Plan-and-Execute Pattern
```python
class TaskPlanner:
    def __init__(self, llm_client):
        self.llm = llm_client
        
    def generate_plan(self, task_description, codebase_context):
        """Generate comprehensive multi-step plan upfront"""
        system_prompt = """You are an expert software engineer. Analyze the task and create a detailed plan.
        
        Format your response as:
        PLAN:
        1. [Step description] - [Expected outcome] - [Files involved]
        2. [Step description] - [Expected outcome] - [Files involved]
        ...
        
        DEPENDENCIES:
        - Step X depends on Step Y
        
        RISK_ASSESSMENT:
        - [Potential issues and mitigation strategies]
        """
        
        response = self.llm.generate(system_prompt, task_description, codebase_context)
        return self.parse_plan(response)
```

### State Machine Workflow
```python
from langgraph import StateGraph, END

class AgentState(TypedDict):
    task: str
    plan: List[Dict]
    current_step: int
    files_modified: List[str]
    test_results: Dict
    errors: List[str]
    memory_snapshot: Dict

def create_workflow():
    workflow = StateGraph(AgentState)
    
    # Define nodes
    workflow.add_node("initialize", initialize_task)
    workflow.add_node("plan", generate_plan)
    workflow.add_node("code", execute_code_changes)
    workflow.add_node("test", run_tests)
    workflow.add_node("debug", handle_errors)
    workflow.add_node("review", review_changes)
    
    # Define edges with conditions
    workflow.set_entry_point("initialize")
    workflow.add_edge("initialize", "plan")
    workflow.add_edge("plan", "code")
    workflow.add_conditional_edges("code", should_test, {"test": "test", "review": "review"})
    workflow.add_conditional_edges("test", handle_test_results, 
                                 {"debug": "debug", "code": "code", "review": "review"})
    workflow.add_edge("debug", "code")
    workflow.add_edge("review", END)
    
    return workflow.compile()
```

## 4. Code Execution & Editing

### Unified Diff Format (3x more effective than JSON)
```python
class CodeEditor:
    def __init__(self):
        self.diff_generator = DiffGenerator()
        self.validator = CodeValidator()
        
    def apply_changes(self, file_path, modifications):
        """Apply code changes using unified diff format"""
        original_content = self.read_file(file_path)
        
        # Generate unified diff
        diff_prompt = f"""
        Apply the following changes to the code using unified diff format:
        
        Original file: {file_path}
        
        Changes needed: {modifications}
        
        Provide response in format:
        ```diff
        --- a/{file_path}
        +++ b/{file_path}
        @@ -line_start,line_count +line_start,line_count @@
         context_line
        -removed_line
        +added_line
         context_line
        ```
        """
        
        diff_response = self.llm.generate(diff_prompt)
        diff_patch = self.parse_diff(diff_response)
        
        # Apply patch
        new_content = self.apply_patch(original_content, diff_patch)
        
        # Validate changes
        if self.validator.is_valid(new_content, file_path):
            self.write_file(file_path, new_content)
            return True
        else:
            self.handle_validation_error(file_path, diff_patch)
            return False
```

### Docker Containerization
```python
import docker
from fastapi import FastAPI

class DockerExecutionEnvironment:
    def __init__(self):
        self.client = docker.from_env()
        self.app = FastAPI()
        self.active_containers = {}
        
    def create_container(self, task_id, base_image="python:3.11"):
        """Create isolated container for code execution"""
        container = self.client.containers.run(
            image=base_image,
            command="tail -f /dev/null",  # Keep alive
            detach=True,
            name=f"workmemeval_{task_id}",
            volumes={
                f"/tmp/task_{task_id}": {
                    'bind': '/workspace', 
                    'mode': 'rw'
                }
            },
            working_dir='/workspace',
            network_disabled=False,  # Allow network for package installation
            mem_limit='1g',
            cpu_quota=50000  # 50% CPU limit
        )
        
        self.active_containers[task_id] = container
        return container
    
    def execute_command(self, task_id, command, timeout=30):
        """Execute command in container with safety measures"""
        container = self.active_containers[task_id]
        
        try:
            result = container.exec_run(
                command, 
                timeout=timeout,
                workdir='/workspace'
            )
            return {
                'exit_code': result.exit_code,
                'output': result.output.decode('utf-8'),
                'success': result.exit_code == 0
            }
        except docker.errors.APIError as e:
            return {
                'exit_code': -1,
                'output': str(e),
                'success': False
            }
```

## 5. Tool Interface (Minimal Set)

### Core Tools Following SWE-agent Success
```python
class AgentTools:
    def __init__(self, container_env):
        self.container = container_env
        
    def bash_execute(self, command: str) -> Dict:
        """Execute bash command in container"""
        return self.container.execute_command(command)
    
    def file_read(self, file_path: str) -> str:
        """Read file content"""
        result = self.bash_execute(f"cat {file_path}")
        return result['output'] if result['success'] else ""
    
    def file_write(self, file_path: str, content: str) -> bool:
        """Write content to file"""
        # Escape content for shell
        escaped_content = content.replace("'", "'\"'\"'")
        result = self.bash_execute(f"cat > {file_path} << 'EOF'\n{content}\nEOF")
        return result['success']
    
    def file_edit_diff(self, file_path: str, diff_patch: str) -> bool:
        """Apply unified diff patch"""
        # Write patch to temporary file
        patch_file = f"/tmp/patch_{hash(diff_patch)}.patch"
        self.file_write(patch_file, diff_patch)
        
        # Apply patch
        result = self.bash_execute(f"patch {file_path} < {patch_file}")
        return result['success']
    
    def run_tests(self, test_command: str = "python -m pytest") -> Dict:
        """Execute test suite"""
        return self.bash_execute(test_command)
    
    def lint_code(self, file_path: str) -> Dict:
        """Run linting on file"""
        return self.bash_execute(f"python -m flake8 {file_path}")
```

## 6. Observability & Monitoring

### Langfuse Integration for Comprehensive Tracing
```python
from langfuse import Langfuse
from langfuse.decorators import observe

class ObservabilityManager:
    def __init__(self):
        self.langfuse = Langfuse()
        self.current_trace = None
        
    @observe()
    def start_task_trace(self, task_description, task_id):
        """Start comprehensive task tracing"""
        self.current_trace = self.langfuse.trace(
            name="workmemeval_task",
            input={"task": task_description, "task_id": task_id},
            metadata={"benchmark": "WorkMemEval", "agent_version": "1.0"}
        )
        return self.current_trace
    
    @observe()
    def log_memory_state(self, step_id, memory_snapshot):
        """Log memory state for WorkMemEval analysis"""
        self.langfuse.event(
            name="memory_checkpoint",
            input={"step": step_id, "memory": memory_snapshot},
            metadata={"type": "working_memory"}
        )
    
    @observe()
    def log_tool_call(self, tool_name, tool_input, tool_output, success):
        """Track all tool interactions"""
        self.langfuse.span(
            name=f"tool_{tool_name}",
            input=tool_input,
            output=tool_output,
            metadata={"success": success, "tool_type": tool_name}
        )
```

### WorkMemEval Specific Metrics Collection
```python
class WorkMemEvalMetrics:
    def __init__(self):
        self.step_history = []
        self.state_changes = []
        self.interruption_points = []
        
    def record_step(self, step_id, memory_state, files_touched, success):
        """Record step for WSI calculation"""
        self.step_history.append({
            'step_id': step_id,
            'memory_state': memory_state,
            'files_touched': files_touched,
            'success': success,
            'timestamp': time.time()
        })
    
    def calculate_working_span_index(self):
        """Calculate longest successful chain without losing state"""
        max_span = 0
        current_span = 0
        
        for step in self.step_history:
            if step['success'] and self.has_coherent_state(step):
                current_span += 1
                max_span = max(max_span, current_span)
            else:
                current_span = 0
                
        return max_span
    
    def calculate_sustained_recall_accuracy(self, n_steps_back=5):
        """Calculate % of facts recalled correctly after N steps"""
        if len(self.step_history) < n_steps_back:
            return 0.0
            
        recent_steps = self.step_history[-n_steps_back:]
        correct_recalls = 0
        total_recalls = 0
        
        for step in recent_steps:
            facts_to_verify = self.extract_verifiable_facts(step)
            for fact in facts_to_verify:
                total_recalls += 1
                if self.verify_fact_accuracy(fact):
                    correct_recalls += 1
                    
        return correct_recalls / total_recalls if total_recalls > 0 else 0.0
```

## 7. Main Agent Implementation

### Core Agent Class
```python
class WorkMemEvalCodingAgent:
    def __init__(self, llm_config, task_config):
        # Core components
        self.llm = self.initialize_llm(llm_config)
        self.memory_manager = MemoryManager()
        self.planner = TaskPlanner(self.llm)
        self.executor = CodeExecutor(self.llm)
        self.tools = AgentTools(DockerExecutionEnvironment())
        self.observer = ObservabilityManager()
        self.metrics = WorkMemEvalMetrics()
        
        # Workflow
        self.workflow = create_workflow()
        
    def execute_task(self, task_description, codebase_path):
        """Main entry point for WorkMemEval task execution"""
        # Start observability
        trace = self.observer.start_task_trace(task_description, 
                                             hashlib.md5(task_description.encode()).hexdigest())
        
        try:
            # Initialize state
            initial_state = AgentState(
                task=task_description,
                plan=[],
                current_step=0,
                files_modified=[],
                test_results={},
                errors=[],
                memory_snapshot={}
            )
            
            # Execute workflow
            final_state = self.workflow.invoke(initial_state)
            
            # Calculate metrics
            metrics = self.metrics.calculate_all_metrics()
            
            return {
                'success': len(final_state['errors']) == 0,
                'final_state': final_state,
                'metrics': metrics,
                'trace_id': trace.id
            }
            
        except Exception as e:
            self.observer.langfuse.event(
                name="task_error",
                input={"error": str(e)},
                metadata={"error_type": type(e).__name__}
            )
            raise
    
    def handle_interruption(self, interruption_data):
        """Handle WorkMemEval interruption scenarios"""
        # Save current state
        current_state = self.memory_manager.create_full_snapshot()
        
        # Process interruption
        interruption_result = self.process_interruption(interruption_data)
        
        # Attempt to resume
        resume_success = self.resume_from_snapshot(current_state)
        
        # Record for RSR metric
        self.metrics.record_interruption(current_state, interruption_result, resume_success)
        
        return resume_success
```

## 8. Configuration & Deployment

### Environment Setup
```python
# requirements.txt
langchain>=0.1.0
langgraph>=0.0.40
langfuse>=2.0.0
docker>=6.0.0
fastapi>=0.100.0
tree-sitter>=0.20.0
gitpython>=3.1.0
pytest>=7.0.0
```

### Agent Configuration
```python
agent_config = {
    "llm": {
        "provider": "anthropic",  # or "openai"
        "model": "claude-3-sonnet-20240229",
        "temperature": 0.1,
        "max_tokens": 4000
    },
    "memory": {
        "working_memory_size": 1000,  # number of items
        "persistent_memory_path": "./memory/persistent.db",
        "context_window_size": 50000,  # tokens
        "memory_consolidation_threshold": 100
    },
    "execution": {
        "docker_base_image": "python:3.11",
        "timeout_seconds": 300,
        "resource_limits": {
            "memory": "2g",
            "cpu_quota": 100000
        }
    },
    "observability": {
        "langfuse_enabled": True,
        "trace_level": "detailed",
        "metrics_collection": True
    }
}
```

## 9. Integration with WorkMemEval Benchmark

### Benchmark Adapter
```python
class WorkMemEvalAdapter:
    """Adapter for integrating agent with WorkMemEval benchmark suite"""
    
    def __init__(self, agent):
        self.agent = agent
        self.test_environments = {}
        
    def load_test_environment(self, env_config):
        """Load specific WorkMemEval test environment"""
        # Setup codebase
        codebase = self.setup_codebase(env_config['codebase_template'])
        
        # Configure complexity parameters
        complexity_params = {
            'working_span_target': env_config['target_working_span'],
            'interference_level': env_config['interference_parameters'],
            'context_switch_frequency': env_config['interruption_schedule']
        }
        
        return TestEnvironment(codebase, complexity_params)
    
    def run_evaluation(self, test_suite):
        """Execute full WorkMemEval test suite"""
        results = {}
        
        for test_case in test_suite:
            env = self.load_test_environment(test_case['environment'])
            result = self.agent.execute_task(
                test_case['task_description'],
                env.codebase_path
            )
            
            results[test_case['id']] = {
                'success': result['success'],
                'metrics': result['metrics'],
                'trace_id': result['trace_id']
            }
            
        return self.aggregate_results(results)
```

## 10. Key Design Principles

1. **Simplicity Over Complexity**: Single-agent architecture with minimal tool set
2. **Memory-Centric**: Sophisticated memory management as the primary performance driver
3. **Observable**: Comprehensive tracing for benchmark analysis
4. **Controllable**: Step-by-step execution with explicit checkpoints
5. **Safe**: Docker containerization with resource limits
6. **Reproducible**: Deterministic execution with proper state management
7. **Extensible**: Modular design allowing easy enhancement for research

This implementation provides the foundation for a WorkMemEval-compatible coding agent that prioritizes the architectural patterns proven most effective by current research while maintaining the observability and control necessary for rigorous benchmark evaluation.