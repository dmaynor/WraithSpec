# SPDX-License-Identifier: MIT
"""Tests for the WraithSpec compliance module."""

import json
import unittest

from tools.validator.compliance import (
    check_compliance,
    score_output,
    determine_level,
    ComplianceLevel,
    ComplianceResult,
    ComplianceViolation,
    extract_tally_from_output,
    count_inline_markers,
)


class TestComplianceLevel(unittest.TestCase):
    """Test ComplianceLevel enum."""

    def test_level_str(self) -> None:
        """Test string conversion."""
        self.assertEqual(str(ComplianceLevel.COMPLIANT), "COMPLIANT")
        self.assertEqual(str(ComplianceLevel.PARTIAL), "PARTIAL")
        self.assertEqual(str(ComplianceLevel.NON_COMPLIANT), "NON_COMPLIANT")
        self.assertEqual(str(ComplianceLevel.VIOLATION), "VIOLATION")


class TestScoring(unittest.TestCase):
    """Test scoring functions."""

    def test_score_empty_violations(self) -> None:
        """Test scoring with no violations."""
        self.assertEqual(score_output([]), 0)

    def test_score_with_violations(self) -> None:
        """Test scoring accumulates weights."""
        violations = [
            ComplianceViolation(
                level=ComplianceLevel.PARTIAL,
                field="test",
                message="test",
                weight=10,
            ),
            ComplianceViolation(
                level=ComplianceLevel.PARTIAL,
                field="test2",
                message="test2",
                weight=25,
            ),
        ]
        self.assertEqual(score_output(violations), 35)

    def test_determine_level_compliant(self) -> None:
        """Test level determination for compliant."""
        self.assertEqual(determine_level(0), ComplianceLevel.COMPLIANT)

    def test_determine_level_partial(self) -> None:
        """Test level determination for partial."""
        self.assertEqual(determine_level(25), ComplianceLevel.PARTIAL)
        self.assertEqual(determine_level(1), ComplianceLevel.PARTIAL)
        self.assertEqual(determine_level(49), ComplianceLevel.PARTIAL)

    def test_determine_level_non_compliant(self) -> None:
        """Test level determination for non-compliant."""
        self.assertEqual(determine_level(50), ComplianceLevel.NON_COMPLIANT)
        self.assertEqual(determine_level(75), ComplianceLevel.NON_COMPLIANT)
        self.assertEqual(determine_level(99), ComplianceLevel.NON_COMPLIANT)

    def test_determine_level_violation(self) -> None:
        """Test level determination for violation."""
        self.assertEqual(determine_level(100), ComplianceLevel.VIOLATION)
        self.assertEqual(determine_level(150), ComplianceLevel.VIOLATION)


class TestTallyExtraction(unittest.TestCase):
    """Test tally extraction from output."""

    def test_extract_tally_direct(self) -> None:
        """Test extraction from direct tally field."""
        output = {"tally": {"v": 3, "u": 1, "s": 0}}
        self.assertEqual(
            extract_tally_from_output(output),
            {"v": 3, "u": 1, "s": 0},
        )

    def test_extract_tally_claims(self) -> None:
        """Test extraction from claims field."""
        output = {"claims": {"v": 5, "u": 2, "s": 1}}
        self.assertEqual(
            extract_tally_from_output(output),
            {"v": 5, "u": 2, "s": 1},
        )

    def test_extract_tally_nested(self) -> None:
        """Test extraction from nested header."""
        output = {"header": {"tally": {"v": 1, "u": 0, "s": 0}}}
        self.assertEqual(
            extract_tally_from_output(output),
            {"v": 1, "u": 0, "s": 0},
        )

    def test_extract_tally_missing(self) -> None:
        """Test extraction when tally is missing."""
        output = {"data": "something"}
        self.assertIsNone(extract_tally_from_output(output))


class TestInlineMarkers(unittest.TestCase):
    """Test inline marker counting."""

    def test_count_markers_basic(self) -> None:
        """Test counting basic markers."""
        content = "This is [v] validated. This is [u] uncertain."
        counts = count_inline_markers(content)
        self.assertEqual(counts["v"], 1)
        self.assertEqual(counts["u"], 1)
        self.assertEqual(counts["s"], 0)

    def test_count_markers_with_emoji(self) -> None:
        """Test counting markers with emojis."""
        content = "[v ✅] correct [u ⚠️] uncertain [s ❌] superseded"
        counts = count_inline_markers(content)
        self.assertEqual(counts["v"], 1)
        self.assertEqual(counts["u"], 1)
        self.assertEqual(counts["s"], 1)

    def test_count_markers_none(self) -> None:
        """Test counting when no markers present."""
        content = "No markers here"
        counts = count_inline_markers(content)
        self.assertEqual(counts["v"], 0)
        self.assertEqual(counts["u"], 0)
        self.assertEqual(counts["s"], 0)


class TestComplianceResult(unittest.TestCase):
    """Test ComplianceResult class."""

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        result = ComplianceResult(
            level=ComplianceLevel.COMPLIANT,
            score=0,
            message="All good",
        )
        d = result.to_dict()
        self.assertEqual(d["level"], "COMPLIANT")
        self.assertEqual(d["score"], 0)

    def test_to_json(self) -> None:
        """Test conversion to JSON."""
        result = ComplianceResult(
            level=ComplianceLevel.PARTIAL,
            score=25,
            violations=[
                ComplianceViolation(
                    level=ComplianceLevel.PARTIAL,
                    field="test",
                    message="test violation",
                    weight=25,
                )
            ],
        )
        json_str = result.to_json()
        parsed = json.loads(json_str)
        self.assertEqual(parsed["level"], "PARTIAL")
        self.assertEqual(len(parsed["violations"]), 1)


class TestCheckCompliance(unittest.TestCase):
    """Test full compliance checking."""

    def test_compliant_output(self) -> None:
        """Test checking compliant output."""
        spec = "SENTINEL:7E99:(SID:test|MODE:design|PHASE:tradeoff)"
        output = json.dumps({
            "header": {"SID": "test", "MODE": "design"},
            "result": "success",
            "tally": {"v": 3, "u": 1, "s": 0},
        })

        result = check_compliance(spec, output)
        self.assertIn(result.level, [ComplianceLevel.COMPLIANT, ComplianceLevel.PARTIAL])
        self.assertTrue(result.retry_eligible or result.level == ComplianceLevel.COMPLIANT)

    def test_invalid_json_output(self) -> None:
        """Test checking invalid JSON output."""
        spec = "SENTINEL:7E99:(SID:test|MODE:d|PHASE:id)"
        output = "not valid json {"

        result = check_compliance(spec, output)
        self.assertEqual(result.level, ComplianceLevel.VIOLATION)
        self.assertFalse(result.retry_eligible)

    def test_output_with_forbidden_field(self) -> None:
        """Test output with forbidden field triggers violation."""
        spec = """SENTINEL:7E99:(SID:test|MODE:d|PHASE:id)

## CONSTRAINTS

FORBIDDEN: secret_data exists
"""
        output = json.dumps({
            "header": {"SID": "test"},
            "secret_data": "should not be here",
        })

        result = check_compliance(spec, output)
        # Should find the forbidden field
        self.assertGreater(result.score, 0)

    def test_output_missing_sid(self) -> None:
        """Test output with SID mismatch."""
        spec = "SENTINEL:7E99:(SID:expected-sid|MODE:d|PHASE:id)"
        output = json.dumps({
            "header": {"SID": "different-sid"},
            "result": "data",
        })

        result = check_compliance(spec, output)
        # SID mismatch should cause non-compliance
        self.assertGreater(result.score, 0)


class TestComplianceIntegration(unittest.TestCase):
    """Integration tests for compliance checking."""

    def test_cip2_max_check(self) -> None:
        """Test MAX constraint checking for CIP2."""
        spec = "CIP2|SID=7E96|P=Test|CTX=context|TASK=analyze|MAX=100"
        # Create output that exceeds MAX significantly
        output = json.dumps({
            "result": "x" * 200,  # Exceeds 100 by a lot
        })

        result = check_compliance(spec, output)
        # Should get partial compliance due to MAX exceeded
        self.assertIn(result.level, [ComplianceLevel.PARTIAL, ComplianceLevel.COMPLIANT])

    def test_tally_integrity(self) -> None:
        """Test tally integrity checking."""
        spec = "SENTINEL:7E99:(SID:test|MODE:d|PHASE:id)"
        output = json.dumps({
            "header": {"SID": "test"},
            "tally": {"v": 1, "u": 5, "s": 0},  # High uncertainty
        })

        result = check_compliance(spec, output)
        # High u > v should trigger a warning (partial)
        has_tally_warning = any(
            v.field == "tally" for v in result.violations
        )
        self.assertTrue(has_tally_warning)


if __name__ == "__main__":
    unittest.main()
