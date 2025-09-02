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
import json
from pathlib import Path
from typing import List
import asyncio

from .evaluation.runner import BasicWorkMemEvalRunner
from .agents.simple_agent import SimpleWorkMemAgent
from .agents.real_agent import RealAgent
from .memory.reference_implementations import SimpleContextMemory
from .evaluation.results import EvaluationResult, ComparisonResult


def cmd_run(args: argparse.Namespace) -> int:
    task_path = Path(args.task)
    working_directory = Path(args.workspace) if args.workspace else None

    # Select agent based on arguments
    if args.agent == 'real':
        memory = SimpleContextMemory(config={'max_items': 100})
        agent = RealAgent(memory, {
            'model': args.model or 'moonshotai/kimi-k2',
            'temperature': 0.1,
            'max_tokens': 4000
        })
    else:
        memory = SimpleContextMemory(config={'max_items': 100})
        agent = SimpleWorkMemAgent(memory, {
            'max_iterations': 10,
            'memory_context_limit': 5,
            'llm_config': {'response_delay': 0.0}
        })

    runner = BasicWorkMemEvalRunner(containerized=getattr(args, 'container', False), docker_image=getattr(args, 'docker_image', None))

    try:
        from evaluation.integration_runner import CompactEvaluationRunner
        
        # Use compact recording system
        compact_runner = CompactEvaluationRunner()
        result_path = compact_runner.run_evaluation(
            task_id=task_path.stem,
            agent_name=args.agent,
            task_result=runner.run_evaluation(
                task_path, agent, memory, working_directory=working_directory
            ),
            recording_mode=args.recording_mode
        )
        
        print(f"Evaluation complete. Results saved to: {result_path}")
        return 0

    except ImportError:
        async def _run():
            result = await runner.run_evaluation(task_path, agent, memory, working_directory=working_directory)
            result.print_summary()
            return 0

        return asyncio.run(_run())


def _gather_result_files(paths: List[Path]) -> List[Path]:
    files: List[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.glob('**/*.json')))
        elif p.is_file() and p.suffix == '.json':
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
        with open(jf, 'r') as f:
            data = json.load(f)
        results.append(EvaluationResult.from_dict(data))

    cmp = ComparisonResult("CLI Comparison")
    for r in results:
        cmp.add_evaluation(r)
    cmp.calculate_comparison_metrics()
    cmp.print_comparison()
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='WorkMemEval CLI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Run command
    run_parser = subparsers.add_parser('run', help='Run evaluation with agent')
    run_parser.add_argument('--task', required=True, help='Task JSON file')
    run_parser.add_argument('--workspace', help='Working directory (optional)')
    run_parser.add_argument('--agent', choices=['simple', 'real'], default='simple',
                           help='Agent to use (simple or real)')
    run_parser.add_argument('--model', help='LLM model for real agent')
    run_parser.add_argument('--container', action='store_true', help='Run in Docker container')
    run_parser.add_argument("--recording-mode", choices=["compact", "legacy", "both", "summary", "debug"],
                        default="compact", help="Recording format for evaluation results (default: compact)")
    run_parser.add_argument("--compress", action="store_true", help="Enable compression for compact recordings")
    run_parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    run_parser.add_argument('--docker-image', default="workmemeval/eval:local",
                        help="Docker image to use for containerized runs (default: workmemeval/eval:local)")
    run_parser.set_defaults(func=cmd_run)

    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare evaluation results')
    compare_parser.add_argument('paths', nargs='+', help='Result JSON files or directories containing JSON results')
    compare_parser.set_defaults(func=cmd_compare)

    args = parser.parse_args(argv)
    if not hasattr(args, 'func'):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())

