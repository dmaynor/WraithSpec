# SPDX-License-Identifier: MIT
"""
WraithSpec Validator CLI

Command-line interface for validating WraithSpec documents and checking
output compliance against specifications.

Usage:
    python -m tools.validator.cli validate <file>
    python -m tools.validator.cli check-output <spec> <output>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from .parser import parse_document, parse_header, ParseError
from .validator import validate_document, ValidationResult
from .compliance import check_compliance, ComplianceLevel, ComplianceResult


def read_file(path: str) -> str:
    """
    Read a file and return its contents.

    Args:
        path: Path to the file

    Returns:
        File contents as string

    Raises:
        FileNotFoundError: If file does not exist
        IOError: If file cannot be read
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def format_validation_result(result: ValidationResult) -> str:
    """
    Format a validation result for display.

    Args:
        result: The validation result to format

    Returns:
        Formatted string for display
    """
    lines: List[str] = []

    if result.valid:
        lines.append("VALID")
        lines.append(f"  Header type: {result.header_kind}")
        lines.append(f"  Fields found: {', '.join(sorted(result.fields_found))}")
    else:
        lines.append("INVALID")
        lines.append(f"  Header type: {result.header_kind or 'unknown'}")
        lines.append(f"  Violations: {len(result.violations)}")

        for v in result.violations:
            lines.append(f"    - [{v.field}] {v.message}")
            if v.expected:
                lines.append(f"      Expected: {v.expected}")
            if v.actual:
                lines.append(f"      Actual: {v.actual}")

    if result.warnings:
        lines.append(f"  Warnings: {len(result.warnings)}")
        for w in result.warnings:
            lines.append(f"    - [{w.field}] {w.message}")

    return "\n".join(lines)


def format_compliance_result(result: ComplianceResult) -> str:
    """
    Format a compliance result for display.

    Args:
        result: The compliance result to format

    Returns:
        Formatted string for display
    """
    lines: List[str] = []

    lines.append(f"Level: {result.level}")
    lines.append(f"Score: {result.score}")
    lines.append(f"Message: {result.message}")
    lines.append(f"Retry eligible: {result.retry_eligible}")

    if result.violations:
        lines.append(f"Violations ({len(result.violations)}):")
        for v in result.violations:
            lines.append(f"  - [{v.level}] {v.field}: {v.message}")
            if v.expected is not None:
                lines.append(f"    Expected: {v.expected}")
            if v.actual is not None:
                lines.append(f"    Actual: {v.actual}")

    return "\n".join(lines)


def cmd_validate(args: argparse.Namespace) -> int:
    """
    Validate a WraithSpec document.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for valid, 1 for invalid)
    """
    try:
        content = read_file(args.file)
    except FileNotFoundError:
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1
    except IOError as e:
        print(f"Error: Cannot read file: {e}", file=sys.stderr)
        return 1

    result = validate_document(content)

    if args.json:
        output = {
            "valid": result.valid,
            "header_kind": result.header_kind,
            "fields_found": result.fields_found,
            "violations": [
                {
                    "field": v.field,
                    "message": v.message,
                    "severity": v.severity,
                    "expected": v.expected,
                    "actual": v.actual,
                }
                for v in result.violations
            ],
            "warnings": [
                {
                    "field": w.field,
                    "message": w.message,
                }
                for w in result.warnings
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_validation_result(result))

    return 0 if result.valid else 1


def cmd_check_output(args: argparse.Namespace) -> int:
    """
    Check output compliance against a specification.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for compliant/partial, 1 for non-compliant/violation)
    """
    try:
        spec_content = read_file(args.spec)
    except FileNotFoundError:
        print(f"Error: Spec file not found: {args.spec}", file=sys.stderr)
        return 1
    except IOError as e:
        print(f"Error: Cannot read spec file: {e}", file=sys.stderr)
        return 1

    try:
        output_content = read_file(args.output)
    except FileNotFoundError:
        print(f"Error: Output file not found: {args.output}", file=sys.stderr)
        return 1
    except IOError as e:
        print(f"Error: Cannot read output file: {e}", file=sys.stderr)
        return 1

    try:
        result = check_compliance(spec_content, output_content)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(result.to_json())
    else:
        print(format_compliance_result(result))

    # Return 0 for COMPLIANT or PARTIAL, 1 for NON_COMPLIANT or VIOLATION
    if result.level in {ComplianceLevel.COMPLIANT, ComplianceLevel.PARTIAL}:
        return 0
    return 1


def cmd_parse(args: argparse.Namespace) -> int:
    """
    Parse and display a WraithSpec document structure.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        content = read_file(args.file)
    except FileNotFoundError:
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1
    except IOError as e:
        print(f"Error: Cannot read file: {e}", file=sys.stderr)
        return 1

    try:
        doc = parse_document(content)
    except ParseError as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return 1

    output = {
        "header": {
            "kind": doc.header.kind if doc.header else None,
            "version": doc.header.version if doc.header else None,
            "fields": doc.header.fields if doc.header else {},
        } if doc.header else None,
        "sections": [
            {
                "name": s.name,
                "level": s.level,
                "content_lines": len(s.content),
                "subsections": [sub.name for sub in s.subsections],
            }
            for s in doc.sections
        ],
        "constraints": [
            {
                "type": c.constraint_type,
                "field_path": c.field_path,
                "operator": c.operator,
                "value": c.value,
            }
            for c in doc.constraints
        ],
        "capabilities": [
            {
                "name": cap.name,
                "params": cap.params,
            }
            for cap in doc.capabilities
        ],
        "directives": doc.directives,
    }

    print(json.dumps(output, indent=2, default=str))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """
    Build the argument parser for the CLI.

    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        prog="wraithspec",
        description="WraithSpec document validator and compliance checker",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate a WraithSpec document",
    )
    validate_parser.add_argument(
        "file",
        help="Path to the WraithSpec document to validate",
    )
    validate_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    validate_parser.set_defaults(func=cmd_validate)

    # check-output command
    check_parser = subparsers.add_parser(
        "check-output",
        help="Check output compliance against a specification",
    )
    check_parser.add_argument(
        "spec",
        help="Path to the WraithSpec specification",
    )
    check_parser.add_argument(
        "output",
        help="Path to the output file to check (JSON)",
    )
    check_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    check_parser.set_defaults(func=cmd_check_output)

    # parse command
    parse_parser = subparsers.add_parser(
        "parse",
        help="Parse and display document structure",
    )
    parse_parser.add_argument(
        "file",
        help="Path to the WraithSpec document to parse",
    )
    parse_parser.set_defaults(func=cmd_parse)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for the CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv)

    Returns:
        Exit code
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if hasattr(args, "func"):
        return args.func(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
