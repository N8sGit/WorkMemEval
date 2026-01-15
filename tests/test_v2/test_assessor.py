"""
Unit tests for WorkpadAssessor.

Tests the core pattern matching logic without needing agents or runners.
"""

import pytest
from src.v2.assessor import WorkpadAssessor
from src.v2.models import WorkpadCheck


class TestMustContain:
    """Tests for must_contain checks."""
    
    def test_all_terms_present(self):
        assessor = WorkpadAssessor()
        content = "The free shipping threshold is $75 and loyalty rate is 100 points per dollar"
        check = WorkpadCheck(
            pillar="fidelity",
            must_contain=["75", "100", "shipping"]
        )
        result = assessor.evaluate(content, [check])
        assert result["fidelity"] == 1.0
    
    def test_partial_terms_present(self):
        assessor = WorkpadAssessor()
        content = "The threshold is $75"
        check = WorkpadCheck(
            pillar="fidelity",
            must_contain=["75", "100", "shipping"]
        )
        result = assessor.evaluate(content, [check])
        # 1 out of 3 found = 0.333...
        assert 0.3 <= result["fidelity"] <= 0.4
    
    def test_no_terms_present(self):
        assessor = WorkpadAssessor()
        content = "Nothing relevant here"
        check = WorkpadCheck(
            pillar="fidelity",
            must_contain=["75", "100"]
        )
        result = assessor.evaluate(content, [check])
        assert result["fidelity"] == 0.0
    
    def test_case_insensitive_by_default(self):
        assessor = WorkpadAssessor()
        content = "The SHIPPING threshold is $75"
        check = WorkpadCheck(
            pillar="fidelity",
            must_contain=["shipping", "75"]
        )
        result = assessor.evaluate(content, [check])
        assert result["fidelity"] == 1.0


class TestMustContainOneOf:
    """Tests for must_contain_one_of checks."""
    
    def test_one_term_present(self):
        assessor = WorkpadAssessor()
        content = "I will reject this suggestion as it contradicts policy"
        check = WorkpadCheck(
            pillar="relevance",
            must_contain_one_of=["reject", "ignore", "contradicts"]
        )
        result = assessor.evaluate(content, [check])
        assert result["relevance"] == 1.0
    
    def test_multiple_terms_present(self):
        assessor = WorkpadAssessor()
        content = "I reject this as it contradicts our rules"
        check = WorkpadCheck(
            pillar="relevance",
            must_contain_one_of=["reject", "ignore", "contradicts"]
        )
        result = assessor.evaluate(content, [check])
        assert result["relevance"] == 1.0
    
    def test_no_terms_present(self):
        assessor = WorkpadAssessor()
        content = "This sounds like a great idea!"
        check = WorkpadCheck(
            pillar="relevance",
            must_contain_one_of=["reject", "ignore", "contradicts"]
        )
        result = assessor.evaluate(content, [check])
        assert result["relevance"] == 0.0


class TestMustNotContain:
    """Tests for must_not_contain checks."""
    
    def test_no_forbidden_terms(self):
        assessor = WorkpadAssessor()
        content = "I will use the established discount rules"
        check = WorkpadCheck(
            pillar="relevance",
            must_not_contain=["stack discounts", "great idea"]
        )
        result = assessor.evaluate(content, [check])
        assert result["relevance"] == 1.0
    
    def test_one_forbidden_term(self):
        assessor = WorkpadAssessor()
        content = "Great idea! Let's stack discounts"
        check = WorkpadCheck(
            pillar="relevance",
            must_not_contain=["stack discounts", "great idea"]
        )
        result = assessor.evaluate(content, [check])
        # Both violations = 0.0
        assert result["relevance"] == 0.0
    
    def test_partial_violation(self):
        assessor = WorkpadAssessor()
        content = "This is a great idea but we can't do it"
        check = WorkpadCheck(
            pillar="relevance",
            must_not_contain=["stack discounts", "great idea"]
        )
        result = assessor.evaluate(content, [check])
        # 1 of 2 forbidden = 0.5
        assert result["relevance"] == 0.5


class TestRegexPatterns:
    """Tests for regex pattern matching."""
    
    def test_simple_pattern_match(self):
        assessor = WorkpadAssessor()
        content = "Return window is 45 days for standard customers"
        check = WorkpadCheck(
            pillar="integrity",
            regex_patterns=[r"45\s*days"]
        )
        result = assessor.evaluate(content, [check])
        assert result["integrity"] == 1.0
    
    def test_multiple_patterns(self):
        assessor = WorkpadAssessor()
        content = "Standard: 45 days, VIP: 90 days, Digital: 14 days"
        check = WorkpadCheck(
            pillar="integrity",
            regex_patterns=[r"45\s*days", r"90\s*days", r"14\s*days"]
        )
        result = assessor.evaluate(content, [check])
        assert result["integrity"] == 1.0
    
    def test_pattern_no_match(self):
        assessor = WorkpadAssessor()
        content = "Return window is 30 days"
        check = WorkpadCheck(
            pillar="integrity",
            regex_patterns=[r"45\s*days"]
        )
        result = assessor.evaluate(content, [check])
        assert result["integrity"] == 0.0


class TestCombinedChecks:
    """Tests for checks with multiple criteria."""
    
    def test_must_contain_and_must_not_contain(self):
        assessor = WorkpadAssessor()
        content = "The threshold is $75. I reject stacking discounts."
        check = WorkpadCheck(
            pillar="fidelity",
            must_contain=["75"],
            must_not_contain=["stack discounts"]
        )
        result = assessor.evaluate(content, [check])
        # Both conditions satisfied
        assert result["fidelity"] == 1.0
    
    def test_mixed_success(self):
        assessor = WorkpadAssessor()
        content = "Great idea to stack discounts! Threshold is $75."
        check = WorkpadCheck(
            pillar="relevance",
            must_contain=["75"],
            must_not_contain=["stack discounts", "great idea"]
        )
        result = assessor.evaluate(content, [check])
        # must_contain: 1.0 (found 75)
        # must_not_contain: 0.0 (both violations)
        # Average: 0.5
        assert result["relevance"] == 0.5


class TestMultipleChecks:
    """Tests for multiple checks on same content."""
    
    def test_multiple_pillars(self):
        assessor = WorkpadAssessor()
        content = """
        ## Business Rules
        - Free shipping at $75
        - 100 points = $1
        
        ## Decisions
        - Rejecting colleague suggestion (contradicts policy)
        
        ## Updates
        - New return window: 45 days standard
        """
        checks = [
            WorkpadCheck(pillar="fidelity", must_contain=["75", "100"]),
            WorkpadCheck(pillar="relevance", must_contain_one_of=["reject", "contradicts"]),
            WorkpadCheck(pillar="integrity", must_contain=["45"]),
        ]
        result = assessor.evaluate(content, checks)
        
        assert result["fidelity"] == 1.0
        assert result["relevance"] == 1.0
        assert result["integrity"] == 1.0
    
    def test_weighted_checks(self):
        assessor = WorkpadAssessor()
        content = "Only has 75"
        checks = [
            WorkpadCheck(pillar="fidelity", must_contain=["75"], weight=2.0),
            WorkpadCheck(pillar="fidelity", must_contain=["100"], weight=1.0),
        ]
        result = assessor.evaluate(content, checks)
        # First check: 1.0 * weight 2.0
        # Second check: 0.0 * weight 1.0
        # Total: 2.0 / 3.0 = 0.667
        assert 0.65 <= result["fidelity"] <= 0.68


class TestEvaluateWithDetails:
    """Tests for detailed evaluation output."""
    
    def test_returns_check_details(self):
        assessor = WorkpadAssessor()
        content = "Threshold is $75, rejecting bad suggestion"
        checks = [
            WorkpadCheck(
                pillar="fidelity",
                must_contain=["75", "100"],
                description="Recall business rules"
            ),
        ]
        scores, details = assessor.evaluate_with_details(content, checks)
        
        assert len(details) == 1
        assert details[0]["pillar"] == "fidelity"
        assert details[0]["description"] == "Recall business rules"
        assert details[0]["details"]["must_contain"]["75"] is True
        assert details[0]["details"]["must_contain"]["100"] is False
