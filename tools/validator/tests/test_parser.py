# SPDX-License-Identifier: MIT
"""Tests for the WraithSpec parser module."""

import unittest

from tools.validator.parser import (
    parse_document,
    parse_header,
    parse_sentinel_full,
    parse_sentinel_compact,
    parse_ci1,
    parse_cip2,
    ParseError,
    split_pipe_segments,
    parse_kv_pairs,
    unescape_value,
)


class TestUtilities(unittest.TestCase):
    """Test utility functions."""

    def test_unescape_value(self) -> None:
        """Test reserved character unescaping."""
        self.assertEqual(unescape_value(r"foo\|bar"), "foo|bar")
        self.assertEqual(unescape_value(r"a\;b\,c"), "a;b,c")
        self.assertEqual(unescape_value(r"key\=value"), "key=value")
        self.assertEqual(unescape_value("no escapes"), "no escapes")
        self.assertEqual(unescape_value(""), "")

    def test_split_pipe_segments(self) -> None:
        """Test pipe segment splitting."""
        self.assertEqual(
            split_pipe_segments("a|b|c"),
            ["a", "b", "c"],
        )
        self.assertEqual(
            split_pipe_segments(r"a\|b|c"),
            [r"a\|b", "c"],
        )
        self.assertEqual(
            split_pipe_segments("CI1|SID=123|P=Test"),
            ["CI1", "SID=123", "P=Test"],
        )

    def test_parse_kv_pairs(self) -> None:
        """Test key-value pair parsing."""
        segments = ["SID=7E99", "MODE=d", "flag"]
        result = parse_kv_pairs(segments, separator="=")
        self.assertEqual(result["SID"], "7E99")
        self.assertEqual(result["MODE"], "d")
        self.assertEqual(result["flag"], "true")


class TestSentinelFullFrame(unittest.TestCase):
    """Test SENTINEL full frame parsing."""

    def test_parse_basic(self) -> None:
        """Test parsing a basic full frame header."""
        content = "SENTINEL:7E99:(SID:test-123|MODE:design|PHASE:tradeoff)"
        header = parse_sentinel_full(content)

        self.assertEqual(header.kind, "SENTINEL_FULL")
        self.assertEqual(header.version, "7E99")
        self.assertEqual(header.fields["SID"], "test-123")
        self.assertEqual(header.fields["MODE"], "design")
        self.assertEqual(header.fields["PHASE"], "tradeoff")

    def test_parse_with_aliases(self) -> None:
        """Test that mode/phase aliases are normalized."""
        content = "SENTINEL:7E99:(SID:abc|MODE:d|PHASE:tr)"
        header = parse_sentinel_full(content)

        self.assertEqual(header.fields["MODE"], "design")
        self.assertEqual(header.fields["PHASE"], "tradeoff")

    def test_parse_with_claims(self) -> None:
        """Test parsing CLAIMS field."""
        content = "SENTINEL:7E99:(SID:test|MODE:d|PHASE:id|CLAIMS:v=3;u=1;s=0)"
        header = parse_sentinel_full(content)

        self.assertEqual(header.fields["CLAIMS"], {"v": 3, "u": 1, "s": 0})

    def test_invalid_format(self) -> None:
        """Test that invalid format raises ParseError."""
        with self.assertRaises(ParseError):
            parse_sentinel_full("INVALID:header")


class TestSentinelCompact(unittest.TestCase):
    """Test SENTINEL compact header parsing."""

    def test_parse_basic(self) -> None:
        """Test parsing a basic compact header."""
        content = "SID=7E99|MODE=d|PHASE=tr|AC=f|RD=3"
        header = parse_sentinel_compact(content)

        self.assertEqual(header.kind, "SENTINEL_COMPACT")
        self.assertEqual(header.fields["SID"], "7E99")
        self.assertEqual(header.fields["MODE"], "design")
        self.assertEqual(header.fields["PHASE"], "tradeoff")
        self.assertEqual(header.fields["AC"], "f")
        self.assertEqual(header.fields["RD"], "3")

    def test_parse_with_tally(self) -> None:
        """Test parsing TALLY field."""
        content = "SID=7E99|TALLY=v:3,u:1,s:0"
        header = parse_sentinel_compact(content)

        self.assertEqual(header.fields["TALLY"], {"v": 3, "u": 1, "s": 0})

    def test_invalid_missing_pipe(self) -> None:
        """Test that missing pipe raises ParseError."""
        with self.assertRaises(ParseError):
            parse_sentinel_compact("SID=7E99")


class TestCI1(unittest.TestCase):
    """Test CI1 micro-line parsing."""

    def test_parse_basic(self) -> None:
        """Test parsing a basic CI1 header."""
        content = "CI1|SID=7E96|P=Violator-Actual|HdrC=compact|HdrF=Stack:VA;Model:Claude"
        header = parse_ci1(content)

        self.assertEqual(header.kind, "CI1")
        self.assertEqual(header.fields["SID"], "7E96")
        self.assertEqual(header.fields["P"], "Violator-Actual")
        self.assertEqual(header.fields["HdrC"], "compact")
        self.assertEqual(header.fields["HdrF"]["Stack"], "VA")
        self.assertEqual(header.fields["HdrF"]["Model"], "Claude")

    def test_parse_with_behavior(self) -> None:
        """Test parsing behavior indices."""
        content = "CI1|SID=7E96|P=Test|HdrC=c|HdrF=s:v|B=0,1,2"
        header = parse_ci1(content)

        self.assertEqual(header.fields["B"], [0, 1, 2])

    def test_missing_required(self) -> None:
        """Test that missing required fields raises ParseError."""
        with self.assertRaises(ParseError) as ctx:
            parse_ci1("CI1|SID=123|P=Test")  # Missing HdrC, HdrF

        self.assertIn("HdrC", str(ctx.exception))


class TestCIP2(unittest.TestCase):
    """Test CIP2 micro-line parsing."""

    def test_parse_basic(self) -> None:
        """Test parsing a basic CIP2 header."""
        content = "CIP2|SID=7E96|P=Test|CTX=test:context|TASK=do_something"
        header = parse_cip2(content)

        self.assertEqual(header.kind, "CIP2")
        self.assertEqual(header.fields["SID"], "7E96")
        self.assertEqual(header.fields["P"], "Test")
        self.assertEqual(header.fields["CTX"], "test:context")
        self.assertEqual(header.fields["TASK"], "do_something")

    def test_parse_with_constraints(self) -> None:
        """Test parsing constraints list."""
        content = "CIP2|SID=7E96|P=Test|CTX=ctx|TASK=task|CONS=concise+accurate+traced"
        header = parse_cip2(content)

        self.assertEqual(header.fields["CONS"], ["concise", "accurate", "traced"])

    def test_parse_with_max(self) -> None:
        """Test parsing MAX field."""
        content = "CIP2|SID=7E96|P=Test|CTX=ctx|TASK=task|MAX=400"
        header = parse_cip2(content)

        self.assertEqual(header.fields["MAX"], 400)

    def test_missing_required(self) -> None:
        """Test that missing required fields raises ParseError."""
        with self.assertRaises(ParseError) as ctx:
            parse_cip2("CIP2|SID=123|P=Test")  # Missing CTX, TASK

        self.assertIn("CTX", str(ctx.exception))


class TestParseHeader(unittest.TestCase):
    """Test auto-detecting header format."""

    def test_detect_sentinel_full(self) -> None:
        """Test detection of SENTINEL full frame."""
        content = "SENTINEL:7E99:(SID:abc|MODE:d|PHASE:id)"
        header = parse_header(content)
        self.assertEqual(header.kind, "SENTINEL_FULL")

    def test_detect_ci1(self) -> None:
        """Test detection of CI1."""
        content = "CI1|SID=123|P=Test|HdrC=c|HdrF=s:v"
        header = parse_header(content)
        self.assertEqual(header.kind, "CI1")

    def test_detect_cip2(self) -> None:
        """Test detection of CIP2."""
        content = "CIP2|SID=123|P=Test|CTX=c|TASK=t"
        header = parse_header(content)
        self.assertEqual(header.kind, "CIP2")

    def test_detect_compact(self) -> None:
        """Test detection of compact header."""
        content = "SID=7E99|MODE=d"
        header = parse_header(content)
        self.assertEqual(header.kind, "SENTINEL_COMPACT")

    def test_empty_raises(self) -> None:
        """Test that empty content raises ParseError."""
        with self.assertRaises(ParseError):
            parse_header("")

    def test_unknown_raises(self) -> None:
        """Test that unknown format raises ParseError."""
        with self.assertRaises(ParseError):
            parse_header("random text without structure")


class TestParseDocument(unittest.TestCase):
    """Test full document parsing."""

    def test_parse_with_header(self) -> None:
        """Test parsing document with header."""
        content = """SENTINEL:7E99:(SID:test|MODE:d|PHASE:tr)

## Overview

This is the overview section.
"""
        doc = parse_document(content)

        self.assertIsNotNone(doc.header)
        self.assertEqual(doc.header.kind, "SENTINEL_FULL")
        self.assertEqual(len(doc.sections), 1)
        self.assertEqual(doc.sections[0].name, "Overview")

    def test_parse_with_directives(self) -> None:
        """Test parsing document with directive block."""
        content = """---
version: 0.1
profile: VA-P1
---

SENTINEL:7E99:(SID:test|MODE:d|PHASE:tr)
"""
        doc = parse_document(content)

        self.assertEqual(doc.directives["version"], "0.1")
        self.assertEqual(doc.directives["profile"], "VA-P1")

    def test_parse_with_capabilities(self) -> None:
        """Test parsing document with capability declarations."""
        content = """SENTINEL:7E99:(SID:test|MODE:d|PHASE:tr)

CAPABILITY: memory_access(persistent=true, scope=session)
CAPABILITY: code_execution
"""
        doc = parse_document(content)

        self.assertEqual(len(doc.capabilities), 2)
        self.assertEqual(doc.capabilities[0].name, "memory_access")
        self.assertEqual(doc.capabilities[0].params["persistent"], "true")
        self.assertEqual(doc.capabilities[1].name, "code_execution")


if __name__ == "__main__":
    unittest.main()
