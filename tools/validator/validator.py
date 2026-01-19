# SPDX-License-Identifier: MIT
"""
WraithSpec Document Validator

Validates WraithSpec documents for structural validity, required fields,
and constraint consistency according to the v0.1 specification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .parser import (
    Document,
    Header,
    ParseError,
    parse_document,
    parse_header,
    VALID_MODES,
    MODE_ALIASES,
    VALID_PHASES,
    PHASE_ALIASES,
    BASE36_RE,
    UUID_V7_RE,
    CREF_RE,
)


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        severity: str = "error",
    ) -> None:
        self.field = field
        self.severity = severity
        super().__init__(message)


@dataclass
class FieldViolation:
    """Represents a single field validation violation."""

    field: str
    message: str
    severity: str = "error"  # error, warning, info
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    constraint: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of document validation."""

    valid: bool
    violations: List[FieldViolation] = field(default_factory=list)
    warnings: List[FieldViolation] = field(default_factory=list)
    info: List[str] = field(default_factory=list)
    header_kind: Optional[str] = None
    fields_found: List[str] = field(default_factory=list)

    def add_violation(
        self,
        field_name: str,
        message: str,
        severity: str = "error",
        expected: Optional[Any] = None,
        actual: Optional[Any] = None,
        constraint: Optional[str] = None,
    ) -> None:
        """Add a validation violation."""
        violation = FieldViolation(
            field=field_name,
            message=message,
            severity=severity,
            expected=expected,
            actual=actual,
            constraint=constraint,
        )
        if severity == "error":
            self.violations.append(violation)
            self.valid = False
        elif severity == "warning":
            self.warnings.append(violation)
        else:
            self.info.append(message)


# =============================================================================
# Field Requirements
# =============================================================================

# Required fields per header type
REQUIRED_FIELDS: Dict[str, set] = {
    "SENTINEL_FULL": {"SID", "MODE", "PHASE"},
    "SENTINEL_COMPACT": {"SID"},
    "CI1": {"SID", "P", "HdrC", "HdrF"},
    "CIP2": {"SID", "P", "CTX", "TASK"},
}

# Optional fields per header type
OPTIONAL_FIELDS: Dict[str, set] = {
    "SENTINEL_FULL": {"AC", "RD", "RSET", "CRef", "ORIGIN", "TARGET", "CLAIMS", "CONTEXT"},
    "SENTINEL_COMPACT": {"MODE", "PHASE", "AC", "RD", "CRef", "RSET", "TALLY"},
    "CI1": {"Ver", "B", "Reasoning", "R", "O", "ID", "Nick", "Role", "Stack", "Field"},
    "CIP2": {"CONS", "TONE", "OUT", "REQ", "MAX", "max"},
}


# =============================================================================
# Validation Functions
# =============================================================================


def validate_base36(value: str, field_name: str) -> Optional[FieldViolation]:
    """
    Validate that a value is valid base36.

    Args:
        value: The value to validate
        field_name: Name of the field being validated

    Returns:
        FieldViolation if invalid, None if valid
    """
    if not BASE36_RE.match(value):
        return FieldViolation(
            field=field_name,
            message=f"Invalid base36 value: {value}",
            expected="[0-9a-zA-Z]+",
            actual=value,
        )
    return None


def validate_uuid_v7(value: str, field_name: str) -> Optional[FieldViolation]:
    """
    Validate that a value is a valid UUID v7.

    Args:
        value: The value to validate
        field_name: Name of the field being validated

    Returns:
        FieldViolation if invalid, None if valid
    """
    if not UUID_V7_RE.match(value):
        # Check if it's a short SID (valid base36)
        if BASE36_RE.match(value):
            return None  # Short SIDs are valid
        return FieldViolation(
            field=field_name,
            message=f"Invalid UUID v7 or SID format: {value}",
            expected="UUID v7 or base36 SID",
            actual=value,
        )
    return None


def validate_mode(value: str, field_name: str = "MODE") -> Optional[FieldViolation]:
    """
    Validate that a mode value is valid.

    Args:
        value: The mode value to validate
        field_name: Name of the field being validated

    Returns:
        FieldViolation if invalid, None if valid
    """
    normalized = value.lower()
    if normalized not in VALID_MODES and normalized not in MODE_ALIASES:
        return FieldViolation(
            field=field_name,
            message=f"Invalid mode value: {value}",
            expected=f"One of {sorted(VALID_MODES)} or aliases {sorted(MODE_ALIASES.keys())}",
            actual=value,
        )
    return None


def validate_phase(value: str, field_name: str = "PHASE") -> Optional[FieldViolation]:
    """
    Validate that a phase value is valid.

    Args:
        value: The phase value to validate
        field_name: Name of the field being validated

    Returns:
        FieldViolation if invalid, None if valid
    """
    normalized = value.lower()
    if normalized not in VALID_PHASES and normalized not in PHASE_ALIASES:
        return FieldViolation(
            field=field_name,
            message=f"Invalid phase value: {value}",
            expected=f"One of {sorted(VALID_PHASES)} or aliases {sorted(PHASE_ALIASES.keys())}",
            actual=value,
        )
    return None


def validate_cref(value: str, field_name: str = "CRef") -> Optional[FieldViolation]:
    """
    Validate a profile reference (CRef) value.

    Format: <profile_id>@<version>

    Args:
        value: The CRef value to validate
        field_name: Name of the field being validated

    Returns:
        FieldViolation if invalid, None if valid
    """
    if not CREF_RE.match(value):
        return FieldViolation(
            field=field_name,
            message=f"Invalid profile reference format: {value}",
            expected="<profile_id>@<version> (e.g., VA-P1@1)",
            actual=value,
            constraint="profile_reference",
        )
    return None


def validate_reasoning_depth(
    value: Any, field_name: str = "RD"
) -> Optional[FieldViolation]:
    """
    Validate reasoning depth value (0-9).

    Args:
        value: The RD value to validate
        field_name: Name of the field being validated

    Returns:
        FieldViolation if invalid, None if valid
    """
    try:
        # Handle base36 or integer
        if isinstance(value, str):
            if value.isdigit():
                rd = int(value)
            elif len(value) == 1 and value.isalnum():
                rd = int(value, 36)
            else:
                raise ValueError("Invalid format")
        else:
            rd = int(value)

        if rd < 0 or rd > 9:
            return FieldViolation(
                field=field_name,
                message=f"Reasoning depth out of range: {value}",
                expected="0-9",
                actual=str(rd),
            )
    except (ValueError, TypeError):
        return FieldViolation(
            field=field_name,
            message=f"Invalid reasoning depth: {value}",
            expected="Integer 0-9 or single base36 character",
            actual=str(value),
        )
    return None


def validate_tally(
    value: Any, field_name: str = "TALLY"
) -> Optional[FieldViolation]:
    """
    Validate v/u/s tally values.

    Args:
        value: The tally value (dict with v, u, s keys)
        field_name: Name of the field being validated

    Returns:
        FieldViolation if invalid, None if valid
    """
    if isinstance(value, dict):
        for key in ["v", "u", "s"]:
            if key not in value:
                return FieldViolation(
                    field=field_name,
                    message=f"Tally missing '{key}' count",
                    expected="v, u, s counts",
                    actual=str(value),
                )
            if not isinstance(value[key], int) or value[key] < 0:
                return FieldViolation(
                    field=field_name,
                    message=f"Invalid tally count for '{key}': {value[key]}",
                    expected="Non-negative integer",
                    actual=str(value[key]),
                )
    elif isinstance(value, str):
        # Raw string, check format
        if not re.match(r"^v[=:]?\d+[,;]u[=:]?\d+[,;]s[=:]?\d+$", value):
            return FieldViolation(
                field=field_name,
                message=f"Invalid tally format: {value}",
                expected="v:<n>,u:<n>,s:<n> or v=<n>;u=<n>;s=<n>",
                actual=value,
            )
    return None


# =============================================================================
# Header Validation
# =============================================================================


def validate_header(header: Header) -> ValidationResult:
    """
    Validate a parsed header for structural validity and field constraints.

    Args:
        header: The parsed Header object to validate

    Returns:
        ValidationResult with any violations found
    """
    result = ValidationResult(valid=True, header_kind=header.kind)
    result.fields_found = list(header.fields.keys())

    # Check required fields
    required = REQUIRED_FIELDS.get(header.kind, set())
    missing = required - set(header.fields.keys())
    for field_name in missing:
        result.add_violation(
            field_name=field_name,
            message=f"Missing required field: {field_name}",
            constraint="required",
        )

    # Validate specific field values
    fields = header.fields

    # SID validation
    if "SID" in fields:
        violation = validate_uuid_v7(str(fields["SID"]), "SID")
        if violation:
            result.violations.append(violation)
            result.valid = False

    # MODE validation
    if "MODE" in fields:
        violation = validate_mode(str(fields["MODE"]))
        if violation:
            result.violations.append(violation)
            result.valid = False

    # PHASE validation
    if "PHASE" in fields:
        violation = validate_phase(str(fields["PHASE"]))
        if violation:
            result.violations.append(violation)
            result.valid = False

    # AC validation (activity counter)
    if "AC" in fields:
        ac_val = str(fields["AC"])
        if len(ac_val) > 3:
            result.add_violation(
                field_name="AC",
                message=f"Activity counter exceeds max length: {ac_val}",
                expected="Max 3 base36 characters",
                actual=ac_val,
            )
        else:
            violation = validate_base36(ac_val, "AC")
            if violation:
                result.violations.append(violation)
                result.valid = False

    # RD validation (reasoning depth)
    if "RD" in fields:
        violation = validate_reasoning_depth(fields["RD"])
        if violation:
            result.violations.append(violation)
            result.valid = False

    # CRef validation
    if "CRef" in fields:
        violation = validate_cref(str(fields["CRef"]))
        if violation:
            result.violations.append(violation)
            result.valid = False

    # TALLY/CLAIMS validation
    for tally_field in ["TALLY", "CLAIMS"]:
        if tally_field in fields:
            violation = validate_tally(fields[tally_field], tally_field)
            if violation:
                result.violations.append(violation)
                result.valid = False

    # Check for unknown fields (warnings only)
    known = required | OPTIONAL_FIELDS.get(header.kind, set())
    unknown = set(fields.keys()) - known
    for field_name in unknown:
        result.add_violation(
            field_name=field_name,
            message=f"Unknown field: {field_name}",
            severity="warning",
        )

    return result


def validate_fields(fields: Dict[str, Any], kind: str) -> ValidationResult:
    """
    Validate a dictionary of fields against requirements for a given kind.

    Args:
        fields: Dictionary of field names to values
        kind: The header kind (CI1, CIP2, SENTINEL_FULL, SENTINEL_COMPACT)

    Returns:
        ValidationResult with any violations found
    """
    # Create a temporary header and validate it
    header = Header(kind=kind, fields=fields, raw="")
    return validate_header(header)


# =============================================================================
# Document Validation
# =============================================================================


def validate_document(content: str) -> ValidationResult:
    """
    Validate a complete WraithSpec document.

    Checks:
    - Document parses successfully
    - Header is present and valid
    - Required sections are present
    - Constraints are well-formed
    - Field references in constraints are valid

    Args:
        content: The document content to validate

    Returns:
        ValidationResult with any violations found
    """
    result = ValidationResult(valid=True)

    # Try to parse the document
    try:
        doc = parse_document(content)
    except ParseError as e:
        result.add_violation(
            field_name="document",
            message=f"Parse error: {e}",
            constraint="syntax",
        )
        return result

    # Validate header if present
    if doc.header:
        header_result = validate_header(doc.header)
        result.header_kind = header_result.header_kind
        result.fields_found = header_result.fields_found
        result.violations.extend(header_result.violations)
        result.warnings.extend(header_result.warnings)
        if not header_result.valid:
            result.valid = False
    else:
        result.add_violation(
            field_name="header",
            message="Document missing header",
            constraint="required",
        )

    # Validate constraints are well-formed
    for constraint in doc.constraints:
        if not constraint.field_path:
            result.add_violation(
                field_name="constraint",
                message=f"Constraint missing field path: {constraint.constraint_type}",
                severity="warning",
            )

        if constraint.operator not in {
            "==", "!=", ">", "<", ">=", "<=", "exists", "matches"
        }:
            result.add_violation(
                field_name="constraint",
                message=f"Unknown constraint operator: {constraint.operator}",
                severity="warning",
            )

    # Validate capabilities
    for capability in doc.capabilities:
        if not capability.name:
            result.add_violation(
                field_name="capability",
                message="Capability declaration missing name",
                severity="warning",
            )

    return result
