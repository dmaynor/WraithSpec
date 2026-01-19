# SPDX-License-Identifier: MIT
"""
WraithSpec Reference Validator

A Python package for parsing and validating WraithSpec documents.
Provides compliance scoring against the WraithSpec specification.

Usage:
    from tools.validator import parse_document, validate_document, check_compliance

    # Parse a document
    doc = parse_document(content)

    # Validate structure
    result = validate_document(content)

    # Check output compliance
    level = check_compliance(spec_content, output_content)
"""

from .parser import (
    parse_document,
    parse_header,
    parse_sentinel_full,
    parse_sentinel_compact,
    parse_ci1,
    parse_cip2,
    ParseError,
    Document,
    Header,
)

from .validator import (
    validate_document,
    validate_header,
    validate_fields,
    ValidationResult,
    ValidationError,
)

from .compliance import (
    check_compliance,
    score_output,
    ComplianceLevel,
    ComplianceResult,
)

__version__ = "0.1.0"
__all__ = [
    # Parser exports
    "parse_document",
    "parse_header",
    "parse_sentinel_full",
    "parse_sentinel_compact",
    "parse_ci1",
    "parse_cip2",
    "ParseError",
    "Document",
    "Header",
    # Validator exports
    "validate_document",
    "validate_header",
    "validate_fields",
    "ValidationResult",
    "ValidationError",
    # Compliance exports
    "check_compliance",
    "score_output",
    "ComplianceLevel",
    "ComplianceResult",
    # Version
    "__version__",
]
