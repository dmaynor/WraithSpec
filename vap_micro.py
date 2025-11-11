#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
WraithSpec › VAP Core — CI1 (config) & CIP2 (prompt) micro-format encoder/decoder.

This module provides:
- Deterministic parse/expand for CI1 and CIP2 micro-lines. [v ✅]
- Safe escaping/unescaping of reserved delimiters. [v ✅]
- CLI: decode/encode/inspect/validate. [v ✅]
- Pure stdlib; Python 3.8+. [v ✅]

Micro-grammar (stable)
----------------------
• Top-level segments are pipe '|' separated:  KIND|k1=v1|k2=v2|flag
• Nested pairs inside values use semicolons ';' : "k1:v1;k2:v2"
• CSV lists use ',' and '+' where noted.
• Reserved chars in values must be backslash-escaped: \| \; \, \+ \=
• KIND ∈ {"CI1", "CIP2"}

Required keys
-------------
CI1:  SID, P, HdrC, HdrF
CIP2: SID, P, CTX, TASK

License: MIT
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

# -------------------------- Declared constants --------------------------------

# Behavior map aligned to indices for B=0,1,..
BEHAVIOR_MAP: List[str] = [
    "Professional (no flattery)",
    "Precise",
    "Don’t paraphrase input",
    "Code: PEP-8 + docs + tests",
    "Inline [v/u/s] tags + tally in Full",
    "Red-team ideas & failure modes",
    "Clean closure (no promises)",
]

CI1_REQUIRED_KEYS = {"SID", "P", "HdrC", "HdrF"}
CIP2_REQUIRED_KEYS = {"SID", "P", "CTX", "TASK"}

# Escaping patterns
_ESCAPE_CHARS = r"[|\;\,\+\=]"
_ESCAPE_RE = re.compile(rf"(\\{_ESCAPE_CHARS}|{_ESCAPE_CHARS})")
_UNESCAPE_RE = re.compile(r"\\([|\;\,\+\=])")

# ----------------------------- Utilities --------------------------------------


def escape_value(raw: str) -> str:
    """
    Escape reserved delimiter characters inside a value.
    """
    if not raw:
        return raw

    def _esc(m: re.Match) -> str:
        s = m.group(0)
        return s if s.startswith("\\") else "\\" + s

    return _ESCAPE_RE.sub(_esc, raw)


def unescape_value(raw: str) -> str:
    """
    Unescape reserved characters previously escaped with backslash.
    """
    if not raw:
        return raw
    return _UNESCAPE_RE.sub(lambda m: m.group(1), raw)


def _split_topline(line: str) -> Tuple[str, List[str]]:
    if not line or "|" not in line:
        raise ValueError("Invalid micro-line: missing '|' separators")

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
            segments.append("".join(current))
            current = []
            continue
        current.append(ch)

    segments.append("".join(current))
    parts = [p for p in segments if p != ""]
    return parts[0].strip(), parts[1:]


def _kv_from_segments(segments: List[str]) -> Dict[str, str]:
    """
    Convert pipe segments into a dict. Bare flags become key=true.
    """
    out: Dict[str, str] = {}
    for seg in segments:
        if "=" in seg:
            k, v = seg.split("=", 1)
            out[k.strip()] = unescape_value(v.strip())
        else:
            out[seg.strip()] = "true"
    return out


def _require_keys(kind: str, kv: Dict[str, str]) -> None:
    if kind == "CI1":
        missing = CI1_REQUIRED_KEYS - set(kv)
    elif kind == "CIP2":
        missing = CIP2_REQUIRED_KEYS - set(kv)
    else:
        raise ValueError(f"Unsupported kind '{kind}'")
    if missing:
        raise KeyError(f"Missing required keys for {kind}: {sorted(missing)}")


def _pairs_to_dict(pairs: str) -> Dict[str, str]:
    """
    Convert semicolon pairs "k1:v1;k2:v2;flag" to dict; bare tokens => "true".
    """
    result: Dict[str, str] = {}
    if not pairs:
        return result
    for item in filter(None, (s.strip() for s in pairs.split(";"))):
        if ":" in item:
            k, v = item.split(":", 1)
            result[k.strip()] = v.strip()
        else:
            result[item] = "true"
    return result


def _csv_list(val: str) -> List[str]:
    return [x for x in (t.strip() for t in (val or "").split(",")) if x]


def _plus_list(val: str) -> List[str]:
    return [x for x in (t.strip() for t in (val or "").split("+")) if x]


def _to_int(val: str) -> int:
    try:
        return int(val)
    except ValueError:
        return 0


# -------------------------- Public dataclasses --------------------------------


@dataclass
class DecodeResult:
    kind: str
    data: Dict[str, object]

    def to_json(self) -> str:
        return json.dumps(self.data, indent=2, ensure_ascii=False)


# ----------------------------- Core API ---------------------------------------


def decode(line: str) -> DecodeResult:
    """
    Decode a CI/CIP micro-line to a structured dict. [v ✅]
    Raises ValueError/KeyError on malformed or incomplete input. [v ✅]
    """
    kind, segs = _split_topline(line)
    kv = _kv_from_segments(segs)
    _require_keys(kind, kv)

    if kind == "CI1":
        behaviors: List[str] = []
        if "B" in kv and kv["B"]:
            idxs = []
            for token in kv["B"].split(","):
                token = token.strip()
                if token.isdigit():
                    idxs.append(int(token))
            behaviors = [BEHAVIOR_MAP[i] for i in idxs if 0 <= i < len(BEHAVIOR_MAP)]

        data = {
            "Kind": "CI1",
            "Profile": kv.get("P", ""),
            "Sentinel": kv.get("SID", ""),
            "Header": {
                "Compact": kv.get("HdrC", ""),
                "Full": _pairs_to_dict(kv.get("HdrF", "")),
            },
            "Behavior": behaviors,
            "Reasoning": kv.get("Reasoning", kv.get("R", "")),
            "Ops": {
                "Modules": _csv_list(kv.get("O", "")),
                "Intent": kv.get("I", ""),
            },
            "ExternalActions": kv.get("ExtA", ""),
            "Identity": {
                "ID": kv.get("ID", ""),
                "Nick": kv.get("Nick", ""),
                "Role": kv.get("Role", ""),
                "Stack": kv.get("Stack") or kv.get("P", ""),
                "Field": _csv_list(kv.get("Field", "")),
                "Version": kv.get("Ver", ""),
            },
            "Version": kv.get("Ver", ""),
            "_raw": kv,
        }
        return DecodeResult(kind="CI1", data=data)

    if kind == "CIP2":
        req_items = _csv_list(kv.get("REQ", ""))
        data = {
            "Kind": "CIP2",
            "Profile": kv.get("P", ""),
            "Sentinel": kv.get("SID", ""),
            "Prompt": {
                "Context": kv.get("CTX", ""),
                "Task": kv.get("TASK", ""),
                "Constraints": _plus_list(kv.get("CONS", "")),
                "Tone": kv.get("TONE", ""),
                "Output": kv.get("OUT", ""),
                "Request": req_items,
                "Max": _to_int(kv.get("MAX", kv.get("max", ""))),
            },
            "_raw": kv,
        }
        return DecodeResult(kind="CIP2", data=data)

    raise ValueError(f"Unsupported kind '{kind}'")


def encode(kind: str, mapping: Dict[str, str]) -> str:
    """
    Encode a mapping to a micro-line with deterministic sorted key order. [v ✅]
    Values are auto-escaped for reserved delimiters. [v ✅]
    """
    if kind not in {"CI1", "CIP2"}:
        raise ValueError("kind must be 'CI1' or 'CIP2'")
    items = [kind]
    for k in sorted(mapping.keys()):
        v = escape_value(str(mapping[k]))
        items.append(f"{k}={v}")
    return "|".join(items)


def validate(line: str) -> Dict[str, object]:
    """
    Validate a micro-line and return a brief report. [v ✅]
    """
    report = {"ok": False, "kind": "", "missing": []}
    try:
        kind, segs = _split_topline(line)
        kv = _kv_from_segments(segs)
        try:
            _require_keys(kind, kv)
        except KeyError as e:
            missing = re.findall(r"'([^']+)'", str(e))
            report.update({"ok": False, "kind": kind, "missing": missing})
            return report
        # Decoding will raise if anything else is wrong
        _ = decode(line)
        report.update({"ok": True, "kind": kind, "missing": []})
        return report
    except Exception as exc:  # pragma: no cover
        report.update({"ok": False, "error": str(exc)})
        return report


# ------------------------------- CLI ------------------------------------------


def _build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="WraithSpec › VAP Core micro-format tools (CI1/CIP2)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("decode", help="Decode a micro-line to JSON")
    d.add_argument("line", nargs="?", help="Micro-line (reads stdin if omitted)")

    e = sub.add_parser("encode", help="Encode key=value pairs to a micro-line")
    e.add_argument("--kind", required=True, choices=["CI1", "CIP2"])
    e.add_argument(
        "--field", action="append", default=[], metavar="key=value",
        help="Add a key=value field (repeatable)"
    )

    i = sub.add_parser("inspect", help="Show required keys for a kind")
    i.add_argument("--kind", required=True, choices=["CI1", "CIP2"])

    v = sub.add_parser("validate", help="Validate a micro-line quickly")
    v.add_argument("line", help="Micro-line")

    return p


def _cli(argv=None) -> int:
    p = _build_cli()
    args = p.parse_args(argv)

    if args.cmd == "decode":
        raw = args.line or sys.stdin.read()
        obj = decode(raw.strip())
        print(obj.to_json())
        return 0

    if args.cmd == "encode":
        mapping: Dict[str, str] = {}
        for pair in args.field:
            if "=" not in pair:
                p.error(f"--field requires key=value, got: {pair}")
            k, v = pair.split("=", 1)
            mapping[k.strip()] = v.strip()
        print(encode(args.kind, mapping))
        return 0

    if args.cmd == "inspect":
        req = sorted(CI1_REQUIRED_KEYS if args.kind == "CI1" else CIP2_REQUIRED_KEYS)
        print(json.dumps({"Kind": args.kind, "Required": req}, indent=2))
        return 0

    if args.cmd == "validate":
        print(json.dumps(validate(args.line), indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(_cli())
