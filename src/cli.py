#!/usr/bin/env python3
"""
Simple CLI for WorkMemEval

Commands:
- run: evaluate a task with SimpleWorkMemAgent + SimpleContextMemory
- compare: load result JSON files or directories and print comparison

Usage examples:
  python3 -m src.cli run --task tasks/simple_calculator.json
  python3 -m src.cli compare evaluation_runs/simple_calculator
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import List

from .agents.reference_agent import ReferenceWorkMemAgent
from .core.plugin_loader import PluginLoader, PluginConfig
from .evaluation.results import ComparisonResult, EvaluationResult
from .evaluation.runner import BasicWorkMemEvalRunner, AgentifiedRunner
from .memory import SimpleContextMemory


def cmd_run(args: argparse.Namespace) -> int:
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(name)s - %(levelname)s - %(message)s'
    )
    
    task_path = Path(args.task)
    working_directory = Path(args.workspace) if args.workspace else None

    # Load configuration for agent if provided
    agent_config = {}
    if args.agent_config:
        try:
            agent_config = json.loads(args.agent_config)
        except json.JSONDecodeError as e:
            print(f"Error parsing agent config JSON: {e}")
            return 1

    memory = SimpleContextMemory({"max_items": 100})

    if args.agent:
        # Use plugin loader for custom agent
        loader = PluginLoader()
        try:
            print(f"Loading custom agent: {args.agent}")
            agent = loader.load_agent(
                PluginConfig(class_path=args.agent, config=agent_config),
                memory_system=memory
            )
        except Exception as e:
            print(f"Failed to load agent {args.agent}: {e}")
            import traceback
            traceback.print_exc()
            return 1
    else:
        # Default to ReferenceWorkMemAgent
        default_config = {
            "max_iterations": 10,
            "memory_context_limit": 5,
            "llm_config": {"response_delay": 0.0},
        }
        # Merge provided config with default if any
        default_config.update(agent_config)
        
        agent = ReferenceWorkMemAgent(
            memory,
            default_config,
        )

    # Use the new Agentified Architecture by default
    print("Initializing Agentified Runner (Assessor-Driven Evaluation)...")
    runner = AgentifiedRunner()

    async def _run():
        result = await runner.run_evaluation(
            task_path, agent, memory, working_directory=working_directory
        )
        result.print_summary()
        return 0

    return asyncio.run(_run())


def _gather_result_files(paths: List[Path]) -> List[Path]:
    files: List[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.glob("**/*.json")))
        elif p.is_file() and p.suffix == ".json":
            files.append(p)
    return files


def cmd_compare(args: argparse.Namespace) -> int:
    paths = [Path(p) for p in args.paths]
    json_files = _gather_result_files(paths)
    if not json_files:
        print("No JSON result files found.")
        return 1

    results: List[EvaluationResult] = []
    for jf in json_files:
        with open(jf, "r") as f:
            data = json.load(f)
        results.append(EvaluationResult.from_dict(data))

    cmp = ComparisonResult("CLI Comparison")
    for r in results:
        cmp.add_evaluation(r)
    cmp.calculate_comparison_metrics()
    cmp.print_comparison()
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="WorkMemEval CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run an evaluation for a task")
    p_run.add_argument("--task", required=True, help="Path to task JSON")
    p_run.add_argument("--workspace", help="Working directory for execution (optional)")
    group = p_run.add_mutually_exclusive_group()
    group.add_argument(
        "--container",
        dest="container",
        action="store_true",
        help="Run tests inside Docker (default)",
    )
    group.add_argument(
        "--no-container",
        dest="container",
        action="store_false",
        help="Run tests locally without Docker",
    )
    p_run.add_argument(
        "--docker-image",
        default="workmemeval/eval:local",
        help="Docker image to use when running containerized",
    )
    p_run.add_argument(
        "--agent",
        help="Custom agent class path (e.g. module.submodule:ClassName)",
    )
    p_run.add_argument(
        "--agent-config",
        help="JSON string configuration for the agent",
    )
    p_run.set_defaults(func=cmd_run, container=True)

    p_cmp = sub.add_parser(
        "compare", help="Compare one or more evaluation result files or directories"
    )
    p_cmp.add_argument(
        "paths",
        nargs="+",
        help="Result JSON files or directories containing JSON results",
    )
    p_cmp.set_defaults(func=cmd_compare)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
