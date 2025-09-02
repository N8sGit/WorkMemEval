"""
Mathematical utilities for WorkMemEval.
"""

from typing import List, Sequence


def lcs_len(a: Sequence[str], b: Sequence[str]) -> int:
    """
    Calculate Longest Common Subsequence length.
    
    Args:
        a: First sequence
        b: Second sequence
        
    Returns:
        Length of LCS
    """
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        ai = a[i - 1]
        for j in range(1, m + 1):
            if ai == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[n][m]


def avg(values: List[float]) -> float:
    """
    Calculate average of a list of numbers.
    
    Args:
        values: List of numeric values
        
    Returns:
        Average value, 0.0 if empty list
    """
    return sum(values) / len(values) if values else 0.0


def greedy_match_ratio(plan: List[str], exec_: List[str], numerator_over: str) -> float:
    """
    Calculate greedy match ratio between planned and executed actions.
    
    Args:
        plan: Planned actions
        exec_: Executed actions
        numerator_over: 'plan' or 'exec' for denominator
        
    Returns:
        Match ratio between 0.0 and 1.0
    """
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
