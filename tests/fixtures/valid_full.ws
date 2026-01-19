---
version: 0.1
profile: VA-P1
strict: true
---

SENTINEL:7E99:(SID:full-test-7e99|MODE:design|PHASE:tradeoff|AC:f|RD:3|CRef:VA-P1@1|RSET:soft|CLAIMS:v=5;u=2;s=0|CONTEXT:Full specification example|ORIGIN:desktop|TARGET:web)

## Overview

This is a full-featured WraithSpec document demonstrating all constructs
defined in the v0.1 grammar specification.

### Purpose

The document serves as a reference implementation for:
- SENTINEL header formats
- Section structure
- Capability declarations
- Constraint blocks

## Capabilities

CAPABILITY: memory_access(persistent=true, scope=session)
CAPABILITY: code_execution(sandboxed=true)
CAPABILITY: web_access(allowed_domains=docs.example.com)

## CONSTRAINTS

REQUIRED: header.SID exists
REQUIRED: header.MODE exists
REQUIRED: header.PHASE exists
OPTIONAL: header.CONTEXT exists
FORBIDDEN: output.secrets exists
CONDITIONAL: header.RD >= 2 == output.tally exists

## Output Schema

The expected output should conform to the following structure:

- header: Object containing SID and operational state
- result: The primary output content
- tally: v/u/s claim counts matching inline markers
- trace: Optional reasoning trace when RD >= 1

## Validation Rules

All outputs must satisfy:
1. SID matches the specification SID
2. MODE/PHASE reflect current operational state
3. Tally counts are accurate and balanced
4. No forbidden fields are present

## Examples

### Valid Output

```json
{
  "header": {
    "SID": "full-test-7e99",
    "MODE": "design",
    "PHASE": "tradeoff"
  },
  "result": "Analysis complete",
  "tally": {"v": 5, "u": 2, "s": 0}
}
```

### Tally Markers

Use inline markers to track claim status:
- [v] Validated claim with evidence
- [u] Uncertain claim pending verification
- [s] Superseded claim (retracted)

## Appendix

### Profile Reference

This document uses CRef:VA-P1@1 which defines:
- Mode aliases (bs, d, bl, r, n)
- Phase aliases (id, tr, cd, rt, ex)
- Base36 encoding for counters
- Reset policies (hard, soft, transfer)

### Revision History

- v0.1: Initial specification
