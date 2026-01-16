"""
WorkMemEval V2: Workpad Assessor

Evaluates workpad content against defined checks.
Simple pattern matching - no AST, no code parsing, no complex verification chains.
"""

import re
from typing import Any
from .models import WorkpadCheck, Pillar


class WorkpadAssessor:
    """
    Evaluates WORKPAD.md content against checkpoint checks.
    
    Scoring is straightforward:
    - must_contain: All terms must be present (score = found/total)
    - must_contain_one_of: At least one term must be present (binary)
    - must_not_contain: No forbidden terms (penalty per violation)
    - regex_patterns: All patterns must match (score = matched/total)
    """
    
    def __init__(self, case_sensitive: bool = False):
        self.case_sensitive = case_sensitive
    
    def evaluate(self, workpad_content: str, checks: list[WorkpadCheck]) -> dict[str, float]:
        """
        Evaluate workpad content against all checks.
        
        Args:
            workpad_content: The content of WORKPAD.md
            checks: List of WorkpadCheck objects to verify
            
        Returns:
            Dictionary mapping pillar names to scores (0.0 - 1.0)
        """
        # Normalize content for matching
        content = workpad_content if self.case_sensitive else workpad_content.lower()
        
        # Accumulate scores per pillar
        pillar_scores: dict[str, list[tuple[float, float]]] = {}  # pillar -> [(score, weight), ...]
        
        for check in checks:
            score, details = self._evaluate_check(content, check)
            
            if check.pillar not in pillar_scores:
                pillar_scores[check.pillar] = []
            pillar_scores[check.pillar].append((score, check.weight))
        
        # Calculate weighted average per pillar
        result = {}
        for pillar, scores_and_weights in pillar_scores.items():
            total_weight = sum(w for _, w in scores_and_weights)
            if total_weight > 0:
                weighted_sum = sum(s * w for s, w in scores_and_weights)
                result[pillar] = weighted_sum / total_weight
            else:
                result[pillar] = 0.0
        
        return result
    
    def evaluate_with_details(
        self, workpad_content: str, checks: list[WorkpadCheck]
    ) -> tuple[dict[str, float], list[dict[str, Any]]]:
        """
        Evaluate with detailed per-check breakdown.
        
        Returns:
            Tuple of (pillar_scores, check_details)
        """
        content = workpad_content if self.case_sensitive else workpad_content.lower()
        
        pillar_scores: dict[str, list[tuple[float, float]]] = {}
        check_details = []
        
        for check in checks:
            score, details = self._evaluate_check(content, check)
            
            if check.pillar not in pillar_scores:
                pillar_scores[check.pillar] = []
            pillar_scores[check.pillar].append((score, check.weight))
            
            check_details.append({
                "pillar": check.pillar,
                "score": score,
                "weight": check.weight,
                "details": details,
                "description": check.description,
            })
        
        # Calculate weighted averages
        result = {}
        for pillar, scores_and_weights in pillar_scores.items():
            total_weight = sum(w for _, w in scores_and_weights)
            if total_weight > 0:
                weighted_sum = sum(s * w for s, w in scores_and_weights)
                result[pillar] = weighted_sum / total_weight
            else:
                result[pillar] = 0.0
        
        return result, check_details
    
    def _evaluate_check(self, content: str, check: WorkpadCheck) -> tuple[float, dict]:
        """
        Evaluate a single check against content.
        
        Returns:
            Tuple of (score, details_dict)
        """
        details = {
            "must_contain": {},
            "must_contain_one_of": {},
            "must_not_contain": {},
            "regex_patterns": {},
        }
        
        scores = []
        
        # must_contain: All terms must be present
        if check.must_contain:
            found = 0
            for term in check.must_contain:
                term_normalized = term if self.case_sensitive else term.lower()
                present = term_normalized in content
                details["must_contain"][term] = present
                if present:
                    found += 1
            
            score = found / len(check.must_contain)
            scores.append(score)
        
        # must_contain_one_of: At least one term must be present
        if check.must_contain_one_of:
            found_any = False
            for term in check.must_contain_one_of:
                term_normalized = term if self.case_sensitive else term.lower()
                present = term_normalized in content
                details["must_contain_one_of"][term] = present
                if present:
                    found_any = True
            
            score = 1.0 if found_any else 0.0
            scores.append(score)
        
        # must_not_contain: No forbidden terms
        if check.must_not_contain:
            violations = 0
            for term in check.must_not_contain:
                term_normalized = term if self.case_sensitive else term.lower()
                present = term_normalized in content
                details["must_not_contain"][term] = present  # True = violation
                if present:
                    violations += 1
            
            # Score decreases with violations
            score = max(0.0, 1.0 - (violations / len(check.must_not_contain)))
            scores.append(score)
        
        # regex_patterns: All patterns must match
        if check.regex_patterns:
            matched = 0
            flags = 0 if self.case_sensitive else re.IGNORECASE
            for pattern in check.regex_patterns:
                try:
                    match = bool(re.search(pattern, content, flags))
                    details["regex_patterns"][pattern] = match
                    if match:
                        matched += 1
                except re.error as e:
                    details["regex_patterns"][pattern] = f"ERROR: {e}"
            
            score = matched / len(check.regex_patterns)
            scores.append(score)
        
        # Overall score is average of all components
        final_score = sum(scores) / len(scores) if scores else 1.0
        
        return final_score, details
