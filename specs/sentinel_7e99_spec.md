# SENTINEL 7E99 Header Specification

**Lineage:** 7E90 → 7E99  \
**Status:** Stable  \
**Compatible Profiles:** `CRef:VA-P1@1`

---

## 1. Overview

SENTINEL 7E99 defines a bidirectional, mode-aware header format for agent-to-agent and human-to-agent communication. It preserves auditability while enabling compression via alias profiles and deterministic field ordering.

Primary goals:

1. Encode operational state (mode, phase, activity counter, reasoning depth) in a compact frame.
2. Support persistent memory references that travel across platforms.
3. Provide trace hooks for claim validation (v/u/s) and reset policy negotiation.

---

## 2. Header Layouts

### 2.1 Compact Form (`HdrC`)

```
SID=<base36>|MODE=<alias>|PHASE=<alias>|AC=<base36>|RD=<base36>|CRef=<profile>@<ver>|RSET=<alias>|TALLY=v:<#>,u:<#>,s:<#>
```

- Fields are separated by `|` with unescaped values.
- Aliases reference `CMap=1` (see §3) unless overridden inline.
- `AC` (activity counter) increments per agent action; max length 3 base36 digits.
- `RD` (reasoning depth) tracks nested reasoning passes and failure escalations.
- `TALLY` compresses claim counts using the v/u/s classification scheme.

### 2.2 Full Frame (`HdrF`)

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

## 3. Alias Map (`CMap=1`)

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

## 4. Reasoning Depth Model

Reasoning depth (`RD`) increments with each nested deliberation loop:

- **0 — Direct**: Single-pass response with minimal decomposition.
- **1 — Trace**: Includes explicit input/output lineage and justification.
- **2 — Ledger**: Adds claim ledger referencing v/u/s tallies.
- **3 — Decision**: Evaluates alternatives, records chosen path, and mitigations.
- **4 — Critique**: Engages adversarial review and cross-check agents.
- **5+ — Recursive**: Delegates to specialized agents or persistent threads.

Default escalation policy: advance depth when a prior pass yields uncertainty (`u`) > validation (`v`) or when reset policy demands requalification.

---

## 5. Mode & Phase Progression

Mode tracking synchronizes high-level intent with operational phases:

1. **Brainstorm (`bs`) → Ideation (`id`)** — gather raw ideas and hypotheses.
2. **Design (`d`) → Tradeoff (`tr`)** — synthesize options, choose direction.
3. **Build (`bl`) → Coding (`cd`)** — implement, verify, and document artifacts.
4. **Review (`r`) → Red-Team (`rt`)** — challenge outputs, ensure resilience.
5. **Narrative (`n`) → Explain (`ex`)** — package findings for communication.

Transitions may skip stages when `AC` > 24 (base10) and `RD` ≥ 3, indicating mature context.

---

## 6. Activity Counter (AC)

`AC` tracks the cumulative number of agent actions since the last reset:

- Encoded in base36 (`0-9a-z`), rolling over after `zz`.
- Increment occurs on each discrete task (analysis, code change, validation run).
- Coupled with `MODE`/`PHASE` to infer workload distribution and detect stalls.

When `AC mod 6 == 0`, agents must append a `CONTEXT` checkpoint summarizing state.

---

## 7. Reset Policy Negotiation

`RSET` references policy documents (e.g., `RSet@1`) detailing what memory persists:

- **Hard Reset** — clears all context except immutable identity keys.
- **Soft Reset** — retains validated claims (`v`) and key decisions while flushing drafts.
- **Transfer Reset** — prepares cross-platform handoff, persisting `CRef` and `RD`.

Policies determine whether `AC` restarts at `0` or inherits the last known counter.

---

## 8. Persistent Memory & Cross-Platform Access

`CRef:<profile>@<version>` links headers to stored profiles containing alias maps, compression rules, and long-term context references. Agents use platform-specific adapters to resolve the reference:

- **iOS / Desktop / Web** — ChatGPT clients fetch from shared long-term memory vaults.
- **GhostTool** — Access via service token bridging the same memory ID.
- **WraithApp** — Locally caches profile snapshots for offline continuity.

Resolution failures must trigger a fallback to canonical field names (`HdrF`).

---

## 9. Claim Tally (v/u/s)

The tally field enforces rigorous fact tracking:

- `v` (validated) — corroborated statements with supporting evidence.
- `u` (uncertain) — hypotheses pending validation or with incomplete data.
- `s` (superseded) — claims retracted or contradicted by newer evidence.

Counters inform reasoning depth escalation and reset policies.

---

Profile Integration:
Each WraithSpec header can declare CRef:<profile>@<version> to delegate static mappings, enabling both human-readable and compressed exchange formats.
