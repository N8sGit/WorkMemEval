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
from .memory.simple_memory import SimpleContextMemory
from .evaluation.results import EvaluationResult, ComparisonResult


def cmd_run(args: argparse.Namespace) -> int:
    task_path = Path(args.task)
    working_directory = Path(args.workspace) if args.workspace else None

    memory = SimpleContextMemory({'max_items': 100})
    agent = SimpleWorkMemAgent(memory, {
        'max_iterations': 10,
        'memory_context_limit': 5,
        'llm_config': {'response_delay': 0.0}
    })

    runner = BasicWorkMemEvalRunner(containerized=getattr(args, 'container', False), docker_image=getattr(args, 'docker_image', None))

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
    parser = argparse.ArgumentParser(prog='WorkMemEval CLI')
    sub = parser.add_subparsers(dest='command', required=True)

    p_run = sub.add_parser('run', help='Run an evaluation for a task')
    p_run.add_argument('--task', required=True, help='Path to task JSON')
    p_run.add_argument('--workspace', help='Working directory for execution (optional)')
    group = p_run.add_mutually_exclusive_group()
    group.add_argument('--container', dest='container', action='store_true', help='Run tests inside Docker (default)')
    group.add_argument('--no-container', dest='container', action='store_false', help='Run tests locally without Docker')
    p_run.add_argument('--docker-image', default='workmemeval/eval:local', help='Docker image to use when running containerized')
    p_run.set_defaults(func=cmd_run, container=True)

    p_cmp = sub.add_parser('compare', help='Compare one or more evaluation result files or directories')
    p_cmp.add_argument('paths', nargs='+', help='Result JSON files or directories containing JSON results')
    p_cmp.set_defaults(func=cmd_compare)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())

