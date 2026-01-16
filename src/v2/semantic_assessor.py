"""
WorkMemEval V2: Semantic Assessor (LLM-based)

Optional LLM-powered assessment that complements pattern matching.
Uses structured prompts with explicit truth sources to grade workpad content.

Design choices for reliability:
- Temperature 0.0 for determinism
- Structured JSON output format
- Binary/ternary grading (not continuous)
- Truth source explicitly provided to LLM
- Can run multiple times and take majority vote
"""

import json
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
import httpx


class Grade(Enum):
    """Simple grading scale to reduce LLM variance."""
    CORRECT = "correct"      # Fully accurate
    PARTIAL = "partial"      # Partially accurate or semantically close
    INCORRECT = "incorrect"  # Wrong or missing


@dataclass
class SemanticCheck:
    """A semantic check with truth source."""
    pillar: str
    description: str
    truth: str              # What the agent SHOULD have remembered
    weight: float = 1.0


@dataclass  
class SemanticResult:
    """Result of semantic assessment."""
    grade: Grade
    score: float            # 1.0 for correct, 0.5 for partial, 0.0 for incorrect
    reasoning: str          # LLM's explanation
    truth: str              # The expected answer
    found: str              # What was found in workpad


class SemanticAssessor:
    """
    LLM-based assessor that grades workpad content against truth sources.
    
    This is OPTIONAL and complements the deterministic pattern matching.
    Use when you need semantic understanding beyond exact string matching.
    
    Example use cases:
    - "$75" vs "seventy-five dollars" vs "$75.00" (all equivalent)
    - "VIP gets 10% off" vs "10% discount for VIP members" (same meaning)
    - Partial credit for close-but-not-exact answers
    """
    
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    GRADING_PROMPT = '''You are a precise grading assistant. Your job is to compare an agent's workpad notes against ground truth facts.

GROUND TRUTH (what the agent should have remembered):
{truth}

AGENT'S WORKPAD:
{workpad}

TASK: Grade whether the agent correctly captured the ground truth in their workpad.

GRADING CRITERIA:
- CORRECT: The information is present and accurate (exact match or semantic equivalent)
- PARTIAL: The information is partially present, or close but with minor errors
- INCORRECT: The information is missing, wrong, or contradicted

Respond with ONLY this JSON format:
{{"grade": "correct|partial|incorrect", "reasoning": "brief explanation", "found": "relevant text from workpad or 'not found'"}}'''

    def __init__(
        self,
        model: str = "openai/gpt-5.2",
        api_key: Optional[str] = None,
        temperature: float = 0.0,
        num_votes: int = 1,
    ):
        """
        Initialize semantic assessor.
        
        Args:
            model: OpenRouter model to use
            api_key: OpenRouter API key (or set OPENROUTER_API_KEY env var)
            temperature: LLM temperature (0.0 recommended for consistency)
            num_votes: Run assessment this many times and take majority (odd number)
        """
        self.model = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.temperature = temperature
        self.num_votes = num_votes if num_votes % 2 == 1 else num_votes + 1
        
        if not self.api_key:
            raise ValueError("OpenRouter API key required")
    
    async def evaluate(
        self, 
        workpad_content: str, 
        checks: list[SemanticCheck]
    ) -> dict[str, float]:
        """
        Evaluate workpad against semantic checks.
        
        Returns:
            Dictionary mapping pillar names to scores (0.0 - 1.0)
        """
        pillar_scores: dict[str, list[tuple[float, float]]] = {}
        
        for check in checks:
            result = await self._grade_check(workpad_content, check)
            
            if check.pillar not in pillar_scores:
                pillar_scores[check.pillar] = []
            pillar_scores[check.pillar].append((result.score, check.weight))
        
        # Calculate weighted averages
        final_scores = {}
        for pillar, scores_weights in pillar_scores.items():
            total_weight = sum(w for _, w in scores_weights)
            if total_weight > 0:
                weighted_sum = sum(s * w for s, w in scores_weights)
                final_scores[pillar] = weighted_sum / total_weight
            else:
                final_scores[pillar] = 0.0
        
        return final_scores
    
    async def evaluate_with_details(
        self,
        workpad_content: str,
        checks: list[SemanticCheck]
    ) -> tuple[dict[str, float], list[dict[str, Any]]]:
        """
        Evaluate with detailed per-check results.
        
        Returns:
            Tuple of (pillar_scores, check_details)
        """
        pillar_scores: dict[str, list[tuple[float, float]]] = {}
        check_details = []
        
        for check in checks:
            result = await self._grade_check(workpad_content, check)
            
            if check.pillar not in pillar_scores:
                pillar_scores[check.pillar] = []
            pillar_scores[check.pillar].append((result.score, check.weight))
            
            check_details.append({
                "pillar": check.pillar,
                "description": check.description,
                "truth": check.truth,
                "grade": result.grade.value,
                "score": result.score,
                "reasoning": result.reasoning,
                "found": result.found,
                "weight": check.weight,
            })
        
        # Calculate weighted averages
        final_scores = {}
        for pillar, scores_weights in pillar_scores.items():
            total_weight = sum(w for _, w in scores_weights)
            if total_weight > 0:
                weighted_sum = sum(s * w for s, w in scores_weights)
                final_scores[pillar] = weighted_sum / total_weight
            else:
                final_scores[pillar] = 0.0
        
        return final_scores, check_details
    
    async def _grade_check(
        self, 
        workpad_content: str, 
        check: SemanticCheck
    ) -> SemanticResult:
        """Grade a single check, optionally with majority voting."""
        if self.num_votes == 1:
            return await self._single_grade(workpad_content, check)
        
        # Multiple votes for stability
        votes: list[SemanticResult] = []
        for _ in range(self.num_votes):
            result = await self._single_grade(workpad_content, check)
            votes.append(result)
        
        # Majority vote on grade
        grade_counts = {Grade.CORRECT: 0, Grade.PARTIAL: 0, Grade.INCORRECT: 0}
        for v in votes:
            grade_counts[v.grade] += 1
        
        majority_grade = max(grade_counts, key=grade_counts.get)
        majority_result = next(v for v in votes if v.grade == majority_grade)
        
        return majority_result
    
    async def _single_grade(
        self, 
        workpad_content: str, 
        check: SemanticCheck
    ) -> SemanticResult:
        """Perform a single grading call."""
        prompt = self.GRADING_PROMPT.format(
            truth=check.truth,
            workpad=workpad_content[:4000]  # Limit context
        )
        
        try:
            response = await self._call_llm(prompt)
            return self._parse_response(response, check.truth)
        except Exception as e:
            # Fallback to incorrect on error
            return SemanticResult(
                grade=Grade.INCORRECT,
                score=0.0,
                reasoning=f"Assessment error: {e}",
                truth=check.truth,
                found="error"
            )
    
    async def _call_llm(self, prompt: str) -> str:
        """Call OpenRouter API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": 500,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.OPENROUTER_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    def _parse_response(self, response: str, truth: str) -> SemanticResult:
        """Parse LLM response into SemanticResult."""
        # Extract JSON from response
        try:
            # Try direct JSON parse
            data = json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON in response
            match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    data = {}
            else:
                data = {}
        
        grade_str = data.get("grade", "incorrect").lower()
        grade_map = {
            "correct": Grade.CORRECT,
            "partial": Grade.PARTIAL,
            "incorrect": Grade.INCORRECT,
        }
        grade = grade_map.get(grade_str, Grade.INCORRECT)
        
        score_map = {
            Grade.CORRECT: 1.0,
            Grade.PARTIAL: 0.5,
            Grade.INCORRECT: 0.0,
        }
        
        return SemanticResult(
            grade=grade,
            score=score_map[grade],
            reasoning=data.get("reasoning", "No reasoning provided"),
            truth=truth,
            found=data.get("found", "unknown")
        )


class HybridAssessor:
    """
    Combines pattern matching (deterministic) with semantic assessment (LLM).
    
    The final score is a weighted combination:
    - pattern_weight * pattern_score + semantic_weight * semantic_score
    
    Default: 70% pattern, 30% semantic (prioritizes determinism)
    """
    
    def __init__(
        self,
        pattern_assessor,  # WorkpadAssessor
        semantic_assessor: Optional[SemanticAssessor] = None,
        pattern_weight: float = 0.7,
        semantic_weight: float = 0.3,
    ):
        self.pattern_assessor = pattern_assessor
        self.semantic_assessor = semantic_assessor
        self.pattern_weight = pattern_weight
        self.semantic_weight = semantic_weight
        
        # Normalize weights
        total = pattern_weight + semantic_weight
        self.pattern_weight /= total
        self.semantic_weight /= total
    
    async def evaluate(
        self,
        workpad_content: str,
        pattern_checks: list,        # WorkpadCheck objects
        semantic_checks: Optional[list[SemanticCheck]] = None,
    ) -> dict[str, float]:
        """
        Evaluate using both pattern and semantic assessment.
        
        Returns combined scores per pillar.
        """
        # Pattern matching (always run)
        pattern_scores = self.pattern_assessor.evaluate(workpad_content, pattern_checks)
        
        # Semantic assessment (optional)
        if self.semantic_assessor and semantic_checks:
            semantic_scores = await self.semantic_assessor.evaluate(
                workpad_content, semantic_checks
            )
            
            # Combine scores per pillar
            all_pillars = set(pattern_scores.keys()) | set(semantic_scores.keys())
            combined = {}
            
            for pillar in all_pillars:
                p_score = pattern_scores.get(pillar, 0.0)
                s_score = semantic_scores.get(pillar, 0.0)
                
                # If only one method has the pillar, use that score
                if pillar not in pattern_scores:
                    combined[pillar] = s_score
                elif pillar not in semantic_scores:
                    combined[pillar] = p_score
                else:
                    combined[pillar] = (
                        self.pattern_weight * p_score +
                        self.semantic_weight * s_score
                    )
            
            return combined
        
        return pattern_scores
