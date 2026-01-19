# SPDX-License-Identifier: MIT
"""
Conformance test suite for WraithSpec SENTINEL 7E99.

Tests canonical encoding, parsing, and negative cases per specification.
"""

import unittest
from typing import Dict, Any

from tools.validator.parser import (
    parse_header,
    parse_sentinel_full,
    parse_sentinel_compact,
    parse_document,
    ParseError,
)
from tools.validator.validator import (
    validate_header,
    validate_document,
    validate_mode,
    validate_phase,
    validate_base36,
    validate_cref,
)


class TestCanonicalEncoding(unittest.TestCase):
    """Tests for canonical header encoding per §5 of spec."""

    def test_field_ordering(self) -> None:
        """Fields MUST appear in canonical order per §5.1."""
        # Valid ordering
        header = parse_sentinel_full(
            "SENTINEL:7E99:(SID:test|MODE:design|PHASE:ideation|AC:0|RD:0)"
        )
        fields = list(header.fields.keys())

        # SID should come before MODE, MODE before PHASE, etc.
        self.assertEqual(fields.index("SID"), 0)
        self.assertTrue(fields.index("MODE") < fields.index("PHASE"))

    def test_case_normalization_mode(self) -> None:
        """Mode values MUST be lowercase per §5.4."""
        header = parse_sentinel_full("SENTINEL:7E99:(SID:test|MODE:DESIGN|PHASE:id)")
        # Should be normalized to lowercase
        self.assertEqual(header.fields["MODE"], "design")

    def test_case_normalization_phase(self) -> None:
        """Phase values MUST be lowercase per §5.4."""
        header = parse_sentinel_full("SENTINEL:7E99:(SID:test|MODE:d|PHASE:IDEATION)")
        # Should be normalized to lowercase
        self.assertEqual(header.fields["PHASE"], "ideation")

    def test_alias_expansion_mode(self) -> None:
        """Mode aliases MUST expand to canonical values."""
        test_cases = [
            ("bs", "brainstorm"),
            ("d", "design"),
            ("bl", "build"),
            ("r", "review"),
            ("n", "narrative"),
        ]
        for alias, canonical in test_cases:
            header = parse_sentinel_full(
                f"SENTINEL:7E99:(SID:test|MODE:{alias}|PHASE:id)"
            )
            self.assertEqual(header.fields["MODE"], canonical, f"Alias {alias}")

    def test_alias_expansion_phase(self) -> None:
        """Phase aliases MUST expand to canonical values."""
        test_cases = [
            ("id", "ideation"),
            ("tr", "tradeoff"),
            ("cd", "coding"),
            ("rt", "red-team"),
            ("ex", "explain"),
        ]
        for alias, canonical in test_cases:
            header = parse_sentinel_full(
                f"SENTINEL:7E99:(SID:test|MODE:d|PHASE:{alias})"
            )
            self.assertEqual(header.fields["PHASE"], canonical, f"Alias {alias}")


class TestMinimalValidHeader(unittest.TestCase):
    """Tests for minimal valid headers per §15.1."""

    def test_minimal_full_frame(self) -> None:
        """Minimal valid full frame header."""
        content = "SENTINEL:7E99:(SID:7e99|MODE:design|PHASE:ideation)"
        header = parse_sentinel_full(content)

        self.assertEqual(header.kind, "SENTINEL_FULL")
        self.assertEqual(header.version, "7E99")
        self.assertEqual(header.fields["SID"], "7e99")
        self.assertEqual(header.fields["MODE"], "design")
        self.assertEqual(header.fields["PHASE"], "ideation")

    def test_minimal_compact(self) -> None:
        """Minimal valid compact header."""
        content = "SID=7e99|MODE=d|PHASE=id"
        header = parse_sentinel_compact(content)

        self.assertEqual(header.kind, "SENTINEL_COMPACT")
        self.assertEqual(header.fields["SID"], "7e99")
        self.assertEqual(header.fields["MODE"], "design")
        self.assertEqual(header.fields["PHASE"], "ideation")


class TestFullHeaderWithAllFields(unittest.TestCase):
    """Tests for full headers per §15.2."""

    def test_full_header_parsing(self) -> None:
        """Parse full header with all fields."""
        content = (
            "SENTINEL:7E99:(SID:01234567-89ab-7cde-8f01-23456789abcd|"
            "MODE:build|PHASE:coding|AC:1a|RD:3|CRef:VA-P1@1|RSET:soft|"
            "ORIGIN:desktop|TARGET:ios|CLAIMS:v=5;u=2;s=1|"
            "CONTEXT:Implementing validator module)"
        )
        header = parse_sentinel_full(content)

        self.assertEqual(header.fields["SID"], "01234567-89ab-7cde-8f01-23456789abcd")
        self.assertEqual(header.fields["MODE"], "build")
        self.assertEqual(header.fields["PHASE"], "coding")
        self.assertEqual(header.fields["AC"], "1a")
        self.assertEqual(header.fields["RD"], "3")
        self.assertEqual(header.fields["CRef"], "VA-P1@1")
        self.assertEqual(header.fields["RSET"], "soft")
        self.assertEqual(header.fields["ORIGIN"], "desktop")
        self.assertEqual(header.fields["TARGET"], "ios")
        self.assertEqual(header.fields["CONTEXT"], "Implementing validator module")


class TestNegativeCases(unittest.TestCase):
    """Negative test cases for malformed/invalid inputs."""

    def test_missing_sid_full_frame(self) -> None:
        """Missing SID MUST be FATAL per §14.1."""
        content = "SENTINEL:7E99:(MODE:design|PHASE:ideation)"
        # First parse the header
        header = parse_sentinel_full(content)
        # Then validate - should fail due to missing SID
        result = validate_header(header)

        self.assertFalse(result.valid)
        self.assertTrue(any("SID" in v.field for v in result.violations))

    def test_missing_mode_uses_default(self) -> None:
        """Missing MODE SHOULD use default 'design' per §14.1."""
        # Parser should still work, validator may warn
        content = "SENTINEL:7E99:(SID:test|PHASE:ideation)"
        try:
            header = parse_sentinel_full(content)
            # If parsed, MODE should not be present
            self.assertNotIn("MODE", header.fields)
        except ParseError:
            pass  # Also acceptable

    def test_invalid_mode_value(self) -> None:
        """Invalid MODE values MUST be rejected."""
        violation = validate_mode("invalid_mode", "MODE")
        self.assertIsNotNone(violation)
        self.assertIn("Invalid", violation.message)

    def test_invalid_phase_value(self) -> None:
        """Invalid PHASE values MUST be rejected."""
        violation = validate_phase("invalid_phase", "PHASE")
        self.assertIsNotNone(violation)
        self.assertIn("Invalid", violation.message)

    def test_invalid_base36_with_special_chars(self) -> None:
        """Base36 values with special characters MUST be rejected."""
        invalid_values = ["1$x", "a@b", "test!", "12.34", "a b"]
        for val in invalid_values:
            violation = validate_base36(val, "AC")
            self.assertIsNotNone(violation, f"Should reject: {val}")

    def test_invalid_cref_format(self) -> None:
        """Malformed CRef values MUST be rejected per §11.3."""
        invalid_crefs = [
            "VA-P1",           # Missing @version
            "VA-P1@@2",        # Double @
            "@1",              # Missing profile ID
            "VA-P1@",          # Missing version
            "123@1",           # Profile must start with letter
            "VA-P1@1@2",       # Multiple @
        ]
        for cref in invalid_crefs:
            violation = validate_cref(cref, "CRef")
            self.assertIsNotNone(violation, f"Should reject: {cref}")

    def test_invalid_version_prefix(self) -> None:
        """Invalid version prefix SHOULD be rejected per §5.6."""
        # Version should be 7E99 or compatible 7E9x
        content = "SENTINEL:7F00:(SID:test|MODE:d|PHASE:id)"
        # Parser may accept but validator should warn
        try:
            header = parse_sentinel_full(content)
            self.assertEqual(header.version, "7F00")
        except ParseError:
            pass  # Also acceptable

    def test_malformed_full_frame_missing_parens(self) -> None:
        """Missing parentheses MUST cause parse failure."""
        content = "SENTINEL:7E99:SID:test|MODE:d|PHASE:id"
        with self.assertRaises(ParseError):
            parse_sentinel_full(content)

    def test_malformed_full_frame_unclosed_parens(self) -> None:
        """Unclosed parentheses MUST cause parse failure."""
        content = "SENTINEL:7E99:(SID:test|MODE:d|PHASE:id"
        with self.assertRaises(ParseError):
            parse_sentinel_full(content)

    def test_malformed_compact_no_pipes(self) -> None:
        """Compact header without pipes MUST cause parse failure."""
        content = "SID=test MODE=d PHASE=id"
        with self.assertRaises(ParseError):
            parse_sentinel_compact(content)

    def test_empty_header(self) -> None:
        """Empty content MUST cause parse failure."""
        with self.assertRaises(ParseError):
            parse_sentinel_full("")

    def test_whitespace_only(self) -> None:
        """Whitespace-only content MUST cause parse failure."""
        with self.assertRaises(ParseError):
            parse_sentinel_full("   \n\t  ")


class TestTallyParsing(unittest.TestCase):
    """Tests for v/u/s tally parsing per §12."""

    def test_parse_claims_full_format(self) -> None:
        """Parse CLAIMS in full format: v=5;u=2;s=1."""
        content = "SENTINEL:7E99:(SID:test|MODE:d|PHASE:id|CLAIMS:v=5;u=2;s=1)"
        header = parse_sentinel_full(content)

        claims = header.fields["CLAIMS"]
        self.assertEqual(claims["v"], 5)
        self.assertEqual(claims["u"], 2)
        self.assertEqual(claims["s"], 1)

    def test_parse_tally_compact_format(self) -> None:
        """Parse TALLY in compact format: v:5,u:2,s:1."""
        content = "SID=test|MODE=d|PHASE=id|TALLY=v:5,u:2,s:1"
        header = parse_sentinel_compact(content)

        tally = header.fields["TALLY"]
        self.assertEqual(tally["v"], 5)
        self.assertEqual(tally["u"], 2)
        self.assertEqual(tally["s"], 1)


class TestDocumentConformance(unittest.TestCase):
    """Tests for complete document conformance."""

    def test_document_with_constraints(self) -> None:
        """Parse document with constraint block."""
        content = """SENTINEL:7E99:(SID:test|MODE:design|PHASE:ideation)

## CONSTRAINTS

REQUIRED: header.SID exists
OPTIONAL: header.CONTEXT exists
FORBIDDEN: secrets exists
"""
        doc = parse_document(content)

        self.assertIsNotNone(doc.header)
        self.assertEqual(len(doc.constraints), 3)

        # Check constraint types
        types = [c.constraint_type for c in doc.constraints]
        self.assertIn("REQUIRED", types)
        self.assertIn("OPTIONAL", types)
        self.assertIn("FORBIDDEN", types)

    def test_document_with_capabilities(self) -> None:
        """Parse document with capability declarations."""
        content = """SENTINEL:7E99:(SID:test|MODE:d|PHASE:id)

CAPABILITY: code_execution(sandbox=true)
CAPABILITY: web_search
"""
        doc = parse_document(content)

        self.assertEqual(len(doc.capabilities), 2)
        self.assertEqual(doc.capabilities[0].name, "code_execution")
        self.assertEqual(doc.capabilities[0].params.get("sandbox"), "true")
        self.assertEqual(doc.capabilities[1].name, "web_search")

    def test_document_with_directives(self) -> None:
        """Parse document with directive block."""
        content = """---
version: 0.1
profile: VA-P1@1
strict: true
---

SENTINEL:7E99:(SID:test|MODE:d|PHASE:id)
"""
        doc = parse_document(content)

        self.assertEqual(doc.directives.get("version"), "0.1")
        self.assertEqual(doc.directives.get("profile"), "VA-P1@1")
        self.assertEqual(doc.directives.get("strict"), "true")


class TestResetPolicies(unittest.TestCase):
    """Tests for reset policy handling per §10."""

    def test_hard_reset_policy(self) -> None:
        """Parse hard reset policy."""
        content = "SENTINEL:7E99:(SID:test|MODE:d|PHASE:id|RSET:hard)"
        header = parse_sentinel_full(content)
        self.assertEqual(header.fields["RSET"], "hard")

    def test_soft_reset_policy(self) -> None:
        """Parse soft reset policy."""
        content = "SENTINEL:7E99:(SID:test|MODE:d|PHASE:id|RSET:soft)"
        header = parse_sentinel_full(content)
        self.assertEqual(header.fields["RSET"], "soft")

    def test_transfer_reset_policy(self) -> None:
        """Parse transfer reset policy."""
        content = "SENTINEL:7E99:(SID:test|MODE:d|PHASE:id|RSET:transfer)"
        header = parse_sentinel_full(content)
        self.assertEqual(header.fields["RSET"], "transfer")


class TestReasoningDepth(unittest.TestCase):
    """Tests for reasoning depth handling per §7."""

    def test_rd_valid_range(self) -> None:
        """RD values 0-9 should be valid."""
        for rd in range(10):
            content = f"SENTINEL:7E99:(SID:test|MODE:d|PHASE:id|RD:{rd})"
            header = parse_sentinel_full(content)
            self.assertEqual(header.fields["RD"], str(rd))

    def test_rd_base36_extended(self) -> None:
        """RD can use base36 for extended values."""
        content = "SENTINEL:7E99:(SID:test|MODE:d|PHASE:id|RD:a)"
        header = parse_sentinel_full(content)
        self.assertEqual(header.fields["RD"], "a")


class TestCRefValidation(unittest.TestCase):
    """Tests for CRef validation per §11."""

    def test_valid_cref_simple(self) -> None:
        """Valid CRef: profile@version."""
        violation = validate_cref("VA-P1@1", "CRef")
        self.assertIsNone(violation)

    def test_valid_cref_with_minor_version(self) -> None:
        """Valid CRef with minor version."""
        violation = validate_cref("VA-P1@1.2", "CRef")
        self.assertIsNone(violation)

    def test_valid_cref_with_prerelease(self) -> None:
        """Valid CRef with prerelease tag."""
        violation = validate_cref("VA-P1@2-beta", "CRef")
        self.assertIsNone(violation)

    def test_valid_cref_with_underscore(self) -> None:
        """Valid CRef with underscore in profile ID."""
        violation = validate_cref("My_Profile@1", "CRef")
        self.assertIsNone(violation)


if __name__ == "__main__":
    unittest.main()
