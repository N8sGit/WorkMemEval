#!/usr/bin/env python3
"""
WorkMemEval: Unified Entry Point

A2A-compatible working memory benchmark for AI agents.

Usage:
    # Run evaluation with A2A-compatible reference agent
    python workmemeval.py run --task shopmind
    python workmemeval.py run --task extended --model anthropic/claude-3.5-sonnet

    # Run in Docker (recommended for reproducibility)
    docker compose -f docker/compose.dev.yml run --rm eval python workmemeval.py run --task shopmind

    # Test with mock agent (no API key needed)
    python workmemeval.py demo --task shopmind
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()


def cmd_run(args):
    """Run evaluation with LLM-powered agent."""
    from src.v2 import load_task, V2Runner
    from src.v2.llm_agent import OpenRouterAgent
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set")
        print("Set it with: export OPENROUTER_API_KEY=your_key")
        print("Or add to .env file")
        return 1
    
    task_paths = {
        "simple": Path("tasks/v2/simple_recall.yaml"),
        "shopmind": Path("tasks/v2/shopmind.yaml"),
        "extended": Path("tasks/v2/shopmind_extended.yaml"),
        "semantic": Path("tasks/v2/shopmind_semantic.yaml"),
    }
    
    task_path = task_paths.get(args.task)
    if not task_path:
        # Try as direct path
        task_path = Path(args.task)
    
    if not task_path.exists():
        print(f"Task not found: {args.task}")
        print(f"Available: {list(task_paths.keys())}")
        return 1
    
    print(f"\n{'='*60}")
    print(f"WORKMEMEVAL - EVALUATION")
    print(f"{'='*60}")
    print(f"Task: {task_path}")
    print(f"Model: {args.model}")
    print()
    
    async def _run():
        task = load_task(task_path)
        agent = OpenRouterAgent(model=args.model, api_key=api_key)
        
        runner = V2Runner(
            output_dir=Path("evaluation_runs/v2"),
            use_container=args.container,
            docker_image=args.docker_image,
        )
        result = await runner.run(task, agent)
        
        print("\n" + "="*60)
        print("FINAL WORKPAD:")
        print("="*60)
        print(result.final_workpad)
        return result
    
    asyncio.run(_run())
    return 0


def cmd_demo(args):
    """Run V2 evaluation with mock agent."""
    from src.v2 import load_task, V2Runner
    
    # Import DemoAgent inline to keep it self-contained
    class DemoAgent:
        def __init__(self, mode: str = "passing"):
            self.mode = mode
            self.checkpoint_count = 0
        
        async def execute(self, prompt: str, working_dir: Path) -> None:
            self.checkpoint_count += 1
            workpad_path = working_dir / "WORKPAD.md"
            existing = workpad_path.read_text() if workpad_path.exists() else ""
            
            if self.mode == "passing":
                content = self._passing(prompt)
            else:
                content = f"## Checkpoint {self.checkpoint_count}\nDid some work."
            
            workpad_path.write_text(existing + "\n" + content)
            print(f"  [DemoAgent] Updated WORKPAD.md (checkpoint {self.checkpoint_count})")
        
        def _passing(self, prompt: str) -> str:
            p = prompt.lower()
            if any(x in p for x in ["gift", "shipping", "loyalty", "pricing"]):
                return """
## Business Rules Recalled
- **Free shipping threshold**: $75
- **Loyalty points**: 100 points = $1 discount
- **Discount stacking**: Don't stack - apply better deal
- **VIP loyalty rate**: 2x points
"""
            elif any(x in p for x in ["colleague", "suggestion"]):
                return """
## Decision: Colleague Suggestion
After reviewing colleague_suggestion.md, I must **reject** this suggestion.
It contradicts our established architecture.
"""
            elif any(x in p for x in ["policy", "return", "update"]):
                return """
## Policy Update Applied
- **Standard customers**: 45 days (was 30 days)
- **VIP customers**: 90 days (was 60 days)
"""
            return f"## Checkpoint {self.checkpoint_count}\nCompleted."
    
    task_paths = {
        "simple": Path("tasks/v2/simple_recall.yaml"),
        "shopmind": Path("tasks/v2/shopmind.yaml"),
    }
    
    task_path = task_paths.get(args.task, Path(args.task))
    if not task_path.exists():
        print(f"Task not found: {args.task}")
        return 1
    
    print(f"\n{'='*60}")
    print(f"WORKMEMEVAL - DEMO (Mock Agent)")
    print(f"{'='*60}")
    print(f"Task: {task_path}")
    print(f"Mode: {'failing' if args.failing else 'passing'}")
    
    async def _run():
        task = load_task(task_path)
        agent = DemoAgent(mode="failing" if args.failing else "passing")
        runner = V2Runner(output_dir=Path("evaluation_runs/demo"))
        result = await runner.run(task, agent)
        
        print("\n" + "="*60)
        print("FINAL WORKPAD:")
        print("="*60)
        print(result.final_workpad)
        return result
    
    asyncio.run(_run())
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="WorkMemEval: Working Memory Benchmark for AI Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python workmemeval.py run --task shopmind          # Live LLM evaluation
  python workmemeval.py run --task extended          # 12-checkpoint stress test
  python workmemeval.py demo --task shopmind         # Mock agent test
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # run: V2 with real LLM
    run_parser = subparsers.add_parser("run", help="Run evaluation with real LLM (V2)")
    run_parser.add_argument("--task", default="simple",
                            help="Task name (simple, shopmind, extended) or path")
    run_parser.add_argument("--model", default="openai/gpt-5.2",
                            help="OpenRouter model to use")
    run_parser.add_argument("--container", action="store_true",
                            help="Run in Docker container")
    run_parser.add_argument("--docker-image", default="workmemeval/eval:local",
                            help="Docker image for containerized execution")
    run_parser.set_defaults(func=cmd_run)
    
    # demo: V2 with mock agent
    demo_parser = subparsers.add_parser("demo", help="Run with mock agent (testing)")
    demo_parser.add_argument("--task", default="shopmind",
                             help="Task name (simple, shopmind) or path")
    demo_parser.add_argument("--failing", action="store_true",
                             help="Simulate a failing agent")
    demo_parser.set_defaults(func=cmd_demo)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
