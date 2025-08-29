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

## Security notes
- SecureFileOperations restricts agent file I/O to the working directory with path validation, extension allow-listing, and size limits.
- Containerized tests add OS-level isolation and resource controls.
- .gitignore blocks common local artifacts and .env; pre-commit hooks provide linting and basic security checks.

## CI overview
- CI builds the evaluation image and runs the test suite inside the container (network disabled) for deterministic results.
- Pre-commit hooks run in CI.
- pip-audit checks dependencies listed in `requirements/dev.txt`.


