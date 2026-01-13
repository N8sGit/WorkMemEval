# WorkMemEval: A Working Memory Benchmark for Agentic AI

## Abstract
**WorkMemEval** is a specialized benchmark designed to evaluate the **working memory** capabilities of autonomous agents. Unlike traditional benchmarks that focus solely on correctness or "needle in the haystack" search and retrieval, WorkMemEval measures an agent's ability to maintain **Memory Fidelity** (retention), **Contextual Relevance** (filtering noise), and **Behavioral Integrity** (adapting to dynamic rule changes) over extended multi-step tasks. It employs an **Agentified Benchmark** architecture where a "Green Agent" (the Assessor) actively manages the environment, injects state-based probes, and evaluates the "Purple Agent" (the Assessee) in real-time.

---

## Overview

### The Green Agent (The Benchmark)
The **Assessor Agent** acts as the environment manager and judge. It:
1.  **Orchestrates Execution**: Manages the task lifecycle (Task Start, Checkpoints, Completion).
2.  **Injects Probes**: Dynamically introduces memory challenges (e.g., "Ignore this distractor file", "Update your plan based on this new security alert") using an **Interruption Flow** that pauses execution to test the agent's response.
3.  **Evaluates Pillars**: Scores the agent based on state changes (did the code reflect the new rule?) and behavior (did it read the distractor?) rather than just final output text.

### The Baseline Purple Agent
The **ReferenceWorkMemAgent** (`src/agents/reference_agent.py`) is included as a baseline "Purple Agent". It serves as a gold-standard implementation that:
*   demonstrates the **A2A (Agent-to-Agent)** protocol required to interact with the benchmark.
*   implements a reference memory architecture (currently `SimpleContextMemory`).
*   is capable of solving the tasks and responding correctly to memory probes.

---

## Evaluation Methodology: The Three Pillars

WorkMemEval moves beyond binary pass/fail by scoring agents on three orthogonal dimensions of working memory:

| Pillar | Definition | How it's Measured |
| :--- | :--- | :--- |
| **Contextual Relevance** | The ability to filter out irrelevant information (noise) and focus only on what matters. | **Passive**: Tracking if the agent reads "distractor" files (e.g., `newsletter.txt`). <br> **Active**: Injecting irrelevant urgent requests and verifying the agent ignores them. |
| **Behavioral Integrity** | The ability to maintain consistent behavior and adapt correctly when rules or contexts change dynamically. | **Active**: "Specification Drift" probes (e.g., "Policy Update: Ban Vendor X") mid-task. Scored by verifying the final code/decisions reflect the *new* rule. |
| **Memory Fidelity** | The ability to retain specific details over time and recall them accurately without degradation. | **Active**: "N-Back" probes asking for details provided steps ago. **Metric**: Context Reread Rate (how often files are re-read). |

---

## Benchmark Design Quality
*   **Realistic Scenarios**: Tasks mimic real-world software engineering (e.g., `compliance_clerk` handling expense reports, `ecommerce_refactor` splitting a monolith).
*   **Dynamic Environments**: Unlike static evaluations, the environment changes. Rules update, distractors appear, and the agent must adapt.
*   **State-Based Verification**: Success is measured by inspecting the actual side-effects (files written, code implemented) and running pytest suites, not just LLM-as-a-Judge text evaluation.

---

## Getting Started

### Prerequisites
*   Docker Desktop (macOS) or Docker Engine
*   Python 3.10+ (for local development)

### Quick Start (Docker)
The easiest way to run the benchmark is using the provided Docker image. This runs the **Green Agent** (Assessor) evaluating the bundled **Purple Agent** (Reference).

```bash
# Build the image
docker compose -f docker/compose.dev.yml build

# Run the 'compliance_clerk' task
docker compose -f docker/compose.dev.yml run --rm eval python3 -m src.cli run --task tasks/yaml/compliance_clerk.yaml
```

### Local Development
If you prefer running locally without Docker:

```bash
# Install dependencies
pip install -r requirements/dev.txt

# Run the benchmark with the Reference Agent
python3 -m src.cli run --task tasks/yaml/compliance_clerk.yaml --no-container
```

---

## Repository Structure

*   `src/agents/assessor.py`: **The Green Agent**. Logic for probe scheduling, interruption, and scoring.
*   `src/agents/reference_agent.py`: **The Purple Agent**. Baseline implementation.
*   `tasks/yaml/`: Task definitions (Checkpoints, Probes, Success Criteria).
*   `src/core/`: Core data structures (`MemoryPillar`, `ProbeType`, `ActionTrace`).
*   `docker/`: Dockerfile and Compose configuration for isolated execution.

---

## Containerized execution (default)

By default, the CLI runs checkpoint tests inside a hardened Docker container for isolation and reproducibility:
- Non-root user (UID/GID 10001)
- Read-only root filesystem, with tmpfs /tmp
- Dropped Linux capabilities and no-new-privileges
- CPU/memory limits
- Network disabled for tests by default
- Narrow mounts:
  - evaluation_workspace → /workspace (read-write)
  - repository → /app (read-only)

This minimizes risk when executing untrusted tests and keeps runs deterministic across machines.

### Prerequisites
- Docker Desktop (macOS) or Docker Engine

### Build the local image

```
# From repository root
docker compose -f docker/compose.dev.yml build
```

### Run an evaluation (containerized)

```
python3 -m src.cli run --task tasks/simple_calculator.json
```

- Containerized is now the default.
- To customize the image tag:

```
python3 -m src.cli run --task tasks/simple_calculator.json --docker-image workmemeval/eval:local
```

### Disable containerization (local test execution)

```
python3 -m src.cli run --task tasks/simple_calculator.json --no-container
```

Use this only if you need to debug locally without Docker. It’s less isolated.

### Direct compose usage

```
# Run a single test directly (network disabled by default)
docker compose -f docker/compose.dev.yml run --rm eval python3 -m pytest -q /workspace/tests/test_calculator_cp1.py
```

### Outputs
- Results are written to `evaluation_runs/<task_id>/<timestamp>.json`
- The working directory for a run defaults to `evaluation_workspace/<task_id>` unless you pass `--workspace`.

## Security notes
- SecureFileOperations restricts agent file I/O to the working directory with path validation, extension allow-listing, and size limits.
- Containerized tests add OS-level isolation and resource controls.
- .gitignore blocks common local artifacts and .env; pre-commit hooks provide linting and basic security checks.

## CI overview
- CI builds the evaluation image and runs the test suite inside the container (network disabled) for deterministic results.
- Pre-commit hooks run in CI.
- pip-audit checks dependencies listed in `requirements/dev.txt`.

## Adding New Challenges

WorkMemEval supports defining challenges (tasks) using a simple YAML format. This allows you to rapidly create new evaluation scenarios without writing complex Python configuration code.

### 1. Define the Task Specification (YAML)

Create a new `.yaml` file in `tasks/yaml/` (e.g., `tasks/yaml/my_new_task.yaml`). This file defines the "contract" for the task, including checkpoints, success criteria, and memory probes.

**Key Fields:**
*   **`task_id`**: Unique identifier (e.g., `ecommerce_refactor`).
*   **`repository.template_name`**: The name of the folder you will create in Step 2.
*   **`working_history`**: (Optional) A list of pre-existing context or history items to stress the agent's memory from the start.
*   **`history_file`**: (Optional) Path to a JSON or YAML file containing pre-existing context (useful for very long contexts).
*   **`checkpoints`**: A list of milestones. Each needs:
    *   `stub_file`: The file the agent should modify.
    *   `test_file`: The test file used to verify success (path relative to the template root).
*   **`memory_probes`**: Injections to test memory pillars (e.g., `distractor_injection`, `context_switch`).

**Example Snippet (Bringing Your Own Context):**
```yaml
task_id: custom_audit_01
title: Custom Security Audit
history_file: "my_contexts/security_policy_v2.json"  # Point to your own long context
checkpoints:
  - id: verify_compliance
    stub_file: src/config.py
    test_file: tests/test_security.py
    requirements: "Ensure the config follows the historical security policy."
```

**Format for `history_file` (JSON):**
```json
[
  {
    "role": "system",
    "content": "A 5000-token document describing complex organizational rules..."
  },
  {
    "role": "user",
    "content": "We are starting the Q1 migration."
  }
]
```


### 2. Create the Repository Template

Create a directory in `templates/` that matches your `template_name`. This defines the initial environment the agent starts with.

**Directory Structure:**
```text
WorkMemEval/
├── templates/
│   └── my_task_template/       # Your template_name
│       ├── src/
│       │   └── main.py         # The stub file (initial state)
│       ├── tests/
│       │   ├── test_cp1.py     # Test for Checkpoint 1
│       │   └── test_cp2.py     # Test for Checkpoint 2
│       └── README.md           # Optional context
```

### 3. Verification

Run the task using the CLI to ensure the harness loads it correctly and the agent can interact with it.

```bash
python3 -m src.cli run --task tasks/yaml/my_new_task.yaml
```

## Custom Agent Implementation

WorkMemEval allows you to plug in your own agent implementation (e.g., LangChain, LlamaIndex, or custom logic) by implementing a simple interface.

### 1. Implement the Interface

Create a Python class that inherits from `AgentImplementation`. You must implement three methods:

```python
# my_project/my_agent.py
from src.core.plugin_interfaces import AgentImplementation, PluginCapabilities

class MyCustomAgent(AgentImplementation):
    def __init__(self, memory_system, config):
        super().__init__(memory_system, config)
        self.api_key = config.get("api_key")
        
    def get_capabilities(self) -> PluginCapabilities:
        return PluginCapabilities(supports_images=False)

    async def execute_checkpoint(self, checkpoint) -> bool:
        # 1. Retrieve context from memory
        context = self.memory_system.retrieve_information(checkpoint.requirements)
        
        # 2. Run your agent logic (The "Black Box")
        # Your agent should read files, think, and modify the codebase
        success = await self.my_agent_logic(checkpoint, context)
        
        return success

    def get_behavioral_trace(self):
        # Return a log of actions for evaluation metrics
        return self.trace_log
```

### 2. Run with Your Agent

Use the `--agent` flag to point to your class using Python module path syntax (`module:Class`).

```bash
python3 -m src.cli run \
  --task tasks/yaml/compliance_clerk.yaml \
  --agent my_project.my_agent:MyCustomAgent \
  --agent-config '{"api_key": "sk-..."}'
```

The harness will dynamically load your class, instantiate it with the memory system, and run the evaluation.

---

## Bringing Your Own Context (BYOC)

WorkMemEval allows you to simulate a "working history" by injecting pre-existing context into the agent's memory before the task begins. This is critical for testing an agent's ability to retrieve information from a long, multi-turn history without explicit prompting.

### 1. Specify History in YAML
You can provide history either **inline** or via an **external file**.

#### Option A: Inline History
Add the `working_history` field directly to your task specification. Each item in the history represents a previous interaction or context block.

```yaml
task_id: legacy_migration_01
title: Legacy System Migration
working_history:
  - role: system
    content: "Architectural Decision: All new microservices must use gRPC for internal communication."
  - role: user
    content: "We previously decided to avoid XML-RPC due to security concerns."
```

#### Option B: External History File (Recommended for Long Contexts)
For very large contexts (thousands of tokens), use the `history_file` field to point to a JSON or YAML file containing your history list.

```yaml
task_id: legacy_migration_01
history_file: "path/to/my_long_context.json"
```

**Format for `my_long_context.json`:**
```json
[
  {
    "role": "system",
    "content": "A very long document describing the legacy database schema..."
  },
  {
    "role": "user",
    "content": "Can you summarize the performance bottlenecks we found last week?"
  }
]
```

### 2. How it Works
When the benchmark starts:
1.  The **Assessor Agent** resolves and bundles the history into the initial session handshake.
2.  The **Assessee Adapter** propagates this to the agent via `agent.initialize_working_history(history)`.
3.  The agent stores these items in its `MemorySystem` immediately, making them available for retrieval during the task.

This feature allows you to "stress test" memory by bringing real-world context that the agent must navigate to find critical constraints.

---

## Organizing Custom Task Libraries

WorkMemEval is designed to be highly flexible. You can organize your own tasks and contexts in any directory structure outside of the core `tasks/` folder.

### Recommended Structure
```text
my_eval_project/
├── tasks/
│   ├── migration_v1.yaml
│   └── audit_v2.yaml
├── contexts/
│   ├── legacy_docs.json
│   └── previous_decisions.yaml
└── templates/
    └── my_custom_app/
```

### Running from Custom Locations
When running the CLI, simply provide the path to your YAML file. Use `--workspace` to control where the evaluation runs.

```bash
python3 -m src.cli run \
  --task ../my_project/tasks/migration_v1.yaml \
  --workspace ./custom_runs/migration_test
```

The `history_file` path in your YAML can be absolute or relative to the directory where you run the CLI command.

