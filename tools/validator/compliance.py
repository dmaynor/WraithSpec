# SPDX-License-Identifier: MIT
"""
WraithSpec Compliance Checker

Scores output against a WraithSpec specification and returns
a compliance level according to the defined taxonomy.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .parser import Document, Header, ParseError, parse_document, parse_header
from .validator import (
    ValidationResult,
    FieldViolation,
    validate_header,
    validate_document,
)


class ComplianceLevel(Enum):
    """
    Compliance level taxonomy.

    Levels are ordered from most compliant to most severe violation.
    """

    COMPLIANT = "COMPLIANT"
    PARTIAL = "PARTIAL"
    NON_COMPLIANT = "NON_COMPLIANT"
    VIOLATION = "VIOLATION"

    def __str__(self) -> str:
        return self.value


@dataclass
class ComplianceViolation:
    """Represents a compliance violation in the output."""

    level: ComplianceLevel
    field: str
    message: str
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    weight: int = 0


@dataclass
class ComplianceResult:
    """Result of compliance checking."""

    level: ComplianceLevel
    score: int  # 0 = fully compliant, higher = worse
    violations: List[ComplianceViolation] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    retry_eligible: bool = True
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "level": str(self.level),
            "score": self.score,
            "violations": [
                {
                    "level": str(v.level),
                    "field": v.field,
                    "message": v.message,
                    "expected": v.expected,
                    "actual": v.actual,
                    "weight": v.weight,
                }
                for v in self.violations
            ],
            "details": self.details,
            "retry_eligible": self.retry_eligible,
            "message": self.message,
        }

    def to_json(self) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


# =============================================================================
# Compliance Weights
# =============================================================================

# Severity weights from compliance_levels.yaml
CONSTRAINT_WEIGHTS = {
    "REQUIRED": 50,
    "OPTIONAL": 10,
    "FORBIDDEN": 100,
    "CONDITIONAL": 25,
    "FORMAT": 15,
    "RANGE": 20,
    "REFERENCE": 30,
}

# Score ranges for compliance levels
SCORE_RANGES = {
    ComplianceLevel.COMPLIANT: (0, 0),
    ComplianceLevel.PARTIAL: (1, 49),
    ComplianceLevel.NON_COMPLIANT: (50, 99),
    ComplianceLevel.VIOLATION: (100, float("inf")),
}


# =============================================================================
# Output Parsing
# =============================================================================


def parse_json_output(content: str) -> Dict[str, Any]:
    """
    Parse JSON output content.

    Args:
        content: JSON string to parse

    Returns:
        Parsed dictionary

    Raises:
        ValueError: If content is not valid JSON
    """
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def extract_tally_from_output(output: Dict[str, Any]) -> Optional[Dict[str, int]]:
    """
    Extract v/u/s tally from output if present.

    Args:
        output: Parsed output dictionary

    Returns:
        Tally dictionary or None if not found
    """
    # Check common locations for tally
    if "tally" in output:
        return output["tally"]
    if "claims" in output:
        return output["claims"]
    if "TALLY" in output:
        return output["TALLY"]
    if "CLAIMS" in output:
        return output["CLAIMS"]

    # Check nested locations
    if "header" in output and isinstance(output["header"], dict):
        header = output["header"]
        if "tally" in header:
            return header["tally"]
        if "TALLY" in header:
            return header["TALLY"]

    return None


def count_inline_markers(content: str) -> Dict[str, int]:
    """
    Count inline [v], [u], [s] markers in content.

    Args:
        content: String content to search

    Returns:
        Dictionary with v, u, s counts
    """
    counts = {"v": 0, "u": 0, "s": 0}

    # Look for [v], [u], [s] markers
    for marker in ["v", "u", "s"]:
        pattern = rf"\[{marker}\s*(?:✅|⚠️|❌)?\]"
        counts[marker] = len(re.findall(pattern, content, re.IGNORECASE))

    return counts


# =============================================================================
# Compliance Checking
# =============================================================================


def check_required_fields(
    spec: Document, output: Dict[str, Any]
) -> List[ComplianceViolation]:
    """
    Check that required fields from spec are present in output.

    Args:
        spec: The specification document
        output: The output to check

    Returns:
        List of violations found
    """
    violations: List[ComplianceViolation] = []

    # Check header requirements
    if spec.header:
        # Extract output header if present
        output_header = output.get("header", output.get("Header", {}))

        # Check SID matches if both present
        spec_sid = spec.header.fields.get("SID")
        output_sid = output_header.get("SID", output_header.get("Sentinel"))

        if spec_sid and output_sid and str(spec_sid) != str(output_sid):
            violations.append(
                ComplianceViolation(
                    level=ComplianceLevel.NON_COMPLIANT,
                    field="SID",
                    message="Output SID does not match spec SID",
                    expected=spec_sid,
                    actual=output_sid,
                    weight=CONSTRAINT_WEIGHTS["REQUIRED"],
                )
            )

    # Check constraints from spec
    for constraint in spec.constraints:
        if constraint.constraint_type == "REQUIRED":
            field_path = constraint.field_path
            value = _get_nested_value(output, field_path)

            if value is None:
                violations.append(
                    ComplianceViolation(
                        level=ComplianceLevel.NON_COMPLIANT,
                        field=field_path,
                        message=f"Required field missing: {field_path}",
                        expected="present",
                        actual="missing",
                        weight=CONSTRAINT_WEIGHTS["REQUIRED"],
                    )
                )

        elif constraint.constraint_type == "FORBIDDEN":
            field_path = constraint.field_path
            value = _get_nested_value(output, field_path)

            if value is not None:
                violations.append(
                    ComplianceViolation(
                        level=ComplianceLevel.VIOLATION,
                        field=field_path,
                        message=f"Forbidden field present: {field_path}",
                        expected="absent",
                        actual=str(value),
                        weight=CONSTRAINT_WEIGHTS["FORBIDDEN"],
                    )
                )

    return violations


def check_format_constraints(
    spec: Document, output: Dict[str, Any]
) -> List[ComplianceViolation]:
    """
    Check format constraints on output fields.

    Args:
        spec: The specification document
        output: The output to check

    Returns:
        List of violations found
    """
    violations: List[ComplianceViolation] = []

    # Check MAX constraint if specified
    if spec.header and spec.header.kind == "CIP2":
        max_val = spec.header.fields.get("MAX")
        if max_val:
            # Estimate output length
            output_str = json.dumps(output)
            output_len = len(output_str)

            if isinstance(max_val, int):
                # Check if exceeded by more than 20% (soft limit)
                if output_len > max_val * 1.2:
                    violations.append(
                        ComplianceViolation(
                            level=ComplianceLevel.PARTIAL,
                            field="MAX",
                            message=f"Output exceeds MAX limit significantly",
                            expected=max_val,
                            actual=output_len,
                            weight=CONSTRAINT_WEIGHTS["OPTIONAL"],
                        )
                    )

    return violations


def check_tally_integrity(
    spec: Document, output: Dict[str, Any], content: str = ""
) -> List[ComplianceViolation]:
    """
    Check v/u/s tally integrity.

    Args:
        spec: The specification document
        output: The output to check
        content: Optional raw content string for marker counting

    Returns:
        List of violations found
    """
    violations: List[ComplianceViolation] = []

    # Get tally from output
    output_tally = extract_tally_from_output(output)

    if output_tally:
        # Count inline markers
        if content:
            marker_counts = count_inline_markers(content)

            # Check if counts match
            for key in ["v", "u", "s"]:
                tally_count = output_tally.get(key, 0)
                marker_count = marker_counts.get(key, 0)

                # Allow some tolerance (markers might be in nested content)
                if marker_count > 0 and abs(tally_count - marker_count) > marker_count:
                    violations.append(
                        ComplianceViolation(
                            level=ComplianceLevel.PARTIAL,
                            field="tally",
                            message=f"Tally '{key}' count may not match markers",
                            expected=marker_count,
                            actual=tally_count,
                            weight=CONSTRAINT_WEIGHTS["OPTIONAL"],
                        )
                    )

        # Check tally ratios (high uncertainty is a warning)
        v_count = output_tally.get("v", 0)
        u_count = output_tally.get("u", 0)

        if u_count > v_count and v_count > 0:
            violations.append(
                ComplianceViolation(
                    level=ComplianceLevel.PARTIAL,
                    field="tally",
                    message="Uncertainty exceeds validation count",
                    expected=f"v >= u",
                    actual=f"v={v_count}, u={u_count}",
                    weight=CONSTRAINT_WEIGHTS["OPTIONAL"],
                )
            )

    return violations


def _get_nested_value(data: Dict[str, Any], path: str) -> Any:
    """
    Get a nested value from a dictionary using dot notation.

    Args:
        data: The dictionary to search
        path: Dot-separated path (e.g., "header.SID")

    Returns:
        The value at the path, or None if not found
    """
    parts = path.split(".")
    current = data

    for part in parts:
        if isinstance(current, dict):
            # Try exact match first
            if part in current:
                current = current[part]
            # Try case-insensitive match
            elif part.lower() in {k.lower() for k in current}:
                for k in current:
                    if k.lower() == part.lower():
                        current = current[k]
                        break
            else:
                return None
        else:
            return None

    return current


def score_output(violations: List[ComplianceViolation]) -> int:
    """
    Calculate a compliance score from violations.

    Args:
        violations: List of compliance violations

    Returns:
        Numeric score (0 = compliant, higher = worse)
    """
    return sum(v.weight for v in violations)


def determine_level(score: int) -> ComplianceLevel:
    """
    Determine compliance level from score.

    Args:
        score: Numeric compliance score

    Returns:
        ComplianceLevel enum value
    """
    for level, (min_score, max_score) in SCORE_RANGES.items():
        if min_score <= score <= max_score:
            return level
    return ComplianceLevel.VIOLATION


def check_compliance(spec_content: str, output_content: str) -> ComplianceResult:
    """
    Check output compliance against a specification.

    Args:
        spec_content: The WraithSpec specification content
        output_content: The output to check (JSON string)

    Returns:
        ComplianceResult with level, score, and violations

    Raises:
        ValueError: If spec or output cannot be parsed
    """
    # Parse the specification
    try:
        spec = parse_document(spec_content)
    except ParseError as e:
        raise ValueError(f"Failed to parse specification: {e}")

    # Parse the output
    try:
        output = parse_json_output(output_content)
    except ValueError as e:
        return ComplianceResult(
            level=ComplianceLevel.VIOLATION,
            score=100,
            violations=[
                ComplianceViolation(
                    level=ComplianceLevel.VIOLATION,
                    field="output",
                    message=str(e),
                    weight=100,
                )
            ],
            retry_eligible=False,
            message=f"Output parsing failed: {e}",
        )

    # Collect all violations
    violations: List[ComplianceViolation] = []

    # Check required fields
    violations.extend(check_required_fields(spec, output))

    # Check format constraints
    violations.extend(check_format_constraints(spec, output))

    # Check tally integrity
    violations.extend(check_tally_integrity(spec, output, output_content))

    # Calculate score and determine level
    score = score_output(violations)
    level = determine_level(score)

    # Determine retry eligibility
    retry_eligible = level in {ComplianceLevel.PARTIAL, ComplianceLevel.NON_COMPLIANT}

    # Build message
    if level == ComplianceLevel.COMPLIANT:
        message = "Output fully complies with specification"
    elif level == ComplianceLevel.PARTIAL:
        message = f"Output partially compliant with {len(violations)} minor violation(s)"
    elif level == ComplianceLevel.NON_COMPLIANT:
        message = f"Output non-compliant with {len(violations)} violation(s)"
    else:
        message = f"Output violates hard constraints: {len(violations)} violation(s)"

    return ComplianceResult(
        level=level,
        score=score,
        violations=violations,
        details={
            "spec_kind": spec.header.kind if spec.header else None,
            "output_fields": list(output.keys()),
        },
        retry_eligible=retry_eligible,
        message=message,
    )
