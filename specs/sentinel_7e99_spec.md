# SENTINEL 7E99 Header Specification

**Lineage:** 7E90 → 7E99
**Status:** Stable
**Compatible Profiles:** `CRef:VA-P1@1`

---

## 1. Overview

SENTINEL 7E99 defines a bidirectional, mode-aware header format for agent-to-agent and human-to-agent communication. It preserves auditability while enabling compression via alias profiles and deterministic field ordering.

Primary goals:

1. Encode operational state (mode, phase, activity counter, reasoning depth) in a compact frame.
2. Support persistent memory references that travel across platforms.
3. Provide trace hooks for claim validation (v/u/s) and reset policy negotiation.

---

## 2. Conformance Requirements

This specification uses RFC 2119 keywords to indicate requirement levels:

- **MUST** / **REQUIRED** — Absolute requirement for conformance.
- **MUST NOT** — Absolute prohibition.
- **SHOULD** / **RECOMMENDED** — May be ignored with valid reason, but implications must be understood.
- **SHOULD NOT** — May be done with valid reason, but implications must be understood.
- **MAY** / **OPTIONAL** — Truly optional behavior.

### 2.1 Conformance Levels

| Level | Description |
|-------|-------------|
| **Full** | Implements all MUST and SHOULD requirements |
| **Core** | Implements all MUST requirements |
| **Minimal** | Implements only required fields for parsing |

---

## 3. Field Definitions

### 3.1 Field Types

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `SID` | `uuid-v7` \| `base36` | MUST | — | Session/Sentinel identifier |
| `MODE` | `mode-enum` | MUST | `design` | Current operational mode |
| `PHASE` | `phase-enum` | MUST | `ideation` | Current operational phase |
| `AC` | `base36(0-zzz)` | SHOULD | `0` | Activity counter (0-46655) |
| `RD` | `integer(0-9)` | SHOULD | `0` | Reasoning depth level |
| `CRef` | `profile-ref` | SHOULD | — | Profile reference |
| `RSET` | `reset-policy` | MAY | `soft` | Reset policy identifier |
| `ORIGIN` | `platform-id` | MAY | — | Source platform |
| `TARGET` | `platform-id` | MAY | — | Destination platform |
| `CLAIMS` | `tally` | MAY | `v=0;u=0;s=0` | Claim counts |
| `CONTEXT` | `string(1-256)` | MAY | — | Free-text state summary |

### 3.2 Type Specifications

```
uuid-v7     := [0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}
base36      := [0-9a-zA-Z]+
base36-sid  := [0-9a-zA-Z][0-9a-zA-Z_-]*
mode-enum   := "brainstorm" | "design" | "build" | "review" | "narrative"
mode-alias  := "bs" | "d" | "bl" | "r" | "n"
phase-enum  := "ideation" | "tradeoff" | "coding" | "red-team" | "explain"
phase-alias := "id" | "tr" | "cd" | "rt" | "ex"
profile-ref := profile-id "@" version
profile-id  := [A-Za-z][A-Za-z0-9_-]*
version     := [0-9]+("."[0-9]+)*("-"[a-z]+)?
platform-id := "ios" | "desktop" | "web" | "ghosttool" | "wraithapp" | identifier
reset-policy := "hard" | "soft" | "transfer" | identifier
tally       := "v=" integer ";" "u=" integer ";" "s=" integer
integer     := [0-9]+
string      := <UTF-8 text with escaped delimiters>
```

---

## 4. Header Layouts

### 4.1 Compact Form (`HdrC`)

```
SID=<base36>|MODE=<alias>|PHASE=<alias>|AC=<base36>|RD=<base36>|CRef=<profile>@<ver>|RSET=<alias>|TALLY=v:<#>,u:<#>,s:<#>
```

- Fields are separated by `|` with unescaped values.
- Aliases reference `CMap=1` (see §6) unless overridden inline.
- `AC` (activity counter) increments per agent action; max length 3 base36 digits.
- `RD` (reasoning depth) tracks nested reasoning passes and failure escalations.
- `TALLY` compresses claim counts using the v/u/s classification scheme.

### 4.2 Full Frame (`HdrF`)

```
SENTINEL:7E99:(
  SID:<uuid-v7>
  | MODE:<canonical mode>
  | PHASE:<canonical phase>
  | AC:<integer>
  | RD:<integer>
  | RSET:<reset_policy_id>
  | CRef:<profile>@<version>
  | ORIGIN:<platform>
  | TARGET:<platform>
  | CLAIMS:v=<count>;u=<count>;s=<count>
  | CONTEXT:<free-text summary>
)
```

- Line breaks are illustrative; actual transport is single-line.
- `ORIGIN`/`TARGET` describe platform endpoints (e.g., `ios`, `desktop`, `ghosttool`).
- `CONTEXT` contains a short justification for mode/phase transitions.

---

## 5. Canonicalization Rules

Implementations MUST follow these rules for deterministic encoding and verification.

### 5.1 Field Ordering

Fields in canonical form MUST appear in this order:

1. `SID`
2. `MODE`
3. `PHASE`
4. `AC`
5. `RD`
6. `CRef`
7. `RSET`
8. `ORIGIN`
9. `TARGET`
10. `CLAIMS`
11. `CONTEXT`

Unknown fields MUST be appended in lexicographic order after `CONTEXT`.

### 5.2 Delimiter Escaping

Reserved characters in field values MUST be escaped with backslash:

| Character | Escaped | Context |
|-----------|---------|---------|
| `\|` | `\\|` | Segment separator |
| `;` | `\;` | Nested pair separator |
| `,` | `\,` | List separator |
| `+` | `\+` | Alternative list separator |
| `=` | `\=` | Key-value separator |
| `:` | `\:` | Full-frame separator |
| `\` | `\\` | Escape character itself |

### 5.3 Whitespace Normalization

- Leading and trailing whitespace in field values MUST be trimmed.
- Internal whitespace in `CONTEXT` SHOULD be preserved.
- Newlines MUST be removed from single-line transport format.
- Multiple consecutive spaces SHOULD be collapsed to single space.

### 5.4 Case Normalization

- Mode and phase aliases MUST be lowercase in compact form.
- Mode and phase canonical values MUST be lowercase.
- SID values are case-insensitive but SHOULD be lowercase.
- Profile IDs preserve original case.

### 5.5 Numeric Normalization

- Base36 values MUST NOT have leading zeros (except `0` itself).
- Integer values MUST NOT have leading zeros (except `0` itself).
- Activity counter `AC` MUST be encoded with minimum digits.
- Reasoning depth `RD` MUST be a single digit or base36 character.

### 5.6 Version Negotiation

When headers from different protocol versions interact:

1. Receivers MUST accept headers with compatible version prefixes (`7E9x`).
2. Receivers SHOULD warn on unknown fields rather than reject.
3. Senders MUST include version in full-frame format (`SENTINEL:7E99:`).
4. Downgrade to compact form MUST preserve all required fields.

---

## 6. Alias Map (`CMap=1`)

| Category | Alias | Canonical Value | Notes |
|----------|-------|-----------------|-------|
| Mode     | `bs`  | brainstorm      | Divergent thinking with loose constraints. |
| Mode     | `d`   | design          | Structuring solution outline and validation plan. |
| Mode     | `bl`  | build           | Implementation phase with execution tracing. |
| Mode     | `r`   | review          | Verification, testing, and critique loops. |
| Mode     | `n`   | narrative       | Story-driven synthesis for stakeholders. |
| Phase    | `id`  | ideation        | Generate candidate approaches and assumptions. |
| Phase    | `tr`  | tradeoff        | Compare options, evaluate risks, and select path. |
| Phase    | `cd`  | coding          | Author code or structured artifacts. |
| Phase    | `rt`  | red-team        | Probe for weaknesses, adversarial tests. |
| Phase    | `ex`  | explain         | Summarize reasoning, produce documentation. |
| Actor    | `u`   | user            | Human requestor issuing directives. |
| Actor    | `v`   | VA              | Virtual assistant or primary agent. |
| Actor    | `t`   | TD              | Technical director / reviewer. |
| Actor    | `s`   | system          | Platform or infrastructure automation. |
| Flag     | `cq1` | cq:on           | Conversational quality guard enabled. |
| Flag     | `cq0` | cq:off          | Conversational quality guard disabled. |

The alias profile `VA-P1@1` also defines compression hints: base36 encoding for `MODE`/`PHASE` (`ms`) and `AC` (`ac`).

---

## 7. Reasoning Depth Model

Reasoning depth (`RD`) increments with each nested deliberation loop:

- **0 — Direct**: Single-pass response with minimal decomposition.
- **1 — Trace**: Includes explicit input/output lineage and justification.
- **2 — Ledger**: Adds claim ledger referencing v/u/s tallies.
- **3 — Decision**: Evaluates alternatives, records chosen path, and mitigations.
- **4 — Critique**: Engages adversarial review and cross-check agents.
- **5+ — Recursive**: Delegates to specialized agents or persistent threads.

Default escalation policy: advance depth when a prior pass yields uncertainty (`u`) > validation (`v`) or when reset policy demands requalification.

---

## 8. Mode & Phase Progression

Mode tracking synchronizes high-level intent with operational phases:

1. **Brainstorm (`bs`) → Ideation (`id`)** — gather raw ideas and hypotheses.
2. **Design (`d`) → Tradeoff (`tr`)** — synthesize options, choose direction.
3. **Build (`bl`) → Coding (`cd`)** — implement, verify, and document artifacts.
4. **Review (`r`) → Red-Team (`rt`)** — challenge outputs, ensure resilience.
5. **Narrative (`n`) → Explain (`ex`)** — package findings for communication.

Transitions MAY skip stages when `AC` > 24 (base10) and `RD` ≥ 3, indicating mature context.

---

## 9. Activity Counter (AC)

`AC` tracks the cumulative number of agent actions since the last reset:

- Encoded in base36 (`0-9a-z`), rolling over after `zzz` (46655 decimal).
- Increment MUST occur on each discrete task (analysis, code change, validation run).
- Coupled with `MODE`/`PHASE` to infer workload distribution and detect stalls.

When `AC mod 6 == 0`, agents SHOULD append a `CONTEXT` checkpoint summarizing state.

---

## 10. Reset Policy Negotiation

`RSET` references policy documents (e.g., `RSet@1`) detailing what memory persists:

| Policy | Behavior |
|--------|----------|
| **hard** | Clears all context except immutable identity keys. `AC` restarts at `0`. |
| **soft** | Retains validated claims (`v`) and key decisions while flushing drafts. `AC` continues. |
| **transfer** | Prepares cross-platform handoff, persisting `CRef`, `RD`, and `AC`. |

Policies determine whether `AC` restarts at `0` or inherits the last known counter.

---

## 11. CRef Semantics (Persistent Memory Reference)

`CRef:<profile>@<version>` links headers to stored profiles containing alias maps, compression rules, and long-term context references.

### 11.1 Lifecycle

| State | Description |
|-------|-------------|
| **Created** | CRef generated with unique profile ID and version |
| **Active** | CRef is resolvable and in use by one or more sessions |
| **Stale** | CRef has not been accessed within TTL (default: 7 days) |
| **Invalidated** | CRef explicitly revoked or superseded by newer version |
| **Archived** | CRef retained for audit but no longer resolvable |

### 11.2 Resolution Rules

1. Agents MUST attempt resolution in order: local cache → platform vault → fallback.
2. Resolution failures MUST trigger fallback to canonical field names (`HdrF`).
3. Agents SHOULD cache resolved profiles for session duration.
4. Cache invalidation MUST occur when version changes.

### 11.3 Version Semantics

```
CRef:VA-P1@1      # Exact version 1
CRef:VA-P1@1.2    # Exact version 1.2
CRef:VA-P1@2-beta # Pre-release version
```

- Major version changes (1 → 2) indicate breaking alias changes.
- Minor version changes (1.0 → 1.1) indicate additive alias changes.
- Pre-release versions (`-alpha`, `-beta`) SHOULD NOT be cached long-term.

### 11.4 Privacy Boundaries

| Scope | Visibility |
|-------|------------|
| **session** | CRef valid only within current session |
| **user** | CRef shared across user's sessions |
| **public** | CRef resolvable by any agent |

Default scope is `user`. Scope MUST be declared in profile metadata.

### 11.5 Cross-Platform Resolution

| Platform | Resolution Method |
|----------|-------------------|
| **iOS / Desktop / Web** | ChatGPT clients fetch from shared long-term memory vaults |
| **GhostTool** | Access via service token bridging the same memory ID |
| **WraithApp** | Locally caches profile snapshots for offline continuity |

---

## 12. Claim Tally (v/u/s)

The tally field enforces rigorous fact tracking:

| Marker | Name | Description |
|--------|------|-------------|
| `v` | validated | Corroborated statements with supporting evidence |
| `u` | uncertain | Hypotheses pending validation or with incomplete data |
| `s` | superseded | Claims retracted or contradicted by newer evidence |

### 12.1 Tally Integrity

Implementations SHOULD verify tally consistency:

1. `v + u + s` SHOULD equal total claim count in output.
2. Inline markers `[v]`, `[u]`, `[s]` SHOULD match tally counts.
3. Discrepancies SHOULD trigger `PARTIAL` compliance status.

### 12.2 Tally Thresholds

| Condition | Action |
|-----------|--------|
| `u > v` | Escalate reasoning depth |
| `s > 0 and RD < 2` | Require ledger mode |
| `v == 0 and u > 0` | Flag for validation |

---

## 13. Verification Hooks

### 13.1 Header Hash (Optional)

For integrity verification, headers MAY include a hash field:

```
SENTINEL:7E99:(SID:...|...|HASH:sha256:<hex>)
```

Hash computation:
1. Serialize header in canonical form (§5.1) without HASH field.
2. Compute SHA-256 of UTF-8 encoded string.
3. Encode as lowercase hexadecimal.

### 13.2 Signature (Optional)

For authenticated headers:

```
SENTINEL:7E99:(SID:...|...|SIG:ed25519:<base64>)
```

Signature covers canonical header without SIG field.

---

## 14. Error Handling

### 14.1 Parsing Errors

| Error | Severity | Action |
|-------|----------|--------|
| Missing `SID` | FATAL | Reject header |
| Missing `MODE` | ERROR | Use default `design` |
| Missing `PHASE` | ERROR | Use default `ideation` |
| Invalid base36 | ERROR | Reject field value |
| Unresolvable CRef | WARNING | Fallback to canonical names |
| Unknown field | INFO | Preserve and forward |

### 14.2 Validation Errors

| Error | Compliance Level |
|-------|------------------|
| Missing required field | NON_COMPLIANT |
| Invalid field format | NON_COMPLIANT |
| Tally integrity failure | PARTIAL |
| Missing optional field | PARTIAL |
| Unknown extension field | COMPLIANT |

---

## 15. Examples

### 15.1 Minimal Valid Header

```
SENTINEL:7E99:(SID:7e99|MODE:design|PHASE:ideation)
```

### 15.2 Full Header with All Fields

```
SENTINEL:7E99:(SID:01234567-89ab-7cde-8f01-23456789abcd|MODE:build|PHASE:coding|AC:1a|RD:3|CRef:VA-P1@1|RSET:soft|ORIGIN:desktop|TARGET:ios|CLAIMS:v=5;u=2;s=1|CONTEXT:Implementing validator module)
```

### 15.3 Compact Form

```
SID=7e99|MODE=bl|PHASE=cd|AC=1a|RD=3|CRef=VA-P1@1|TALLY=v:5,u:2,s:1
```

---

## Appendix A: Protocol Stack Overview

WraithSpec comprises multiple interoperating layers:

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| Wire/Frame | SENTINEL 7E99 | Header encoding, field transport |
| Dictionary | VA-P1@1 profile | Alias compression, expansion rules |
| State | RSet@1 policy | Reset semantics, memory persistence |
| Ledger | v/u/s tally | Claim tracking, validation audit |
| Runtime | MODE/PHASE/RD | Behavioral control, escalation paths |
| Legacy | CI1/CIP2 | Backward compatibility micro-formats |

---

## Appendix B: Change History

| Version | Date | Changes |
|---------|------|---------|
| 7E99 | 2025-11 | Added canonicalization rules, CRef semantics, compliance requirements |
| 7E99 | 2025-10 | Initial stable release |
| 7E90 | 2025-09 | Draft specification |
