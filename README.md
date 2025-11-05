# WraithSpec › VAP Core (CI1 & CIP2)

**VAP Core** defines compact, reversible micro-formats for AI↔human communications:
- **CI1** — configuration micro-format (headers, behavior, ops, identity). [v ✅]
- **CIP2** — prompt micro-format with a **reasoning-response contract** (`REQ=Trace,Ledger,Decision,Critique`). [v ✅]

This repo contains a reference implementation (`vap_micro.py`) and tests.

## Install & Run
```bash
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -U pip
# No deps required
python vap_micro.py inspect --kind CI1
```

## Quick Start

### Decode (CI1)
```bash
python vap_micro.py decode "CI1|SID=7E96|P=Violator-Actual|HdrC=SENTINEL:7E96:(<UUID>|Violator-Actual|<UTC>|i:[<i>]|2i:[<2i>]|T:<#>|S:<#>)|HdrF=Stack:Violator-Actual;Ts:<UTC>;Model:GPT-5;SENTINEL:7E96"
```

### Decode (CIP2)
```bash
python vap_micro.py decode "CIP2|SID=7E96|P=Violator-Actual|CTX=GhostInTheShellSAC|TASK=analyze_outfit_symbolism|CONS=concise+accurate+traced|TONE=analytical|OUT=essay+trace|REQ=Trace,Ledger,Decision,Critique|MAX=400"
```

### Encode
```bash
python vap_micro.py encode --kind CIP2 \
  --field SID=7E96 --field P="Violator-Actual" \
  --field CTX=GhostInTheShellSAC --field TASK=explain_meaning \
  --field CONS=concise+accurate+traced --field TONE=analytical \
  --field OUT=essay+trace --field REQ=Trace,Ledger,Decision,Critique --field MAX=400
```

### Validate
```bash
python vap_micro.py validate "CIP2|SID=7E96|P=Violator-Actual|TASK=explain"
```

## Grammar (ABNF-like)
```
micro      = kind "|" kv *( "|" kv / "|" flag )
kind       = "CI1" / "CIP2"
kv         = key "=" value
flag       = key
key        = 1*( ALPHA / DIGIT / "_" )
value      = *escapedchar
escapedchar= "\" ( "|" / ";" / "," / "+" / "=" ) / VCHAR
```

Escaping: values must escape reserved delimiters with backslash (\| \; \, \+ \=). [v ✅]

## Required Keys
- CI1: SID, P, HdrC, HdrF
- CIP2: SID, P, CTX, TASK

## Why CIP2?

CIP2 adds an explicit response contract via `REQ=` so answers include:
- REASONING TRACE (Goal → Inputs → Steps → Tests → Outcome)
- CLAIM LEDGER with [v ✅]/[u ❓]/[s ❌]
- DECISION RECORD (options + winner rationale)
- CRITIQUE (failure modes + mitigations)

This turns prompts into auditable artifacts. [v ✅]

## Testing
```bash
python -m unittest -v
```

## License

MIT

---

### `pyproject.toml` (optional, for packaging/lint)
```toml
[project]
name = "wraithspec-vap"
version = "0.1.0"
description = "WraithSpec › VAP Core micro-formats (CI1 & CIP2) reference implementation"
readme = "README.md"
requires-python = ">=3.8"
dependencies = []

[project.scripts]
vap-micro = "vap_micro:_cli"
```

Notes
- Escaping/unescaping ensures lossless transport through headers, env vars, and logs. [v ✅]
- Deterministic key ordering in encode() improves diffs and reproducibility. [v ✅]
- Tests cover round-trip, required-key validation, and escaping edge cases. [v ✅]

If you want JS/Go adapters next, I’ll mirror the same grammar and conformance vectors.
