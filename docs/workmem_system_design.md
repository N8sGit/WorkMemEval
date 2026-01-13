# WorkMemEval System Design: YAML-First Task Configuration
WorkMemEval is a benchmark for agentic working memory, not just static recall. This document describes how the YAML task configuration layer maps onto the existing Python runtime models and how we will progressively treat YAML as the canonical task specification format, with JSON treated as a legacy/serialization detail.

## 1. Goals and Non-Goals
### 1.1 Goals
- Make **YAML the primary authoring format** for tasks.
- Encode the working-memory concepts (task length, task depth, probes, difficulty) directly in YAML.
- Cleanly map YAML tasks to the existing runtime task model (`TaskSpecification`) without duplicating logic.
- Preserve backward compatibility with existing JSON tasks during migration.

### 1.2 Non-Goals
- We do not require that legacy JSON task files disappear immediately; they remain supported as long as needed.
- We do not change the core evaluation loop semantics (checkpoints, pytest-based verification, action tracing); YAML is a configuration front-end for those.

## 2. Conceptual Model: What We Are Measuring
### 2.1 Agentic Working Memory
WorkMemEval targets **working memory in action**, not just long-term recall or conversational memory. In this framing:
- The **context window** is a stateless viewport: whatever happens to be in scope for a single model invocation.
- **Working memory** is the system that decides what enters that viewport, when, and in what transformed form (raw, summarized, compressed, etc.).

Agentic working memory emerges from the interaction of:
- A memory backend (storage, compression, retrieval, salience scoring).
- Attention/allocation mechanisms (which items to surface now).
- Executive control (how these choices affect behavior over long workflows).

### 2.2 Three Pillars
The benchmark is organized around three evaluation pillars:
- **Memory Fidelity**
  - Can the agent retain and reuse information without repeatedly re-reading the same sources?
  - Can it compress information without losing task-critical details?
- **Contextual Relevance**
  - Is the information it brings into context actually relevant to the current step in the task?
  - Does it resist distractors and stale information?
- **Behavioral Integrity**
  - Does good memory translate into coherent, goal-directed behavior under load?
  - Can the agent handle requirement changes, interruptions, and long workflows without drifting or collapsing?

### 2.3 Task Length, Task Depth, and Composition
Tasks are characterized along three axes:
- **Task Length** (temporal dimension)
  - How many steps or minutes of sustained activity the task requires.
  - Directly stresses Memory Fidelity (longitudinal coherence).
- **Task Depth** (informational dimension)
  - How dense and complex each step is in terms of critical tokens vs distractors.
  - Directly stresses Contextual Relevance (signal vs noise filtering).
- **Composition / Structural Complexity**
  - How many components must be integrated and how intertwined they are.
  - Primarily stresses Behavioral Integrity, but in practice interacts with both other pillars.

The YAML schema encodes these dimensions in a way that is explicit enough for researchers to reason about and for the runtime to consume.

## 3. YAML Task Schema (System View)
The YAML schema is defined by `YAMLTaskSpecification` and related models in `src/core/yaml_task_models.py`. YAML is the **canonical authoring format**; other representations (such as JSON) are treated as internal or legacy.

### 3.1 Top-Level YAMLTaskSpecification
Key fields in `YAMLTaskSpecification`:
- `task_id: str`
  - Lowercase identifier for the task; used as the stable key across the system.
- `title: str`
  - Human-readable task name.
- `domain: TaskDomain`
  - One of `distributed_systems`, `data_processing`, `web_services`, `security`, `infrastructure`.
- `difficulty: TaskDifficulty`
  - One of `beginner`, `intermediate`, `advanced`, `expert`.
- `description: str`
  - Detailed natural-language description of the task, requirements, and environment.
- `memory_dimensions: MemoryDimensions`
  - Quantified difficulty knobs for working memory.
- `success_criteria: List[str]`
  - At least 3 measurable criteria describing what it means to succeed.
- `memory_probes: List[MemoryProbe]`
  - Optional list of explicit working-memory challenges during the task.
- `evaluation_config: EvaluationConfig`
  - Episode-level envelope (duration, context constraints, etc.).
- `tags: List[str]`, `created_by: str`, `version: str`
  - Metadata for experiment management.

These fields are validated via Pydantic with strong constraints and coherence checks (e.g., probe trigger times vs max duration, temporal span vs duration, uniqueness of probe triggers).

### 3.2 MemoryDimensions → Task Length/Depth
`MemoryDimensions` encodes the primary difficulty axes:
- `information_density: int`
  - Approximate count of task-critical tokens that must be retained.
  - Maps to **Task Depth** and contributes to Memory Fidelity and Contextual Relevance.
- `temporal_span: int`
  - Minutes of sustained attention required.
  - Maps to **Task Length** and strongly drives Memory Fidelity.
- `context_switches: int`
  - Number of major context shifts during the task.
  - Directly relevant to Behavioral Integrity and task stickiness.
- `dependency_depth: int`
  - Levels of interdependent concepts/components.
  - Contributes to Composition / structural complexity.

Validators in `MemoryDimensions` enforce reasonable ranges and provide descriptive error messages; YAML authors are guided toward meaningful difficulty settings rather than arbitrary numbers.

### 3.3 MemoryProbes → Challenge Types
`MemoryProbe` specifies explicit working memory challenges:
- `type: MemoryProbeType`
  - `n_back_recall` (recall earlier decisions or facts).
  - `context_switch` (interrupt and resume).
  - `specification_drift` (changing requirements mid-task).
  - `distractor_injection` (inject noise and irrelevant context).
  - `compression_stress` (stress summarization/compaction).
- `trigger_at_minute: int`
  - When in the episode the probe fires.
- `description: str`
  - Human-readable explanation of the probe.
- Type-specific fields, e.g.:
  - `target_information` for `n_back_recall`.
  - `interruption_task`, `duration_minutes` for `context_switch`.
  - `requirement_change` for `specification_drift`.
  - `distractor_ratio` for `distractor_injection`.

Model-level validation ensures probes are internally consistent (e.g., required fields per probe type, unique trigger times, appropriate relationship to `max_duration_minutes`).

### 3.4 EvaluationConfig → Episode Envelope
`EvaluationConfig` captures how the episode is run:
- `max_duration_minutes: int`
  - Upper bound on task duration; also constrains probe trigger times.
- `context_window_limit: Optional[int]`
  - Optional explicit bound on tokens allowed in the model context.
- `allow_external_memory: bool`
  - Whether the agent may use external memory systems.
- `track_context_usage: bool`
  - Whether to collect context-usage diagnostics.

This mirrors how WorkMemEval treats **context window** as a controlled condition and potential confounder, separate from the memory system itself.

## 4. Runtime Task Model and YAML Adapter
The existing runtime model for executable tasks is defined in `src/core/task_specification.py`:
- `TaskSpecification`
  - Unified task model used by the evaluation runner.
  - Encodes checkpoints, repository template, planning phase, legacy memory challenges, and optional enhanced features.
- `CheckpointSpecification`
  - Defines concrete implementation steps:
    - Stub file/function, natural language requirements, test file, dependency relationships.
- `TaskComplexityMetrics` and `EnhancedComplexityProfile`
  - Represent length, depth, composition, and pillar stress mapping.

Tasks are currently loaded via `TaskSpecificationLoader` in `src/evaluation/runner.py` from **JSON** files (e.g. `tasks/calculator_demo.json`). That JSON format is treated as **legacy** for authoring; YAML is the new primary format.

### 4.1 YAML as Canonical, JSON as Legacy
We adopt the following stance:
- YAML is the **canonical authoring format** for tasks.
- `YAMLTaskSpecification` is the primary configuration object that human authors edit.
- `TaskSpecification` remains the **runtime execution model** that the runner, tests, and metrics operate on.
- JSON files are considered either:
  - Legacy authoring artifacts, or
  - A serialization format for `TaskSpecification` (e.g. for persistence or debugging).

Over time, new tasks should be written in YAML only; JSON will remain supported for backward compatibility and for storing derived runtime specs if needed.

### 4.2 YAML → TaskSpecification Adapter (Conceptual Design)
To integrate YAML cleanly, we introduce an adapter layer that transforms `YAMLTaskSpecification` objects into `TaskSpecification` instances.

Responsibilities of the adapter:
- **Load and validate YAML** using `TaskLoader` (`src/core/yaml_task_loader.py`).
- **Map YAML fields to runtime fields**, including:
  - `task_id`, `title`, `description`, `domain`, `difficulty`.
  - Derived complexity: Task Length, Task Depth, Composition.
  - Memory probes and context constraints.
- **Attach implementation details** (checkpoints, repository template, planning phase) needed by the runtime.

This mapping can be implemented in a dedicated module such as `src/core/yaml_task_adapter.py` or as utility functions co-located with the YAML loader.

At a high level, the adapter would:
- Accept a `YAMLTaskSpecification` and additional implementation config (e.g. which template and checkpoint set to use).
- Construct a `TaskSpecification` with:
  - A generated list of `CheckpointSpecification` entries.
  - A `RepositoryTemplate` selecting a code template under `templates/`.
  - A `PlanningPhase` appropriate for the task.
  - An `EvaluationConfiguration` that blends YAML `evaluation_config` with existing runtime evaluation settings.
  - Optionally, an `EnhancedComplexityProfile` that is derived from `memory_dimensions` instead of only from checkpoint tokens.

### 4.3 Bridging YAML Complexity to Runtime Complexity
`TaskSpecification` currently derives complexity metrics from checkpoint structure (`length`, `depth`, `composition`) and can further derive an `EnhancedComplexityProfile` for pillar mapping.

For YAML-first tasks, we want `memory_dimensions` to inform or override these metrics. The adapter is responsible for this bridge, for example:
- Map `memory_dimensions.temporal_span` to a **length-like** quantity.
- Map `memory_dimensions.information_density` to a **depth-like** quantity.
- Map `memory_dimensions.context_switches` and `dependency_depth` to aspects of composition / Behavioral Integrity stress.

The adapter can either:
- Create a `TaskComplexityMetrics` directly from `MemoryDimensions`, or
- Derive an `EnhancedComplexityProfile` that uses both `MemoryDimensions` and checkpoint-derived metrics to compute pillar stress scores.

## 5. Migration and Compatibility
### 5.1 Current State
- Runtime tasks are loaded from JSON via `TaskSpecificationLoader`.
- `tasks/calculator_demo.json` demonstrates the legacy JSON format.
- YAML models and loader (`YAMLTaskSpecification`, `TaskLoader`) are implemented and tested but not yet wired into the runner.

### 5.2 Target State
- New tasks are authored as YAML files that validate against `YAMLTaskSpecification`.
- The evaluation runner accepts YAML paths and uses the YAML loader + adapter to produce a `TaskSpecification` for execution.
- JSON remains supported for:
  - Legacy tasks.
  - Serialized runtime specs.

### 5.3 Incremental Integration Path
A minimal, backward-compatible path to YAML-first operation is:
1. **Add YAML Awareness to the Runner**
   - Extend `TaskSpecificationLoader` (or introduce a sibling loader) to:
     - Detect file extension.
     - For `.yaml` / `.yml`, call `load_yaml_task()` to get a `YAMLTaskSpecification`.
     - Pass the result through the YAML→`TaskSpecification` adapter.

2. **Introduce a YAML Adapter**
   - Implement a function such as `from_yaml_spec(yaml_spec: YAMLTaskSpecification, implementation_config: Dict[str, Any]) -> TaskSpecification` that:
     - Constructs checkpoints and repository template.
     - Initializes complexity metrics from `memory_dimensions`.
     - Translates `memory_probes` and `evaluation_config` into enhanced runtime features.

3. **Add an End-to-End YAML Test**
   - Use `tasks/yaml/example_distributed_cache.yaml` as a canonical example.
   - Write a test that:
     - Loads this YAML.
     - Adapts it to `TaskSpecification`.
     - Runs a small evaluation end-to-end (using a simple agent/memory system) to ensure the wiring is correct.

4. **Gradually Deprecate JSON Authoring**
   - Update documentation and examples to show YAML as the default.
   - Optionally provide a tool to convert existing JSON tasks into YAML representations compatible with `YAMLTaskSpecification`.

## 6. Summary
- **YAML is the primary configuration language** for WorkMemEval tasks going forward.
- The YAML schema, centered on `YAMLTaskSpecification`, `MemoryDimensions`, `MemoryProbe`, and `EvaluationConfig`, encodes the theory of agentic working memory directly into configuration.
- The existing runtime model (`TaskSpecification` and friends) remains the execution backbone, now fed by a YAML→runtime adapter rather than by hand-authored JSON.
- This design preserves backward compatibility while making the conceptual model of working memory (task length, depth, probes, and pillars) first-class and explicit in the configuration surface.
