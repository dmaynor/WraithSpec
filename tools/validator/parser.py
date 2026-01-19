# SPDX-License-Identifier: MIT
"""
WraithSpec Document Parser

Parses WraithSpec documents including SENTINEL headers, CI1/CIP2 micro-formats,
and document sections according to the v0.1 grammar specification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


class ParseError(Exception):
    """Raised when parsing fails due to invalid syntax."""

    def __init__(self, message: str, line: int = 0, column: int = 0) -> None:
        self.line = line
        self.column = column
        super().__init__(f"{message} (line {line}, col {column})" if line else message)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Header:
    """Represents a parsed WraithSpec header."""

    kind: str  # "SENTINEL_FULL", "SENTINEL_COMPACT", "CI1", "CIP2"
    version: Optional[str] = None
    fields: Dict[str, Any] = field(default_factory=dict)
    raw: str = ""


@dataclass
class Section:
    """Represents a document section."""

    name: str
    level: int  # 2 for ##, 3 for ###
    content: List[str] = field(default_factory=list)
    subsections: List["Section"] = field(default_factory=list)


@dataclass
class Constraint:
    """Represents a constraint rule."""

    constraint_type: str  # REQUIRED, OPTIONAL, FORBIDDEN, CONDITIONAL
    field_path: str
    operator: str
    value: Any


@dataclass
class Capability:
    """Represents a capability declaration."""

    name: str
    params: Dict[str, str] = field(default_factory=dict)


@dataclass
class Document:
    """Represents a complete parsed WraithSpec document."""

    header: Optional[Header] = None
    sections: List[Section] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    capabilities: List[Capability] = field(default_factory=list)
    directives: Dict[str, str] = field(default_factory=dict)
    raw: str = ""


# =============================================================================
# Regex Patterns
# =============================================================================

# SENTINEL full frame pattern
SENTINEL_FULL_RE = re.compile(
    r"^SENTINEL:([0-9A-Fa-f]{4}):\((.+)\)$", re.DOTALL
)

# Pipe-separated segments (respecting escapes)
PIPE_SPLIT_RE = re.compile(r"(?<!\\)\|")

# Key=value pattern
KV_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")

# Key:value pattern (for full frame)
KV_COLON_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(.*)$")

# Profile reference pattern
CREF_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)@(\d+(?:\.\d+)*(?:-[a-z]+)?)$")

# Base36 pattern
BASE36_RE = re.compile(r"^[0-9a-zA-Z]+$")

# UUID v7 pattern
UUID_V7_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# v/u/s tally patterns
TALLY_COMPACT_RE = re.compile(r"^v:(\d+),u:(\d+),s:(\d+)$")
TALLY_FULL_RE = re.compile(r"^v=(\d+);u=(\d+);s=(\d+)$")

# Section markers
SECTION_RE = re.compile(r"^(#{2,3})\s+(.+)$")

# Constraint pattern
CONSTRAINT_RE = re.compile(
    r"^(REQUIRED|OPTIONAL|FORBIDDEN|CONDITIONAL):\s*(.+)$"
)

# Capability pattern
CAPABILITY_RE = re.compile(
    r"^CAPABILITY:\s*([A-Za-z_][A-Za-z0-9_]*)(?:\(([^)]*)\))?$"
)

# Directive block markers
DIRECTIVE_START_RE = re.compile(r"^---\s*$")

# Mode values
VALID_MODES = {"brainstorm", "design", "build", "review", "narrative"}
MODE_ALIASES = {"bs": "brainstorm", "d": "design", "bl": "build", "r": "review", "n": "narrative"}

# Phase values
VALID_PHASES = {"ideation", "tradeoff", "coding", "red-team", "explain"}
PHASE_ALIASES = {"id": "ideation", "tr": "tradeoff", "cd": "coding", "rt": "red-team", "ex": "explain"}


# =============================================================================
# Utility Functions
# =============================================================================


def unescape_value(raw: str) -> str:
    """Unescape reserved characters in field values."""
    if not raw:
        return raw
    return re.sub(r"\\([|;,+=])", r"\1", raw)


def split_pipe_segments(line: str) -> List[str]:
    """Split a line by unescaped pipe characters."""
    segments: List[str] = []
    current: List[str] = []
    escaped = False

    for ch in line.strip():
        if escaped:
            current.append(ch)
            escaped = False
            continue
        if ch == "\\":
            current.append(ch)
            escaped = True
            continue
        if ch == "|":
            segments.append("".join(current).strip())
            current = []
            continue
        current.append(ch)

    if current:
        segments.append("".join(current).strip())

    return [s for s in segments if s]


def parse_kv_pairs(segments: List[str], separator: str = "=") -> Dict[str, str]:
    """Parse key=value or key:value pairs from segments."""
    result: Dict[str, str] = {}
    pattern = KV_RE if separator == "=" else KV_COLON_RE

    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        match = pattern.match(seg)
        if match:
            key, value = match.groups()
            result[key] = unescape_value(value)
        elif separator == "=" and "=" not in seg:
            # Bare flag becomes key=true
            result[seg] = "true"

    return result


def parse_semicolon_pairs(value: str) -> Dict[str, Any]:
    """Parse semicolon-separated pairs: k1:v1;k2:v2;flag."""
    result: Dict[str, Any] = {}
    if not value:
        return result

    for item in value.split(";"):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            k, v = item.split(":", 1)
            result[k.strip()] = v.strip()
        else:
            result[item] = True

    return result


def parse_tally(value: str) -> Optional[Dict[str, int]]:
    """Parse v/u/s tally from compact or full format."""
    # Try compact format: v:3,u:1,s:0
    match = TALLY_COMPACT_RE.match(value)
    if match:
        return {
            "v": int(match.group(1)),
            "u": int(match.group(2)),
            "s": int(match.group(3)),
        }

    # Try full format: v=3;u=1;s=0
    match = TALLY_FULL_RE.match(value)
    if match:
        return {
            "v": int(match.group(1)),
            "u": int(match.group(2)),
            "s": int(match.group(3)),
        }

    return None


# =============================================================================
# Header Parsers
# =============================================================================


def parse_sentinel_full(content: str) -> Header:
    """
    Parse a SENTINEL full frame header.

    Format: SENTINEL:7E99:(SID:<uuid>|MODE:<mode>|...)

    Args:
        content: The header string to parse

    Returns:
        Header object with parsed fields

    Raises:
        ParseError: If the header format is invalid
    """
    content = content.strip()
    match = SENTINEL_FULL_RE.match(content)
    if not match:
        raise ParseError("Invalid SENTINEL full frame format")

    version = match.group(1)
    fields_str = match.group(2)

    # Parse pipe-separated fields
    segments = split_pipe_segments(fields_str)
    fields = parse_kv_pairs(segments, separator=":")

    # Normalize mode and phase
    if "MODE" in fields:
        mode = fields["MODE"].lower()
        fields["MODE"] = MODE_ALIASES.get(mode, mode)

    if "PHASE" in fields:
        phase = fields["PHASE"].lower()
        fields["PHASE"] = PHASE_ALIASES.get(phase, phase)

    # Parse CLAIMS if present
    if "CLAIMS" in fields:
        tally = parse_tally(fields["CLAIMS"])
        if tally:
            fields["CLAIMS"] = tally

    return Header(
        kind="SENTINEL_FULL",
        version=version,
        fields=fields,
        raw=content,
    )


def parse_sentinel_compact(content: str) -> Header:
    """
    Parse a SENTINEL compact header (HdrC format).

    Format: SID=7E99|MODE=d|PHASE=tr|AC=f|RD=3|...

    Args:
        content: The header string to parse

    Returns:
        Header object with parsed fields

    Raises:
        ParseError: If the header format is invalid
    """
    content = content.strip()

    if "|" not in content:
        raise ParseError("Invalid compact header: missing pipe separators")

    segments = split_pipe_segments(content)
    fields = parse_kv_pairs(segments, separator="=")

    # Normalize mode and phase
    if "MODE" in fields:
        mode = fields["MODE"].lower()
        fields["MODE"] = MODE_ALIASES.get(mode, mode)

    if "PHASE" in fields:
        phase = fields["PHASE"].lower()
        fields["PHASE"] = PHASE_ALIASES.get(phase, phase)

    # Parse TALLY if present
    if "TALLY" in fields:
        tally = parse_tally(fields["TALLY"])
        if tally:
            fields["TALLY"] = tally

    return Header(
        kind="SENTINEL_COMPACT",
        version=None,
        fields=fields,
        raw=content,
    )


def parse_ci1(content: str) -> Header:
    """
    Parse a CI1 (configuration) micro-line.

    Format: CI1|SID=7E96|P=Profile|HdrC=...|HdrF=...

    Args:
        content: The micro-line to parse

    Returns:
        Header object with parsed fields

    Raises:
        ParseError: If the format is invalid or required fields missing
    """
    content = content.strip()

    if not content.startswith("CI1"):
        raise ParseError("Invalid CI1 header: must start with 'CI1'")

    segments = split_pipe_segments(content)
    if segments[0] != "CI1":
        raise ParseError("Invalid CI1 header: first segment must be 'CI1'")

    fields = parse_kv_pairs(segments[1:], separator="=")

    # Check required fields
    required = {"SID", "P", "HdrC", "HdrF"}
    missing = required - set(fields.keys())
    if missing:
        raise ParseError(f"CI1 missing required fields: {sorted(missing)}")

    # Parse nested HdrF pairs
    if "HdrF" in fields and isinstance(fields["HdrF"], str):
        fields["HdrF"] = parse_semicolon_pairs(fields["HdrF"])

    # Parse behavior indices
    if "B" in fields:
        indices = []
        for token in fields["B"].replace("+", ",").split(","):
            token = token.strip()
            if token.isdigit():
                indices.append(int(token))
        fields["B"] = indices

    return Header(
        kind="CI1",
        version=fields.get("Ver"),
        fields=fields,
        raw=content,
    )


def parse_cip2(content: str) -> Header:
    """
    Parse a CIP2 (prompt) micro-line.

    Format: CIP2|SID=7E96|P=Profile|CTX=context|TASK=task|...

    Args:
        content: The micro-line to parse

    Returns:
        Header object with parsed fields

    Raises:
        ParseError: If the format is invalid or required fields missing
    """
    content = content.strip()

    if not content.startswith("CIP2"):
        raise ParseError("Invalid CIP2 header: must start with 'CIP2'")

    segments = split_pipe_segments(content)
    if segments[0] != "CIP2":
        raise ParseError("Invalid CIP2 header: first segment must be 'CIP2'")

    fields = parse_kv_pairs(segments[1:], separator="=")

    # Check required fields
    required = {"SID", "P", "CTX", "TASK"}
    missing = required - set(fields.keys())
    if missing:
        raise ParseError(f"CIP2 missing required fields: {sorted(missing)}")

    # Parse constraints list
    if "CONS" in fields:
        fields["CONS"] = [c.strip() for c in fields["CONS"].split("+") if c.strip()]

    # Parse output format list
    if "OUT" in fields:
        fields["OUT"] = [o.strip() for o in fields["OUT"].split("+") if o.strip()]

    # Parse request list
    if "REQ" in fields:
        fields["REQ"] = [r.strip() for r in fields["REQ"].split(",") if r.strip()]

    # Parse MAX as integer
    max_field = fields.get("MAX") or fields.get("max")
    if max_field:
        try:
            fields["MAX"] = int(max_field)
        except ValueError:
            pass

    return Header(
        kind="CIP2",
        version=None,
        fields=fields,
        raw=content,
    )


def parse_header(content: str) -> Header:
    """
    Parse a WraithSpec header, auto-detecting the format.

    Supports:
    - SENTINEL full frame: SENTINEL:7E99:(...)
    - SENTINEL compact: SID=...|MODE=...|...
    - CI1 micro-line: CI1|...
    - CIP2 micro-line: CIP2|...

    Args:
        content: The header string to parse

    Returns:
        Header object with parsed fields

    Raises:
        ParseError: If the header format cannot be determined or is invalid
    """
    content = content.strip()

    if not content:
        raise ParseError("Empty header")

    # Check for SENTINEL full frame
    if content.startswith("SENTINEL:"):
        return parse_sentinel_full(content)

    # Check for CI1
    if content.startswith("CI1"):
        return parse_ci1(content)

    # Check for CIP2
    if content.startswith("CIP2"):
        return parse_cip2(content)

    # Check for compact header (has SID=)
    if "SID=" in content and "|" in content:
        return parse_sentinel_compact(content)

    raise ParseError("Unable to determine header format")


# =============================================================================
# Document Parser
# =============================================================================


def parse_document(content: str) -> Document:
    """
    Parse a complete WraithSpec document.

    The document may contain:
    - A header (SENTINEL, CI1, or CIP2)
    - Sections marked with ## or ###
    - Constraint blocks
    - Capability declarations
    - Directive blocks (--- delimited)

    Args:
        content: The document content to parse

    Returns:
        Document object with all parsed components

    Raises:
        ParseError: If the document structure is invalid
    """
    doc = Document(raw=content)
    lines = content.split("\n")
    line_num = 0

    # Track parsing state
    in_directive_block = False
    current_section: Optional[Section] = None
    in_constraints = False

    while line_num < len(lines):
        line = lines[line_num]
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            line_num += 1
            continue

        # Check for directive block markers
        if DIRECTIVE_START_RE.match(stripped):
            if in_directive_block:
                # End of directive block
                in_directive_block = False
            else:
                # Start of directive block
                in_directive_block = True
            line_num += 1
            continue

        # Handle directive lines
        if in_directive_block:
            if ":" in stripped:
                key, value = stripped.split(":", 1)
                doc.directives[key.strip()] = value.strip()
            line_num += 1
            continue

        # Check for header (only at document start or after directives)
        if doc.header is None:
            try:
                if (
                    stripped.startswith("SENTINEL:")
                    or stripped.startswith("CI1")
                    or stripped.startswith("CIP2")
                    or ("SID=" in stripped and "|" in stripped)
                ):
                    doc.header = parse_header(stripped)
                    line_num += 1
                    continue
            except ParseError:
                pass  # Not a header, continue parsing as content

        # Check for section markers
        section_match = SECTION_RE.match(stripped)
        if section_match:
            level = len(section_match.group(1))
            name = section_match.group(2).strip()

            section = Section(name=name, level=level)

            if level == 2:
                doc.sections.append(section)
                current_section = section
            elif level == 3 and current_section:
                current_section.subsections.append(section)
                current_section = section

            # Check if this is a CONSTRAINTS section
            in_constraints = name.upper() == "CONSTRAINTS"
            line_num += 1
            continue

        # Check for capability declarations
        cap_match = CAPABILITY_RE.match(stripped)
        if cap_match:
            name = cap_match.group(1)
            params_str = cap_match.group(2) or ""
            params = {}
            if params_str:
                for pair in params_str.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        params[k.strip()] = v.strip()
                    else:
                        params[pair.strip()] = "true"
            doc.capabilities.append(Capability(name=name, params=params))
            line_num += 1
            continue

        # Check for constraint rules
        if in_constraints:
            constraint_match = CONSTRAINT_RE.match(stripped)
            if constraint_match:
                ctype = constraint_match.group(1)
                expr = constraint_match.group(2).strip()

                # Parse constraint expression: field_path op value
                # Simple parsing for common patterns
                constraint = Constraint(
                    constraint_type=ctype,
                    field_path=expr,
                    operator="exists",
                    value=None,
                )

                # Handle operators with values: "field op value"
                for op in ["==", "!=", ">=", "<=", ">", "<", "matches"]:
                    if f" {op} " in expr:
                        parts = expr.split(f" {op} ", 1)
                        constraint.field_path = parts[0].strip()
                        constraint.operator = op
                        if len(parts) > 1:
                            constraint.value = parts[1].strip().strip('"\'')
                        break
                else:
                    # Handle "field exists" at end of expression
                    if expr.endswith(" exists"):
                        constraint.field_path = expr[:-7].strip()  # Remove " exists"
                        constraint.operator = "exists"
                        constraint.value = None

                doc.constraints.append(constraint)
                line_num += 1
                continue

        # Regular content line
        if current_section:
            current_section.content.append(line)

        line_num += 1

    return doc
