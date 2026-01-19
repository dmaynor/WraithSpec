# WraithSpec — Standard for Agent Interoperability and AI Meta-Communication

**Version:** SENTINEL 7E99 (VA-Ops)

## Purpose

WraithSpec defines the serialization, compression, and state management protocols that enable consistent, auditable exchanges between agents and human collaborators. This repository serves as the canonical specification for the Wraith ecosystem.

## Current Implementation

This branch integrates the SENTINEL 7E99 header specification, alias-mapped memory profiles, and persistent reasoning context management. The specification targets interoperability across iOS, desktop, and web ChatGPT instances as well as companion agents built on the WraithApp and GhostTool protocol layers.

### Key Components

- **SENTINEL 7E99 Header** — compact, mode-aware communication frame with compressed fields and tracing hooks.
- **VA-P1@1 Profile** — alias map for compression covering modes, phases, and actors.
- **RSet@1 Reset Policy** — controlled knowledge reset mechanisms with selective retention of public or session-limited data.
- **v/u/s Tally System** — factual classification layer for tracking validated, uncertain, and superseded claims.
- **Persistent Memory Reference (CRef)** — cross-platform storage pointer used to synchronize long-term memory across ChatGPT clients.
- **Compatibility Matrix** — confirmed support for WraithApp telemetry relays and GhostTool orchestration APIs.

## Repository Layout

```
WraithSpec/
├── README.md
├── AGENTS.md
├── VAP_CORE_GUIDE.md
├── vap_micro.py
├── specs/
│   ├── sentinel_7e99_spec.md
│   ├── grammar/
│   │   └── wraithspec_v0.1.ebnf
│   └── compliance_levels.yaml
├── tools/
│   └── validator/
│       ├── __init__.py
│       ├── parser.py
│       ├── validator.py
│       ├── compliance.py
│       ├── cli.py
│       └── tests/
├── tests/
│   ├── __init__.py
│   ├── test_vap_micro.py
│   └── fixtures/
│       ├── valid_minimal.ws
│       ├── valid_full.ws
│       ├── invalid_missing_header.ws
│       ├── invalid_malformed_cref.ws
│       ├── output_compliant.json
│       ├── output_partial.json
│       └── output_violation.json
└── CHANGELOG.md
```

> **Note:** Files not yet present in this branch are reserved for upcoming drops and will be published as the implementation matures.

## Grammar Specification

The formal grammar for WraithSpec v0.1 is defined in EBNF notation at `specs/grammar/wraithspec_v0.1.ebnf`. The grammar covers:

### Document Structure
- Headers (SENTINEL full frame, compact, CI1, CIP2)
- Sections marked with `##` or `###`
- Directive blocks delimited by `---`
- Capability declarations
- Constraint blocks

### SENTINEL Header Format
```
SENTINEL:7E99:(SID:<id>|MODE:<mode>|PHASE:<phase>|AC:<counter>|RD:<depth>|CRef:<profile>@<version>)
```

Fields:
- **SID** — Session/Sentinel identifier (UUID v7 or base36)
- **MODE** — Operational mode: `brainstorm`, `design`, `build`, `review`, `narrative` (aliases: `bs`, `d`, `bl`, `r`, `n`)
- **PHASE** — Current phase: `ideation`, `tradeoff`, `coding`, `red-team`, `explain` (aliases: `id`, `tr`, `cd`, `rt`, `ex`)
- **AC** — Activity counter (base36, max 3 digits)
- **RD** — Reasoning depth (0-5+)
- **CRef** — Profile reference for alias resolution

### Micro-Formats
- **CI1** (Configuration): `CI1|SID=<id>|P=<profile>|HdrC=<compact>|HdrF=<full>`
- **CIP2** (Prompt): `CIP2|SID=<id>|P=<profile>|CTX=<context>|TASK=<task>`

### v/u/s Tally Syntax
- Inline markers: `[v]`, `[u]`, `[s]`
- Compact: `TALLY=v:3,u:1,s:0`
- Full: `CLAIMS:v=3;u=1;s=0`

## Reference Validator

The reference validator is a Python package for parsing and validating WraithSpec documents.

### Installation

The validator requires Python 3.10+ and has no external dependencies.

```bash
# Clone the repository
git clone https://github.com/dmaynor/WraithSpec.git
cd WraithSpec

# Run directly (no installation needed)
python -m tools.validator.cli --help
```

### Usage

#### Validate a WraithSpec Document

```bash
# Validate a document
python -m tools.validator.cli validate tests/fixtures/valid_full.ws

# Output as JSON
python -m tools.validator.cli validate tests/fixtures/valid_full.ws --json
```

Exit codes:
- `0` — Document is valid
- `1` — Document has validation errors

#### Check Output Compliance

```bash
# Check output against a specification
python -m tools.validator.cli check-output tests/fixtures/valid_full.ws tests/fixtures/output_compliant.json

# Output as JSON
python -m tools.validator.cli check-output tests/fixtures/valid_full.ws tests/fixtures/output_compliant.json --json
```

Exit codes:
- `0` — Output is COMPLIANT or PARTIAL
- `1` — Output is NON_COMPLIANT or VIOLATION

#### Parse Document Structure

```bash
# Display parsed document structure as JSON
python -m tools.validator.cli parse tests/fixtures/valid_full.ws
```

### Programmatic API

```python
from tools.validator import parse_document, validate_document, check_compliance

# Parse a document
doc = parse_document(content)
print(f"Header kind: {doc.header.kind}")
print(f"Fields: {doc.header.fields}")

# Validate structure
result = validate_document(content)
if result.valid:
    print("Document is valid")
else:
    for v in result.violations:
        print(f"Error: {v.field} - {v.message}")

# Check output compliance
compliance = check_compliance(spec_content, output_json)
print(f"Level: {compliance.level}")
print(f"Score: {compliance.score}")
```

### Running Tests

```bash
# Run all validator tests
python -m pytest tools/validator/tests/

# Run with verbose output
python -m pytest tools/validator/tests/ -v

# Run specific test file
python -m pytest tools/validator/tests/test_parser.py
```

## Compliance Levels

The compliance level schema (`specs/compliance_levels.yaml`) defines four levels for classifying output conformance:

### COMPLIANT
All requirements met. Output fully conforms to the specification.
- Severity weight: 0
- Retry eligible: No (no need to retry)

### PARTIAL
Core requirements met but optional fields or soft constraints have violations.
- Severity weight: 25
- Retry eligible: Yes (with hints)
- Examples:
  - Missing optional CONTEXT field
  - CRef without @version suffix
  - Output slightly exceeds MAX soft limit
  - Missing tally in trace mode

### NON_COMPLIANT
One or more core requirements are violated. Requires correction.
- Severity weight: 75
- Retry eligible: Yes (with specific remediation)
- Examples:
  - Missing required SID field
  - Invalid MODE value
  - Malformed CRef format
  - Invalid base36 in AC field

### VIOLATION
Hard constraint breach indicating protocol failure or integrity issue.
- Severity weight: 100
- Retry eligible: No (requires manual review)
- Examples:
  - Forbidden field present
  - Protocol version mismatch
  - Tally integrity failure
  - Reset policy violation

### Scoring

Compliance scores are calculated as weighted sums of violations:

| Constraint Type | Weight |
|----------------|--------|
| REQUIRED       | 50     |
| OPTIONAL       | 10     |
| FORBIDDEN      | 100    |
| CONDITIONAL    | 25     |
| FORMAT         | 15     |
| RANGE          | 20     |
| REFERENCE      | 30     |

Score ranges:
- 0: COMPLIANT
- 1-49: PARTIAL
- 50-99: NON_COMPLIANT
- 100+: VIOLATION

## Getting Started

This repository is documentation-first. Tooling such as `vap_micro.py` remains available for reference decoding and validation of legacy CI1/CIP2 micro-formats.

### Inspect Legacy Micro-Formats

```bash
python vap_micro.py inspect --kind CI1
```

### Decode SENTINEL 7E99 Headers (Preview)

Use the examples under `tests/fixtures/` as fixtures when testing cross-agent integrations.

## Spec Highlights

- Persistent header fields include `SID`, `AC` (activity counter), `RD` (reasoning depth), `MODE`, and `PHASE` with optional alias compression.
- Profiles referenced via `CRef:<profile>@<version>` expose alias dictionaries and compression policies.
- Mode tracking and reasoning depth matrices define default escalation paths for brainstorm → design → build → review loops.
- Reset policies (`RSet@1`) govern how agents clear or persist memory across sessions, including mobile and desktop continuations.
- The v/u/s tally system records validated facts (`v`), uncertain statements (`u`), and superseded or contradicted items (`s`).

## Contributing

Contributions should extend the specification while keeping backward compatibility for existing CI1/CIP2 tooling. Please open issues to discuss major protocol changes before submitting PRs.

### Grammar Extensions

When extending the EBNF grammar:

1. **Preserve existing rules** — Do not modify production rules that affect existing document parsing.

2. **Add new rules at the end** — New constructs should be added as new production rules, not modifications to existing ones.

3. **Document changes** — Include comments explaining each new production rule and its purpose.

4. **Update validator** — Ensure the reference validator is updated to handle new grammar constructs.

5. **Add test fixtures** — Create both valid and invalid examples demonstrating the new constructs.

6. **Version appropriately** — Grammar changes that break backward compatibility require a minor version bump (e.g., v0.1 → v0.2).

### Pull Request Guidelines

1. **One concern per PR** — Keep changes focused on a single feature or fix.

2. **Include tests** — All new functionality must have corresponding test coverage.

3. **Update documentation** — Update README and relevant spec files.

4. **Maintain compatibility** — Ensure existing CI1/CIP2 references in `vap_micro.py` continue to work.

5. **Use conventional commits** — Prefix commits with `[foundation]`, `[grammar]`, `[validator]`, etc.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/dmaynor/WraithSpec.git
cd WraithSpec

# Run validator tests
python -m pytest tools/validator/tests/ -v

# Run legacy micro-format tests
python -m pytest tests/ -v

# Validate all fixtures
python -m tools.validator.cli validate tests/fixtures/valid_full.ws
python -m tools.validator.cli validate tests/fixtures/valid_minimal.ws
```

## License

MIT
