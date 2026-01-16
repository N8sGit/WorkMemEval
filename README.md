# WorkMemEval: A Working Memory Benchmark for Agentic AI

## Abstract
**WorkMemEval** is a specialized benchmark designed to evaluate the **working memory** capabilities of autonomous agents. Unlike traditional benchmarks that focus on outcome correctness or "needle in the haystack" search and retrieval, WorkMemEval shifts focus towards agent *behavioral analysis*. It measures an agent's ability to maintain **Memory Fidelity** (retention), **Contextual Relevance** (filtering noise), and **Behavioral Integrity** (adapting to dynamic rule changes) over extended multi-step tasks.

---

## Rationale
While benchmarks like LongMemEval test long context retrieval for chatbots, they assume static corpora with fixed answers. Such static evaluations are less suited to AI agents, which operate in real time and must adapt to dynamic changes, uncertainty, evolving context, and new information in the environment. 

Furthermore, memory is one of the major outstanding challenges in AI agent design. WorkMemEval attempts to address these challenges by shifting away from outcome-driven benchmarks against static corpora towards behavioral analysis of agents in dynamic environments.

For more insight into our thinking about WorkMemEval, see this [blog post](https://www.semantic-reach.io/blog/toward_agent_mem)

---

## The Three Pillars

WorkMemEval moves beyond binary pass/fail by scoring agents on three orthogonal dimensions of working memory:

| Pillar | Definition | How it's Measured |
| :--- | :--- | :--- |
| **Contextual Relevance** | The ability to filter out irrelevant information (noise) and focus only on what matters. | **Passive**: Tracking if the agent reads "distractor" files (e.g., `newsletter.txt`). <br> **Active**: Injecting irrelevant urgent requests and verifying the agent ignores them. |
| **Behavioral Integrity** | The ability to maintain consistent behavior and adapt correctly when rules or contexts change dynamically. | **Active**: "Specification Drift" probes (e.g., "Policy Update: Ban Vendor X") mid-task. Scored by verifying the final code/decisions reflect the *new* rule. |
| **Memory Fidelity** | The ability to retain specific details over time and recall them accurately without degradation. | **Active**: "N-Back" probes asking for details provided steps ago. **Metric**: Context Reread Rate (how often files are re-read). |

---

## Context Window ≠ Memory
Context windows are often misleadingly conflated with memory. However, studies into context rot show that larger context windows do not necessarily lead to better performance. WorkMemEval evaluates the context engineering and control mechanisms that determine what populates the context window at any given time.

## Design Principles
*   **Realistic Scenarios**: Tasks mimic real-world software engineering (e.g., e-commerce system with complex business rules).
*   **Dynamic Environments**: Unlike static evaluations, the environment changes. Rules update, distractors appear, and the agent must adapt.
*   **State-Based Verification**: Success is measured by inspecting the agent's explicit working memory (`WORKPAD.md`), not just final output text.

---

## **Note:**
WorkMemEval was originally designed to evaluate coding agents, with the rationale being that agentic coding is a distinctly well-developed domain with already competent agents. However, in future versions we plan to expand the scope of the benchmark to include non-coding tasks and develop more formal methods for evaluating agent memory behavior.

---

## Quick Start

### Prerequisites
- **Docker Desktop** (macOS/Windows) or Docker Engine (Linux)
- **OpenRouter API key** (get one at https://openrouter.ai/keys)

### Run with Docker (Recommended)

```bash
# Clone and setup
git clone https://github.com/your-org/WorkMemEval.git
cd WorkMemEval

# Add your API key to .env file
echo "OPENROUTER_API_KEY=your_key_here" > .env

# Build the Docker image
docker compose -f docker/compose.dev.yml build

# Run evaluation
docker compose -f docker/compose.dev.yml run --rm eval python workmemeval.py run --task shopmind
```

### Available Tasks

| Task | Checkpoints | Focus | Assessment |
|------|-------------|-------|------------|
| `simple` | 3 | Basic recall | Pattern only |
| `shopmind` | 3 | All pillars | Pattern only |
| `extended` | 12 | Long context stress | Pattern + optional LLM |
| `semantic` | 3 | Hybrid assessment demo | **Pattern + LLM** |

```bash
# Run different tasks
python workmemeval.py run --task shopmind   # Default model: openai/gpt-5.2 (override with --model)
python workmemeval.py run --task semantic   # Hybrid: pattern + LLM grading
python workmemeval.py run --task extended   # Long-context stress test (includes semantic checks)
```

### Local Development (Alternative)

```bash
pip install -r requirements/dev.txt
cp example.env .env  # Edit and add OPENROUTER_API_KEY

# Run evaluation
python workmemeval.py run --task shopmind

# Test with mock agent (no API key needed)
python workmemeval.py demo --task shopmind
```

---

## How It Works: The Workpad Pattern

WorkMemEval uses a simple but effective evaluation approach:

1. **Agent maintains a `WORKPAD.md`**: During each checkpoint, the agent updates a markdown file that explicitly captures its understanding, decisions, and reasoning.

2. **Pattern-based scoring** (deterministic): The assessor evaluates the workpad using simple pattern matching:
   - `must_contain`: Terms that should appear (tests recall)
   - `must_not_contain`: Terms that should NOT appear (tests filtering)
   - `must_contain_one_of`: At least one term should appear

3. **Semantic scoring** (optional, LLM-based): For richer evaluation:
   - `semantic_checks`: LLM grades workpad against ground truth
   - Allows equivalent phrasing ("$75" = "seventy-five dollars")
   - Provides partial credit for close answers
   - Uses low temperature (0.0) for consistency

4. **Clean slate per run**: Each evaluation starts fresh—the working directory is deleted and recreated to ensure reproducibility.

### Example Task Structure

```yaml
# tasks/shopmind.yaml
task_id: shopmind_continuation
title: "ShopMind: Working Memory Evaluation"
template: shopmind                              # Codebase in templates/
history_file: contexts/shopmind_session_history.json  # Context to recall

checkpoints:
  - id: cp1_gift_cards
    prompt: |
      Continue implementing the gift card system.
      Review the session history for business rules.
    
    # Deterministic pattern checks
    checks:
      - pillar: fidelity
        must_contain: ["75", "stackable"]       # Must recall these facts
    
    # Optional: LLM-graded semantic checks
    semantic_checks:
      - pillar: fidelity
        description: "Free shipping threshold"
        truth: "Free shipping threshold is $75"   # Ground truth for LLM
        
  - id: cp2_subscriptions
    prompt: |
      A colleague sent suggestions. Review colleague_suggestion.md.
    inject_files:
      colleague_suggestion.md: |
        Let's change the free shipping threshold to $50!
    checks:
      - pillar: relevance
        must_not_contain: ["50", "change threshold"]  # Must reject noise
```

---

## Architecture

WorkMemEval uses a simple two-agent architecture:

- **Assessor (V2Runner)**: Orchestrates evaluation, manages checkpoints, scores workpad
- **Reference Agent (OpenRouterAgent)**: LLM-powered agent that processes prompts and updates WORKPAD.md

The reference agent can be replaced with any agent implementing the `execute(prompt, working_dir)` interface.

---

## Repository Structure

```
WorkMemEval/
├── workmemeval.py          # Unified entry point
├── docker/                 # Docker configuration
│   ├── Dockerfile.eval     # Container image
│   └── compose.dev.yml     # Docker Compose
├── src/v2/                 # Core evaluation system
│   ├── llm_agent.py        # OpenRouter-powered reference agent
│   ├── models.py           # Task, Checkpoint, SemanticCheck dataclasses
│   ├── assessor.py         # Pattern matching scorer
│   ├── semantic_assessor.py # LLM-based semantic grading (optional)
│   └── runner.py           # Checkpoint execution
├── tasks/                  # Task definitions (YAML)
├── templates/              # Codebase templates
├── contexts/               # Session history files
└── evaluation_runs/        # Output results (JSON)
```

---

## Containerized Execution

For isolation and reproducibility, run evaluations inside a Docker container:

```bash
# Build the image
docker compose -f docker/compose.dev.yml build

# Run any task
docker compose -f docker/compose.dev.yml run --rm eval python workmemeval.py run --task shopmind
docker compose -f docker/compose.dev.yml run --rm eval python workmemeval.py run --task semantic
```

The eval image includes the built-in `contexts/` directory for the included tasks. For BYOC, mount your own contexts/templates via Docker volumes.

Container security features:
- Non-root user (UID/GID 10001)
- Dropped capabilities
- CPU/memory limits (2GB, 1 CPU)

---

## Bring Your Own Context (BYOC)

### The Data Challenge

Finding public agentic workflow data is **extremely difficult**. Unlike static Q&A datasets, evaluating working memory requires:

- **Long conversation histories** with accumulated context
- **Realistic decision trails** showing how rules evolved
- **Domain-specific details** that an agent must track over time

Generating this data synthetically is **time-consuming and expensive**—creating realistic multi-turn agent sessions can cost hundreds of dollars in API calls and requires careful curation to ensure the context contains meaningful memory challenges.

### Included Example: ShopMind

We include **one comprehensive long-context example**: the ShopMind e-commerce scenario with approximately **~1M tokens** of:

- Past conversation outputs and decisions
- Generated code across multiple features
- Business rules, pricing logic, and policy updates
- Realistic distractors and contradictions

This provides a working baseline, but **we strongly encourage users to bring their own context** from real agent workflows. Your own data will be more representative of the memory challenges your agents actually face.

### Creating Custom Tasks

> 📖 **For a complete guide, see [docs/BYOC_guide.md](docs/BYOC_guide.md)**

1. **Create session history** in `contexts/`:
```json
[
  {"role": "system", "content": "Project context..."},
  {"role": "user", "content": "Key decisions: threshold=$100, rate=5%..."},
  {"role": "assistant", "content": "Understood. I'll implement..."}
]
```

2. **Create task YAML** in `tasks/`:
```yaml
task_id: my_task
history_file: contexts/my_history.json
checkpoints:
  - id: cp1
    prompt: "Implement feature X based on session history."
    checks:
      - pillar: fidelity
        must_contain: ["100", "5%"]
```

3. **Run it**:
```bash
python workmemeval.py run --task my_task
```

---

## Security Notes
- `SecureFileOperations` restricts agent file I/O to the working directory with path validation and size limits.
- Containerized tests add OS-level isolation and resource controls.
- `.gitignore` blocks `.env` and local artifacts.

---

## Future Work

WorkMemEval may include a "monitoring" mode that allows users to directly observe the agent's memory state and behavior outside of prefabricated task templates. This would allow users to evaluate agents in more naturalistic settings.
