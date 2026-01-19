# SPDX-License-Identifier: MIT
"""Tests for the WraithSpec CLI module."""

import json
import os
import tempfile
import unittest

from tools.validator.cli import (
    main,
    cmd_validate,
    cmd_check_output,
    format_validation_result,
    format_compliance_result,
)
from tools.validator.validator import ValidationResult, FieldViolation
from tools.validator.compliance import ComplianceResult, ComplianceLevel


class TestFormatters(unittest.TestCase):
    """Test result formatters."""

    def test_format_valid_result(self) -> None:
        """Test formatting a valid result."""
        result = ValidationResult(
            valid=True,
            header_kind="CI1",
            fields_found=["SID", "P", "HdrC", "HdrF"],
        )
        output = format_validation_result(result)
        self.assertIn("VALID", output)
        self.assertIn("CI1", output)

    def test_format_invalid_result(self) -> None:
        """Test formatting an invalid result."""
        result = ValidationResult(valid=False, header_kind="CI1")
        result.violations.append(
            FieldViolation(
                field="SID",
                message="Missing required field",
                expected="present",
            )
        )
        output = format_validation_result(result)
        self.assertIn("INVALID", output)
        self.assertIn("SID", output)

    def test_format_compliance_result(self) -> None:
        """Test formatting compliance result."""
        result = ComplianceResult(
            level=ComplianceLevel.COMPLIANT,
            score=0,
            message="All good",
        )
        output = format_compliance_result(result)
        self.assertIn("COMPLIANT", output)
        self.assertIn("0", output)


class TestCLI(unittest.TestCase):
    """Test CLI commands."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def _write_temp_file(self, name: str, content: str) -> str:
        """Write a temporary file and return its path."""
        path = os.path.join(self.temp_dir, name)
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_validate_valid_file(self) -> None:
        """Test validating a valid file."""
        content = "SENTINEL:7E99:(SID:test|MODE:design|PHASE:tradeoff)"
        path = self._write_temp_file("valid.ws", content)

        exit_code = main(["validate", path])
        self.assertEqual(exit_code, 0)

    def test_validate_invalid_file(self) -> None:
        """Test validating an invalid file."""
        content = "CI1|SID=123"  # Missing required fields
        path = self._write_temp_file("invalid.ws", content)

        exit_code = main(["validate", path])
        self.assertEqual(exit_code, 1)

    def test_validate_missing_file(self) -> None:
        """Test validating a non-existent file."""
        exit_code = main(["validate", "/nonexistent/file.ws"])
        self.assertEqual(exit_code, 1)

    def test_validate_json_output(self) -> None:
        """Test validate with JSON output."""
        content = "SENTINEL:7E99:(SID:test|MODE:design|PHASE:tradeoff)"
        path = self._write_temp_file("valid.ws", content)

        # Capture output by checking return code
        exit_code = main(["validate", path, "--json"])
        self.assertEqual(exit_code, 0)

    def test_check_output_compliant(self) -> None:
        """Test checking compliant output."""
        spec_content = "SENTINEL:7E99:(SID:test|MODE:d|PHASE:id)"
        output_content = json.dumps({
            "header": {"SID": "test"},
            "result": "data",
        })

        spec_path = self._write_temp_file("spec.ws", spec_content)
        output_path = self._write_temp_file("output.json", output_content)

        exit_code = main(["check-output", spec_path, output_path])
        self.assertEqual(exit_code, 0)

    def test_check_output_missing_spec(self) -> None:
        """Test check-output with missing spec file."""
        output_path = self._write_temp_file("output.json", "{}")

        exit_code = main(["check-output", "/nonexistent/spec.ws", output_path])
        self.assertEqual(exit_code, 1)

    def test_check_output_missing_output(self) -> None:
        """Test check-output with missing output file."""
        spec_path = self._write_temp_file("spec.ws", "SENTINEL:7E99:(SID:x|MODE:d|PHASE:id)")

        exit_code = main(["check-output", spec_path, "/nonexistent/output.json"])
        self.assertEqual(exit_code, 1)

    def test_parse_command(self) -> None:
        """Test parse command."""
        content = """SENTINEL:7E99:(SID:test|MODE:d|PHASE:tr)

## Overview

Test content.

CAPABILITY: test_cap(enabled=true)
"""
        path = self._write_temp_file("doc.ws", content)

        exit_code = main(["parse", path])
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
