# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### 🚀 Major: Real LLM Integration
- **Added**: First-class LLM integration with `src.llm` module supporting OpenAI, OpenRouter, and mock providers
- **Added**: `LLMInterface` abstract base class for consistent LLM provider API
- **Added**: `OpenAIProvider` with production features: rate limiting, error handling, token tracking, cost calculation
- **Added**: `MockProvider` for deterministic testing with pattern-based responses
- **Added**: `LLMFactory` for easy provider instantiation with convenience methods
- **Changed**: `SimpleWorkMemAgent` now uses configurable LLM providers instead of hardcoded `MockLLM`
- **Added**: Comprehensive LLM usage metrics including token counts, latency, and cost tracking
- **Added**: `examples/llm_config_example.py` with production configuration examples
- **Added**: Environment variable support for `OPENAI_API_KEY` and `OPENROUTER_API_KEY`
- **Dependencies**: Added `aiohttp`, `backoff`, and `tiktoken` for LLM integration
- **Breaking**: `MockLLM` class removed; use `provider: 'mock'` in LLM configuration

### 🔧 Previous Changes
- Changed: MemorySystemFactory now creates the canonical no-memory system from `src.memory.simple_memory.NoMemory` when `memory_type='no_memory'`.
- Removed: `SimpleWorkMemAgent.execute_task`. Migrate to runner orchestration (`BasicWorkMemEvalRunner.run_evaluation`) or call `execute_checkpoint` asynchronously per checkpoint.
- Added: `surface_legacy_metrics` flag to `BasicWorkMemEvalRunner` to optionally (and deprecatedly) surface a subset of three-pillar metrics into the flat `working_memory_metrics` dictionary. Default is `False`.
- Removed: `src.memory.memory_system.NoMemoryBaseline`. Use `src.memory.simple_memory.NoMemory`.
- Docs: Updated README to reflect optional, deprecated legacy metric surfacing and runner orchestration as canonical.
- Test hygiene: Prevented pytest from attempting to collect the production `TestRunner` class.

## Previous

- Initial three-pillar evaluation engine and baseline components.

