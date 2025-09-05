# WorkMemEval

This repository provides a minimal, test-oriented evaluation harness and a simple agent implementation for working-memory research.

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
docker compose -f docker/compose.dev.yml run --rm eval "pytest -q /workspace/tests/test_calculator_cp1.py"
```

### Outputs
- Results are written to `evaluation_runs/<task_id>/<timestamp>.json`
- The working directory for a run defaults to `evaluation_workspace/<task_id>` unless you pass `--workspace`.

#### Recording Formats
The system supports multiple recording formats to optimize storage:

- **Compact format** (default): ~25x smaller than legacy, preserves all metrics
- **Legacy format**: Original verbose format for backward compatibility
- **Compressed format**: Additional zlib compression for maximum space savings

Configure via CLI:
```bash
# Use compact format (default)
python3 -m src.cli run --task tasks/simple_calculator.json --recording-mode compact

# Use legacy format
python3 -m src.cli run --task tasks/simple_calculator.json --recording-mode legacy

# Use both formats during migration
python3 -m src.cli run --task tasks/simple_calculator.json --recording-mode both
```

## Security notes
- SecureFileOperations restricts agent file I/O to the working directory with path validation, extension allow-listing, and size limits.
- Containerized tests add OS-level isolation and resource controls.
- .gitignore blocks common local artifacts and .env; pre-commit hooks provide linting and basic security checks.

## Working memory metrics overview

The evaluation engine implements a three-pillar framework (Memory Fidelity, Contextual Relevance, Behavioral Integrity).
Two challenge-driven metrics were added under Behavioral Integrity:

- Update Robustness (UR)
  - Triggered by requirement_update and integration_constraint challenge events
  - Components (default weights):
    - compliance (0.40): 1.0 if a passing test is observed after the update; 0.5 if only writes/modifies occur (fallback
      when tests are absent); otherwise 0.0
    - latency (0.20): exp(-steps_to_first_signal / τ), τ by severity (small=10, medium=25, large=50)
    - stability (0.20): 1/(1 + conflicts/3) based on subsequent modifications to affected files in a short window
    - consistency (0.20): fraction of subsequent touches that target the affected files
  - Binary success: per-update binary_success=1 only if a passing test is observed; an overall binary_success_rate is
    included in metric details

- Resumption Success Rate (RSR)
  - Triggered by context_switch_resume events (paired with the most recent context_switch_start)
  - Components (default weights):
    - latency (0.35): exp(-steps_to_productive / τ), τ by severity (small=12, medium=18, large=25)
    - recall (0.25) and fidelity (0.25): Jaccard overlap between first post-resume touched files and pre-switch
      files_in_context from a ContextSnapshot
    - overhead (0.15): 1 - min(1, exploratory_action_ratio) in the first N actions post-resume
  - Binary success: per-resume binary_success=1 if the resume event has success=True; metric details include an
    overall binary_success_rate

Runner behavior to support these metrics:
- The runner logs a minimal baseline plan (PLANNING action) at the start of each checkpoint so plan_compliance has a
  consistent source when agents do not log plans.
- Before a context switch challenge, the runner logs a pre-switch ContextSnapshot based on files accessed so far in
  the checkpoint; this improves recall/fidelity confidence in RSR.
- The runner computes the full three-pillar evaluation after execution regardless of test success. This lets you diagnose failures as well as successes.

Additional notes:
- File size warnings for synthetic file operations are suppressed by default; set WM_WARN_SIZE_BYTES=1 to re-enable.

More details: see docs/WORKING_MEMORY.md for a deep dive (components, weights, and examples).

## CI overview
## LLM Integration

WorkMemEval now supports real language models as first-class components:

### Supported Providers
- **OpenAI**: GPT-4o, GPT-4o-mini, GPT-4, GPT-3.5-turbo
- **OpenRouter**: Claude-3 models, Llama models, and other open-source options
- **Mock**: Deterministic responses for testing (no API key required)

### Configuration

```python
# OpenAI configuration
openai_config = {
    'llm_config': {
        'provider': 'openai',
        'model': 'gpt-4o-mini',
        'temperature': 0.1,
        'max_tokens': 4000
    }
}

# OpenRouter configuration
openrouter_config = {
    'llm_config': {
        'provider': 'openrouter',
        'model': 'anthropic/claude-3-haiku',
        'temperature': 0.1,
        'max_tokens': 4000
    }
}

# Mock configuration (for testing)
mock_config = {
    'llm_config': {
        'provider': 'mock',
        'model': 'test-model',
        'response_delay': 0.0
    }
}
```

### Environment Variables
```bash
# For OpenAI
export OPENAI_API_KEY="your-openai-api-key"

# For OpenRouter
export OPENROUTER_API_KEY="your-openrouter-api-key"
```

See `examples/llm_config_example.py` for complete configuration examples.

## Memory systems (notes)

- NoMemoryBaseline is deprecated; prefer src/memory/simple_memory.py:NoMemory. The factory maps "no_memory" to NoMemory.

## CI overview
- CI builds the evaluation image and runs the test suite inside the container (network disabled) for deterministic results.
- Pre-commit hooks run in CI.
- pip-audit checks dependencies listed in `requirements/dev.txt`.


