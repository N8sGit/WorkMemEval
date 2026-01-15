#!/usr/bin/env python3
"""
WorkMemEval V2: Simple CLI

Usage:
  python -m src.v2.cli run tasks/v2/shopmind.yaml
  python -m src.v2.cli run tasks/v2/simple_recall.yaml --agent mock
  python -m src.v2.cli validate tasks/v2/shopmind.yaml
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from .task_loader import load_task
from .runner import V2Runner
from .models import EvaluationResult


def cmd_run(args: argparse.Namespace) -> int:
    """Run an evaluation task."""
    task_path = Path(args.task)
    
    # Load task
    try:
        task = load_task(task_path)
        print(f"Loaded task: {task.title}")
    except Exception as e:
        print(f"Error loading task: {e}")
        return 1
    
    # Get agent
    if args.agent == "mock":
        agent = create_mock_agent(task)
        print("Using MockAgent (for testing)")
    elif args.agent:
        agent = load_custom_agent(args.agent, args.agent_config)
        if agent is None:
            return 1
    else:
        # Default: try to load reference agent with LLM
        agent = create_default_agent(args)
        if agent is None:
            print("Error: No agent available. Use --agent mock for testing.")
            return 1
    
    # Setup workspace
    workspace = Path(args.workspace) if args.workspace else None
    
    # Run evaluation
    runner = V2Runner()
    
    async def _run():
        return await runner.run(task, agent, working_dir=workspace)
    
    result = asyncio.run(_run())
    
    # Output JSON if requested
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    
    # Return success if all pillars >= threshold
    threshold = args.threshold or 0.5
    all_pass = all(score >= threshold for score in result.pillar_scores.values())
    return 0 if all_pass else 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a task file without running it."""
    task_path = Path(args.task)
    
    try:
        task = load_task(task_path)
        print(f"✓ Task is valid: {task.title}")
        print(f"  ID: {task.task_id}")
        print(f"  Checkpoints: {len(task.checkpoints)}")
        
        for cp in task.checkpoints:
            print(f"    - {cp.id}: {len(cp.checks)} checks")
            for check in cp.checks:
                print(f"        [{check.pillar}] weight={check.weight}")
        
        if task.template:
            print(f"  Template: {task.template}")
        if task.history_file:
            print(f"  History: {task.history_file}")
        
        return 0
    except Exception as e:
        print(f"✗ Invalid task: {e}")
        return 1


def create_mock_agent(task):
    """Create a mock agent that produces passing responses."""
    from .runner import AgentProtocol
    
    class PassingMockAgent:
        """Mock agent that writes content designed to pass checks."""
        
        def __init__(self, task):
            self.task = task
            self.checkpoint_index = 0
        
        async def execute(self, prompt: str, working_dir: Path) -> None:
            # Generate workpad content that passes the checks
            workpad = working_dir / self.task.workpad_file
            existing = workpad.read_text() if workpad.exists() else ""
            
            # Get current checkpoint
            if self.checkpoint_index < len(self.task.checkpoints):
                cp = self.task.checkpoints[self.checkpoint_index]
                content = self._generate_passing_content(cp)
                self.checkpoint_index += 1
            else:
                content = "# Additional work\n"
            
            workpad.write_text(existing + "\n" + content)
        
        def _generate_passing_content(self, checkpoint) -> str:
            """Generate content that satisfies all checks."""
            lines = [f"\n## {checkpoint.id}\n"]
            
            for check in checkpoint.checks:
                # Include all must_contain terms
                for term in check.must_contain:
                    lines.append(f"- Noted: {term}")
                
                # Include one of must_contain_one_of
                if check.must_contain_one_of:
                    lines.append(f"- Decision: {check.must_contain_one_of[0]}")
                
                # Add pillar-specific phrasing
                if check.pillar == "fidelity":
                    lines.append("- I recall these facts from previous context")
                elif check.pillar == "relevance":
                    lines.append("- I reject irrelevant suggestions")
                elif check.pillar == "integrity":
                    lines.append("- Updated to reflect new requirements")
            
            return "\n".join(lines)
    
    return PassingMockAgent(task)


def create_default_agent(args):
    """Create the default agent (LLM-based if available)."""
    import os
    from .llm_agent import OpenRouterAgent
    
    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key and not args.model:
        print("Note: No OPENROUTER_API_KEY set. Use --agent mock for testing.")
        return None
    
    if args.model:
        # Create V2 LLM-backed agent
        try:
            return OpenRouterAgent(model=args.model, api_key=api_key)
        except Exception as e:
            print(f"Warning: Could not create OpenRouterAgent: {e}")
            return None

    return None


def load_custom_agent(agent_path: str, config_json: Optional[str]):
    """Load a custom agent from a module path."""
    try:
        module_path, class_name = agent_path.rsplit(":", 1)
        import importlib
        module = importlib.import_module(module_path)
        agent_class = getattr(module, class_name)
        
        config = {}
        if config_json:
            config = json.loads(config_json)
        
        return agent_class(**config)
    except Exception as e:
        print(f"Error loading agent {agent_path}: {e}")
        return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="workmemeval-v2",
        description="WorkMemEval V2: Simple memory evaluation"
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Run command
    p_run = subparsers.add_parser("run", help="Run an evaluation")
    p_run.add_argument("task", help="Path to task YAML file")
    p_run.add_argument("--workspace", help="Working directory (default: auto)")
    p_run.add_argument("--agent", help="Agent to use: 'mock' or module:Class")
    p_run.add_argument("--agent-config", help="JSON config for custom agent")
    p_run.add_argument("--model", help="LLM model (requires OPENROUTER_API_KEY)")
    p_run.add_argument("--json", action="store_true", help="Output JSON result")
    p_run.add_argument("--threshold", type=float, help="Pass threshold (default: 0.5)")
    p_run.set_defaults(func=cmd_run)
    
    # Validate command
    p_val = subparsers.add_parser("validate", help="Validate a task file")
    p_val.add_argument("task", help="Path to task YAML file")
    p_val.set_defaults(func=cmd_validate)
    
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
