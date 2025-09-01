"""
Metrics computation for WorkMemEval.

Includes:
- Memory Fidelity (context reread rate, error rate, error correction overhead)
- Contextual Relevance (precision/recall/f1 against required files proxy)
- Plan Compliance (coverage, order, on-plan action ratio, time-on-plan, replan count)
"""

from __future__ import annotations

import warnings
warnings.warn(
    "src.evaluation.metrics is deprecated and will be removed in a future release. "
    "Use src.evaluation.memory_metrics (three-pillar engine) instead.",
    DeprecationWarning,
    stacklevel=2,
)

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..core.action_trace import TaskTrace, ActionType, CheckpointTrace, ActionTraceEntry
from ..core.task_specification import TaskSpecification


def compute_memory_fidelity(task_trace: TaskTrace) -> Dict[str, float]:
    if not task_trace or not task_trace.checkpoint_traces:
        return {
            "context_reread_rate": 0.0,
            "error_rate": 0.0,
            "error_correction_overhead": 0.0,
        }

    # Reread rate: derive from file access patterns
    file_accesses: List[str] = []
    total_actions = 0
    total_errors = 0
    for cp in task_trace.checkpoint_traces:
        total_actions += len(cp.actions)
        total_errors += len(cp.errors_encountered)
        for a in cp.actions:
            if a.file_path and a.action_type in (ActionType.FILE_READ, ActionType.FILE_WRITE, ActionType.FILE_MODIFY):
                file_accesses.append(a.file_path)

    unique_files = len(set(file_accesses)) if file_accesses else 0
    total_accesses = len(file_accesses)
    context_reread_rate = (1.0 - (unique_files / total_accesses)) if total_accesses > 0 else 0.0

    error_rate = total_errors / max(1, total_actions)

    return {
        "context_reread_rate": context_reread_rate,
        "error_rate": error_rate,
        # v1 proxy: same as error_rate, refine later to correction-only overhead
        "error_correction_overhead": error_rate,
    }


def _basename(path_str: str) -> str:
    try:
        return Path(path_str).name
    except Exception:
        return path_str


def compute_contextual_relevance(task_spec: TaskSpecification, task_trace: TaskTrace) -> Dict[str, float]:
    # Required files (v1): union of stub_file across checkpoints (exclude test files for recall proxy)
    required: set[str] = set()
    for cp in task_spec.checkpoints:
        if cp.stub_file:
            required.add(_basename(cp.stub_file))

    # Accessed files from actions
    accessed: set[str] = set()
    for cp in task_trace.checkpoint_traces:
        for a in cp.actions:
            if a.file_path and a.action_type in (ActionType.FILE_READ, ActionType.FILE_WRITE, ActionType.FILE_MODIFY):
                accessed.add(_basename(a.file_path))

    if len(accessed) == 0:
        precision = 0.0
    else:
        precision = len(accessed & required) / len(accessed)

    if len(required) == 0:
        recall = 0.0
    else:
        recall = len(accessed & required) / len(required)

    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return {
        "relevance_precision": precision,
        "relevance_recall": recall,
        "relevance_f1": f1,
    }


def _planned_step_token(step: Dict) -> Optional[str]:
    action = step.get("action")
    if action == "read_file":
        return f"read_file:{_basename(step.get('file_path',''))}"
    if action in ("create_file", "edit_file"):
        return f"write_file:{_basename(step.get('file_path',''))}"
    if action == "implement":
        return "implement"
    return None


def _executed_action_token(a: ActionTraceEntry) -> Optional[str]:
    if a.action_type == ActionType.FILE_READ and a.file_path:
        return f"read_file:{_basename(a.file_path)}"
    if a.action_type in (ActionType.FILE_WRITE, ActionType.FILE_MODIFY) and a.file_path:
        return f"write_file:{_basename(a.file_path)}"
    if a.action_type == ActionType.LLM_CALL:
        return "implement"
    return None


def _lcs_len(a: List[str], b: List[str]) -> int:
    n, m = len(a), len(b)
    dp = [[0]*(m+1) for _ in range(n+1)]
    for i in range(1, n+1):
        ai = a[i-1]
        for j in range(1, m+1):
            if ai == b[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[n][m]


def _greedy_match_ratio(plan: List[str], exec_: List[str], numerator_over: str) -> float:
    # If numerator_over == 'plan': matched / len(plan)
    # If numerator_over == 'exec': matched / len(exec_)
    # This function keeps order-sensitive matching.
    i = j = matched = 0
    while i < len(plan) and j < len(exec_):
        if plan[i] == exec_[j]:
            matched += 1
            i += 1
            j += 1
        else:
            j += 1
    denom = len(plan) if numerator_over == 'plan' else len(exec_)
    return matched / max(1, denom)


def _time_on_plan_ratio(exec_actions: List[ActionTraceEntry], exec_tokens: List[str], plan: List[str]) -> float:
    # Build indices of matched executed actions via greedy exec->plan matching
    i = j = 0
    matched_exec_idxs: set[int] = set()
    while i < len(plan) and j < len(exec_tokens):
        if plan[i] == exec_tokens[j]:
            matched_exec_idxs.add(j)
            i += 1
            j += 1
        else:
            j += 1

    total = 0.0
    on_plan = 0.0
    for k in range(len(exec_actions) - 1):
        dt = max(0.0, (exec_actions[k+1].timestamp - exec_actions[k].timestamp) or 0.0)
        total += dt
        if k in matched_exec_idxs:
            on_plan += dt
    return (on_plan / total) if total > 0 else 0.0


def compute_plan_compliance(task_spec: TaskSpecification, task_trace: TaskTrace) -> Dict[str, float]:
    if not task_trace or not task_trace.checkpoint_traces:
        return {
            "plan_coverage": 0.0,
            "plan_order_score": 0.0,
            "on_plan_action_ratio": 0.0,
            "time_on_plan_ratio": 0.0,
            "replan_count": 0.0,
        }

    coverages: List[float] = []
    orders: List[float] = []
    on_plan_ratios: List[float] = []
    time_ratios: List[float] = []
    replans: int = 0

    for cp in task_trace.checkpoint_traces:
        # Extract plan from first PLANNING action metadata if present
        plan_steps: List[Dict] = []
        planning_actions = [a for a in cp.actions if a.action_type == ActionType.PLANNING]
        if planning_actions:
            first_plan = planning_actions[0]
            plan_steps = first_plan.metadata.get("plan", []) or []
            # Count replans beyond the first
            replans += max(0, len(planning_actions) - 1)

        planned_tokens = [t for t in (_planned_step_token(s) for s in plan_steps) if t]

        exec_tokens: List[str] = []
        exec_actions: List[ActionTraceEntry] = []
        for a in cp.actions:
            t = _executed_action_token(a)
            if t:
                exec_tokens.append(t)
                exec_actions.append(a)

        # Coverage (order-insensitive): multiset overlap of planned vs executed tokens
        from collections import Counter
        plan_counts = Counter(planned_tokens)
        exec_counts = Counter(exec_tokens)
        matched_counts = sum(min(plan_counts[t], exec_counts.get(t, 0)) for t in plan_counts)
        coverage = matched_counts / max(1, len(planned_tokens))
        # Order score (order-sensitive): LCS over token sequences
        order = (_lcs_len(planned_tokens, exec_tokens) / max(1, len(planned_tokens))) if planned_tokens else 0.0
        on_plan = _greedy_match_ratio(planned_tokens, exec_tokens, numerator_over='exec')
        time_ratio = _time_on_plan_ratio(exec_actions, exec_tokens, planned_tokens) if exec_actions else 0.0

        coverages.append(coverage)
        orders.append(order)
        on_plan_ratios.append(on_plan)
        time_ratios.append(time_ratio)

    def avg(xs: List[float]) -> float:
        return (sum(xs) / len(xs)) if xs else 0.0

    return {
        "plan_coverage": avg(coverages),
        "plan_order_score": avg(orders),
        "on_plan_action_ratio": avg(on_plan_ratios),
        "time_on_plan_ratio": avg(time_ratios),
        "replan_count": float(replans),
    }


def compute_all_metrics(task_spec: TaskSpecification, task_trace: TaskTrace) -> Dict[str, float]:
    m: Dict[str, float] = {}
    m.update(compute_memory_fidelity(task_trace))
    m.update(compute_contextual_relevance(task_spec, task_trace))
    m.update(compute_plan_compliance(task_spec, task_trace))
    return m

