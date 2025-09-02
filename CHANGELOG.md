# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

- Changed: MemorySystemFactory now creates the canonical no-memory system from `src.memory.simple_memory.NoMemory` when `memory_type='no_memory'`.
- Removed: `SimpleWorkMemAgent.execute_task`. Migrate to runner orchestration (`BasicWorkMemEvalRunner.run_evaluation`) or call `execute_checkpoint` asynchronously per checkpoint.
- Added: `surface_legacy_metrics` flag to `BasicWorkMemEvalRunner` to optionally (and deprecatedly) surface a subset of three-pillar metrics into the flat `working_memory_metrics` dictionary. Default is `False`.
- Removed: `src.memory.memory_system.NoMemoryBaseline`. Use `src.memory.simple_memory.NoMemory`.
- Docs: Updated README to reflect optional, deprecated legacy metric surfacing and runner orchestration as canonical.
- Test hygiene: Prevented pytest from attempting to collect the production `TestRunner` class.

## Previous

- Initial three-pillar evaluation engine and baseline components.

