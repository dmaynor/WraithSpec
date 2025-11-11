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
├── specs/
│   ├── sentinel_7e99_spec.md
│   ├── alias_profile_VA-P1@1.yaml
│   ├── reset_policy_RSet@1.yaml
│   ├── mode_tracker_protocol.md
│   └── reasoning_depth_matrix.md
├── examples/
│   ├── header_prettyprint_example.md
│   ├── compressed_header_example.txt
│   └── profile_reference_example.yaml
└── CHANGELOG.md
```

> **Note:** Files not yet present in this branch are reserved for upcoming drops and will be published as the implementation matures.

## Getting Started

This repository is documentation-first. Tooling such as `vap_micro.py` remains available for reference decoding and validation of legacy CI1/CIP2 micro-formats.

### Inspect Legacy Micro-Formats

```bash
python vap_micro.py inspect --kind CI1
```

### Decode SENTINEL 7E99 Headers (Preview)

Use the examples under `examples/` as fixtures when testing cross-agent integrations. Future revisions will include command-line utilities for generating compressed headers directly from the VA-P1@1 profile.

## Spec Highlights

- Persistent header fields include `SID`, `AC` (activity counter), `RD` (reasoning depth), `MODE`, and `PHASE` with optional alias compression.
- Profiles referenced via `CRef:<profile>@<version>` expose alias dictionaries and compression policies.
- Mode tracking and reasoning depth matrices define default escalation paths for brainstorm → design → build → review loops.
- Reset policies (`RSet@1`) govern how agents clear or persist memory across sessions, including mobile and desktop continuations.
- The v/u/s tally system records validated facts (`v`), uncertain statements (`u`), and superseded or contradicted items (`s`).

## Contributing

Contributions should extend the specification while keeping backward compatibility for existing CI1/CIP2 tooling. Please open issues to discuss major protocol changes before submitting PRs.

## License

MIT
