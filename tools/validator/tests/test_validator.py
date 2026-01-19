# SPDX-License-Identifier: MIT
"""Tests for the WraithSpec validator module."""

import unittest

from tools.validator.parser import Header
from tools.validator.validator import (
    validate_document,
    validate_header,
    validate_fields,
    validate_base36,
    validate_mode,
    validate_phase,
    validate_cref,
    validate_reasoning_depth,
    validate_tally,
    ValidationResult,
)


class TestFieldValidators(unittest.TestCase):
    """Test individual field validators."""

    def test_validate_base36_valid(self) -> None:
        """Test valid base36 values."""
        self.assertIsNone(validate_base36("abc", "AC"))
        self.assertIsNone(validate_base36("123", "AC"))
        self.assertIsNone(validate_base36("7E99", "SID"))
        self.assertIsNone(validate_base36("zzz", "AC"))

    def test_validate_base36_invalid(self) -> None:
        """Test invalid base36 values."""
        violation = validate_base36("$$$", "AC")
        self.assertIsNotNone(violation)
        self.assertEqual(violation.field, "AC")

    def test_validate_mode_valid(self) -> None:
        """Test valid mode values."""
        for mode in ["brainstorm", "design", "build", "review", "narrative"]:
            self.assertIsNone(validate_mode(mode))

        for alias in ["bs", "d", "bl", "r", "n"]:
            self.assertIsNone(validate_mode(alias))

    def test_validate_mode_invalid(self) -> None:
        """Test invalid mode values."""
        violation = validate_mode("thinking")
        self.assertIsNotNone(violation)
        self.assertIn("thinking", violation.message)

    def test_validate_phase_valid(self) -> None:
        """Test valid phase values."""
        for phase in ["ideation", "tradeoff", "coding", "red-team", "explain"]:
            self.assertIsNone(validate_phase(phase))

        for alias in ["id", "tr", "cd", "rt", "ex"]:
            self.assertIsNone(validate_phase(alias))

    def test_validate_phase_invalid(self) -> None:
        """Test invalid phase values."""
        violation = validate_phase("unknown")
        self.assertIsNotNone(violation)

    def test_validate_cref_valid(self) -> None:
        """Test valid CRef values."""
        self.assertIsNone(validate_cref("VA-P1@1"))
        self.assertIsNone(validate_cref("Profile@2.1"))
        self.assertIsNone(validate_cref("Test-Profile@1.0.0-beta"))

    def test_validate_cref_invalid(self) -> None:
        """Test invalid CRef values."""
        # Missing version
        violation = validate_cref("VA-P1")
        self.assertIsNotNone(violation)

        # Double @
        violation = validate_cref("VA-P1@@2")
        self.assertIsNotNone(violation)

        # Invalid characters
        violation = validate_cref("VA P1@1")
        self.assertIsNotNone(violation)

    def test_validate_reasoning_depth_valid(self) -> None:
        """Test valid reasoning depth values."""
        for rd in range(10):
            self.assertIsNone(validate_reasoning_depth(rd))
            self.assertIsNone(validate_reasoning_depth(str(rd)))

    def test_validate_reasoning_depth_invalid(self) -> None:
        """Test invalid reasoning depth values."""
        violation = validate_reasoning_depth(-1)
        self.assertIsNotNone(violation)

        violation = validate_reasoning_depth(10)
        self.assertIsNotNone(violation)

    def test_validate_tally_valid(self) -> None:
        """Test valid tally values."""
        tally = {"v": 3, "u": 1, "s": 0}
        self.assertIsNone(validate_tally(tally))

    def test_validate_tally_invalid(self) -> None:
        """Test invalid tally values."""
        # Missing key
        tally = {"v": 3, "u": 1}
        violation = validate_tally(tally)
        self.assertIsNotNone(violation)

        # Negative count
        tally = {"v": -1, "u": 1, "s": 0}
        violation = validate_tally(tally)
        self.assertIsNotNone(violation)


class TestHeaderValidation(unittest.TestCase):
    """Test header validation."""

    def test_validate_sentinel_full_valid(self) -> None:
        """Test validation of valid SENTINEL full frame."""
        header = Header(
            kind="SENTINEL_FULL",
            version="7E99",
            fields={
                "SID": "test123",
                "MODE": "design",
                "PHASE": "tradeoff",
                "AC": "f",
                "RD": "3",
            },
        )
        result = validate_header(header)
        self.assertTrue(result.valid)
        self.assertEqual(len(result.violations), 0)

    def test_validate_sentinel_full_missing_required(self) -> None:
        """Test validation catches missing required fields."""
        header = Header(
            kind="SENTINEL_FULL",
            version="7E99",
            fields={"SID": "test"},  # Missing MODE, PHASE
        )
        result = validate_header(header)
        self.assertFalse(result.valid)
        self.assertTrue(len(result.violations) >= 2)

    def test_validate_ci1_valid(self) -> None:
        """Test validation of valid CI1 header."""
        header = Header(
            kind="CI1",
            fields={
                "SID": "7E96",
                "P": "Test-Profile",
                "HdrC": "compact",
                "HdrF": {"Stack": "VA"},
            },
        )
        result = validate_header(header)
        self.assertTrue(result.valid)

    def test_validate_ci1_missing_required(self) -> None:
        """Test validation catches missing CI1 required fields."""
        header = Header(
            kind="CI1",
            fields={"SID": "7E96", "P": "Test"},  # Missing HdrC, HdrF
        )
        result = validate_header(header)
        self.assertFalse(result.valid)

    def test_validate_cip2_valid(self) -> None:
        """Test validation of valid CIP2 header."""
        header = Header(
            kind="CIP2",
            fields={
                "SID": "7E96",
                "P": "Test",
                "CTX": "context",
                "TASK": "do_task",
            },
        )
        result = validate_header(header)
        self.assertTrue(result.valid)

    def test_validate_invalid_mode(self) -> None:
        """Test validation catches invalid mode."""
        header = Header(
            kind="SENTINEL_FULL",
            fields={
                "SID": "test",
                "MODE": "invalid_mode",
                "PHASE": "ideation",
            },
        )
        result = validate_header(header)
        self.assertFalse(result.valid)

    def test_validate_invalid_cref(self) -> None:
        """Test validation catches invalid CRef."""
        header = Header(
            kind="SENTINEL_COMPACT",
            fields={
                "SID": "test",
                "CRef": "invalid@@ref",
            },
        )
        result = validate_header(header)
        self.assertFalse(result.valid)

    def test_validate_unknown_fields_warning(self) -> None:
        """Test that unknown fields generate warnings."""
        header = Header(
            kind="SENTINEL_COMPACT",
            fields={
                "SID": "test",
                "UNKNOWN_FIELD": "value",
            },
        )
        result = validate_header(header)
        self.assertTrue(result.valid)  # Unknown fields are warnings, not errors
        self.assertTrue(len(result.warnings) > 0)


class TestDocumentValidation(unittest.TestCase):
    """Test full document validation."""

    def test_validate_valid_document(self) -> None:
        """Test validation of valid document."""
        content = "SENTINEL:7E99:(SID:test|MODE:design|PHASE:tradeoff)"
        result = validate_document(content)
        self.assertTrue(result.valid)

    def test_validate_missing_header(self) -> None:
        """Test validation catches missing header."""
        content = """## Overview

Just some content without a header.
"""
        result = validate_document(content)
        self.assertFalse(result.valid)

    def test_validate_invalid_syntax(self) -> None:
        """Test validation catches syntax errors."""
        content = "CI1|SID=123"  # Missing required fields
        result = validate_document(content)
        self.assertFalse(result.valid)


if __name__ == "__main__":
    unittest.main()
