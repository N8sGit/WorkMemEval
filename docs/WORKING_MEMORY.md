# Working Memory Evaluation Guide

This guide explains the three-pillar working memory framework in WorkMemEval, with a deeper focus on the two challenge-driven Behavioral Integrity metrics: Update Robustness (UR) and Resumption Success Rate (RSR). It also describes runner orchestration details that support these metrics, interpretation guidance, and tuning options.


## Three pillars at a glance

- Memory Fidelity: retention and efficiency of information over time
- Contextual Relevance: focusing on relevant information while avoiding distractors
- Behavioral Integrity: coherent, correct action under complexity and load

Each pillar aggregates several component metrics into a normalized score in [0,1]. See implementation in:
- src/evaluation/memory_metrics.py (MemoryFidelityEvaluator, ContextualRelevanceEvaluator, BehavioralIntegrityEvaluator)


## Challenge-driven Behavioral Integrity metrics

Two complementary metrics measure adaptation under stress:

### Update Robustness (UR)

Purpose: How effectively the agent adapts to mid-task requirement updates or integration constraints.

Trigger events:
- requirement_update (from MemoryChallengeType.REQUIREMENT_UPDATE)
- integration_constraint (from MemoryChallengeType.INTEGRATION_CONSTRAINT)

Input mapping (per-challenge evaluation):
- ActionTrace and challenge responses in TaskTrace.memory_challenge_responses
- Files “affected” by the update (heuristic): stub/test files of the affected checkpoint; fallback to all checkpoint stub/test files if unspecified

Components and default weights:
- compliance (0.40)
  - 1.0 if a passing TEST_RUN occurs after the update
  - 0.5 if only write/modify to affected files (fallback when no tests run)
  - 0.0 otherwise
- latency (0.20)
  - exp(-steps_to_first_signal / τ) where τ depends on severity: small=10, medium=25, large=50
  - steps_to_first_signal counts actions between update and first compliance signal (passing test or write fallback)
- stability (0.20)
  - 1/(1 + conflicts/3) where conflicts are subsequent modifications to affected files in a short window
- consistency (0.20)
  - fraction of touches in the next window that target the affected files after the first signal

Binary success signal:
- per-challenge binary_success = 1 only if a passing TEST_RUN is observed after the update
- details.binary_success_rate aggregates binary_success across all UR challenges

Confidence:
- Higher when grounded by a passing test; reduced if consistency cannot be computed

Examples:
- Positive case (small severity):
  - passing tests 5 steps after update; few subsequent modifications; most touches target affected files
  - latency ≈ exp(-5/10) ≈ 0.607; overall score commonly 0.80–0.90+
- Write/no tests case (medium severity):
  - only write to affected files 3 steps after update; moderate stability/consistency
  - compliance 0.5; latency ≈ exp(-3/25) ≈ 0.887; overall can still be moderate (e.g., ~0.6–0.75)
  - binary_success=0 (no passing test) highlights diagnostic failure while continuous score reflects partial adaptation

Implementation reference:
- src/evaluation/memory_metrics.py: BehavioralIntegrityEvaluator._update_robustness


### Resumption Success Rate (RSR)

Purpose: How effectively the agent resumes productive work and recalls pre-switch context after interruptions.

Trigger events:
- context_switch_resume (paired with the most recent context_switch_start)

Input mapping (per-resume evaluation):
- ActionTrace and memory challenge responses for context switch start/resume
- Pre-switch ContextSnapshot (files_in_context) if present

Components and default weights:
- latency (0.35)
  - exp(-steps_to_productive / τ) where τ depends on severity: small=12, medium=18, large=25
- recall (0.25)
  - Jaccard(files_touched soon after resume, pre_switch files_in_context) if ContextSnapshot exists; omitted otherwise
- fidelity (0.25)
  - Same Jaccard proxy as recall – emphasizes correct early focus when explicit plan hints are absent
- overhead (0.15)
  - 1 - min(1, exploratory_action_ratio) in the first N actions post-resume

Binary success signal:
- per-resume binary_success = 1 if the CONTEXT_SWITCH_RESUME action had success=True
- details.binary_success_rate aggregates binary_success across resumes

Confidence:
- Reduced if no pre-switch ContextSnapshot is available for recall/fidelity

Examples:
- Successful resume (medium severity):
  - steps_to_productive=4 → latency ≈ exp(-4/18) ≈ 0.801; moderate recall/fidelity; low overhead → overall ~0.65–0.8
- Failed resume:
  - resume event success=False; binary_success=0; score commonly lower, but still considers partial signals (e.g., quick productive action or strong overlap)

Implementation reference:
- src/evaluation/memory_metrics.py: BehavioralIntegrityEvaluator._resumption_success_rate


## Runner orchestration to support metrics

- Baseline plan artifact (plan_compliance support)
  - At the start of each checkpoint, the runner logs a PLANNING action with a minimal plan: [read_file -> implement -> edit_file] for the checkpoint stub file
  - Ensures plan_compliance has a standardized source even when agents do not explicitly log plans

- Pre-context-switch snapshot (RSR support)
  - Before executing a CONTEXT_SWITCH challenge, the runner logs a ContextSnapshot using files accessed so far in the checkpoint
  - Improves RSR recall/fidelity by providing a pre-switch files_in_context reference


- Error handling
  - Checkpoint exceptions are logged and then propagated by the runner (strict behavior). This ensures tests and
    orchestrations that expect exceptions to bubble up work as intended.

Implementation reference:
- src/evaluation/runner.py (see BasicWorkMemEvalRunner docstring and logic around PLANNING, snapshots, and legacy fields)


## Interpretation thresholds (default)

- Excellent: ≥ 0.85
- Good: ≥ 0.70
- Moderate: ≥ 0.50
- Poor: < 0.50

Consider both continuous metric value and binary_success_rate within each metric’s details:
- A higher continuous value without binary_success may indicate partial adaptation (e.g., quick writes) but lack of verified correctness
- Binary success highlights objective signals (tests passing for UR; explicit resume success for RSR)


## Tuning and calibration

- Adjusting component weights:
  - UR: compliance/latency/stability/consistency default to 0.40/0.20/0.20/0.20
  - RSR: latency/recall/fidelity/overhead default to 0.35/0.25/0.25/0.15
  - You may raise compliance weight if you want to emphasize verified correctness (UR) or reduce overhead impact (RSR)

- Adjusting τ (latency decay):
  - UR τ: small=10, medium=25, large=50 actions
  - RSR τ: small=12, medium=18, large=25 actions
  - Lower τ penalizes slower responses more aggressively; higher τ is more forgiving

- Confidence adjustments:
  - Metrics reduce confidence when critical context is missing (e.g., RSR without a pre-switch snapshot)
  - Aggregation across multiple events is confidence-weighted


## Edge cases and guidance

- No tests present (UR):
  - UR’s compliance uses a 0.5 fallback for write/modify signals; consider combining with binary_success_rate for diagnosis

- No pre-switch snapshot (RSR):
  - Recall/fidelity components are omitted and confidence reduced; focus remains on latency and overhead

- Multiple updates/resumes:
  - Coverage and confidence-weighted aggregation across events; examine per_challenge details for diagnostics


## Result structure overview

EvaluationResult (src/evaluation/results.py) includes:
- three_pillar_evaluation: structured evaluation (if available)
- working_memory_metrics: reserved for basic/legacy metrics (empty by default)
- task_trace: serialized TaskTrace, including memory_challenge_responses and context snapshots

### Recording Formats

The evaluation system now supports multiple recording formats to optimize storage:

**Compact Format (default)**
- **Size reduction**: ~25x smaller than legacy format
- **Compression**: Additional 2.6x with zlib compression
- **Data retention**: All essential metrics and context preserved
- **File naming**: `{timestamp}_compact.json` or `{timestamp}_compact.json.gz`

**Legacy Format**
- **File naming**: `{timestamp}.json`
- **Use case**: Backward compatibility during migration
- **Size**: Original verbose format with full trace details

**Configuration**
```bash
# CLI usage
python3 -m src.cli run --task tasks/simple_calculator.json --recording-mode compact
python3 -m src.cli run --task tasks/simple_calculator.json --recording-mode legacy
python3 -m src.cli run --task tasks/simple_calculator.json --recording-mode both
```

**Storage Statistics**
- Legacy: ~890 bytes per simple task
- Compact: ~850 bytes per simple task  
- Compressed: ~337 bytes per simple task

### Migration Support

For existing evaluation runs, use the migration adapter:
```python
from evaluation.migration_adapter import LegacyAdapter
adapter = LegacyAdapter()
adapter.batch_migrate_directory("evaluation_runs")
```


## File references

- Metrics and evaluation:
  - src/evaluation/memory_metrics.py (includes native plan compliance)
- Runner orchestration and results:
  - src/evaluation/runner.py
  - src/evaluation/results.py
- Core data structures:
  - src/core/action_trace.py (ActionType, ActionTraceEntry, ContextSnapshot, CheckpointTrace, TaskTrace)
  - src/core/task_specification.py (TaskSpecification, MemoryChallengeType)


## Reproducibility tips

- Use containerized execution (default) to minimize environment variance
- Ensure tasks define clear tests; UR benefits from passing TEST_RUN signals
- Provide pre-switch ContextSnapshots (or rely on runner capture) for better RSR fidelity/recall confidence
- Control file size warnings from synthetic file ops via WM_WARN_SIZE_BYTES=1 (default suppressed)


## Changelog note

- The runner now logs a baseline plan and a pre-context-switch snapshot. If you have agents that already log detailed plans or snapshots, you can adapt the runner accordingly (e.g., disable baseline plan logging) to avoid duplication.

