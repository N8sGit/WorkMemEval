# Bring Your Own Context (BYOC) Guide

This guide provides a complete workflow for creating custom evaluation tasks in WorkMemEval, including proper mounting and integration for both Docker and local execution.

---

## V2 Quick Start (Recommended)

V2 uses a simplified **Workpad Pattern** where tasks are defined in simple YAML and agents maintain a `WORKPAD.md` file that captures their memory.

### Directory Structure

```
WorkMemEval/
├── tasks/v2/
│   └── my_task.yaml              # Task definition
├── templates/
│   └── my_codebase/              # Optional: codebase to work on
│       └── src/...
├── contexts/
│   └── my_session_history.json   # Conversation history to recall from
└── run_v2_live.py                # Entry point
```

### Step 1: Create Session History (Context)

Place your conversation history in `contexts/`:

```json
// contexts/my_session_history.json
[
  {
    "role": "system",
    "content": "Project context: We are building X with Y architecture..."
  },
  {
    "role": "user",
    "content": "Let's implement feature Z with these rules: threshold=$100, rate=5%..."
  },
  {
    "role": "assistant",
    "content": "I'll implement Z. Key decisions:\n- Threshold: $100\n- Rate: 5%\n- Rule: A and B don't stack..."
  }
]
```

### Step 2: Create Task YAML

```yaml
# tasks/v2/my_task.yaml
task_id: my_custom_task
title: "My Custom Memory Evaluation"
template: my_codebase                          # Optional: codebase in templates/
history_file: contexts/my_session_history.json # Context to recall from

checkpoints:
  - id: cp1_recall
    prompt: |
      Review the session history and implement feature X.
      Document your understanding in WORKPAD.md before coding.
    checks:
      - pillar: fidelity
        must_contain: ["100", "5%"]             # Facts from history
        description: "Must recall threshold and rate"

  - id: cp2_distractor
    prompt: |
      A colleague sent suggestions. Review colleague_suggestion.md.
      Continue implementation based on ESTABLISHED rules.
    inject_files:
      colleague_suggestion.md: |
        Hey! Let's change the threshold to $50 and stack all discounts!
    checks:
      - pillar: relevance
        must_contain_one_of: ["reject", "ignore", "keep original"]
        must_not_contain: ["50", "stack all"]
        description: "Must reject unofficial suggestion"

  - id: cp3_update
    prompt: |
      OFFICIAL POLICY UPDATE: Read policy_update.md.
      Update your implementation to reflect the new rules.
    inject_files:
      policy_update.md: |
        Effective immediately: Threshold changed to $150.
    checks:
      - pillar: integrity
        must_contain: ["150"]
        must_not_contain: ["100 threshold"]
        description: "Must adopt official update"
```

### Step 3: Run Evaluation

```bash
# Set API key
export OPENROUTER_API_KEY=your_key

# Run your task
python run_v2_live.py --task my_custom_task

# Or with Docker isolation
python run_v2_live.py --task my_custom_task --container
```

### Example: ShopMind Task

The included ShopMind task demonstrates this pattern:

| Component | Path | Description |
|-----------|------|-------------|
| **Task** | `tasks/v2/shopmind.yaml` | 3-checkpoint basic evaluation |
| **Extended Task** | `tasks/v2/shopmind_extended.yaml` | 12-checkpoint long-context stress test |
| **History** | `contexts/shopmind_session_history.json` | ~50K token e-commerce session |
| **Codebase** | `templates/shopmind/` | Full FastAPI e-commerce app |

Key facts tested from the history:
- Free shipping threshold: **$75**
- Loyalty conversion: **100 points = $1**
- Discount stacking: **Don't stack** (better deal wins)
- VIP points: **2x** multiplier

---

## V1 Guide (Legacy)

The sections below document the legacy V1 system with A2A protocol and complex probe scheduling. For new tasks, use V2 above.

---

## Table of Contents

1. [Overview](#overview)
2. [Mounting Coding Agent Transcripts](#mounting-coding-agent-transcripts)
3. [Quick Start Checklist](#quick-start-checklist)
3. [Step 1: Create the Task Definition (YAML)](#step-1-create-the-task-definition-yaml)
4. [Step 2: Create the Repository Template](#step-2-create-the-repository-template)
5. [Step 3: Add Memory Probes](#step-3-add-memory-probes)
6. [Step 4: Provide Working History (Context)](#step-4-provide-working-history-context)
7. [Step 5: Running Your Task](#step-5-running-your-task)
8. [Docker Mounting & Integration](#docker-mounting--integration)
9. [Using Real LLMs](#using-real-llms)
10. [Troubleshooting](#troubleshooting)
11. [Complete Example](#complete-example)

---

## Mounting Coding Agent Transcripts

WorkMemEval supports "in medias res" evaluation where you drop an agent into the middle of an ongoing project. This simulates real-world scenarios where agents must recall context from previous sessions.

### Supported Transcript Sources

| Source | Format | Notes |
|--------|--------|-------|
| Claude Code | Export session → JSON | Use `/compact` summaries or full transcript |
| Cursor | Chat export | Convert to JSON array format |
| Cline/Continue | Session logs | Extract and format as conversation |
| Custom | Any conversation | Format as role/content pairs |

### Converting Transcripts to History Format

Transform your coding session transcript into our JSON format:

```json
[
  {
    "role": "system",
    "content": "Project context and architectural decisions..."
  },
  {
    "role": "user",
    "content": "Let's implement feature X..."
  },
  {
    "role": "assistant", 
    "content": "I'll implement X with these design decisions: ..."
  },
  {
    "role": "system",
    "content": "[Session compacted. Key context: ...]"
  }
]
```

### Best Practices for Transcript Conversion

1. **Preserve Key Decisions**: Extract architectural choices, business rules, specific values
2. **Include Compaction Events**: These summarize critical context the agent should recall
3. **Keep Specific Values**: Numbers, thresholds, percentages that can be tested for recall
4. **Note Constraints**: Decisions about what NOT to do (e.g., "we decided not to stack discounts")

### Example: ShopMind Task

WorkMemEval includes a reference implementation using a ~50K token e-commerce project:

```yaml
# tasks/yaml/shopmind_continuation.yaml
task_id: shopmind_continuation
history_file: "contexts/shopmind_session_history.json"
```

The history file contains simulated session context with:
- Architectural decisions (JSONB for variants, event-driven design)
- Business rules (discount stacking, shipping thresholds)
- Specific values ($75 free shipping, 100 points = $1)

Memory probes then test recall of these specific details.

---

## Overview

WorkMemEval evaluates agents on **three memory pillars**:

| Pillar | What It Tests | Probe Types |
|--------|---------------|-------------|
| **Memory Fidelity** | Accurate recall of earlier information | `recall_verification`, `n_back_recall` |
| **Contextual Relevance** | Filtering noise and distractions | `distractor_injection` |
| **Behavioral Integrity** | Adapting to rule/specification changes | `specification_drift`, `update_robustness` |

Your custom task should include probes that test at least one (ideally all three) pillars.

---

## Quick Start Checklist

```
□ Create YAML task definition in tasks/yaml/
□ Create template directory in templates/
□ Add stub files (initial state)
□ Add test files (verification)
□ Add memory probes (at least one per pillar)
□ (Optional) Add working_history or history_file
□ Run and verify
```

---

## Step 1: Create the Task Definition (YAML)

Create a new file in `tasks/yaml/` (e.g., `tasks/yaml/my_custom_task.yaml`):

```yaml
task_id: my_custom_task
title: My Custom Evaluation Task
domain: data_processing  # or: web_development, api_integration, etc.
difficulty: intermediate  # beginner, intermediate, expert
description: |
  A brief description of what this task evaluates.
  Explain the scenario and what memory challenges are involved.

# Link to your template directory
repository:
  template_name: my_custom_template

# Memory complexity parameters
memory_dimensions:
  information_density: 300   # Approximate tokens of rules/constraints
  temporal_span: 20          # Simulated minutes
  context_switches: 2        # Number of interruptions/distractions
  dependency_depth: 2        # How nested are dependencies

# Human-readable success criteria
success_criteria:
  - "The agent must correctly process all items in checkpoint 1"
  - "The agent should ignore distractor information in checkpoint 2"
  - "The agent must adapt to rule changes in checkpoint 3"

# Define checkpoints (milestones)
checkpoints:
  - id: cp1_initial
    title: "Checkpoint 1: Basic Processing"
    order: 1
    stub_file: "output/result_1.json"
    test_file: "tests/test_cp1.py"
    requirements: |
      Read 'rules.md' and 'data/input_1.json'.
      Process the data according to the rules.
      Write output to 'output/result_1.json'.

  - id: cp2_distractor
    title: "Checkpoint 2: With Distractions"
    order: 2
    stub_file: "output/result_2.json"
    test_file: "tests/test_cp2.py"
    requirements: |
      Read 'data/input_2.json'.
      NOTE: A 'noise.txt' file has appeared. Ignore it.
      Continue applying rules from 'rules.md'.
      Write output to 'output/result_2.json'.

  - id: cp3_update
    title: "Checkpoint 3: Rule Update"
    order: 3
    stub_file: "output/result_3.json"
    test_file: "tests/test_cp3.py"
    requirements: |
      Read 'data/input_3.json'.
      IMPORTANT: Read 'rule_update.md' for policy changes.
      Apply the UPDATED rules to this batch.
      Write output to 'output/result_3.json'.

# Memory probes (see Step 3)
memory_probes:
  - type: distractor_injection
    trigger_at_minute: 10
    description: "Agent should ignore noise.txt"
    distractor_ratio: 0.3

  - type: specification_drift
    trigger_at_minute: 15
    description: "Rule update must be applied immediately"
    requirement_change: "New rules in rule_update.md"

  - type: recall_verification
    trigger_at_minute: 12
    target_checkpoint: cp2_distractor
    pillar: memory_fidelity
    description: "What was the original threshold value in rules.md?"
    metadata:
      expected_recall:
        - "100"
        - "$100"
      source_document: "rules.md"
      recall_type: "specific_value"

# Evaluation configuration
evaluation_config:
  max_duration_minutes: 30
  track_context_usage: true
```

---

## Step 2: Create the Repository Template

Create a directory structure in `templates/` matching your `template_name`:

```
templates/
└── my_custom_template/
    ├── rules.md              # Primary context/rules document
    ├── data/
    │   ├── input_1.json      # Input for checkpoint 1
    │   ├── input_2.json      # Input for checkpoint 2
    │   └── input_3.json      # Input for checkpoint 3
    ├── output/
    │   └── .gitkeep          # Empty dir for agent output
    ├── tests/
    │   ├── test_cp1.py       # Pytest for checkpoint 1
    │   ├── test_cp2.py       # Pytest for checkpoint 2
    │   └── test_cp3.py       # Pytest for checkpoint 3
    ├── noise.txt             # Distractor file (appears in cp2)
    └── rule_update.md        # Rule changes (appears in cp3)
```

### Test File Format

Each test file should use pytest and verify the agent's output:

```python
# tests/test_cp1.py
import json
import pytest
from pathlib import Path

def test_checkpoint_1_output():
    output_path = Path(__file__).parent.parent / "output" / "result_1.json"
    assert output_path.exists(), "Output file not created"
    
    with open(output_path) as f:
        result = json.load(f)
    
    # Verify structure
    assert "decisions" in result, "Missing 'decisions' key"
    
    # Verify specific expected outcomes
    decisions = {d["id"]: d["status"] for d in result["decisions"]}
    assert decisions.get("item_001") == "APPROVED"
    assert decisions.get("item_002") == "REJECTED"
```

---

## Step 3: Add Memory Probes

Memory probes test specific pillars. Include at least one probe per pillar for comprehensive evaluation.

### Probe Type Reference

| Probe Type | Pillar | Required Fields |
|------------|--------|-----------------|
| `recall_verification` | Memory Fidelity | `target_checkpoint`, `pillar`, `metadata.expected_recall` |
| `n_back_recall` | Memory Fidelity | `target_information` |
| `distractor_injection` | Contextual Relevance | `distractor_ratio` |
| `specification_drift` | Behavioral Integrity | `requirement_change` |
| `context_switch` | Behavioral Integrity | `interruption_task`, `duration_minutes` |

### Memory Fidelity Probe Example

```yaml
- type: recall_verification
  trigger_at_minute: 15
  target_checkpoint: cp2_distractor
  pillar: memory_fidelity
  description: "What is the maximum limit specified in rules.md?"
  metadata:
    expected_recall:
      - "75"
      - "$75"
      - "seventy-five"
    source_document: "rules.md"
    recall_type: "specific_value"
```

### Contextual Relevance Probe Example

```yaml
- type: distractor_injection
  trigger_at_minute: 10
  description: "Newsletter contains fake rules. Agent must ignore."
  distractor_ratio: 0.4
```

### Behavioral Integrity Probe Example

```yaml
- type: specification_drift
  trigger_at_minute: 20
  description: "Memo changes the approval threshold. Agent must adapt."
  requirement_change: "New memo updates threshold from $100 to $150"
```

---

## Step 4: Provide Working History (Context)

For tasks requiring pre-existing context (simulating a long conversation history):

### Option A: Inline History

```yaml
working_history:
  - role: system
    content: "Previous architectural decision: All services must use REST APIs."
  - role: user
    content: "We discussed avoiding vendor X due to licensing issues."
  - role: assistant
    content: "Understood. I will not recommend vendor X solutions."
```

### Option B: External History File (Recommended for Long Contexts)

```yaml
history_file: "contexts/my_long_history.json"
```

**File format (`contexts/my_long_history.json`):**

```json
[
  {
    "role": "system",
    "content": "A 5000-token document describing complex organizational rules and constraints that the agent must remember throughout the task..."
  },
  {
    "role": "user", 
    "content": "Previous conversation turn 1..."
  },
  {
    "role": "assistant",
    "content": "Agent's previous response..."
  }
]
```

---

## Step 5: Running Your Task

### Local Execution (Development)

```bash
# Run your task (V2)
python workmemeval.py run --task tasks/v2/my_task.yaml

# With a real LLM (requires OPENROUTER_API_KEY)
export OPENROUTER_API_KEY=your-key-here
python workmemeval.py run --task tasks/v2/my_task.yaml --model anthropic/claude-3.5-sonnet
```

### Docker Execution (Production/Isolated)

```bash
# Build the image first
docker compose -f docker/compose.dev.yml build

# Run evaluation
docker compose -f docker/compose.dev.yml run --rm eval \
  python workmemeval.py run --task tasks/v2/my_task.yaml
```

---

## Docker Mounting & Integration

### Default Mount Points

| Host Path | Container Path | Access |
|-----------|----------------|--------|
| Repository root | `/app` | Read-only |
| `evaluation_workspace/` | `/app/evaluation_workspace` | Read-write |
| `tasks/yaml/` | `/app/tasks/yaml/` | Read-only |
| `templates/` | `/app/templates/` | Read-only |

### Adding Custom Mount Points

If your contexts or templates are outside the repository, modify `docker/compose.dev.yml`:

```yaml
services:
  eval:
    volumes:
      - ..:/app:ro
      - ../evaluation_workspace:/app/evaluation_workspace:rw
      # Add custom mounts:
      - /path/to/my/contexts:/app/custom_contexts:ro
      - /path/to/my/templates:/app/custom_templates:ro
```

### Path Resolution

The CLI automatically resolves paths in multiple locations:

1. Exact path as provided
2. Relative to current working directory
3. `/app/{path}` (Docker container)
4. `/app/tasks/{path}` (for task files)

**Example:** `--task tasks/yaml/my_task.yaml` resolves to `/app/tasks/yaml/my_task.yaml` in Docker.

### Custom External Tasks

For tasks outside the repository:

```bash
# Mount your custom directory
docker compose -f docker/compose.dev.yml run --rm \
  -v /absolute/path/to/my_tasks:/app/my_tasks:ro \
  -v /absolute/path/to/my_templates:/app/templates/my_templates:ro \
  eval python workmemeval.py run --task my_tasks/custom.yaml
```

---

## Using Real LLMs

### Supported Models (via OpenRouter)

```bash
# Claude
--model claude-3.5-sonnet
--model claude-3-opus

# GPT
--model gpt-4-turbo
--model gpt-4

# Llama
--model llama-3.1-70b

# Or use full OpenRouter model names
--model anthropic/claude-3.5-sonnet
--model meta-llama/llama-3.1-405b-instruct
```

### Environment Setup

```bash
# Option 1: Export directly
export OPENROUTER_API_KEY=sk-or-v1-your-key

# Option 2: Use .env file
echo "OPENROUTER_API_KEY=sk-or-v1-your-key" > .env
source .env
```

### Docker with API Key

```bash
docker compose -f docker/compose.dev.yml run --rm \
  -e OPENROUTER_API_KEY=$OPENROUTER_API_KEY \
  eval python workmemeval.py run --task tasks/v2/my_task.yaml --model anthropic/claude-3.5-sonnet
```

---

## Troubleshooting

### Task File Not Found

```
FileNotFoundError: Task file not found: tasks/yaml/my_task.yaml
```

**Solutions:**
- Verify the file exists at the specified path
- In Docker, ensure the file is under `/app/tasks/yaml/`
- Check file permissions

### Template Not Found

```
ValueError: Template 'my_template' not found
```

**Solutions:**
- Create directory `templates/my_template/`
- Ensure `repository.template_name` in YAML matches directory name exactly
- In Docker, verify template is mounted

### Memory Fidelity Shows "N/A (no probes)"

**Solutions:**
- Add a `recall_verification` probe with explicit `pillar: memory_fidelity`
- Ensure `target_checkpoint` matches an actual checkpoint ID
- Check that probe type is correctly spelled

### Probe Not Triggering

**Solutions:**
- Verify `trigger_at_minute` is within `max_duration_minutes`
- Check that `target_checkpoint` exists in your checkpoints list
- Ensure no validation errors in YAML (check console output)

### LLM Timeout / No Response

**Solutions:**
- Increase timeout: The runner allows 120 seconds idle time
- Check API key is valid: `echo $OPENROUTER_API_KEY`
- Verify network connectivity in Docker (may need `--network host`)

---

## Complete Example

Here's a minimal but complete task that tests all three pillars:

### File: `tasks/yaml/expense_auditor.yaml`

```yaml
task_id: expense_auditor
title: Expense Auditor Memory Test
domain: data_processing
difficulty: beginner
description: |
  Simple expense auditing task that tests all three memory pillars.

repository:
  template_name: expense_auditor

memory_dimensions:
  information_density: 200
  temporal_span: 15
  context_switches: 2
  dependency_depth: 1

success_criteria:
  - "Correctly apply expense policy"
  - "Ignore fake newsletter rules"
  - "Adapt to policy memo updates"

checkpoints:
  - id: cp1_basic
    title: "Basic Expense Review"
    order: 1
    stub_file: "output/batch_1.json"
    test_file: "tests/test_batch_1.py"
    requirements: |
      Read 'policy.md' and 'expenses/batch_1.json'.
      Output decisions to 'output/batch_1.json'.

  - id: cp2_noise
    title: "Review with Distractions"
    order: 2
    stub_file: "output/batch_2.json"
    test_file: "tests/test_batch_2.py"
    requirements: |
      Read 'expenses/batch_2.json'.
      Ignore 'fake_newsletter.md' - it's not official policy.
      Output to 'output/batch_2.json'.

  - id: cp3_update
    title: "Policy Update"
    order: 3
    stub_file: "output/batch_3.json"
    test_file: "tests/test_batch_3.py"
    requirements: |
      Read 'expenses/batch_3.json' and 'policy_update.md'.
      Apply NEW policy rules.
      Output to 'output/batch_3.json'.

memory_probes:
  # Memory Fidelity
  - type: recall_verification
    trigger_at_minute: 8
    target_checkpoint: cp2_noise
    pillar: memory_fidelity
    description: "What is the meal limit in the original policy?"
    metadata:
      expected_recall: ["50", "$50"]
      source_document: "policy.md"

  # Contextual Relevance  
  - type: distractor_injection
    trigger_at_minute: 6
    description: "Newsletter claims unlimited expenses - must ignore"
    distractor_ratio: 0.5

  # Behavioral Integrity
  - type: specification_drift
    trigger_at_minute: 12
    description: "Policy memo raises meal limit - must apply"
    requirement_change: "Meal limit increased to $75"

evaluation_config:
  max_duration_minutes: 20
  track_context_usage: true
```

### Run It

```bash
# Local with real LLM
export OPENROUTER_API_KEY=your-key
python workmemeval.py run --task tasks/v2/expense_auditor.yaml --model anthropic/claude-3.5-sonnet
```

Expected output:

```
=== Evaluation Summary ===
Task: expense_auditor
Status: ✅ SUCCESS
Checkpoints: 3/3 completed

Memory Pillar Scores:
  Memory Fidelity           ██████████ 100.0%
  Contextual Relevance      ██████████ 100.0%
  Behavioral Integrity      ██████████ 100.0%
```

---

## Next Steps

- Review existing tasks in `tasks/yaml/` for more examples
- See `docs/memory_probe_framework.md` for advanced probe configuration
- See `docs/enhanced_evaluation_system.md` for scoring details
